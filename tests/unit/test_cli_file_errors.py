"""Prove new input failures stop before HTTP and contain supplied data.

Examples:
    ```bash
    uv run pytest tests/unit/test_cli_file_errors.py
    ```

See Also:
    - [tests.cli_file_support][]: Installed command runner.
    - [tests.cli_process_support][]: Observed local peer.
"""

import json
from pathlib import Path

import pytest

from tests.cli_file_support import invoke_files
from tests.cli_process_support import CANARY, QUESTIONS, SUCCESS, serve

pytestmark = pytest.mark.unit
CONTENT_CANARY = "private-question-content-127"


@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize(
    "contents",
    [
        b"",
        b" \n",
        b"[]",
        b"{}",
        b'{"q": null}',
        b'{"": {"type":"noul"}}',
        b'{"q": {"type":"unknown"}}',
        b'{"q": {"type":"choice", "criteria":null}}',
        b'{"q": {"type":"score", "criteria":null}}',
        b'{"q":{"type":"noul"},"q":{"type":"noul"}}',
        b'{"q":{"type":"noul","type":"choice"}}',
        ('{"' + CONTENT_CANARY).encode(),
        b"\xff",
    ],
)
def test_questions_content(tmp_path: Path, contents: bytes, as_json: bool) -> None:
    """Reject malformed question files without transmitting or echoing contents."""
    path = tmp_path / CONTENT_CANARY
    path.write_bytes(contents)
    args = ["state", "--questions-file", str(path)]
    if as_json:
        args.append("--json")
    with serve(200, SUCCESS) as peer:
        code, stdout, stderr = invoke_files(peer.url, args)
    assert code == 1
    assert peer.requests == []
    assert stdout == ""
    assert stderr
    assert CONTENT_CANARY not in stderr
    assert CANARY not in stderr
    assert "Traceback" not in stderr
    if as_json:
        assert json.loads(stderr)["error"]


@pytest.mark.parametrize("source", ["--state-file", "--questions-file"])
@pytest.mark.parametrize(
    "kind", ["missing", "directory", "empty", "whitespace", "utf8"]
)
def test_unreadable_source(tmp_path: Path, source: str, kind: str) -> None:
    """Reject file access and decoding failures before a request."""
    path = tmp_path / CONTENT_CANARY
    if kind == "directory":
        path.mkdir()
    elif kind != "missing":
        path.write_bytes({"empty": b"", "whitespace": b" \n", "utf8": b"\xff"}[kind])
    qpath = tmp_path / "valid.json"
    qpath.write_text(json.dumps(QUESTIONS), encoding="utf-8")
    args = ["state", "--questions-file", str(path)]
    if source == "--state-file":
        args = [source, str(path), "--questions-file", str(qpath)]
    with serve(200, SUCCESS) as peer:
        code, stdout, stderr = invoke_files(peer.url, [*args, "--json"])
    assert code == 1
    assert stdout == ""
    assert json.loads(stderr)["error"]
    assert CONTENT_CANARY not in stderr
    assert "Traceback" not in stderr
    assert peer.requests == []


@pytest.mark.parametrize(
    "args",
    [
        ["state", "--state-file", "-", "--questions-file", "absent"],
        ["state", "{}", "--questions-file", "absent"],
        ["state", "--questions-file", "absent", "--questions-file", "absent"],
        ["--state-file", "-", "--state-file", "-", "--questions-file", "absent"],
        ["--questions-file", "absent"],
        ["--state-file", "-"],
        ["--state-file", "-", "{}"],
    ],
)
def test_source_usage(args: list[str]) -> None:
    """Reject ambiguous or missing sources before reading paths or stdin."""
    with serve(200, SUCCESS) as peer:
        code, stdout, stderr = invoke_files(peer.url, [*args, "--json"])
    assert code == 2
    assert stdout == ""
    assert json.loads(stderr)["error"]
    assert peer.requests == []


@pytest.mark.parametrize(
    "stdin", [b"", b" \n", b"\xff", b'{"private-question-content-127']
)
def test_invalid_stdin(tmp_path: Path, stdin: bytes) -> None:
    """Validate explicit stdin state without leaking data or contacting the peer."""
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(QUESTIONS), encoding="utf-8")
    args = ["--state-file", "-", "--questions-file", str(path), "--json"]
    with serve(200, SUCCESS) as peer:
        code, stdout, stderr = invoke_files(peer.url, args, stdin)
    assert code == 1
    assert stdout == ""
    error = json.loads(stderr)["error"].lower()
    assert "stdin" in error or "state" in error
    assert CONTENT_CANARY not in stderr
    assert "Traceback" not in stderr
    assert peer.requests == []
