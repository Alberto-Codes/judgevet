"""Prove the commit-type shadow check in examples/agent-hooks (#313).

The questions file must parse with the CLI question grammar, and its type
labels must equal the commit gate's closed vocabulary, so the two cannot
drift. The commit-msg wrapper must build the state from the message file and
the staged diff stat, and it must exit 0 whatever happens. No test here calls
a model.
"""

import asyncio
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from judgevet.adapters.inbound.cli import parse_questions
from judgevet.domain.questions import Choice
from scripts.check_commit_msg import TYPES
from tests.fixtures.providers import commit_provider, shadow_provider

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / "examples" / "agent-hooks"
QUESTIONS = HOOKS / "commit_questions.json"
WRAPPER = HOOKS / "commit_shadow.py"
MEASURE = HOOKS / "measure_commit_types.py"
PROVIDER = "tests.fixtures.providers.shadow_provider"
STAT = " src/judgevet/cli.py | 4 ++--\n 1 file changed, 2 insertions(+), 2 deletions(-)"
MESSAGE = """feat(cli): add a --quiet flag

The flag silences the summary line.

Closes #12
Generated-By: some-model (local, via pi)
# Please enter the commit message for your changes.
# --- >8 ---
diff --git a/x b/x
"""


def _load(path: Path, name: str) -> ModuleType:
    """Import an example script from its path."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(tmp_path: Path, factory: str, message: str | None) -> tuple[int, Path]:
    """Run the wrapper in-process with a stubbed diff stat."""
    log = tmp_path / "commit.jsonl"
    path = tmp_path / "COMMIT_EDITMSG"
    if message is not None:
        path.write_text(message, encoding="utf-8")
    module = _load(WRAPPER, "commit_shadow")
    argv = [
        "--provider",
        f"{PROVIDER}:{factory}",
        "--model",
        "jev-test",
        "--question",
        str(QUESTIONS),
        "--log",
        str(log),
        str(path),
    ]
    return module.main(argv, staged_stat=lambda: STAT), log


async def _spawn(
    command: list[str], cwd: Path, env: dict[str, str]
) -> tuple[int, bytes, bytes]:
    """Run one child with a bounded runtime; return status, stdout and stderr."""
    child = await asyncio.create_subprocess_exec(
        *command,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(child.communicate(), 60)
    finally:
        if child.returncode is None:
            child.kill()
            await child.wait()
    assert child.returncode is not None
    return child.returncode, stdout, stderr


def _records(log: Path) -> list[dict[str, Any]]:
    """Read the JSON Lines records of a log."""
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return [json.loads(line) for line in lines]


def test_questions_parse_and_type_labels_equal_the_gate_vocabulary() -> None:
    """Both questions parse as Choices; the type labels are exactly `TYPES`."""
    questions = parse_questions(QUESTIONS.read_text(encoding="utf-8"))

    assert list(questions) == ["type", "closes"]
    kind, closes = questions["type"], questions["closes"]
    assert isinstance(kind, Choice)
    assert isinstance(closes, Choice)
    assert tuple(kind.criteria) == TYPES
    assert list(closes.criteria) == ["closes", "refs"]
    assert closes.instructions == "Does this commit finish the issue it names?"
    for question in (kind, closes):
        for description in question.criteria.values():
            assert len(str(description).split()) >= 8


def test_wrapper_builds_the_state_from_the_message_and_the_diff_stat(
    tmp_path: Path,
) -> None:
    """The state holds subject, body and diff stat, without the author's labels."""
    shadow_provider.CALLS.clear()

    code, log = _run(tmp_path, "answering", MESSAGE)

    assert code == 0
    assert json.loads(shadow_provider.CALLS[-1][0]) == {
        "subject": "cli: add a --quiet flag",
        "body": (
            "The flag silences the summary line.\n\n"
            "Issue: #12\nGenerated-By: some-model (local, via pi)"
        ),
        "diff_stat": STAT,
    }
    (record,) = _records(log)
    assert record["hook_event"] == "commit-msg"
    assert record["question_keys"] == ["type", "closes"]
    assert "error" not in record


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        ("failing", MESSAGE),
        ("broken", MESSAGE),
        ("exiting", MESSAGE),
        ("answering", None),
    ],
)
def test_wrapper_exits_zero_on_every_failure(
    tmp_path: Path, factory: str, message: str | None
) -> None:
    """A provider error, a provider bug, a provider exit or no message file exits 0."""
    code, _ = _run(tmp_path, factory, message)

    assert code == 0


def test_wrapper_process_exits_zero_on_a_bad_provider(tmp_path: Path) -> None:
    """The script as a process exits 0 when the provider module does not exist."""
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text("fix: repair a thing\n", encoding="utf-8")
    env = {**os.environ, "XDG_STATE_HOME": str(tmp_path), "PYTHONPATH": str(ROOT)}
    command = [sys.executable, str(WRAPPER), "--provider", "nowhere:make"]
    command += ["--question", str(QUESTIONS), str(message)]

    code, stdout, _ = asyncio.run(_spawn(command, tmp_path, env))

    assert code == 0
    assert stdout == b""
    (record,) = _records(tmp_path / "judgevet" / "shadow.jsonl")
    assert record["error"] == "ModuleNotFoundError"


def test_wrapper_process_reports_an_unexpected_error_by_type_only(
    tmp_path: Path,
) -> None:
    """An error outside the expected list exits 0 and leaves a type-only trace."""
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text("fix: repair a thing\n", encoding="utf-8")
    log = tmp_path / "commit.jsonl"
    env = {**os.environ, "XDG_STATE_HOME": str(tmp_path), "PYTHONPATH": str(ROOT)}
    command = [sys.executable, str(WRAPPER), "--provider"]
    command += ["tests.fixtures.providers.commit_provider:dividing"]
    command += ["--question", str(QUESTIONS), "--log", str(log), str(message)]

    code, stdout, stderr = asyncio.run(_spawn(command, tmp_path, env))

    assert code == 0
    assert stdout == b""
    assert stderr.decode().strip() == "commit_shadow: unexpected ZeroDivisionError"
    assert commit_provider.CANARY.encode() not in stderr
    assert commit_provider.CANARY not in log.read_text(encoding="utf-8")
    (record,) = _records(log)
    assert record["error"] == "ZeroDivisionError"
    assert record["hook_event"] == "commit-msg"
    assert record["question_keys"] == ["type", "closes"]


def test_measure_reads_the_written_type_and_issue_verdict() -> None:
    """The measurement takes labels from the subject and the footer only."""
    measure = _load(MEASURE, "measure_commit_types")

    assert measure.written_labels("feat(cli): add\n\nbody\n\nCloses #3") == (
        "feat",
        "closes",
    )
    assert measure.written_labels("docs!: say\n\nRefs #4, #5") == ("docs", "refs")
    assert measure.written_labels("chore: tidy\n\nmentions Closes #3 inline") == (
        "chore",
        None,
    )
    assert measure.written_labels("Update README") == (None, None)
    assert measure.eligible("chore(main): release 0.18.1", 1) is False
    assert measure.eligible("feat: add", 2) is False
    assert measure.eligible("fix: repair", 1) is True
