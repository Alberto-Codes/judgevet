"""Compare constructed, decoded and legacy policies without changing fixtures."""

import json

import pytest

from judgevet import Choice, Noul, Score
from judgevet.adapters.inbound.cli_inputs import InputFailure
from judgevet.adapters.inbound.cli_policy import parse_policy as legacy_parse
from judgevet.adapters.inbound.cli_policy_eval import evaluate_policy as legacy_evaluate
from judgevet.domain.response_parser import parse_system_one_response
from judgevet.policy import (
    ChoiceRule,
    NoulRule,
    Policy,
    PolicyDefinitionError,
    Rule,
    ScoreRule,
    evaluate_policy,
    validate_policy,
)
from judgevet.policy_json import parse_policy
from tests.cli_process_support import SUCCESS

pytestmark = pytest.mark.unit
QUESTIONS = {
    "noul": Noul(),
    "choice": Choice(criteria={"yes": "Yes", "no": "No"}),
    "score": Score(criteria=["Poor", "Fair", "Good", "Excellent"]),
}


@pytest.mark.parametrize(
    "rule,predicate,expected",
    [
        (NoulRule("noul", 0.42, 0.42), {"noul": {"min": 0.42, "max": 0.42}}, True),
        (NoulRule("noul", 0.43), {"noul": {"min": 0.43}}, False),
        (NoulRule("noul", maximum=0.41), {"noul": {"max": 0.41}}, False),
        (
            ChoiceRule("choice", "yes", 0.8),
            {"choice": "yes", "confidence": {"min": 0.8}},
            True,
        ),
        (ChoiceRule("choice", "no"), {"choice": "no"}, False),
        (
            ChoiceRule("choice", "yes", 0.81),
            {"choice": "yes", "confidence": {"min": 0.81}},
            False,
        ),
        (
            ScoreRule("score", 1.5, 1.5, 0.6),
            {"score": {"min": 1.5, "max": 1.5}, "confidence": {"min": 0.6}},
            True,
        ),
        (ScoreRule("score", 2), {"score": {"min": 2}}, False),
        (ScoreRule("score", maximum=1), {"score": {"max": 1}}, False),
        (
            ScoreRule("score", 1, min_confidence=0.7),
            {"score": {"min": 1}, "confidence": {"min": 0.7}},
            False,
        ),
    ],
)
def test_constructed_decoded_legacy_equivalence(
    rule: Rule, predicate: object, expected: bool
) -> None:
    text = json.dumps({"rules": [{"question": rule.name, "pass": predicate}]})
    constructed = validate_policy(Policy((rule,)), QUESTIONS)
    decoded = parse_policy(text, QUESTIONS)
    assert decoded == constructed
    answers = parse_system_one_response("offline", SUCCESS).answers
    report = evaluate_policy(decoded, answers)
    assert report.passed is expected
    assert report == evaluate_policy(constructed, answers)
    passed, legacy = legacy_evaluate(legacy_parse(text, QUESTIONS), answers)
    assert passed == report.passed
    assert legacy == [
        {"question": item.question, "pass": item.passed, "detail": item.detail}
        for item in report.rules
    ]


@pytest.mark.parametrize(
    "text",
    [
        "{}",
        "[]",
        '{"rules":[]}',
        '{"rules":[null]}',
        '{"private',
        '{"rules":[],"rules":[]}',
        '{"rules":[{"question":"private","pass":{"noul":{"min":0}}}]}',
        '{"rules":[{"question":"noul","pass":{"noul":{"min":NaN}}}]}',
        '{"rules":[{"question":"noul","pass":{"noul":{"min":0,"min":1}}}]}',
    ],
)
def test_public_errors_and_legacy_prefix(text: str) -> None:
    with pytest.raises(PolicyDefinitionError) as public:
        parse_policy(text, QUESTIONS)
    with pytest.raises(InputFailure) as legacy:
        legacy_parse(text, QUESTIONS)
    assert str(legacy.value) == "--policy: " + str(public.value)
    assert "--policy" not in str(public.value)
    assert "private" not in str(public.value)
    assert legacy.value.code == 1


def test_decoded_policy_preserves_subset_order() -> None:
    text = (
        '{"rules":[{"question":"score","pass":{"score":{"min":0}}},'
        '{"question":"noul","pass":{"noul":{"max":1}}}]}'
    )
    policy = parse_policy(text, QUESTIONS)
    assert [rule.name for rule in policy.rules] == ["score", "noul"]
