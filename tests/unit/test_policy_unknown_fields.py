"""Unknown-field policy errors name the first unknown key and the allowed keys.

Source: https://github.com/Alberto-Codes/judgevet/issues/214#issuecomment-5860663681.
"""

import json
from typing import Any

import pytest

from judgevet import Choice, Noul, Score
from judgevet._policy_json import _parse_choice_predicate
from judgevet.policy import PolicyDefinitionError
from judgevet.policy_json import parse_policy

pytestmark = pytest.mark.unit
CHOICE = Choice(criteria={"yes": "Yes", "no": "No"})
QUESTIONS = {
    "noul": Noul(),
    "choice": CHOICE,
    "score": Score(criteria=["Poor", "Fair", "Good", "Excellent"]),
}
LONG = "k" * 100


def _message(rule: dict[str, Any]) -> str:
    """Return the diagnostic for a one-rule policy.

    Args:
        rule: The single rule object.

    Returns:
        The PolicyDefinitionError message.
    """
    with pytest.raises(PolicyDefinitionError) as caught:
        parse_policy(json.dumps({"rules": [rule]}), QUESTIONS)
    return str(caught.value)


def test_rule_names_unknown_field() -> None:
    """The issue's natural guess names `min` and the two rule fields."""
    assert (
        _message({"question": "noul", "min": 0.5})
        == "rule has unknown field 'min'; expected 'question' and 'pass'"
    )


def test_rule_names_first_sorted_unknown_field() -> None:
    """With several unknown keys, the sorted first one is named."""
    rule = {"question": "noul", "zeta": 1, "alpha": 2, "pass": {}}
    assert (
        _message(rule)
        == "rule has unknown field 'alpha'; expected 'question' and 'pass'"
    )


def test_noul_range_names_unknown_field() -> None:
    """A noul bound object names the unknown key and `min` and `max`."""
    rule = {"question": "noul", "pass": {"noul": {"min": 0.5, "unknown": 1}}}
    assert (
        _message(rule)
        == "noul predicate has unknown field 'unknown'; expected 'min' and 'max'"
    )


def test_score_range_truncates_long_field() -> None:
    """A key longer than 64 characters is shortened to 64 before quoting."""
    rule = {"question": "score", "pass": {"score": {"min": 1, LONG: 1}}}
    assert _message(rule) == (
        f"score predicate has unknown field {'k' * 64!r}; expected 'min' and 'max'"
    )


def test_choice_names_unknown_field() -> None:
    """The choice predicate names the unknown key and its allowed fields."""
    with pytest.raises(PolicyDefinitionError) as caught:
        _parse_choice_predicate({"choice": "yes", "chioce": 1}, CHOICE)
    assert str(caught.value) == (
        "choice predicate has unknown field 'chioce'; expected 'choice' and 'confidence'"
    )


def test_choice_truncates_long_field() -> None:
    """The choice diagnostic applies the same 64-character limit."""
    with pytest.raises(PolicyDefinitionError) as caught:
        _parse_choice_predicate({"choice": "yes", LONG: 1}, CHOICE)
    assert f"{'k' * 64!r};" in str(caught.value)
    assert "k" * 65 not in str(caught.value)
