"""Audit policy schema edges independently of the coder's focused test subset.

Examples:
    ```bash
    uv run pytest tests/unit/test_cli_policy_schema_edges.py
    ```

See Also:
    - [judgevet.adapters.inbound.cli_policy][]: Strict policy decoder.
"""

import json

import pytest

from judgevet.adapters.inbound.cli_inputs import InputFailure
from judgevet.adapters.inbound.cli_policy import parse_policy
from judgevet.domain.questions import Choice, Noul, Score

pytestmark = pytest.mark.unit
QUESTIONS = {
    "n": Noul(instructions="True?"),
    "c": Choice(criteria={"yes": "Yes", "no": "No"}),
    "s": Score(criteria=["Poor", "Good", "Excellent"]),
}


@pytest.mark.parametrize(
    "name,predicate",
    [
        ("n", {"noul": {}}),
        ("n", {"noul": []}),
        ("n", {"noul": {"min": None}}),
        ("n", {"noul": {"max": False}}),
        ("n", {"noul": {"min": 10**400}}),
        ("n", {"noul": {"max": -(10**400)}}),
        ("n", {"noul": {"max": "0.5"}}),
        ("n", {"noul": {"min": 0}, "confidence": {"min": 0}}),
        ("n", {"score": {"min": 0}}),
        ("c", {"choice": "YES"}),
        ("c", {"choice": {"choice": "yes"}}),
        ("c", {"choice": "yes", "min": 0}),
        ("c", {"choice": "yes", "confidence": {}}),
        ("c", {"choice": "yes", "confidence": {"min": 0, "max": 1}}),
        ("c", {"choice": "yes", "confidence": 0.5}),
        ("c", {"score": {"min": 0}}),
        ("c", {"noul": {"min": 0}}),
        ("s", {"choice": "yes"}),
        ("s", {"noul": {"min": 0}}),
        ("s", {"score": {"max": 2.1}}),
        ("s", {"score": {"min": 0}, "confidence": {"min": True}}),
        ("s", {"score": {"min": 0}, "confidence": {"min": -0.1}}),
        ("s", {"score": {"min": 0}, "private": 1}),
    ],
)
def test_reject_predicate(name: str, predicate: object) -> None:
    """Every type boundary fails with the advertised sanitized error class."""
    text = json.dumps({"rules": [{"question": name, "pass": predicate}]})
    with pytest.raises(InputFailure) as caught:
        parse_policy(text, QUESTIONS)
    assert caught.value.code == 1
    assert "--policy" in str(caught.value)
    assert "private" not in str(caught.value)


@pytest.mark.parametrize("name", [None, True, 3, [], {}, "", "private"])
def test_bad_reference(name: object) -> None:
    """Question references validate before any dictionary lookup can fail."""
    text = json.dumps({"rules": [{"question": name, "pass": {"noul": {"min": 0}}}]})
    with pytest.raises(InputFailure) as caught:
        parse_policy(text, QUESTIONS)
    assert "private" not in str(caught.value)


def test_subset_order_and_zero_bounds() -> None:
    """Allow an ordered subset with zero and exact rubric endpoints."""
    rules = parse_policy(
        json.dumps(
            {
                "rules": [
                    {"question": "s", "pass": {"score": {"min": 0, "max": 2}}},
                    {"question": "n", "pass": {"noul": {"min": 0, "max": 1}}},
                ]
            }
        ),
        QUESTIONS,
    )
    assert [rule.name for rule in rules] == ["s", "n"]
    assert rules[0].minimum == 0
    assert rules[0].maximum == 2
    assert rules[1].minimum == 0
    assert rules[1].maximum == 1


def test_object_member_order_does_not_select_type() -> None:
    """JSON member order does not change a Choice predicate's interpretation."""
    rules = parse_policy(
        json.dumps(
            {
                "rules": [
                    {
                        "pass": {"confidence": {"min": 0.8}, "choice": "yes"},
                        "question": "c",
                    },
                ]
            }
        ),
        QUESTIONS,
    )
    assert rules[0].kind == "choice"
    assert rules[0].choice == "yes"
    assert rules[0].min_confidence == 0.8
