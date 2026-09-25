"""Contract tests for HTTPSystemOneAdapter.

These tests verify that a fake implementation of SystemOnePort behaves
identically to the real HTTP adapter on the same fixtures.

The fake (_ReplayPort) builds its SystemOneResponse by hand from the fixture's
plain data using domain constructors. It NEVER calls parse_system_one_response.
This is the key: the fake is a SECOND implementation of the translation. If the
real adapter's parser has a bug, the fake won't reproduce it, and the test will
fail.

The real adapter is driven through httpx.MockTransport, which replays the
fixture's HTTP stimulus. The fake is called directly with the same (state,
questions, model) arguments. Both outcomes are compared field-by-field.
"""

from __future__ import annotations

import contextlib
from collections.abc import Mapping
from typing import Any

import anyio
import httpx
import pytest

from judgevet import RetryPolicy
from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.adapters.outbound.spend import SpendCap
from judgevet.domain.answers import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.audit import JudgmentRecord
from judgevet.domain.errors import (
    JevAuthError,
    JevBudgetExceededError,
    JevError,
    JevMaxTokensExceededError,
    JevRateLimitError,
    JevRequestError,
    JevResponseError,
    JevServiceError,
)
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage
from judgevet.ports import AsyncSystemOnePort, SystemOnePort
from judgevet.testing import AsyncFakeSystemOnePort, FakeSystemOnePort

from .fixtures import get_fixture_by_name, get_fixtures


def _error_for(expect_data: tuple[str, str, int | None]) -> JevError:
    """Build the expected error type with the expected status_code."""
    _, error_name, status_code = expect_data

    # The only fixture with None status_code is transport_failure,
    # which expects JevServiceError. Other errors always have int status_code.
    if error_name == "JevServiceError":
        return JevServiceError("service error", status_code)
    assert status_code is not None
    if error_name == "JevAuthError":
        return JevAuthError("auth error", status_code)
    elif error_name == "JevRateLimitError":
        return JevRateLimitError("rate limit", status_code)
    elif error_name == "JevMaxTokensExceededError":
        return JevMaxTokensExceededError("max_tokens_exceeded", status_code)
    elif error_name == "JevRequestError":
        return JevRequestError("request error", status_code)
    elif error_name == "JevResponseError":
        return JevResponseError("response error", status_code)
    else:
        raise ValueError(f"Unknown error type: {error_name}")


class _ReplayPort:
    """Fake SystemOnePort that replays a fixture.

    This is a SECOND implementation of the translation from raw body to domain
    objects. It must NOT call parse_system_one_response or import anything from
    judgevet.adapters.outbound.

    The fake:
    - Records its (state, questions, model) arguments
    - Builds domain objects by hand from fixture plain data
    - Raises the same error type with the same status_code on error fixtures

    It is bound to the port by static annotation in tests, verified by ty_check.
    """

    def __init__(self, fixture: dict[str, Any]) -> None:
        """Initialize the fake port with a fixture."""
        self.fixture = fixture
        self.calls: list[dict[str, Any]] = []

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Any],
        model: str,
    ) -> SystemOneResponse:
        """Build the response by hand from the fixture's plain data."""
        self.calls.append({"state": state, "questions": questions, "model": model})

        expect_kind = self.fixture["expect"][0]

        if expect_kind == "response":
            return self._build_response(
                self.fixture["expect"][1], state, questions, model
            )
        else:
            self._raise_error(self.fixture["expect"])
            raise RuntimeError("Unreachable - _raise_error always raises")

    def _build_response(
        self,
        expect: dict[str, Any],
        state: Any,
        questions: Mapping[str, Any],
        model: str,
    ) -> SystemOneResponse:
        """Build a SystemOneResponse from fixture plain data."""
        model_out = expect["model"]
        usage = Usage(
            input_tokens=expect["usage"]["input_tokens"],
            output_tokens=expect["usage"]["output_tokens"],
        )
        answers: dict[str, Answer] = {}
        for key, ans_data in expect["answers"].items():
            answers[key] = self._build_answer(ans_data)
        return SystemOneResponse(model=model_out, usage=usage, answers=answers)

    def _build_answer(self, ans_data: dict[str, Any]) -> Answer:
        """Build an Answer from fixture plain data."""
        answer_type = ans_data["answer_type"]
        if answer_type == "noul":
            return NoulAnswer(noul=ans_data["noul"])
        elif answer_type == "choice":
            return ChoiceAnswer(
                choice=ans_data["choice"],
                confidence=ans_data["confidence"],
                probabilities=ans_data["probabilities"],
            )
        elif answer_type == "score":
            return ScoreAnswer(
                score=ans_data["score"],
                confidence=ans_data["confidence"],
                legend=ans_data["legend"],
                probabilities=ans_data["probabilities"],
            )
        else:
            raise ValueError(f"Unknown answer type: {answer_type}")

    def _raise_error(self, expect_data: tuple[str, str, int | None]) -> None:
        """Raise the expected error type with the expected status_code."""
        raise _error_for(expect_data)


