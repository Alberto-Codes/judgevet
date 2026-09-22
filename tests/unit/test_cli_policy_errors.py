"""Reject invalid policy input before an observed HTTP request.

Examples:
    ```bash
    uv run pytest tests/unit/test_cli_policy_errors.py
    ```

See Also:
    - [tests.cli_process_support][]: Local peer and typed fixtures.
"""

import json
from pathlib import Path

import pytest

from tests.cli_file_support import invoke_files
from tests.cli_process_support import QUESTIONS, SUCCESS, serve

pytestmark = pytest.mark.unit
PRIVATE = "private-policy-input-128"


@pytest.mark.parametrize(
    "rule",
    [
        {},
        {"question": "absent", "pass": {"noul": {"min": 0.5}}},
        {"question": "noul", "pass": {"choice": "yes"}},
        {"question": "noul", "pass": {"noul": {}}},
        {"question": "noul", "pass": {"noul": 0.5}},
        {"question": "noul", "pass": {"noul": {"min": True}}},
        {"question": "noul", "pass": {"noul": {"min": "0.5"}}},
        {"question": "noul", "pass": {"noul": {"min": None}}},
        {"question": "noul", "pass": {"noul": {"min": -0.1}}},
        {"question": "noul", "pass": {"noul": {"max": 1.1}}},
        {"question": "noul", "pass": {"noul": {"min": 0.8, "max": 0.2}}},
        {"question": "noul", "pass": {"noul": {"min": float("nan")}}},
        {"question": "noul", "pass": {"noul": {"min": float("inf")}}},
        {"question": "noul", "pass": {"noul": {"min": 0.5, "unknown": 1}}},
        {
            "question": "noul",
            "pass": {"noul": {"min": 0.5}, "confidence": {"min": 0.1}},
        },
        {"question": "choice", "pass": {"choice": PRIVATE}},
        {"question": "choice", "pass": {"choice": "yes", "confidence": {"max": 0.8}}},
        {"question": "score", "pass": {"score": {"min": 3.1}}},
        {
            "question": "score",
            "pass": {"score": {"min": 1}, "confidence": {"min": 1.1}},
        },
        {"question": "score", "pass": {"score": {"min": 1}}, "unknown": PRIVATE},
    ],
)
def test_invalid_rule(tmp_path: Path, rule: object) -> None:
    """Policy shape, type, range and question errors are local and sanitized."""
    path = tmp_path / PRIVATE
    path.write_text(json.dumps({"rules": [rule]}), encoding="utf-8")
    args = ["text", json.dumps(QUESTIONS), "--policy", str(path), "--json"]
    with serve(200, SUCCESS) as peer:
        code, stdout, stderr = invoke_files(peer.url, args)
    assert code == 1
    assert stdout == ""
    assert json.loads(stderr)["error"]
    assert PRIVATE not in stderr
    assert "Traceback" not in stderr
    assert peer.requests == []


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b" \n",
        b"[]",
        b"{}",
        b'{"rules":[]}',
        b'{"rules":{}}',
        b'{"rules":[null]}',
        b'{"rules":[],"rules":[]}',
        b'{"rules":[{"question":"noul","pass":{"noul":{"min":0.5,"min":0.6}}}]}',
        b'{"rules":[{"question":"noul","pass":{"noul":{"min":0.5}}},{"question":"noul","pass":{"noul":{"min":0.5}}}]}',
        b'{"rules":[],"private-policy-input-128":1}',
        b"\xff",
        b'{"private-policy-input-128',
    ],
)
def test_invalid_policy_file(tmp_path: Path, content: bytes) -> None:
    """Malformed policy files cannot contact the service or reveal their content."""
    path = tmp_path / PRIVATE
    path.write_bytes(content)
    args = ["text", json.dumps(QUESTIONS), "--policy", str(path), "--json"]
    with serve(200, SUCCESS) as peer:
        code, stdout, stderr = invoke_files(peer.url, args)
    assert code == 1
    assert stdout == ""
    assert json.loads(stderr)["error"]
    assert PRIVATE not in stderr
    assert peer.requests == []


def test_repeated_policy_is_usage_error() -> None:
    """Reject repeated policy selectors before opening either missing path."""
    args = [
        "text",
        json.dumps(QUESTIONS),
        "--policy",
        PRIVATE,
        "--policy",
        PRIVATE,
        "--json",
    ]
    with serve(200, SUCCESS) as peer:
        code, stdout, stderr = invoke_files(peer.url, args)
    assert code == 2
    assert stdout == ""
    assert json.loads(stderr)["error"]
    assert PRIVATE not in stderr
    assert peer.requests == []
