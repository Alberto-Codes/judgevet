"""Check policy composition ownership, validation order and explicit overrides.

Examples:
    ```bash
    uv run pytest tests/unit/test_cli_policy_lifecycle.py
    ```

See Also:
    - [judgevet.adapters.inbound.cli_policy_run][]: Policy composition root.
"""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from judgevet.adapters.inbound import cli, cli_policy_run
from tests.unit.test_cli_exit_lifecycle import QUESTIONS, RecordingPort

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "floor,fail,expected", [(0.5, False, 0), (0.6, False, 3), (0.5, True, 1)]
)
@pytest.mark.parametrize("as_json", [False, True])
def test_policy_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    floor: float,
    fail: bool,
    expected: int,
    as_json: bool,
) -> None:
    """Every request outcome closes its owner and preserves explicit key/model."""
    port = RecordingPort(fail)
    construction: list[dict[str, object]] = []

    def factory(**kwargs: object) -> RecordingPort:
        construction.append(kwargs)
        return port

    monkeypatch.setattr(cli_policy_run, "HTTPSystemOneAdapter", factory)
    monkeypatch.setenv("JEV_API__KEY", "environment-canary")
    path = tmp_path / "policy.json"
    path.write_text(
        json.dumps({"rules": [{"question": "q", "pass": {"noul": {"min": floor}}}]}),
        encoding="utf-8",
    )
    args = [
        "text",
        QUESTIONS,
        "--policy",
        str(path),
        "--api-key",
        "explicit-canary",
        "--model",
        "explicit-model",
    ]
    if as_json:
        args.append("--json")
    result = CliRunner().invoke(cli.app, args)
    assert result.exit_code == expected
    assert port.calls == 1
    assert port.closes == 1
    assert len(construction) == 1
    assert construction[0]["api_key"] == "explicit-canary"
    assert construction[0]["default_model"] == "explicit-model"
    if as_json and not fail:
        assert json.loads(result.stdout)["policy"]["result"] == (
            "pass" if expected == 0 else "fail"
        )
        assert result.stderr == ""


@pytest.mark.parametrize(
    "kind", ["missing", "directory", "utf8", "bad_questions", "bad_state"]
)
def test_validation_before_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Input failures occur before adapter construction, not just before a request."""

    def forbidden(**kwargs: object) -> RecordingPort:
        raise AssertionError("Adapter constructed before validating input")

    monkeypatch.setattr(cli_policy_run, "HTTPSystemOneAdapter", forbidden)
    path = tmp_path / "private-policy-canary"
    if kind == "directory":
        path.mkdir()
    elif kind == "utf8":
        path.write_bytes(b"\xff")
    elif kind in {"bad_questions", "bad_state"}:
        path.write_text(
            '{"rules":[{"question":"q","pass":{"noul":{"min":0}}}]}', encoding="utf-8"
        )
    state = "{private-policy-canary" if kind == "bad_state" else "text"
    questions = "[]" if kind == "bad_questions" else QUESTIONS
    result = CliRunner().invoke(
        cli.app, [state, questions, "--policy", str(path), "--json"]
    )
    assert result.exit_code == 1
    assert result.stdout == ""
    assert json.loads(result.stderr)["error"]
    assert "private-policy-canary" not in result.stderr
