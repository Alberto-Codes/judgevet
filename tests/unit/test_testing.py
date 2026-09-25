"""Unit tests for the offline fakes in judgevet.testing."""

from __future__ import annotations

from typing import Any

import anyio
import pytest

from judgevet.diagnostics import bind_request_id
from judgevet.domain.answers import ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.audit import JudgmentRecord
from judgevet.domain.errors import (
    JevBudgetExceededError,
    JevRateLimitError,
    JevResponseError,
    JevServiceError,
)
from judgevet.domain.questions import Choice, Noul, Score
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.spend import SpendCap
from judgevet.domain.usage import Usage
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


@pytest.mark.unit
def test_defaults_carry_empty_usage_and_no_error() -> None:
    fake = FakeSystemOnePort()
    assert fake.usage == Usage()
    assert fake.error is None
    assert _call(fake).usage == Usage()


@pytest.mark.unit
def test_scripted_usage_is_on_every_response() -> None:
    usage = Usage(input_tokens=40, output_tokens=2)
    fake = FakeSystemOnePort(usage=usage)
    assert _call(fake).usage == usage
    assert _call(fake).usage == usage


@pytest.mark.unit
def test_async_scripted_usage_is_on_the_response() -> None:
    usage = Usage(input_tokens=5, output_tokens=1)
    port: AsyncSystemOnePort = AsyncFakeSystemOnePort(usage=usage)

    async def call() -> SystemOneResponse:
        return await port.system_one("text", QUESTIONS, "jev-test")

    assert anyio.run(call).usage == usage


@pytest.mark.unit
def test_sync_scripted_error_is_raised_after_the_call_is_recorded() -> None:
    error = JevRateLimitError("slow down", 429)
    fake = FakeSystemOnePort(error=error)
    with pytest.raises(JevRateLimitError) as info:
        _call(fake, state="first")
    assert info.value is error
    assert [call[0] for call in fake.calls] == ["first"]


@pytest.mark.unit
def test_async_scripted_error_is_raised_after_the_call_is_recorded() -> None:
    error = JevServiceError("down", 503)
    fake = AsyncFakeSystemOnePort(error=error)
    port: AsyncSystemOnePort = fake

    async def call() -> SystemOneResponse:
        return await port.system_one("second", QUESTIONS, "jev-test")

    with pytest.raises(JevServiceError) as info:
        anyio.run(call)
    assert info.value is error
    assert fake.calls == [("second", dict(QUESTIONS), "jev-test")]


class ListSink:
    """Collect every record a fake writes."""

    def __init__(self) -> None:
        """Start with no records."""
        self.records: list[JudgmentRecord] = []

    def record(self, record: JudgmentRecord) -> None:
        """Store one record.

        Args:
            record: The record written by the fake.
        """
        self.records.append(record)


class FailingSink:
    """Raise on every write, as a full disk would."""

    def record(self, record: JudgmentRecord) -> None:
        """Refuse the record.

        Args:
            record: The record written by the fake.

        Raises:
            OSError: Always.
        """
        raise OSError("sink-failure-canary")


FAKES = pytest.mark.parametrize(
    "fake_type", [FakeSystemOnePort, AsyncFakeSystemOnePort], ids=["sync", "async"]
)


def _run(fake: FakeSystemOnePort | AsyncFakeSystemOnePort) -> SystemOneResponse:
    """Call either fake once with the shared questions."""
    if isinstance(fake, FakeSystemOnePort):
        return _call(fake)

    async def call() -> SystemOneResponse:
        return await fake.system_one("text", QUESTIONS, "jev-test")

    return anyio.run(call)


def _make(
    fake_type: type, **options: Any
) -> FakeSystemOnePort | AsyncFakeSystemOnePort:
    """Build the named fake with the given keyword options."""
    fake = fake_type(**options)
    assert isinstance(fake, FakeSystemOnePort | AsyncFakeSystemOnePort)
    return fake


@pytest.mark.unit
@FAKES
def test_refused_claim_writes_one_record_and_records_no_call(fake_type: type) -> None:
    sink = ListSink()
    cap = SpendCap(max_attempts=1)
    cap.claim()
    fake = _make(fake_type, spend_cap=cap, audit=sink)
    with pytest.raises(JevBudgetExceededError):
        _run(fake)
    assert fake.calls == []
    [record] = sink.records
    assert (record.outcome, record.error_type, record.status_code) == (
        "error",
        "JevBudgetExceededError",
        None,
    )
    assert (record.answers, record.usage, record.resolved_model) == (None, None, None)


@pytest.mark.unit
@FAKES
def test_success_settles_input_tokens_and_records_no_status(fake_type: type) -> None:
    sink = ListSink()
    cap = SpendCap()
    usage = Usage(input_tokens=9, output_tokens=1)
    fake = _make(fake_type, usage=usage, spend_cap=cap, audit=sink)
    response = _run(fake)
    assert (cap.attempts, cap.input_tokens) == (1, 9)
    [record] = sink.records
    assert (record.outcome, record.status_code, record.error_type) == (
        "success",
        None,
        None,
    )
    assert record.usage == usage
    assert record.answers == response.answers
    assert record.resolved_model == "jev-test"
    assert record.questions == {"billing": "noul", "queue": "choice", "tone": "score"}


