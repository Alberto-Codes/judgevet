"""Offline fakes of the System One ports for caller tests.

`FakeSystemOnePort` satisfies [judgevet.ports.SystemOnePort][] and
`AsyncFakeSystemOnePort` satisfies [judgevet.ports.AsyncSystemOnePort][]. Both
make no network call. A scripted answer is returned for its question name.
Every other typed question receives a seeded answer that passes the domain
answer validators. The same seed, state and question give the same answer.

Seeded values are synthetic. They exercise caller code paths; they do not
predict what the service would answer. The returned `model` echoes the model
argument.

Each fake takes four keyword-only arguments. Two script the whole call and
two match the HTTP adapter options of the same name:

Args:
    usage (Usage | None): The `Usage` every response carries. The default is
        `Usage()`, which has no token counts.
    error (BaseException | None): An exception every call raises. The fake
        records the call in `calls` first, then raises this instance. The error
        covers the whole call, because the real adapter never fails one
        question of a call.
    spend_cap (SpendCap | None): A cap the fake claims one attempt from before
        each call. A refused claim raises `JevBudgetExceededError` before the
        call is recorded. A successful call settles its `usage.input_tokens`;
        a failed call settles nothing.
    audit (AuditSink | None): A sink that receives one `JudgmentRecord` per
        call, whether it returned, raised or was refused. The record carries
        no HTTP status on success, because no HTTP response arrived. A sink
        failure never changes the result.

Examples:
    ```python
    from judgevet.domain.answers import NoulAnswer
    from judgevet.domain.questions import Choice, Noul
    from judgevet.testing import FakeSystemOnePort

    fake = FakeSystemOnePort(seed=3, answers={"billing": NoulAnswer(noul=0.9)})
    response = fake.system_one(
        state="I was charged twice.",
        questions={
            "billing": Noul(instructions="Is this about billing?"),
            "queue": Choice(criteria={"billing": "Money", "technical": "Bugs"}),
        },
        model="jev-1.13.0",
    )
    assert response.nouls["billing"].noul == 0.9
    assert response.choices["queue"].choice in {"billing", "technical"}
    assert len(fake.calls) == 1

    from judgevet.domain.errors import JevRateLimitError
    from judgevet.domain.usage import Usage

    metered = FakeSystemOnePort(usage=Usage(input_tokens=12, output_tokens=3))
    assert metered.system_one("text", {"q": Noul()}, "m").usage.input_tokens == 12
    limited = FakeSystemOnePort(error=JevRateLimitError("slow down", 429))
    try:
        limited.system_one("text", {"q": Noul()}, "m")
    except JevRateLimitError as error:
        assert error.status_code == 429
    else:
        raise AssertionError("the scripted error was not raised")
    assert len(limited.calls) == 1

    from judgevet.domain.errors import JevBudgetExceededError
    from judgevet.domain.spend import SpendCap


    class ListSink:
        def __init__(self) -> None:
            self.records = []

        def record(self, record) -> None:
            self.records.append(record)


    sink = ListSink()
    capped = FakeSystemOnePort(spend_cap=SpendCap(max_attempts=1), audit=sink)
    capped.system_one("text", {"q": Noul()}, "m")
    try:
        capped.system_one("text", {"q": Noul()}, "m")
    except JevBudgetExceededError as error:
        assert error.limit == "attempts"
    else:
        raise AssertionError("the spend cap did not refuse the second call")
    assert [r.outcome for r in sink.records] == ["success", "error"]
    assert len(capped.calls) == 1
    ```

See Also:
    - [judgevet.ports][]: The protocols these fakes satisfy
    - [judgevet.domain.answers][]: The answer types and their validators
    - [judgevet.domain.questions][]: The typed questions the fakes answer
    - [judgevet.domain.spend][]: The cap both fakes accept as `spend_cap=`
    - [judgevet.domain.audit][]: The record both fakes write to `audit=`
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from judgevet.diagnostics import current_request_id
from judgevet.domain.answers import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.audit import JudgmentRecord
from judgevet.domain.questions import Choice, Noul, Question, Score, question_types
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.spend import SpendCap
from judgevet.domain.usage import Usage
from judgevet.ports import AuditSink

State = str | dict[str, Any] | list[Any]
Questions = Mapping[str, Question | Mapping[str, Any]]
Call = tuple[State, Questions, str]


def _uniforms(key: str, count: int) -> list[float]:
    """Derive deterministic values in [0, 1) from a key.

    SHA-256 keeps the values stable across processes and Python versions. The
    values are not secret and serve only as test data.

    Args:
        key: The text that fixes the values.
        count: The number of values to derive.

    Returns:
        Values in [0, 1), one per index.
    """
    return [
        int.from_bytes(hashlib.sha256(f"{key}#{i}".encode()).digest()[:8]) / 2**64
        for i in range(count)
    ]


def _distribution(key: str, count: int) -> list[float]:
    """Derive a probability distribution of the given length.

    Args:
        key: The text that fixes the distribution.
        count: The number of probabilities, at least one.

    Returns:
        Positive probabilities whose float sum is 1.0 within rounding error.
    """
    weights = [value + 0.01 for value in _uniforms(key, count)]
    total = sum(weights)
    return [weight / total for weight in weights]


def _choice_answer(key: str, question: Choice) -> ChoiceAnswer:
    """Draw a Choice answer over the question's criteria labels.

    Args:
        key: The text that fixes the answer.
        question: The Choice question to answer.

    Returns:
        An answer that selects the most probable label.

    Raises:
        ValueError: If the question has no criteria labels.
    """
    labels = list(question.criteria)
    if not labels:
        raise ValueError("a Choice question needs at least one criteria label")
    probabilities = dict(zip(labels, _distribution(key, len(labels)), strict=True))
    choice = max(labels, key=probabilities.__getitem__)
    return ChoiceAnswer(
        choice=choice, confidence=probabilities[choice], probabilities=probabilities
    )


def _score_answer(key: str, question: Score) -> ScoreAnswer:
    """Draw a Score answer whose legend is the question's criteria.

    Legend levels start at zero, one per criteria entry in order.

    Args:
        key: The text that fixes the answer.
        question: The Score question to answer.

    Returns:
        An answer whose score is the probability-weighted level.

    Raises:
        ValueError: If the question has no criteria entries.
    """
    if not question.criteria:
        raise ValueError("a Score question needs at least one criteria entry")
    legend = {
        level: entry if isinstance(entry, str) else repr(entry)
        for level, entry in enumerate(question.criteria)
    }
    probabilities = dict(enumerate(_distribution(key, len(legend))))
    expected = sum(level * p for level, p in probabilities.items())
    score = min(max(expected, 0.0), float(len(legend) - 1))
    return ScoreAnswer(
        score=score,
        confidence=max(probabilities.values()),
        legend=legend,
        probabilities=probabilities,
    )


class _FakeCore:
    """Shared answer logic for the sync and async fakes.

    Attributes:
        seed (int): The seed mixed into every generated answer.
        answers (dict[str, Answer]): Scripted answers keyed by question name.
        usage (Usage): The usage every response carries.
        error (BaseException | None): The exception every call raises after
            it is recorded, or None to answer normally.
        spend_cap (SpendCap | None): The cap claimed before each call.
        audit (AuditSink | None): The sink that receives one record per call.
        calls (list[Call]): Each call's (state, questions, model) in order.
            The questions mapping is copied, so later caller edits do not
            change the record.

    Examples:
        ```python
        core = _FakeCore(seed=2)
        assert core.calls == []
        ```
    """

    def __init__(
        self,
        seed: int = 0,
        answers: Mapping[str, Answer] | None = None,
        *,
        usage: Usage | None = None,
        error: BaseException | None = None,
        spend_cap: SpendCap | None = None,
        audit: AuditSink | None = None,
    ):
        """Store the seed, a copy of the scripted answers and the call options.

        Args:
            seed: The seed mixed into every generated answer.
            answers: Scripted answers keyed by question name.
            usage: The usage every response carries. None means `Usage()`.
            error: The exception every call raises after it is recorded.
                None means every call answers.
            spend_cap: The cap claimed before each call and settled after a
                successful one. None means no cap.
            audit: The sink that receives one record per call. None means no
                record.
        """
        self.seed = seed
        self.answers: dict[str, Answer] = dict(answers or {})
        self.usage = usage if usage is not None else Usage()
        self.error = error
        self.spend_cap = spend_cap
        self.audit = audit
        self.calls: list[Call] = []

    def _respond(
        self, state: State, questions: Questions, model: str
    ) -> SystemOneResponse:
        """Claim, answer and settle one call, then write its audit record.

        Args:
            state: The content the caller would judge.
            questions: Question names mapped to typed or raw questions.
            model: The model name, echoed into the response.

        Returns:
            A response with one answer per question name and the scripted usage.

        Raises:
            JevBudgetExceededError: If the spend cap refuses the call.
            BaseException: The scripted error, when one is set.
        """
        response: SystemOneResponse | None = None
        failure: BaseException | None = None
        try:
            if self.spend_cap is not None:
                self.spend_cap.claim()
            response = self._answer_all(state, questions, model)
        except BaseException as exc:
            failure = exc
            raise
        else:
            if self.spend_cap is not None:
                self.spend_cap.settle(response.usage.input_tokens)
            return response
        finally:
            self._write(model, questions, response, failure)

    def _write(
        self,
        model: str,
        questions: Questions,
        response: SystemOneResponse | None,
        failure: BaseException | None,
    ) -> None:
        """Write one record to the sink and contain any failure of the write.

        The fields follow the HTTP adapter's record. A success carries no
        status code, because no HTTP response arrived.

        Args:
            model: The requested model name.
            questions: Question names mapped to typed or raw questions.
            response: The returned response, or None when the call failed.
            failure: The exception that ended the call, or None on success.
        """
        if self.audit is None:
            return
        answer = response if failure is None else None
        if failure is None:
            outcome = "success"
        else:
            outcome = "error" if isinstance(failure, Exception) else "cancelled"
        with suppress(Exception):
            self.audit.record(
                JudgmentRecord(
                    timestamp=datetime.now(UTC),
                    outcome=outcome,
                    requested_model=model,
                    questions=question_types(questions),
                    error_type=None if failure is None else type(failure).__name__,
                    status_code=getattr(failure, "status_code", None),
                    resolved_model=None if answer is None else answer.model,
                    answers=None if answer is None else answer.answers,
                    usage=None if answer is None else answer.usage,
                    request_id=current_request_id(),
                )
            )

    def _answer_all(
        self, state: State, questions: Questions, model: str
    ) -> SystemOneResponse:
        """Append the call to `calls`, then raise the scripted error or answer it.

        Args:
            state: The content the caller would judge.
            questions: Question names mapped to typed or raw questions.
            model: The model name, echoed into the response.

        Returns:
            A response with one answer per question name and the scripted usage.

        Raises:
            BaseException: The scripted error, when one is set.
        """
        self.calls.append((state, dict(questions), model))
        if self.error is not None:
            raise self.error
        answers = {
            name: self._answer(state, name, question)
            for name, question in questions.items()
        }
        return SystemOneResponse(model=model, usage=self.usage, answers=answers)

    def _answer(
        self, state: State, name: str, question: Question | Mapping[str, Any]
    ) -> Answer:
        """Return the scripted answer or draw a seeded one.

        Args:
            state: The content the caller would judge.
            name: The question name.
            question: The typed or raw question.

        Returns:
            The scripted answer for the name, or a seeded answer.

        Raises:
            TypeError: If an unscripted question is a raw mapping.
        """
        if name in self.answers:
            return self.answers[name]
        key = repr((self.seed, state, name, question))
        if isinstance(question, Noul):
            return NoulAnswer(noul=_uniforms(key, 1)[0])
        if isinstance(question, Choice):
            return _choice_answer(key, question)
        if isinstance(question, Score):
            return _score_answer(key, question)
        raise TypeError(
            f"question {name!r} is a raw mapping; script its answer or pass a "
            "Noul, Choice or Score"
        )


class FakeSystemOnePort(_FakeCore):
    """Synchronous offline fake of [judgevet.ports.SystemOnePort][].

    Attributes:
        seed (int): The seed mixed into every generated answer.
        answers (dict[str, Answer]): Scripted answers keyed by question name.
        usage (Usage): The usage every response carries.
        error (BaseException | None): The exception every call raises after
            it is recorded, or None to answer normally.
        spend_cap (SpendCap | None): The cap claimed before each call.
        audit (AuditSink | None): The sink that receives one record per call.
        calls (list[Call]): Each call's (state, questions, model) in order.
            The questions mapping is copied, so later caller edits do not
            change the record.

    Examples:
        ```python
        from judgevet.domain.questions import Score
        from judgevet.ports import SystemOnePort

        port: SystemOnePort = FakeSystemOnePort(seed=1)
        response = port.system_one(
            "text", {"tone": Score(criteria=["cold", "warm"])}, "jev-1.13.0"
        )
        assert response.scores["tone"].legend == {0: "cold", 1: "warm"}
        ```

    See Also:
        - [judgevet.testing.AsyncFakeSystemOnePort][]: The awaitable twin
    """

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Record the call and answer every question without a network call.

        Args:
            state: The content the caller would judge.
            questions: Question names mapped to typed or raw questions.
            model: The model name, echoed into the response.

        Returns:
            A response with one answer per question name and the scripted
            usage.

        Raises:
            JevBudgetExceededError: If the spend cap refuses the call.
            BaseException: The scripted error, after the call is recorded.
        """
        return self._respond(state, questions, model)


