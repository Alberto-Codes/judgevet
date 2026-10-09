"""Prove the stop-check recipe in examples/agent-hooks (#314).

`stop_state.py` turns Stop and SubagentStop hook input into a state with the
last user request and the final assistant message. Its output pipes into
`shadow_judge.py`. No test calls a model; the transcript fixture is synthetic.
Source: https://code.claude.com/docs/en/hooks.
"""

import asyncio
import importlib.util
import io
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from judgevet.adapters.inbound.cli import parse_questions
from judgevet.domain.questions import Noul
from tests.fixtures.providers import shadow_provider, stop_provider

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "agent-hooks"
HOOKS = ROOT / "tests" / "fixtures" / "agent_hooks"
QUESTION = EXAMPLES / "stop_question.json"
TRANSCRIPT = HOOKS / "stop_transcript.jsonl"
CASES = HOOKS / "stop_cases.jsonl"
PROVIDER = "tests.fixtures.providers.shadow_provider"
STOP_PROVIDER = "tests.fixtures.providers.stop_provider"
REQUEST = "Add a --dry-run flag to the export command and document it in the README."
FALLBACK = "Added --dry-run to export and a README section that shows it."


def _load(name: str) -> ModuleType:
    """Import one example script from its path."""
    spec = importlib.util.spec_from_file_location(name, EXAMPLES / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _hook(transcript: Path | str, **extra: Any) -> str:
    """Build Stop hook input that points at a transcript."""
    hook = json.loads((HOOKS / "stop.json").read_text(encoding="utf-8"))
    hook["transcript_path"] = str(transcript)
    hook.update(extra)
    return json.dumps(hook)


def _state(stdin: str, *argv: str) -> tuple[int, str]:
    """Run stop_state.py in-process and return its status and stdout."""
    out = io.StringIO()
    code = _load("stop_state").main(list(argv), io.StringIO(stdin), out)
    return code, out.getvalue()


def _rows() -> list[dict[str, Any]]:
    """Read every labelled case."""
    lines = CASES.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def test_question_parses_as_one_noul_with_both_criteria() -> None:
    questions = parse_questions(QUESTION.read_text(encoding="utf-8"))
    assert list(questions) == ["done"]
    question = questions["done"]
    assert isinstance(question, Noul)
    assert question.instructions == (
        "The request in this transcript excerpt is fully completed, with no "
        "step the assistant said it would do still undone."
    )
    assert question.criteria is not None
    assert set(question.criteria) == {"true", "false"}


def test_state_holds_last_human_request_and_hook_message() -> None:
    code, out = _state(_hook(TRANSCRIPT))
    assert code == 0
    state = json.loads(out)
    assert state["last_user_request"] == REQUEST
    assert state["final_assistant_message"] == (
        "I've completed the refactoring and all tests pass."
    )
    assert state["hook_event_name"] == "Stop"
    assert state["session_id"] == "session-stop"


def test_state_falls_back_to_transcript_assistant_text() -> None:
    code, out = _state(_hook(TRANSCRIPT, last_assistant_message=None))
    assert code == 0
    assert json.loads(out)["final_assistant_message"] == FALLBACK


def test_subagent_stop_reads_the_agent_transcript() -> None:
    hook = json.loads((HOOKS / "stop_subagent.json").read_text(encoding="utf-8"))
    hook["agent_transcript_path"] = str(TRANSCRIPT)
    code, out = _state(json.dumps(hook))
    assert code == 0
    state = json.loads(out)
    assert state["last_user_request"] == REQUEST
    assert state["final_assistant_message"] == "Found three call sites of read_config."
    assert state["hook_event_name"] == "SubagentStop"


@pytest.mark.parametrize("path", ["/nonexistent/stop-314.jsonl", "", None])
def test_missing_transcript_keeps_the_hook_message(path: str | None) -> None:
    code, out = _state(
        _hook(path) if path is not None else _hook("x", transcript_path=None)
    )
    assert code == 0
    state = json.loads(out)
    assert state["last_user_request"] is None
    assert state["final_assistant_message"].startswith("I've completed")


def test_unreadable_transcript_keeps_the_hook_message(tmp_path: Path) -> None:
    code, out = _state(_hook(tmp_path))
    assert code == 0
    assert json.loads(out)["last_user_request"] is None


@pytest.mark.parametrize("stdin", ["", "{broken", "[1, 2]"])
def test_bad_hook_input_exits_one_with_empty_stdout(stdin: str) -> None:
    assert _state(stdin) == (1, "")


@pytest.mark.parametrize("argv", [["--max-chars", "many"], ["--unknown"], ["--help"]])
def test_arguments_never_exit_two_or_print(argv: list[str]) -> None:
    code, out = _state(_hook(TRANSCRIPT), *argv)
    assert code in (0, 1)
    assert out == ""


def test_each_message_is_cut_to_the_budget() -> None:
    long_message = "Summary line. " + "x" * 500 + " Next I will run the tests."
    code, out = _state(
        _hook(TRANSCRIPT, last_assistant_message=long_message), "--max-chars", "40"
    )
    assert code == 0
    state = json.loads(out)
    assert state["last_user_request"] == REQUEST[:40]
    assert len(state["final_assistant_message"]) == 40
    assert state["final_assistant_message"].endswith("Next I will run the tests.")


def test_control_characters_are_removed_before_the_budget() -> None:
    noisy = "\x1b[31mred\x1b[0m\tdone\n" + "\x00\x07" * 300 + "end"
    code, out = _state(
        _hook(TRANSCRIPT, last_assistant_message=noisy), "--max-chars", "40"
    )
    assert code == 0
    assert json.loads(out)["final_assistant_message"] == "[31mred[0m\tdone\nend"


def test_in_process_pipe_sends_both_messages_to_the_provider(tmp_path: Path) -> None:
    code, out = _state(_hook(TRANSCRIPT))
    assert code == 0
    shadow_provider.CALLS.clear()
    log = tmp_path / "stop.jsonl"
    argv = ["--provider", f"{PROVIDER}:answering", "--model", "jev-test"]
    argv += ["--question", str(QUESTION), "--log", str(log)]
    argv += ["--state-field", "last_user_request"]
    argv += ["--state-field", "final_assistant_message"]
    assert _load("shadow_judge").main(argv, io.StringIO(out)) == 0
    (call,) = shadow_provider.CALLS
    state = json.loads(call[0])
    assert state == {
        "last_user_request": REQUEST,
        "final_assistant_message": "I've completed the refactoring and all tests pass.",
    }
    (record,) = [json.loads(line) for line in log.read_text().splitlines()]
    assert record["hook_event"] == "Stop"
    assert record["question_keys"] == ["done"]
    assert "done" in record["answers"]
    assert REQUEST not in log.read_text()


@pytest.mark.e2e
@pytest.mark.parametrize(
    ("transcript", "expected"),
    [(str(TRANSCRIPT), REQUEST), ("/nonexistent/stop-314.jsonl", None)],
)
def test_shell_pipe_sends_the_request_and_stays_silent(
    tmp_path: Path, transcript: str, expected: str | None
) -> None:
    log = tmp_path / "stop.jsonl"
    sent = tmp_path / "states.jsonl"
    command = (
        f'"{sys.executable}" "{EXAMPLES / "stop_state.py"}" | '
        f'"{sys.executable}" "{EXAMPLES / "shadow_judge.py"}" '
        f'--provider {STOP_PROVIDER}:recording --question "{QUESTION}" '
        "--state-field last_user_request --state-field final_assistant_message "
        f'--log "{log}"'
    )
    env = {"PATH": os.defpath, "PYTHONPATH": str(ROOT), "HOME": str(tmp_path)}
    env[stop_provider.STATE_FILE_ENV] = str(sent)
    code, stdout = asyncio.run(_shell(command, _hook(transcript), tmp_path, env))
    assert code == 0
    assert stdout == b""
    (state,) = [json.loads(line) for line in sent.read_text().splitlines()]
    assert state.get("last_user_request") == expected
    assert state["final_assistant_message"].startswith("I've completed")
    (record,) = [json.loads(line) for line in log.read_text().splitlines()]
    assert record["hook_event"] == "Stop"
    assert "error" not in record
    assert record["answers"]["done"]["noul"] == 0.9


async def _shell(
    command: str, stdin: str, cwd: Path, env: dict[str, str]
) -> tuple[int, bytes]:
    """Run a shell pipeline with hook input on stdin and a bounded runtime."""
    child = await asyncio.create_subprocess_shell(
        command,
        cwd=cwd,
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, _ = await asyncio.wait_for(child.communicate(stdin.encode()), 60)
    finally:
        if child.returncode is None:
            child.kill()
            await child.wait()
    assert child.returncode is not None
    return child.returncode, stdout


def test_cases_are_labelled_and_balanced() -> None:
    rows = _rows()
    keys = {"id", "label", "hard", "last_user_request", "final_assistant_message"}
    for row in rows:
        assert set(row) == keys
        assert isinstance(row["label"], bool)
        assert isinstance(row["hard"], bool)
        assert row["last_user_request"].strip()
        assert row["final_assistant_message"].strip()
    assert len({row["id"] for row in rows}) == len(rows) == 20
    assert [row["label"] for row in rows].count(True) == 10
    assert sum(row["hard"] for row in rows) >= 3


def test_measure_reports_rates_and_latency(capsys: pytest.CaptureFixture[str]) -> None:
    argv = ["--provider", f"{PROVIDER}:answering", "--cases", str(CASES)]
    assert _load("measure_stop").main(argv) == 0
    out = capsys.readouterr().out
    assert "| 0.5 |" in out
    assert "| 0.8 |" in out
    assert "latency s: p50" in out
    assert out.count("| done-") + out.count("| open-") >= 20