@pytest.mark.unit
@FAKES
def test_scripted_error_settles_nothing(fake_type: type) -> None:
    cap = SpendCap()
    usage = Usage(input_tokens=9, output_tokens=1)
    fake = _make(
        fake_type, usage=usage, error=JevServiceError("down", 503), spend_cap=cap
    )
    with pytest.raises(JevServiceError):
        _run(fake)
    assert (cap.attempts, cap.input_tokens) == (1, 0)


@pytest.mark.unit
@FAKES
def test_failing_sink_does_not_change_the_response(fake_type: type) -> None:
    plain = _run(_make(fake_type, seed=4))
    assert _run(_make(fake_type, seed=4, audit=FailingSink())) == plain


@pytest.mark.unit
@FAKES
def test_failing_sink_does_not_change_the_scripted_error(fake_type: type) -> None:
    error = JevRateLimitError("slow down", 429)
    with pytest.raises(JevRateLimitError) as info:
        _run(_make(fake_type, error=error, audit=FailingSink()))
    assert info.value is error


@pytest.mark.unit
@FAKES
def test_non_jev_error_records_no_status(fake_type: type) -> None:
    sink = ListSink()
    with pytest.raises(RuntimeError):
        _run(_make(fake_type, error=RuntimeError("boom"), audit=sink))
    [record] = sink.records
    assert (record.outcome, record.error_type, record.status_code) == (
        "error",
        "RuntimeError",
        None,
    )


@pytest.mark.unit
@FAKES
def test_scripted_error_records_its_status(fake_type: type) -> None:
    sink = ListSink()
    with pytest.raises(JevRateLimitError):
        _run(_make(fake_type, error=JevRateLimitError("slow", 429), audit=sink))
    assert [r.status_code for r in sink.records] == [429]


@pytest.mark.unit
@FAKES
def test_base_exception_records_cancelled(fake_type: type) -> None:
    sink = ListSink()
    with pytest.raises(KeyboardInterrupt):
        _run(_make(fake_type, error=KeyboardInterrupt(), audit=sink))
    [record] = sink.records
    assert (record.outcome, record.error_type) == ("cancelled", "KeyboardInterrupt")


@pytest.mark.unit
@FAKES
def test_record_carries_the_bound_request_id(fake_type: type) -> None:
    sink = ListSink()
    fake = _make(fake_type, audit=sink)
    with bind_request_id("req-fake-1"):
        _run(fake)
    _run(fake)
    assert [r.request_id for r in sink.records] == ["req-fake-1", None]


OFF_LIST_CHOICE = ChoiceAnswer("sales", 0.6, {"billing": 0.4, "sales": 0.6})


@pytest.mark.unit
def test_fake_rejects_off_list_choice() -> None:
    port: SystemOnePort = FakeSystemOnePort(answers={"queue": OFF_LIST_CHOICE})
    with pytest.raises(JevResponseError) as info:
        _call(port)
    assert info.value.status_code == 200
    assert "'queue'" in str(info.value)
    assert "'sales'" in str(info.value)


@pytest.mark.unit
def test_async_fake_rejects_off_list_choice() -> None:
    port: AsyncSystemOnePort = AsyncFakeSystemOnePort(
        answers={"queue": OFF_LIST_CHOICE}
    )

    async def call() -> SystemOneResponse:
        return await port.system_one("I was charged twice.", QUESTIONS, "jev-test")

    with pytest.raises(JevResponseError) as info:
        anyio.run(call)
    assert info.value.status_code == 200
    assert "'queue'" in str(info.value)
    assert "'sales'" in str(info.value)


@pytest.mark.unit
def test_fake_rejects_off_list_probability_key() -> None:
    answer = ChoiceAnswer("billing", 0.7, {"billing": 0.7, "refunds": 0.3})
    port: SystemOnePort = FakeSystemOnePort(answers={"queue": answer})
    with pytest.raises(JevResponseError) as info:
        _call(port)
    assert info.value.status_code == 200
    assert "'queue'" in str(info.value)
    assert "'refunds'" in str(info.value)


FINGERPRINT_KEY = b"\x00" * 32
FINGERPRINT_VECTOR = "ddc817f8d4f77bdd497151cf4c4614acaa49f4e151da3ff948f4d8f32d6a1212"


def _run_state(
    fake: FakeSystemOnePort | AsyncFakeSystemOnePort, state: str
) -> SystemOneResponse:
    """Call either fake once with the given state and the shared questions."""
    if isinstance(fake, FakeSystemOnePort):
        return fake.system_one(state, QUESTIONS, "jev-test")

    async def call() -> SystemOneResponse:
        return await fake.system_one(state, QUESTIONS, "jev-test")

    return anyio.run(call)


@pytest.mark.unit
@FAKES
def test_fingerprint_key_records_the_vector(fake_type: type) -> None:
    sink = ListSink()
    fake = _make(fake_type, audit=sink, fingerprint_key=FINGERPRINT_KEY)
    _run_state(fake, "synthetic")
    [record] = sink.records
    assert record.state_fingerprint == FINGERPRINT_VECTOR


@pytest.mark.unit
@FAKES
def test_without_fingerprint_key_the_field_is_none(fake_type: type) -> None:
    sink = ListSink()
    _run_state(_make(fake_type, audit=sink), "synthetic")
    [record] = sink.records
    assert record.state_fingerprint is None
