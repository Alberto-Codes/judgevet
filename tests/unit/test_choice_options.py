"""Unit tests for the off-list Choice check in judgevet.domain.choice_options."""

from __future__ import annotations

from typing import Any

import pytest

from judgevet.domain.answers import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.choice_options import check_choice_options
from judgevet.domain.errors import JevResponseError
from judgevet.domain.questions import Choice, Noul, Score

QUEUE = Choice(criteria={"billing": "Money", "technical": "Bugs", "other": None})


def _raised(questions: dict[str, Any], answers: dict[str, Answer]) -> str:
    """Run the check, require a JevResponseError with status 200, return its text.

    Returns:
        The error message.
    """
    with pytest.raises(JevResponseError) as info:
        check_choice_options(questions, answers)
    assert info.value.status_code == 200
    return str(info.value)


@pytest.mark.unit
def test_off_list_choice_raises() -> None:
    answer = ChoiceAnswer("sales", 0.9, {"sales": 0.9, "billing": 0.1})
    message = _raised({"queue": QUEUE}, {"queue": answer})
    assert message.startswith(
        "Invalid choice answer for question 'queue': "
        "option 'sales' is not in the question's criteria"
    )


@pytest.mark.unit
def test_off_list_probability_key_raises() -> None:
    answer = ChoiceAnswer("billing", 0.9, {"billing": 0.9, "refunds": 0.1})
    message = _raised({"queue": QUEUE}, {"queue": answer})
    assert "'queue'" in message
    assert "'refunds'" in message


@pytest.mark.unit
def test_subset_of_probabilities_passes() -> None:
    answer = ChoiceAnswer("billing", 1.0, {"billing": 1.0})
    assert check_choice_options({"queue": QUEUE}, {"queue": answer}) is None


@pytest.mark.unit
def test_noul_and_score_answers_are_ignored() -> None:
    questions = {
        "refund": Noul(instructions="Refund?"),
        "tone": Score(criteria=["hostile", "friendly"]),
    }
    answers: dict[str, Answer] = {
        "refund": NoulAnswer(noul=0.5),
        "tone": ScoreAnswer(0.5, 0.5, {0: "hostile", 1: "friendly"}, {0: 0.5, 1: 0.5}),
    }
    assert check_choice_options(questions, answers) is None


@pytest.mark.unit
def test_raw_choice_mapping_is_checked() -> None:
    raw = {"type": "choice", "criteria": {"billing": "Money", "technical": "Bugs"}}
    answer = ChoiceAnswer("sales", 1.0, {"sales": 1.0})
    message = _raised({"queue": raw}, {"queue": answer})
    assert "'sales'" in message


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        {"type": "choice"},
        {"type": "choice", "criteria": None},
        {"type": "choice", "criteria": ["billing", "technical"]},
        {"type": "noul", "criteria": {"billing": "Money"}},
    ],
    ids=["missing", "none", "sequence", "other-type"],
)
def test_raw_mapping_without_choice_criteria_is_not_checked(
    raw: dict[str, Any],
) -> None:
    answer = ChoiceAnswer("sales", 1.0, {"sales": 1.0})
    assert check_choice_options({"queue": raw}, {"queue": answer}) is None


@pytest.mark.unit
def test_answer_without_question_is_not_checked() -> None:
    answer = ChoiceAnswer("sales", 1.0, {"sales": 1.0})
    assert check_choice_options({"queue": QUEUE}, {"unasked": answer}) is None


@pytest.mark.unit
def test_message_bounds_name_and_option() -> None:
    name, option = "q" * 100, "o" * 100
    questions = {name: Choice(criteria={"billing": None})}
    message = _raised(questions, {name: ChoiceAnswer(option, 1.0, {option: 1.0})})
    assert repr("q" * 80) in message
    assert repr("o" * 80) in message
    assert "q" * 81 not in message
    assert "o" * 81 not in message
