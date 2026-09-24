"""Acceptance for pure ordered evaluation and defensive question snapshots."""

from dataclasses import replace
from typing import assert_type

import pytest

from judgevet import Answer, Choice, ChoiceAnswer, Noul, NoulAnswer, Score, ScoreAnswer
from judgevet.policy import (
    ChoiceRule,
    NoulRule,
    Policy,
    PolicyAnswerError,
    PolicyReport,
    ScoreRule,
    evaluate_policy,
    validate_policy,
)

pytestmark = pytest.mark.unit
QUESTIONS = {
    "n": Noul(),
    "c": Choice({"yes": "Yes", "no": "No"}),
    "s": Score(["Low", "High"]),
}
ANSWERS: dict[str, Answer] = {
    "n": NoulAnswer(0.5),
    "c": ChoiceAnswer("yes", 0.5, {"yes": 0.5, "no": 0.5}),
    "s": ScoreAnswer(0.5, 0.5, {0: "Low", 1: "High"}, {0: 0.5, 1: 0.5}),
}


@pytest.mark.parametrize("failed", [False, True])
def test_inclusive_comparisons_and_complete_order(failed: bool) -> None:
    policy = Policy(
        (
            NoulRule("n", minimum=0.6 if failed else 0.5, maximum=0.6),
            ChoiceRule("c", "yes", min_confidence=0.5),
            ScoreRule("s", minimum=0.5, maximum=0.5, min_confidence=0.5),
        )
    )
    report = evaluate_policy(validate_policy(policy, QUESTIONS), ANSWERS)
    assert_type(report, PolicyReport)
    assert report.passed is (not failed)
    assert [rule.question for rule in report.rules] == ["n", "c", "s"]
    assert [rule.passed for rule in report.rules] == [not failed, True, True]
    assert (
        report.rules[1].detail
        == "choice 'yes' == 'yes' and confidence 0.5 >= 0.5 -> pass"
    )
    assert (
        report.rules[2].detail
        == "score 0.5 >= 0.5 and score 0.5 <= 0.5 and confidence 0.5 >= 0.5 -> pass"
    )


@pytest.mark.parametrize(
    "rule",
    [
        NoulRule("n", maximum=0.4),
        ChoiceRule("c", "no"),
        ChoiceRule("c", "yes", min_confidence=0.6),
        ScoreRule("s", minimum=0.6),
        ScoreRule("s", maximum=0.4),
        ScoreRule("s", minimum=0, min_confidence=0.6),
    ],
)
def test_unmet_predicates_return_failed_report(
    rule: NoulRule | ChoiceRule | ScoreRule,
) -> None:
    report = evaluate_policy(validate_policy(Policy((rule,)), QUESTIONS), ANSWERS)
    assert report.passed is False
    assert report.rules[0].passed is False
    assert report.rules[0].detail.endswith(" -> fail")


@pytest.mark.parametrize("name", ["n", "c", "s"])
@pytest.mark.parametrize("failure", ["missing", "wrong", "nonfinite"])
def test_invalid_answers_raise(name: str, failure: str) -> None:
    rules = {"n": NoulRule("n", 0), "c": ChoiceRule("c", "yes"), "s": ScoreRule("s", 0)}
    answers = dict(ANSWERS)
    if failure == "missing":
        del answers[name]
    elif failure == "wrong":
        answers[name] = ANSWERS["c" if name == "n" else "n"]
    else:
        answers[name] = replace(ANSWERS[name])
        field = {"n": "noul", "c": "confidence", "s": "score"}[name]
        # Exercise policy defenses after deliberately bypassing construction.
        object.__setattr__(answers[name], field, float("nan"))
    with pytest.raises(PolicyAnswerError):
        evaluate_policy(validate_policy(Policy((rules[name],)), QUESTIONS), answers)


def test_question_constraints_are_snapshotted() -> None:
    choice = Choice({"yes": "Yes", "no": "No"})
    score = Score(["Low", "High"])
    questions = {"c": choice, "s": score}
    policy = validate_policy(
        Policy((ChoiceRule("c", "yes"), ScoreRule("s", minimum=0))), questions
    )
    choice.criteria.clear()
    score.criteria.clear()
    questions.clear()
    assert evaluate_policy(policy, ANSWERS).passed
    bad_choice = dict(ANSWERS, c=ChoiceAnswer("other", 1, {"other": 1}))
    with pytest.raises(PolicyAnswerError):
        evaluate_policy(policy, bad_choice)
    bad_score = dict(ANSWERS, s=ScoreAnswer(2, 1, {2: "Other"}, {2: 1}))
    with pytest.raises(PolicyAnswerError):
        evaluate_policy(policy, bad_score)


def test_score_confidence_is_checked_without_predicate() -> None:
    answer = ANSWERS["s"]
    assert isinstance(answer, ScoreAnswer)
    corrupted = replace(answer)
    field = "confidence"
    object.__setattr__(corrupted, field, float("nan"))
    answers = dict(ANSWERS, s=corrupted)
    policy = validate_policy(Policy((ScoreRule("s", minimum=0),)), QUESTIONS)
    with pytest.raises(PolicyAnswerError):
        evaluate_policy(policy, answers)


@pytest.mark.parametrize("value", [True, "bad", -1, 2, float("inf")])
def test_invalid_score_scalar(value: object) -> None:
    answer = ScoreAnswer(0.5, 0.5, {0: "Low", 1: "High"}, {0: 0.5, 1: 0.5})
    field = "score"
    object.__setattr__(answer, field, value)
    policy = validate_policy(Policy((ScoreRule("s", minimum=0),)), QUESTIONS)
    with pytest.raises(PolicyAnswerError):
        evaluate_policy(policy, dict(ANSWERS, s=answer))


def test_invalid_answer_after_unmet_rule_still_raises() -> None:
    policy = validate_policy(
        Policy((NoulRule("n", minimum=1), ChoiceRule("c", "yes"))), QUESTIONS
    )
    with pytest.raises(PolicyAnswerError):
        evaluate_policy(policy, {"n": NoulAnswer(0)})