def _transport_for(fixture: dict[str, Any]) -> httpx.MockTransport:
    """Build an httpx.MockTransport that replays the fixture's stimulus."""
    status = fixture.get("status")
    body = fixture.get("body", {})
    raw_bytes = fixture.get("raw_bytes")
    raise_connect_error = fixture.get("raise_connect_error", False)

    def handler(request: httpx.Request) -> httpx.Response:
        if raise_connect_error:
            raise httpx.ConnectError("Network error")
        if raw_bytes is not None:
            return httpx.Response(status_code=status or 200, content=raw_bytes)
        return httpx.Response(
            status_code=status or 200,
            json=body,
        )

    return httpx.MockTransport(handler)


def _assert_responses_equal(real: SystemOneResponse, fake: SystemOneResponse) -> None:
    """Assert that two responses are equal field-by-field."""
    assert real.model == fake.model, f"model: {real.model!r} != {fake.model!r}"
    assert real.usage.input_tokens == fake.usage.input_tokens, (
        f"usage.input_tokens: {real.usage.input_tokens} != {fake.usage.input_tokens}"
    )
    assert real.usage.output_tokens == fake.usage.output_tokens, (
        f"usage.output_tokens: {real.usage.output_tokens} != {fake.usage.output_tokens}"
    )
    assert set(real.answers.keys()) == set(fake.answers.keys()), (
        f"answers keys: {set(real.answers.keys())} != {set(fake.answers.keys())}"
    )

    for key in real.answers:
        _assert_answers_equal(real.answers[key], fake.answers[key])


def _assert_answers_equal(real: Answer, fake: Answer) -> None:
    """Assert that two answers are equal field-by-field."""
    if isinstance(real, NoulAnswer) and isinstance(fake, NoulAnswer):
        assert real.noul == fake.noul, f"noul: {real.noul} != {fake.noul}"
    elif isinstance(real, ChoiceAnswer) and isinstance(fake, ChoiceAnswer):
        assert real.choice == fake.choice, f"choice: {real.choice!r} != {fake.choice!r}"
        assert real.confidence == fake.confidence, (
            f"confidence: {real.confidence} != {fake.confidence}"
        )
        assert real.probabilities == fake.probabilities, (
            f"probabilities: {real.probabilities} != {fake.probabilities}"
        )
    elif isinstance(real, ScoreAnswer) and isinstance(fake, ScoreAnswer):
        assert real.score == fake.score, f"score: {real.score} != {fake.score}"
        assert real.confidence == fake.confidence, (
            f"confidence: {real.confidence} != {fake.confidence}"
        )
        assert real.legend == fake.legend, f"legend: {real.legend} != {fake.legend}"
        assert real.probabilities == fake.probabilities, (
            f"probabilities: {real.probabilities} != {fake.probabilities}"
        )
    else:
        raise TypeError(
            f"Answer type mismatch: {type(real).__name__} != {type(fake).__name__}"
        )


def _assert_errors_equal(real_exc: JevError, fake_exc: JevError) -> None:
    """Assert that two exceptions are equal type and status_code."""
    assert type(real_exc).__name__ == type(fake_exc).__name__, (
        f"exception type: {type(real_exc).__name__} != {type(fake_exc).__name__}"
    )
    assert real_exc.status_code == fake_exc.status_code, (
        f"status_code: {real_exc.status_code} != {fake_exc.status_code}"
    )


