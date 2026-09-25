"""Unit tests for the offline fakes in judgevet.testing."""

from __future__ import annotations

import anyio
import pytest

from judgevet.domain.answers import ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.questions import Choice, Noul, Score
from judgevet.domain.response import SystemOneResponse
from judgevet.ports import AsyncSystemOnePort, SystemOnePort
from judgevet.testing import AsyncFakeSystemOnePort, FakeSystemOnePort

QUESTIONS = {
    "billing": Noul(instructions="Is this about billing?"),
    "queue": Choice(criteria={"billing": "Money", "technical": "Bugs", "other": None}),
    "tone": Score(criteria=["hostile", "neutral", "friendly"]),
}


def _call(
    port: SystemOnePort, state: str = "I was charged twice."
) -> SystemOneResponse:
    """Call a sync port with the shared questions."""
    return port.system_one(state, QUESTIONS, "jev-test")


@pytest.mark.unit
def test_scripted_answer_is_returned_by_name() -> None:
    scripted = NoulAnswer(noul=0.9)
    port: SystemOnePort = FakeSystemOnePort(answers={"billing": scripted})
    response = _call(port)
    assert response.answers["billing"] is scripted
    assert response.model == "jev-test"
    assert set(response.answers) == set(QUESTIONS)


@pytest.mark.unit
def test_seeded_answers_have_the_question_type() -> None:
    response = _call(FakeSystemOnePort(seed=7))
    assert isinstance(response.answers["billing"], NoulAnswer)
    choice = response.choices["queue"]
    assert set(choice.probabilities) == {"billing", "technical", "other"}
    assert choice.probabilities[choice.choice] == max(choice.probabilities.values())
    score = response.scores["tone"]
    assert score.legend == {0: "hostile", 1: "neutral", 2: "friendly"}
    assert set(score.probabilities) == set(score.legend)
    assert 0 <= score.score <= 2


@pytest.mark.unit
@pytest.mark.parametrize("seed", range(50))
def test_seeded_answers_satisfy_domain_validators(seed: int) -> None:
    response = _call(FakeSystemOnePort(seed=seed), state=f"state {seed}")
    for answer in response.answers.values():
        # Reconstructing runs every __post_init__ validator again.
        assert type(answer)(**vars(answer)) == answer


@pytest.mark.unit
def test_same_seed_is_deterministic_and_other_seed_differs() -> None:
    first = _call(FakeSystemOnePort(seed=1))
    again = _call(FakeSystemOnePort(seed=1))
    other = _call(FakeSystemOnePort(seed=2))
    assert first.answers == again.answers
    assert first.answers != other.answers


@pytest.mark.unit
def test_calls_are_recorded() -> None:
    fake = FakeSystemOnePort()
    _call(fake, state="one")
    _call(fake, state="two")
    assert fake.calls == [
        ("one", QUESTIONS, "jev-test"),
        ("two", QUESTIONS, "jev-test"),
    ]


@pytest.mark.unit
def test_unscripted_raw_question_raises_type_error() -> None:
    fake = FakeSystemOnePort()
    with pytest.raises(TypeError, match="raw"):
        fake.system_one("state", {"q": {"type": "noul"}}, "jev-test")


@pytest.mark.unit
def test_scripted_raw_question_is_answered() -> None:
    scripted = NoulAnswer(noul=0.1)
    fake = FakeSystemOnePort(answers={"q": scripted})
    response = fake.system_one("state", {"q": {"type": "noul"}}, "jev-test")
    assert response.answers == {"q": scripted}


@pytest.mark.unit
def test_async_fake_matches_sync_fake() -> None:
    scripted = {"billing": NoulAnswer(noul=0.3)}
    async_fake = AsyncFakeSystemOnePort(seed=5, answers=scripted)
    port: AsyncSystemOnePort = async_fake

    async def call() -> SystemOneResponse:
        return await port.system_one("state", QUESTIONS, "jev-test")

    awaited = anyio.run(call)
    expected = FakeSystemOnePort(seed=5, answers=scripted).system_one(
        "state", QUESTIONS, "jev-test"
    )
    assert awaited == expected
    assert async_fake.calls == [("state", QUESTIONS, "jev-test")]
    assert isinstance(awaited.answers["queue"], ChoiceAnswer)
    assert isinstance(awaited.answers["tone"], ScoreAnswer)


@pytest.mark.unit
def test_recorded_questions_are_a_copy() -> None:
    fake = FakeSystemOnePort()
    questions = {"q": Noul(instructions="Is it fine?")}
    fake.system_one(state="s", questions=questions, model="jev-test")
    questions["extra"] = Noul(instructions="Added later")
    assert list(fake.calls[0][1]) == ["q"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "question", [Choice(criteria={}), Score(criteria=[])], ids=["choice", "score"]
)
def test_empty_criteria_raise_value_error(question: Choice | Score) -> None:
    fake = FakeSystemOnePort()
    with pytest.raises(ValueError, match="at least one criteria"):
        fake.system_one(state="s", questions={"q": question}, model="jev-test")


@pytest.mark.unit
def test_non_string_score_criteria_enter_the_legend_as_repr() -> None:
    fake = FakeSystemOnePort()
    question = Score(criteria=["Low", {"label": "High"}])
    response = fake.system_one(state="s", questions={"q": question}, model="jev-test")
    answer = response.answers["q"]
    assert isinstance(answer, ScoreAnswer)
    assert answer.legend == {0: "Low", 1: repr({"label": "High"})}
