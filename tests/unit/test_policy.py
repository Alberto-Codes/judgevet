"""Acceptance for immutable typed policy definitions and validation."""

from dataclasses import FrozenInstanceError, replace
from typing import Any

import pytest

from judgevet import Choice, JevError, Noul, Score
from judgevet.policy import (
    ChoiceRule,
    NoulRule,
    Policy,
    PolicyAnswerError,
    PolicyDefinitionError,
    PolicyError,
    PolicyReport,
    RuleReport,
    ScoreRule,
    ValidatedPolicy,
    validate_policy,
)

pytestmark = pytest.mark.unit


def _assert_frozen(target: object, name: str, value: object) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(target, name, value)


@pytest.mark.parametrize("name", ["", None, 1, True])
@pytest.mark.parametrize("kind", [NoulRule, ScoreRule])
def test_invalid_names(name: Any, kind: Any) -> None:
    with pytest.raises(PolicyDefinitionError):
        kind(name, minimum=0)


@pytest.mark.parametrize("value", [True, "0", float("nan"), float("inf"), -1])
@pytest.mark.parametrize("kind", [NoulRule, ScoreRule])
@pytest.mark.parametrize("bound", ["minimum", "maximum"])
def test_invalid_bounds(value: Any, kind: Any, bound: str) -> None:
    with pytest.raises(PolicyDefinitionError):
        kind("q", **{bound: value})


@pytest.mark.parametrize("kind", [NoulRule, ScoreRule])
def test_range_requires_ordered_bounds(kind: Any) -> None:
    with pytest.raises(PolicyDefinitionError):
        kind("q")
    with pytest.raises(PolicyDefinitionError):
        kind("q", minimum=1, maximum=0)


@pytest.mark.parametrize("value", [True, "0", float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_confidence(value: Any) -> None:
    with pytest.raises(PolicyDefinitionError):
        ChoiceRule("q", "yes", min_confidence=value)
    with pytest.raises(PolicyDefinitionError):
        ScoreRule("q", minimum=0, min_confidence=value)


@pytest.mark.parametrize("value", [None, 1, True, []])
def test_invalid_choice(value: Any) -> None:
    with pytest.raises(PolicyDefinitionError):
        ChoiceRule("q", value)


def test_probability_upper_bound() -> None:
    with pytest.raises(PolicyDefinitionError):
        NoulRule("q", maximum=1.1)


@pytest.mark.parametrize("rules", [(), (object(),), (NoulRule("q", 0),) * 2])
def test_invalid_policy(rules: Any) -> None:
    with pytest.raises(PolicyDefinitionError):
        Policy(rules)


@pytest.mark.parametrize(
    "rule,questions",
    [
        (NoulRule("q", 0), {}),
        (NoulRule("q", 0), {"q": Choice({"yes": "Yes"})}),
        (ChoiceRule("q", "no"), {"q": Choice({"yes": "Yes"})}),
        (ScoreRule("q", maximum=2), {"q": Score(["Poor", "Good"])}),
        (ScoreRule("q", minimum=0), {"q": Score([])}),
    ],
)
def test_question_relative_validation(rule: Any, questions: Any) -> None:
    policy = Policy((rule,))
    with pytest.raises(PolicyDefinitionError):
        validate_policy(policy, questions)
    with pytest.raises(PolicyDefinitionError):
        ValidatedPolicy(policy, questions)


def test_rules_and_policy_are_frozen_and_replacements_validate() -> None:
    rule = NoulRule("q", minimum=0)
    _assert_frozen(rule, "minimum", 2)
    with pytest.raises(PolicyDefinitionError):
        replace(rule, minimum=2)
    policy = Policy((rule,))
    _assert_frozen(policy, "rules", ())
    with pytest.raises(PolicyDefinitionError):
        replace(policy, rules=())


def test_policy_copies_sequence_and_validated_policy_is_frozen() -> None:
    rules: Any = [NoulRule("q", minimum=0)]
    policy = Policy(rules)
    rules.clear()
    assert len(policy.rules) == 1
    validated = validate_policy(policy, {"q": Noul()})
    assert validated.rules == policy.rules
    _assert_frozen(validated, "policy", Policy((NoulRule("other", 0),)))


def test_reports_are_immutable_and_aggregate_is_derived() -> None:
    rule = RuleReport("q", False, "failed")
    items: Any = [rule]
    report = PolicyReport(items)
    items.clear()
    assert report.rules == (rule,)
    assert report.passed is False
    _assert_frozen(rule, "passed", True)
    _assert_frozen(report, "rules", ())
    with pytest.raises(PolicyDefinitionError):
        PolicyReport(())


def test_error_families_are_distinct() -> None:
    assert issubclass(PolicyError, ValueError)
    assert issubclass(PolicyDefinitionError, PolicyError)
    assert issubclass(PolicyAnswerError, PolicyError)
    assert not issubclass(PolicyError, JevError)


def test_empty_choice_label_and_single_score_level_remain_valid() -> None:
    policy = Policy((ChoiceRule("c", ""), ScoreRule("s", maximum=0)))
    validated = validate_policy(
        policy, {"c": Choice({"": "Empty"}), "s": Score(["Only"])}
    )
    assert validated.rules == policy.rules


@pytest.mark.parametrize("value", [None, True, {}, "rules", 1])
def test_malformed_containers(value: Any) -> None:
    with pytest.raises(PolicyDefinitionError):
        Policy(value)
    with pytest.raises(PolicyDefinitionError):
        PolicyReport(value)
    with pytest.raises(PolicyDefinitionError):
        ValidatedPolicy(value, {"q": Noul()})


def test_validated_replacement_requires_revalidation() -> None:
    validated = validate_policy(Policy((NoulRule("q", 0),)), {"q": Noul()})
    with pytest.raises(TypeError):
        replace(validated, policy=Policy((NoulRule("other", 0),)))
    with pytest.raises(PolicyDefinitionError):
        replace(
            validated, policy=Policy((NoulRule("other", 0),)), questions={"q": Noul()}
        )
    assert replace(validated, questions={"q": Noul()}) == validated


def test_huge_integer_bound_is_definition_error() -> None:
    with pytest.raises(PolicyDefinitionError):
        ScoreRule("q", minimum=10**400)


@pytest.mark.parametrize("name", ["", None, 1, True])
def test_choice_name_validation(name: Any) -> None:
    with pytest.raises(PolicyDefinitionError):
        ChoiceRule(name, "yes")


@pytest.mark.parametrize("passed,detail", [(1, "ok"), (True, None), ("yes", "ok")])
def test_malformed_rule_report(passed: Any, detail: Any) -> None:
    with pytest.raises(PolicyDefinitionError):
        RuleReport("q", passed, detail)


def test_malformed_report_sequence() -> None:
    with pytest.raises(PolicyDefinitionError):
        PolicyReport((RuleReport("q", True, "ok"),) * 2)
    reports: Any = (object(),)
    with pytest.raises(PolicyDefinitionError):
        PolicyReport(reports)


def test_mutable_question_criteria_are_checked() -> None:
    choice = Choice({"yes": "Yes"})
    score = Score(["Low"])
    field = "criteria"
    setattr(choice, field, None)
    with pytest.raises(PolicyDefinitionError):
        validate_policy(Policy((ChoiceRule("q", "yes"),)), {"q": choice})
    setattr(score, field, None)
    with pytest.raises(PolicyDefinitionError):
        validate_policy(Policy((ScoreRule("q", 0),)), {"q": score})