@pytest.mark.contract
class TestHTTPAdapterContract:
    """Contract tests: fake and real adapter behave identically on fixtures."""

    @pytest.mark.parametrize("fixture", get_fixtures(), ids=lambda f: f["name"])
    def test_contract(self, fixture: dict[str, Any]) -> None:
        """Test that fake and real adapter produce identical outcomes."""
        # Build the replay port (fake)
        port: SystemOnePort = _ReplayPort(fixture)

        # Build the real adapter with MockTransport
        transport = _transport_for(fixture)
        api_key = "test-key"  # required by real adapter but not used by transport
        adapter = HTTPSystemOneAdapter(
            api_key=api_key, transport=transport, retry=RetryPolicy(max_attempts=1)
        )

        # Call both with the same arguments
        expect_kind = fixture["expect"][0]

        if expect_kind == "response":
            # Both should succeed and return equivalent responses
            fake_response = port.system_one(
                state=fixture["request"]["state"],
                questions=fixture["request"]["questions"],
                model=fixture["request"]["model"],
            )
            real_response = adapter.system_one(
                state=fixture["request"]["state"],
                questions=fixture["request"]["questions"],
                model=fixture["request"]["model"],
            )
            _assert_responses_equal(real_response, fake_response)

        else:
            # Both should raise equivalent errors
            with pytest.raises(JevError) as fake_exc_info:
                port.system_one(
                    state=fixture["request"]["state"],
                    questions=fixture["request"]["questions"],
                    model=fixture["request"]["model"],
                )

            with pytest.raises(JevError) as real_exc_info:
                adapter.system_one(
                    state=fixture["request"]["state"],
                    questions=fixture["request"]["questions"],
                    model=fixture["request"]["model"],
                )

            _assert_errors_equal(real_exc_info.value, fake_exc_info.value)


@pytest.mark.contract
def test_max_tokens_exceeded_is_distinguishable() -> None:
    """Both sides raise the oversized-payload error from the probe 1 body (#39)."""
    fixture = get_fixture_by_name("error_max_tokens_exceeded")
    request = fixture["request"]
    args = (request["state"], request["questions"], request["model"])
    port: SystemOnePort = _ReplayPort(fixture)
    with pytest.raises(JevMaxTokensExceededError) as fake_info:
        port.system_one(*args)
    with (
        HTTPSystemOneAdapter(
            api_key="test-key",
            transport=_transport_for(fixture),
            retry=RetryPolicy(max_attempts=1),
        ) as adapter,
        pytest.raises(JevMaxTokensExceededError) as real_info,
    ):
        adapter.system_one(*args)
    for exc in (fake_info.value, real_info.value):
        assert type(exc) is JevMaxTokensExceededError
        assert isinstance(exc, JevRequestError)
        assert exc.status_code == 400
        assert exc.retryable is False
        assert "max_tokens_exceeded" in str(exc)


@pytest.mark.contract
def test_async_adapter_parses_rounded_score() -> None:
    """The async adapter accepts a four-level score that sums to 0.99 (#175)."""
    fixture = get_fixture_by_name("score_rounded_sum")
    request = fixture["request"]
    fake = _ReplayPort(fixture).system_one(
        request["state"], request["questions"], request["model"]
    )

    async def call() -> SystemOneResponse:
        adapter = AsyncHTTPSystemOneAdapter(
            api_key="test-key",
            transport=_transport_for(fixture),
            retry=RetryPolicy(max_attempts=1),
        )
        return await adapter.system_one(
            request["state"], request["questions"], request["model"]
        )

    _assert_responses_equal(anyio.run(call), fake)


@pytest.mark.contract
def test_async_adapter_rejects_off_list_choice() -> None:
    """The async adapter rejects a choice outside the question's criteria (#195)."""
    fixture = get_fixture_by_name("choice_off_list")
    request = fixture["request"]

    async def call() -> SystemOneResponse:
        adapter = AsyncHTTPSystemOneAdapter(
            api_key="test-key",
            transport=_transport_for(fixture),
            retry=RetryPolicy(max_attempts=1),
        )
        return await adapter.system_one(
            request["state"], request["questions"], request["model"]
        )

    with pytest.raises(JevResponseError) as info:
        anyio.run(call)
    assert info.value.status_code == 200
    assert "'queue'" in str(info.value)
    assert "'sales'" in str(info.value)


