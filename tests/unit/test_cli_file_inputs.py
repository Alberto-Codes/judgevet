"""Check supported CLI input sources against an observed HTTP peer.

Examples:
    ```bash
    uv run pytest tests/unit/test_cli_file_inputs.py
    ```

See Also:
    - [tests.cli_file_support][]: Installed process runner.
    - [tests.cli_process_support][]: Observed HTTP peer.
"""

import json
from pathlib import Path

import pytest

from tests.cli_file_support import invoke_files
from tests.cli_process_support import QUESTIONS, SUCCESS, serve

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "mode", ["legacy_dash", "legacy_empty", "positional", "file", "stdin"]
)
@pytest.mark.parametrize("as_json", [False, True])
def test_input_success(tmp_path: Path, mode: str, as_json: bool) -> None:
    """Preserve literal input and parse explicit files through the real console."""
    qpath = tmp_path / "questions.json"
    qpath.write_text(json.dumps(QUESTIONS), encoding="utf-8")
    if mode == "legacy_dash":
        args = ["-", json.dumps(QUESTIONS)]
        expected = "-"
    elif mode == "legacy_empty":
        args = ["", "--questions-file", str(qpath)]
        expected = ""
    elif mode == "positional":
        content = "émoji\n中文\n"
        args = [content, "--questions-file", str(qpath)]
        expected = content
    elif mode == "file":
        statepath = tmp_path / "state.json"
        statepath.write_text('{"version":2}', encoding="utf-8")
        args = ["--state-file", str(statepath), "--questions-file", str(qpath)]
        expected = {"version": 2}
    else:
        args = ["--state-file", "-", "--questions-file", str(qpath)]
        expected = "stdin state\n"
    if as_json:
        args.append("--json")
    with serve(200, SUCCESS) as peer:
        code, stdout, stderr = invoke_files(
            peer.url, args, stdin=b"stdin state\n" if mode == "stdin" else b""
        )
    assert code == 0
    assert stderr == ""
    assert len(peer.requests) == 1
    body = peer.requests[0]["body"]
    assert body["state"] == expected
    assert set(body["questions"]) == set(QUESTIONS)
    if as_json:
        data = json.loads(stdout)
        assert set(data.keys()) == {"model", "usage", "answers"}
        assert data["model"] == SUCCESS["model"]
        assert data["usage"] == SUCCESS["usage"]
        assert set(data["answers"]) == set(SUCCESS["answers"])
        for name, answer in data["answers"].items():
            assert {k: v for k, v in answer.items() if k != "name"} == SUCCESS[
                "answers"
            ][name]
    else:
        assert "Model:" in stdout
        assert "Answers:" in stdout
        for q in QUESTIONS:
            assert q in stdout


@pytest.mark.parametrize("content", ["line1\r\nline2\r\n", "  {not-json", "-"])
def test_file_text_exact(tmp_path: Path, content: str) -> None:
    """Preserve CRLF, leading whitespace and literal dash in explicit files."""
    state = tmp_path / "state.txt"
    state.write_bytes(content.encode("utf-8"))
    questions = tmp_path / "questions.json"
    questions.write_text(json.dumps(QUESTIONS), encoding="utf-8")
    args = ["--state-file", str(state), "--questions-file", str(questions), "--json"]
    with serve(200, SUCCESS) as peer:
        code, stdout, stderr = invoke_files(peer.url, args)
    assert code == 0
    assert stderr == ""
    assert len(peer.requests) == 1
    assert peer.requests[0]["body"]["state"] == content
    assert set(json.loads(stdout)["answers"]) == set(QUESTIONS)
