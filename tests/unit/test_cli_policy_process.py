"""Exercise explicit policy through the installed command and real HTTP adapter.

Examples:
    ```bash
    uv run pytest tests/unit/test_cli_policy_process.py
    ```

See Also:
    - [tests.cli_process_support][]: Observed loopback peer.
    - [judgevet.adapters.inbound.cli][]: Installed command.
"""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from tests.cli_file_support import invoke_files
from tests.cli_process_support import QUESTIONS, SUCCESS, serve

pytestmark = pytest.mark.unit
RULES: list[dict[str, Any]] = [
    {"question": "noul", "pass": {"noul": {"min": 0.42, "max": 0.42}}},
    {"question": "choice", "pass": {"choice": "yes", "confidence": {"min": 0.8}}},
    {"question": "score", "pass": {"score": {"min": 1.5}, "confidence": {"min": 0.6}}},
]


@pytest.mark.parametrize("mode", ["legacy", "stdin"])
@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize("failed_rule", [None, "noul", "choice", "score", "confidence"])
def test_policy_outcome(
    tmp_path: Path, mode: str, as_json: bool, failed_rule: str | None
) -> None:
    """Distinguish an unmet policy from a successful judgment or tool failure."""
    rules = copy.deepcopy(RULES)
    if failed_rule == "noul":
        rules[0]["pass"] = {"noul": {"min": 0.5}}
    elif failed_rule == "choice":
        rules[1]["pass"] = {"choice": "no"}
    elif failed_rule == "score":
        rules[2]["pass"] = {"score": {"min": 2.0}}
    elif failed_rule == "confidence":
        rules[2]["pass"] = {"score": {"min": 1.5}, "confidence": {"min": 0.7}}
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"rules": rules}), encoding="utf-8")
    args = ["text", json.dumps(QUESTIONS)]
    if mode == "stdin":
        questions = tmp_path / "questions.json"
        questions.write_text(json.dumps(QUESTIONS), encoding="utf-8")
        args = ["--state-file", "-", "--questions-file", str(questions)]
    args.extend(["--policy", str(policy)])
    if as_json:
        args.append("--json")
    with serve(200, SUCCESS) as peer:
        code, stdout, stderr = invoke_files(peer.url, args, b"text")
    assert code == (3 if failed_rule else 0)
    assert len(peer.requests) == 1
    assert peer.requests[0]["body"]["state"] == "text"
    if as_json:
        data = json.loads(stdout)
        assert set(data) == {"model", "usage", "answers", "policy"}
        assert set(data["answers"]) == set(QUESTIONS)
        assert data["policy"]["result"] == ("fail" if failed_rule else "pass")
        reports = data["policy"]["rules"]
        assert [rule["question"] for rule in reports] == ["noul", "choice", "score"]
        assert sum(not rule["pass"] for rule in reports) == int(failed_rule is not None)
        assert all(rule["detail"] for rule in reports)
        assert stderr == ""
    else:
        assert "Answers:" in stdout
        assert "Policy:" in stderr
        assert ("FAIL" if failed_rule else "PASS") in stderr.upper()


@pytest.mark.parametrize("failure", ["auth", "missing", "wrong_type"])
def test_policy_response_failure(tmp_path: Path, failure: str) -> None:
    """Invalid responses and auth errors remain exit1 after a real request."""
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"rules": RULES}), encoding="utf-8")
    payload = copy.deepcopy(SUCCESS)
    status = 200
    if failure == "auth":
        payload = {"detail": {"error_type": "auth", "message": "denied"}}
        status = 401
    elif failure == "missing":
        del payload["answers"]["noul"]
    else:
        payload["answers"]["noul"] = payload["answers"]["choice"]
    args = ["text", json.dumps(QUESTIONS), "--policy", str(policy), "--json"]
    with serve(status, payload) as peer:
        code, stdout, stderr = invoke_files(peer.url, args)
    assert code == 1
    assert stdout == ""
    assert json.loads(stderr)["error"]
    assert len(peer.requests) == 1
