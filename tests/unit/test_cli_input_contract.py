"""Exercise source resolution and its parser boundary directly.

Examples:
    ```bash
    uv run pytest tests/unit/test_cli_input_contract.py
    ```

See Also:
    - [judgevet.adapters.inbound.cli_inputs][]: Input source resolver.
"""

import io
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from judgevet.adapters.inbound.cli import app, parse_questions
from judgevet.adapters.inbound.cli_inputs import InputFailure, resolve_inputs
from tests.cli_process_support import QUESTIONS

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("source", ["file", "stdin", "positional"])
def test_resolved_strings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    """Preserve exact content while validating questions through the real parser."""
    text = "héllo\r\n"
    questions = json.dumps(QUESTIONS)
    qpath = tmp_path / "q.json"
    qpath.write_text(questions, encoding="utf-8")
    statepath = tmp_path / "state.txt"
    statepath.write_bytes(text.encode())
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(text.encode())))
    state = text if source == "positional" else None
    files = (
        [] if source == "positional" else ["-" if source == "stdin" else str(statepath)]
    )
    assert resolve_inputs(state, None, files, [str(qpath)], parse_questions) == (
        text,
        questions,
    )
    assert resolve_inputs("", questions, [], [], parse_questions) == ("", questions)


@pytest.mark.parametrize(
    "state,questions,states,question_files",
    [
        (None, "{}", ["-", "-"], []),
        ("state", None, [], ["absent", "absent"]),
        ("state", None, ["-"], ["absent"]),
        ("state", "{}", [], ["absent"]),
        (None, None, [], ["absent"]),
        (None, None, ["-"], []),
    ],
)
def test_selection_before_io(
    state: str | None,
    questions: str | None,
    states: list[str],
    question_files: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source usage errors precede even a closed stdin read or nonexistent path."""
    stream = io.TextIOWrapper(io.BytesIO())
    stream.close()
    monkeypatch.setattr("sys.stdin", stream)
    with pytest.raises(InputFailure) as caught:
        resolve_inputs(state, questions, states, question_files, parse_questions)
    assert caught.value.code == 2


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b" ",
        b"[]",
        b"{}",
        b'{"q":null}',
        b'{"":{"type":"noul"}}',
        b'{"q":{"type":[]}}',
        b'{"q":{"type":"choice","criteria":null}}',
        b'{"q":{"type":"noul"},"q":{"type":"noul"}}',
        b'{"private',
        b"\xff",
    ],
)
def test_question_failures(tmp_path: Path, content: bytes) -> None:
    """Report file validation errors with stable codes and sanitized context."""
    path = tmp_path / "private"
    path.write_bytes(content)
    with pytest.raises(InputFailure) as caught:
        resolve_inputs("state", None, [], [str(path)], parse_questions)
    assert caught.value.code == 1
    assert "--questions-file" in str(caught.value)
    assert "private" not in str(caught.value)


@pytest.mark.parametrize("content", [b"", b" \n", b"\xff", b'{"private'])
def test_state_failures(tmp_path: Path, content: bytes) -> None:
    """Reject explicit state contents before passing them to the adapter."""
    path = tmp_path / "private"
    path.write_bytes(content)
    with pytest.raises(InputFailure) as caught:
        resolve_inputs(None, json.dumps(QUESTIONS), [str(path)], [], parse_questions)
    assert caught.value.code == 1
    assert "private" not in str(caught.value)


@pytest.mark.parametrize("source", ["state", "questions"])
def test_read_failures(tmp_path: Path, source: str) -> None:
    """Translate missing paths without exposing their supplied name."""
    path = str(tmp_path / "private")
    with pytest.raises(InputFailure) as caught:
        if source == "state":
            resolve_inputs(None, "{}", [path], [], parse_questions)
        else:
            resolve_inputs("state", None, [], [path], parse_questions)
    assert caught.value.code == 1
    assert "private" not in str(caught.value)


def test_callback_source_error() -> None:
    """The real command wrapper renders source errors and propagates status."""
    result = CliRunner().invoke(app, ["--questions-file", "absent", "--json"])
    assert result.exit_code == 2
    assert result.stdout == ""
    assert json.loads(result.stderr)["error"]
