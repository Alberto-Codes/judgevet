"""Prove the shadow-mode hook runner in examples/agent-hooks (#309).

The runner reads Claude Code hook input on stdin, asks the selected provider,
appends one JSONL record and always exits 0 with empty stdout.
Source: https://code.claude.com/docs/en/hooks.
"""

import asyncio
import importlib.util
import io
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.fixtures.providers import shadow_provider

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "examples" / "agent-hooks" / "shadow_judge.py"
HOOKS = ROOT / "tests" / "fixtures" / "agent_hooks"
QUESTIONS = HOOKS / "questions.json"
PROVIDER = "tests.fixtures.providers.shadow_provider"
CANARY = "sk-shadow-canary-309-do-not-log"


def _load() -> ModuleType:
    """Import the example script from its path."""
    spec = importlib.util.spec_from_file_location("shadow_judge", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(
    tmp_path: Path, stdin: str, factory: str = "answering", *extra: str
) -> tuple[int, list[dict[str, Any]]]:
    """Run the script in-process and return its status and log records."""
    log = tmp_path / "shadow.jsonl"
    argv = [
        "--provider",
        f"{PROVIDER}:{factory}",
        "--model",
        "jev-test",
        "--question",
        str(QUESTIONS),
        "--log",
        str(log),
        *extra,
    ]
    code = _load().main(argv, io.StringIO(stdin))
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return code, [json.loads(line) for line in lines]


async def _spawn(
    command: list[str], stdin: str, cwd: Path, env: dict[str, str]
) -> tuple[int, bytes, bytes]:
    """Run one child with hook input on stdin and a bounded runtime."""
    child = await asyncio.create_subprocess_exec(
        *command,
        cwd=cwd,
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(child.communicate(stdin.encode()), 60)
    finally:
        if child.returncode is None:
            child.kill()
            await child.wait()
    assert child.returncode is not None
    return child.returncode, stdout, stderr


def _hook(name: str) -> str:
    """Read one recorded hook-input fixture."""
    return (HOOKS / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("fixture", "event", "tool", "session"),
    [
        ("pre_tool_use_bash.json", "PreToolUse", "Bash", "session-pre-bash"),
        (
            "post_tool_use_webfetch.json",
            "PostToolUse",
            "WebFetch",
            "session-post-webfetch",
        ),
        ("stop.json", "Stop", None, "session-stop"),
    ],
)
def test_record_carries_hook_identity_and_answers(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    fixture: str,
    event: str,
    tool: str | None,
    session: str,
) -> None:
    """A successful run appends one record and prints nothing."""
    code, records = _run(tmp_path, _hook(fixture))
    assert code == 0
    assert capsys.readouterr().out == ""
    assert len(records) == 1
    record = records[0]
    assert record["hook_event"] == event
    assert record["tool_name"] == tool
    assert record["session_id"] == session
    assert record["question_keys"] == ["risky", "category"]
    assert record["model"] == "jev-test"
    assert record["answers"]["risky"] == {"name": "risky", "type": "noul", "noul": 0.2}
    assert record["answers"]["category"]["type"] == "choice"
    assert record["answers"]["category"]["choice"] in {"read", "write"}
    assert isinstance(record["latency_ms"], int)
    assert record["latency_ms"] >= 0
    assert "error" not in record
    stamp = datetime.fromisoformat(record["timestamp"])
    assert stamp.utcoffset() == timedelta(0)


def test_state_fields_select_and_truncate(tmp_path: Path) -> None:
    """Dotted state fields build the state, and the budget truncates it."""
    shadow_provider.CALLS.clear()
    hook = _hook("pre_tool_use_bash.json")
    fields = ["--state-field", "tool_input.command", "--state-field", "tool_name"]
    _run(tmp_path, hook, "answering", *fields)
    state = shadow_provider.CALLS[-1][0]
    assert json.loads(state) == {
        "tool_input.command": "rm -rf build/",
        "tool_name": "Bash",
    }
    assert "transcript" not in state
    _run(tmp_path, hook, "answering", *fields, "--max-state-chars", "12")
    assert len(shadow_provider.CALLS[-1][0]) == 12


def test_timeout_fails_open(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A provider slower than the timeout yields an error record and exit 0."""
    hook = _hook("pre_tool_use_bash.json")
    code, records = _run(tmp_path, hook, "slow", "--timeout", "0.1")
    assert code == 0
    assert capsys.readouterr().out == ""
    assert records[0]["error"] == "TimeoutError"
    assert records[0]["answers"] is None
    assert records[0]["latency_ms"] < shadow_provider.DELAY_SECONDS * 1000


def test_provider_error_fails_open(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A provider error yields an error record with the type only."""
    code, records = _run(tmp_path, _hook("stop.json"), "failing")
    assert code == 0
    assert capsys.readouterr().out == ""
    assert records[0]["error"] == "ProviderTransportError"
    assert records[0]["answers"] is None
    assert records[0]["hook_event"] == "Stop"


@pytest.mark.parametrize("stdin", ["{not json", "[1, 2]", ""])
def test_malformed_stdin_fails_open(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stdin: str
) -> None:
    """Unreadable hook input yields an error record and exit 0."""
    code, records = _run(tmp_path, stdin)
    assert code == 0
    assert capsys.readouterr().out == ""
    assert len(records) == 1
    assert records[0]["error"] in {"JSONDecodeError", "TypeError"}
    assert records[0]["hook_event"] is None


def test_invalid_question_file_fails_open(tmp_path: Path) -> None:
    """A question file the CLI grammar rejects yields an error record."""
    bad = tmp_path / "questions.json"
    bad.write_text('{"q": {"type": "unknown"}}', encoding="utf-8")
    log = tmp_path / "shadow.jsonl"
    argv = ["--provider", f"{PROVIDER}:answering", "--question", str(bad)]
    hook = io.StringIO(_hook("stop.json"))
    assert _load().main([*argv, "--log", str(log)], hook) == 0
    record = json.loads(log.read_text(encoding="utf-8"))
    assert record["error"] == "InputFailure"


@pytest.mark.parametrize("argv", [["--bogus"], ["--timeout", "soon"]])
def test_bad_arguments_write_usage_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
) -> None:
    """Bad arguments exit 0 and write a UsageError record to the default log."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    assert _load().main(argv, io.StringIO("{}")) == 0
    assert capsys.readouterr().out == ""
    log = tmp_path / "state" / "judgevet" / "shadow.jsonl"
    record = json.loads(log.read_text(encoding="utf-8"))
    assert record["error"] == "UsageError"
    assert datetime.fromisoformat(record["timestamp"]).utcoffset() == timedelta(0)


def test_usage_record_write_failure_still_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unwritable default log does not change the exit status."""
    blocker = tmp_path / "state"
    blocker.write_text("not a directory", encoding="utf-8")
    monkeypatch.setenv("XDG_STATE_HOME", str(blocker))
    assert _load().main(["--bogus"], io.StringIO("{}")) == 0
    assert blocker.read_text(encoding="utf-8") == "not a directory"


def test_secrets_never_reach_the_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Credentials in the environment, input and error message stay out."""
    monkeypatch.setenv("TYPESAFE_API_KEY", CANARY)
    monkeypatch.setenv(shadow_provider.CREDENTIAL_ENV, CANARY)
    with pytest.raises(Exception, match=CANARY), shadow_provider.failing() as port:
        port.system_one("state", {}, "jev-test")
    hook = json.loads(_hook("pre_tool_use_bash.json"))
    hook["tool_input"]["command"] = f"curl -H 'x-api-key: {CANARY}' example.com"
    _run(tmp_path, json.dumps(hook), "failing")
    _run(tmp_path, json.dumps(hook), "answering")
    text = (tmp_path / "shadow.jsonl").read_text(encoding="utf-8")
    assert len(text.splitlines()) == 2
    assert CANARY not in text


def test_default_log_path_follows_xdg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The default log uses XDG_STATE_HOME, then ~/.local/state."""
    module = _load()
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    assert module.default_log_path() == tmp_path / "state/judgevet/shadow.jsonl"
    monkeypatch.delenv("XDG_STATE_HOME")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    expected = tmp_path / "home/.local/state/judgevet/shadow.jsonl"
    assert module.default_log_path() == expected


@pytest.mark.e2e
def test_subprocess_run_logs_and_stays_silent(tmp_path: Path) -> None:
    """The script run as a hook command exits 0, prints nothing and logs."""
    env = {
        "PATH": os.defpath,
        "PYTHONPATH": str(ROOT),
        "XDG_STATE_HOME": str(tmp_path / "state"),
        "HOME": str(tmp_path / "home"),
        shadow_provider.CREDENTIAL_ENV: CANARY,
    }
    runs = [
        ("post_tool_use_webfetch.json", "failing"),
        ("pre_tool_use_bash.json", "answering"),
    ]
    for name, factory in runs:
        command = [sys.executable, str(SCRIPT), "--provider", f"{PROVIDER}:{factory}"]
        command += ["--question", str(QUESTIONS)]
        code, stdout, stderr = asyncio.run(_spawn(command, _hook(name), tmp_path, env))
        assert code == 0
        assert stdout == b""
        assert CANARY.encode() not in stderr
    log = tmp_path / "state" / "judgevet" / "shadow.jsonl"
    text = log.read_text(encoding="utf-8")
    records = [json.loads(line) for line in text.splitlines()]
    assert [r.get("error") for r in records] == ["ProviderTransportError", None]
    assert records[1]["answers"]["risky"]["noul"] == 0.2
    assert CANARY not in text


@pytest.mark.parametrize(
    ("spec", "error"),
    [
        ("no_such_module_309:factory", "ModuleNotFoundError"),
        (f"{PROVIDER}:missing", "AttributeError"),
        (f"{PROVIDER}:CREDENTIAL_ENV", "TypeError"),
        (PROVIDER, "ValueError"),
    ],
)
def test_bad_provider_fails_open(tmp_path: Path, spec: str, error: str) -> None:
    """A bad --provider value yields an error record and exit 0."""
    log = tmp_path / "shadow.jsonl"
    argv = ["--provider", spec, "--question", str(QUESTIONS), "--log", str(log)]
    assert _load().main(argv, io.StringIO(_hook("stop.json"))) == 0
    assert json.loads(log.read_text(encoding="utf-8"))["error"] == error


def test_provider_exit_maps_to_one(tmp_path: Path) -> None:
    """A provider that exits 2 cannot block: the status becomes 1."""
    code, records = _run(tmp_path, _hook("pre_tool_use_bash.json"), "exiting")
    assert code == 1
    assert records[0]["error"] == "SystemExit"


@pytest.mark.parametrize(
    ("factory", "kind"), [("broken", RuntimeError), ("confused", AttributeError)]
)
def test_unexpected_error_propagates_without_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    factory: str,
    kind: type[Exception],
) -> None:
    """A provider bug outside the known families propagates and logs nothing."""
    monkeypatch.setenv(shadow_provider.CREDENTIAL_ENV, CANARY)
    with pytest.raises(kind, match=CANARY):
        _run(tmp_path, _hook("pre_tool_use_bash.json"), factory)
    log = tmp_path / "shadow.jsonl"
    assert not log.exists() or CANARY not in log.read_text(encoding="utf-8")


@pytest.mark.e2e
@pytest.mark.parametrize(
    ("factory", "line"),
    [
        ("broken", b"unexpected RuntimeError"),
        ("confused", b"unexpected AttributeError"),
        ("exiting", b""),
    ],
)
def test_subprocess_unexpected_error_never_blocks(
    tmp_path: Path, factory: str, line: bytes
) -> None:
    """An unexpected error exits 1, never 2, with no secret on any stream."""
    env = {
        "PATH": os.defpath,
        "PYTHONPATH": str(ROOT),
        "XDG_STATE_HOME": str(tmp_path / "state"),
        "HOME": str(tmp_path / "home"),
        shadow_provider.CREDENTIAL_ENV: CANARY,
    }
    command = [sys.executable, str(SCRIPT), "--provider", f"{PROVIDER}:{factory}"]
    command += ["--question", str(QUESTIONS)]
    code, stdout, stderr = asyncio.run(
        _spawn(command, _hook("pre_tool_use_bash.json"), tmp_path, env)
    )
    assert code == 1
    assert code != 2
    assert stdout == b""
    assert line in stderr
    assert CANARY.encode() not in stderr
    log = tmp_path / "state" / "judgevet" / "shadow.jsonl"
    assert not log.exists() or CANARY not in log.read_text(encoding="utf-8")
