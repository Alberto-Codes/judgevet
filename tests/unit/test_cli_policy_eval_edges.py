"""Audit policy conjunction, reporting and typed answer failures.

Examples:
    ```bash
    uv run pytest tests/unit/test_cli_policy_eval_edges.py
    ```

See Also:
    - [judgevet.adapters.inbound.cli_policy_eval][]: Pure rule evaluation.
"""

import json

import pytest

from judgevet.adapters.inbound.cli_inputs import InputFailure
from judgevet.adapters.inbound.cli_policy import Rule, parse_policy
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


@pytest.mark.parametrize("failures", [[], [0], [1], [2], [0, 1, 2]])
def test_complete_ordered_report(failures: list[int]) -> None:
    """All predicates contribute to an ordered report even after a failed rule."""
    data = [
        {"question": "noul", "pass": {"noul": {"min": 0.5 if 0 in failures else 0}}},
        {"question": "choice", "pass": {"choice": "no" if 1 in failures else "yes"}},
        {"question": "score", "pass": {"score": {"max": 1 if 2 in failures else 3}}},
    ]
    rules = parse_policy(json.dumps({"rules": data}), QUESTIONS)
    answers = parse_system_one_response("offline", SUCCESS).answers
    passed, reports = evaluate_policy(rules, answers)
    assert passed is (not failures)
    assert [report["question"] for report in reports] == ["noul", "choice", "score"]
    assert [report["pass"] for report in reports] == [
        i not in failures for i in range(3)
    ]
    assert all("None" not in str(report["detail"]) for report in reports)


@pytest.mark.parametrize("name", ["noul", "choice", "score"])
@pytest.mark.parametrize("failure", ["missing", "wrong_type", "nan"])
def test_invalid_required_answer(name: str, failure: str) -> None:
    """Every question type rejects missing, wrong-type or nonfinite required data."""
    predicates = {
        "noul": {"noul": {"min": 0}},
        "choice": {"choice": "yes", "confidence": {"min": 0}},
        "score": {"score": {"min": 0}},
    }
    rules = parse_policy(
        json.dumps({"rules": [{"question": name, "pass": predicates[name]}]}), QUESTIONS
    )
    answers = parse_system_one_response("offline", SUCCESS).answers
    if failure == "missing":
        del answers[name]
    elif failure == "wrong_type":
        answers[name] = answers["choice" if name != "choice" else "noul"]
    else:
        field = {"noul": "noul", "choice": "confidence", "score": "score"}[name]
        # Corrupt this freshly parsed answer to exercise policy defenses.
        object.__setattr__(answers[name], field, float("nan"))
    with pytest.raises(InputFailure):
        evaluate_policy(rules, answers)


def test_unknown_rule_kind() -> None:
    """An invalid internal rule cannot silently become a passing predicate."""
    answers = parse_system_one_response("offline", SUCCESS).answers
    with pytest.raises(InputFailure):
        evaluate_policy((Rule("noul", "unknown"),), answers)