def _fixtures_of(kind: str) -> list[dict[str, Any]]:
    """Return the fixtures whose expected outcome has the given kind."""
    return [f for f in get_fixtures() if f["expect"][0] == kind]


def _scripted_answers(fixture: dict[str, Any]) -> dict[str, Answer]:
    """Build the fixture's expected answers with the replay port's constructors."""
    replay = _ReplayPort(fixture)
    expected = fixture["expect"][1]["answers"]
    return {name: replay._build_answer(data) for name, data in expected.items()}


def _scripted_usage(fixture: dict[str, Any]) -> Usage:
    """Build the fixture's expected usage from its plain data."""
    usage = fixture["expect"][1]["usage"]
    return Usage(
        input_tokens=usage["input_tokens"], output_tokens=usage["output_tokens"]
    )


def _call_fake(
    fake_kind: str, fixture: dict[str, Any], **script: Any
) -> SystemOneResponse:
    """Call the named public fake, scripted as given, with the fixture's request."""
    request = fixture["request"]
    args = (request["state"], request["questions"], request["model"])
    if fake_kind == "sync":
        port: SystemOnePort = FakeSystemOnePort(**script)
        return port.system_one(*args)
    async_port: AsyncSystemOnePort = AsyncFakeSystemOnePort(**script)

    async def call() -> SystemOneResponse:
        return await async_port.system_one(*args)

    return anyio.run(call)


def _call_real(fixture: dict[str, Any]) -> SystemOneResponse:
    """Call the HTTP adapter over the fixture's MockTransport."""
    request = fixture["request"]
    with HTTPSystemOneAdapter(
        api_key="test-key",
        transport=_transport_for(fixture),
        retry=RetryPolicy(max_attempts=1),
    ) as adapter:
        return adapter.system_one(
            request["state"], request["questions"], request["model"]
        )


FAKE_KINDS = pytest.mark.parametrize("fake_kind", ["sync", "async"])


@pytest.mark.contract
@FAKE_KINDS
@pytest.mark.parametrize("fixture", _fixtures_of("response"), ids=lambda f: f["name"])
def test_scripted_fakes_match_real_adapter_response(
    fixture: dict[str, Any], fake_kind: str
) -> None:
    """A fake scripted with a fixture's answers and usage equals the adapter."""
    real = _call_real(fixture)
    fake = _call_fake(
        fake_kind,
        fixture,
        answers=_scripted_answers(fixture),
        usage=_scripted_usage(fixture),
    )
    assert real == fake


@pytest.mark.contract
@FAKE_KINDS
@pytest.mark.parametrize("fixture", _fixtures_of("error"), ids=lambda f: f["name"])
def test_scripted_fakes_match_real_adapter_error(
    fixture: dict[str, Any], fake_kind: str
) -> None:
    """A fake scripted with a fixture's error raises what the adapter raises."""
    with pytest.raises(JevError) as real_info:
        _call_real(fixture)
    with pytest.raises(JevError) as fake_info:
        _call_fake(fake_kind, fixture, error=_error_for(fixture["expect"]))
    _assert_errors_equal(real_info.value, fake_info.value)


class _ListSink:
    """Collect every record a port writes, in order."""

    def __init__(self) -> None:
        """Start with no records."""
        self.records: list[JudgmentRecord] = []

    def record(self, record: JudgmentRecord) -> None:
        """Store one record.

        Args:
            record: The record written by the port.
        """
        self.records.append(record)


def _counting_transport(
    fixture: dict[str, Any],
) -> tuple[httpx.MockTransport, list[int]]:
    """Wrap the fixture's transport so the test can count the requests it sees."""
    seen: list[int] = []
    inner = _transport_for(fixture)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(1)
        return inner.handle_request(request)

    return httpx.MockTransport(handler), seen


def _call_twice(call: Any) -> BaseException | None:
    """Run the call once, then prove a second identical call is refused.

    Returns:
        The first call's exception, or None when it returned.
    """
    first: BaseException | None = None
    try:
        call()
    except JevError as exc:
        first = exc
    with pytest.raises(JevBudgetExceededError):
        call()
    return first


