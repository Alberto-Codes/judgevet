"""Check typed policy parsing and evaluation boundaries without process isolation.

Examples:
    ```bash
    uv run pytest tests/unit/test_cli_policy_contract.py
    ```

See Also:
    - [judgevet.adapters.inbound.cli_policy][]: Policy schema.
    - [judgevet.adapters.inbound.cli_policy_eval][]: Typed predicates.
"""

import json
from typing import Any

import pytest

from judgevet.adapters.inbound.cli_inputs import InputFailure
from judgevet.adapters.inbound.cli_policy import parse_policy
from judgevet.adapters.inbound.cli_policy_eval import evaluate_policy
from judgevet.domain.questions import Choice, Noul, Score
from judgevet.domain.response_parser import parse_system_one_response
from tests.cli_process_support import SUCCESS

pytestmark = pytest.mark.unit
QUESTIONS = {
    "noul": Noul(instructions="True?"),
    "choice": Choice(criteria={"yes": "Yes", "no": "No"}),
    "score": Score(criteria=["Poor", "Fair", "Good", "Excellent"]),
}


@pytest.mark.parametrize(
    "name,predicate,passed",
    [
        ("noul", {"noul": {"min": 0.42, "max": 0.42}}, True),
        ("noul", {"noul": {"min": 0.43}}, False),
        ("noul", {"noul": {"max": 0.41}}, False),
        ("choice", {"choice": "yes", "confidence": {"min": 0.8}}, True),
        ("choice", {"choice": "no"}, False),
        ("choice", {"choice": "yes", "confidence": {"min": 0.81}}, False),
        (
            "score",
            {"score": {"min": 1.5, "max": 1.5}, "confidence": {"min": 0.6}},
            True,
        ),
        ("score", {"score": {"min": 2}}, False),
        ("score", {"score": {"max": 1}}, False),
        ("score", {"score": {"min": 1}, "confidence": {"min": 0.7}}, False),
    ],
)
def test_typed_predicate(name: str, predicate: dict[str, Any], passed: bool) -> None:
    """Apply inclusive typed comparisons to the real parsed answer fixtures."""
    text = json.dumps({"rules": [{"question": name, "pass": predicate}]})
    rules = parse_policy(text, QUESTIONS)
    answers = parse_system_one_response("offline", SUCCESS).answers
    actual, reports = evaluate_policy(rules, answers)
    assert actual is passed
    assert len(reports) == 1
    assert reports[0]["question"] == name
    assert reports[0]["pass"] is passed
    assert reports[0]["detail"]


@pytest.mark.parametrize("kind", ["missing", "wrong_type", "nonfinite"])
def test_bad_answer(kind: str) -> None:
    """Missing, mismatched or nonfinite answers cannot count as policy success."""
    rules = parse_policy(
        '{"rules":[{"question":"noul","pass":{"noul":{"min":0}}}]}', QUESTIONS
    )
    answers = parse_system_one_response("offline", SUCCESS).answers
    if kind == "missing":
        del answers["noul"]
    elif kind == "wrong_type":
        answers["noul"] = answers["choice"]
    else:
        field = "noul"
        object.__setattr__(answers["noul"], field, float("nan"))
    with pytest.raises(InputFailure):
        evaluate_policy(rules, answers)