class AsyncFakeSystemOnePort(_FakeCore):
    """Asynchronous offline fake of [judgevet.ports.AsyncSystemOnePort][].

    Attributes:
        seed (int): The seed mixed into every generated answer.
        answers (dict[str, Answer]): Scripted answers keyed by question name.
        usage (Usage): The usage every response carries.
        error (BaseException | None): The exception every call raises after
            it is recorded, or None to answer normally.
        spend_cap (SpendCap | None): The cap claimed before each call.
        audit (AuditSink | None): The sink that receives one record per call.
        calls (list[Call]): Each call's (state, questions, model) in order.
            The questions mapping is copied, so later caller edits do not
            change the record.

    Examples:
        ```python
        import anyio
        from judgevet.domain.questions import Noul


        async def main() -> float:
            fake = AsyncFakeSystemOnePort(seed=1)
            response = await fake.system_one("text", {"q": Noul()}, "jev-1.13.0")
            return response.nouls["q"].noul


        assert 0.0 <= anyio.run(main) <= 1.0
        ```

    See Also:
        - [judgevet.testing.FakeSystemOnePort][]: The synchronous twin
    """

    async def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Record the call and answer every question without a network call.

        Args:
            state: The content the caller would judge.
            questions: Question names mapped to typed or raw questions.
            model: The model name, echoed into the response.

        Returns:
            A response with one answer per question name and the scripted
            usage.

        Raises:
            JevBudgetExceededError: If the spend cap refuses the call.
            BaseException: The scripted error, after the call is recorded.
        """
        return self._respond(state, questions, model)
