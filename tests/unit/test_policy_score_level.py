"""An exact-level score predicate passes on the argmax level, not the expected value.

Contract: https://github.com/Alberto-Codes/judgevet/issues/337 (supervisor
comment of 2026-10-20).
"""

import json

import pytest

from judgevet import Score, ScoreAnswer
from judgevet.policy import (
    Policy,
    PolicyDefinitionError,
    ScoreRule,
    evaluate_policy,
    validate_policy,
)
from judgevet.policy_json import parse_policy
from tests.unit.test_mcp_policy_schema import _errors

pytestmark = pytest.mark.unit
QUESTIONS = {"s": Score(criteria=["Poor", "Fair", "Good"])}
ANSWERS = {
    "s": ScoreAnswer(
        score=1.0005,
        confidence=0.9995,
        legend={1: "Fair", 2: "Good"},
        probabilities={1: 0.9995, 2: 0.0005},
    )
}


def _policy_text(predicate: dict[str, object]) -> str:
    """Return a one-rule policy document over question `s`.

    Args:
        predicate: The `score` predicate object.

    Returns:
        The JSON policy text.
    """
    return json.dumps({"rules": [{"question": "s", "pass": {"score": predicate}}]})


def test_level_passes_on_the_highest_probability_level() -> None:
    decoded = parse_policy(_policy_text({"level": 1}), QUESTIONS)
    constructed = validate_policy(Policy((ScoreRule("s", level=1),)), QUESTIONS)
    assert decoded == constructed
    report = evaluate_policy(decoded, ANSWERS)
    assert report.passed is True
    assert report.rules[0].detail.endswith("-> pass")


def test_level_fails_on_a_lower_probability_level() -> None:
    report = evaluate_policy(
        parse_policy(_policy_text({"level": 2}), QUESTIONS), ANSWERS
    )
    assert report.passed is False
    assert report.rules[0].detail.endswith("-> fail")


def test_level_is_mutually_exclusive_with_bounds() -> None:
    with pytest.raises(PolicyDefinitionError):
        parse_policy(_policy_text({"level": 1, "min": 1}), QUESTIONS)
    with pytest.raises(PolicyDefinitionError):
        ScoreRule("s", minimum=1, level=1)


def test_mcp_policy_schema_accepts_a_level_rule() -> None:
    assert (
        _errors({"rules": [{"question": "s", "pass": {"score": {"level": 1}}}]}) == []
    )


def test_level_tie_picks_the_lowest_level_and_rejects_bad_levels() -> None:
    tied = {"s": ScoreAnswer(1.0, 0.5, {0: "Poor", 2: "Good"}, {0: 0.5, 2: 0.5})}
    policy = validate_policy(Policy((ScoreRule("s", level=0),)), QUESTIONS)
    assert evaluate_policy(policy, tied).passed is True
    policy = validate_policy(Policy((ScoreRule("s", level=2),)), QUESTIONS)
    assert evaluate_policy(policy, tied).passed is False
    for bad in (True, 1.0, -1):
        with pytest.raises(PolicyDefinitionError):
            parse_policy(_policy_text({"level": bad}), QUESTIONS)
    with pytest.raises(PolicyDefinitionError, match="score level is outside"):
        validate_policy(Policy((ScoreRule("s", level=3),)), QUESTIONS)
