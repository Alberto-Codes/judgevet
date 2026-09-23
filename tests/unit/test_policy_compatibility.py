"""Pin deliberate legacy validation differences while sharing comparisons."""

from dataclasses import replace

import pytest

from judgevet import Answer, ChoiceAnswer, ScoreAnswer
from judgevet.adapters.inbound.cli_policy import Rule
from judgevet.adapters.inbound.cli_policy import parse_policy as legacy_parse
from judgevet.adapters.inbound.cli_policy_eval import evaluate_policy as legacy_evaluate
from judgevet.policy import PolicyAnswerError, evaluate_policy
from judgevet.policy_json import parse_policy
from tests.unit.test_policy_json import QUESTIONS

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "name,answer",
    [
        ("choice", ChoiceAnswer("yes", float("nan"), {"yes": 1})),
        ("score", ScoreAnswer(1, float("nan"), {1: "Only"}, {1: 1})),
        ("choice", ChoiceAnswer("other", 1, {"other": 1})),
        ("score", ScoreAnswer(4, 1, {4: "Other"}, {4: 1})),
    ],
)
def test_public_strict_legacy_compatible(name: str, answer: Answer) -> None:
    predicate = '"choice":"yes"' if name == "choice" else '"score":{"min":0}'
    text = '{"rules":[{"question":"' + name + '","pass":{' + predicate + "}}]}"
    with pytest.raises(PolicyAnswerError):
        evaluate_policy(parse_policy(text, QUESTIONS), {name: answer})
    passed, reports = legacy_evaluate(legacy_parse(text, QUESTIONS), {name: answer})
    assert passed is (not isinstance(answer, ChoiceAnswer) or answer.choice == "yes")
    assert len(reports) == 1


def test_legacy_no_bound_constructor_keeps_detail_shape() -> None:
    answer = ScoreAnswer(1, 1, {1: "Only"}, {1: 1})
    passed, reports = legacy_evaluate((Rule("q", "score"),), {"q": answer})
    assert passed
    assert reports == [{"question": "q", "pass": True, "detail": "score 1 -> pass"}]
    failed, _ = legacy_evaluate(
        (replace(Rule("q", "score"), minimum=2),), {"q": answer}
    )
    assert not failed