def _fake_caller(fake_kind: str, fixture: dict[str, Any], **script: Any) -> Any:
    """Build one fake and return a zero-argument function that calls it."""
    request = fixture["request"]
    args = (request["state"], request["questions"], request["model"])
    if fake_kind == "sync":
        port: SystemOnePort = FakeSystemOnePort(**script)
        return lambda: port.system_one(*args)
    async_port: AsyncSystemOnePort = AsyncFakeSystemOnePort(**script)

    async def call() -> SystemOneResponse:
        return await async_port.system_one(*args)

    return lambda: anyio.run(call)


def _fake_script(fixture: dict[str, Any]) -> dict[str, Any]:
    """Script a fake with the fixture's answers and usage, or its error."""
    if fixture["expect"][0] == "error":
        return {"error": _error_for(fixture["expect"])}
    return {"answers": _scripted_answers(fixture), "usage": _scripted_usage(fixture)}


@pytest.mark.contract
@FAKE_KINDS
@pytest.mark.parametrize("fixture", get_fixtures(), ids=lambda f: f["name"])
def test_fakes_match_real_adapter_spend_cap_and_audit(
    fixture: dict[str, Any], fake_kind: str
) -> None:
    """Both sides spend, refuse and record one call the same way."""
    real_cap, fake_cap = SpendCap(max_attempts=1), SpendCap(max_attempts=1)
    real_sink, fake_sink = _ListSink(), _ListSink()
    transport, seen = _counting_transport(fixture)
    request = fixture["request"]
    with HTTPSystemOneAdapter(
        api_key="test-key",
        transport=transport,
        spend_cap=real_cap,
        audit=real_sink,
        retry=RetryPolicy(max_attempts=1),
    ) as adapter:
        _call_twice(
            lambda: adapter.system_one(
                request["state"], request["questions"], request["model"]
            )
        )
    fake = _fake_caller(
        fake_kind,
        fixture,
        spend_cap=fake_cap,
        audit=fake_sink,
        **_fake_script(fixture),
    )
    _call_twice(fake)
    assert len(seen) == 1
    assert (real_cap.attempts, real_cap.input_tokens) == (
        fake_cap.attempts,
        fake_cap.input_tokens,
    )
    assert len(real_sink.records) == 2
    assert len(fake_sink.records) == 2
    real, fake_record = real_sink.records[0], fake_sink.records[0]
    if fixture["expect"][0] == "error":
        assert real.status_code == fake_record.status_code
    else:
        assert (real.status_code, fake_record.status_code) == (200, None)
    assert _fields(real, "status_code") == _fields(fake_record, "status_code")
    real_refused, fake_refused = real_sink.records[1], fake_sink.records[1]
    assert real_refused.error_type == "JevBudgetExceededError"
    assert _fields(real_refused) == _fields(fake_refused)


def _fields(record: JudgmentRecord, *ignored: str) -> dict[str, Any]:
    """Return a record's fields without its timestamp and the named fields."""
    skip = {"timestamp", *ignored}
    return {k: v for k, v in vars(record).items() if k not in skip}


@pytest.mark.contract
@FAKE_KINDS
@pytest.mark.parametrize("fixture", get_fixtures(), ids=lambda f: f["name"])
def test_fakes_match_real_adapter_state_fingerprint(
    fixture: dict[str, Any], fake_kind: str
) -> None:
    """With one key on both sides, the records agree on the state fingerprint."""
    key = b"\x00" * 32
    real_sink, fake_sink = _ListSink(), _ListSink()
    request = fixture["request"]
    with (
        HTTPSystemOneAdapter(
            api_key="test-key",
            transport=_transport_for(fixture),
            audit=real_sink,
            fingerprint_key=key,
            retry=RetryPolicy(max_attempts=1),
        ) as adapter,
        contextlib.suppress(JevError),
    ):
        adapter.system_one(request["state"], request["questions"], request["model"])
    fake = _fake_caller(
        fake_kind,
        fixture,
        audit=fake_sink,
        fingerprint_key=key,
        **_fake_script(fixture),
    )
    with contextlib.suppress(JevError):
        fake()
    [real], [fake_record] = real_sink.records, fake_sink.records
    assert real.state_fingerprint is not None
    assert real.state_fingerprint == fake_record.state_fingerprint
    assert _fields(real, "status_code") == _fields(fake_record, "status_code")
