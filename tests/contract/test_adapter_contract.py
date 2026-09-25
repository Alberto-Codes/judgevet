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

from collections.abc import Mapping
from typing import Any

import anyio
import httpx
import pytest

from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain.answers import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.errors import (
    JevAuthError,
    JevError,
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
        _, error_name, status_code = expect_data

        # The only fixture with None status_code is transport_failure,
        # which expects JevServiceError. Other errors always have int status_code.
        if error_name == "JevAuthError":
            assert status_code is not None
            raise JevAuthError("auth error", status_code)
        elif error_name == "JevRateLimitError":
            assert status_code is not None
            raise JevRateLimitError("rate limit", status_code)
        elif error_name == "JevRequestError":
            assert status_code is not None
            raise JevRequestError("request error", status_code)
        elif error_name == "JevServiceError":
            raise JevServiceError("service error", status_code)
        elif error_name == "JevResponseError":
            assert status_code is not None
            raise JevResponseError("response error", status_code)
        else:
            raise ValueError(f"Unknown error type: {error_name}")


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
        adapter = HTTPSystemOneAdapter(api_key=api_key, transport=transport)

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
def test_async_adapter_parses_rounded_score() -> None:
    """The async adapter accepts a four-level score that sums to 0.99 (#175)."""
    fixture = get_fixture_by_name("score_rounded_sum")
    request = fixture["request"]
    fake = _ReplayPort(fixture).system_one(
        request["state"], request["questions"], request["model"]
    )

    async def call() -> SystemOneResponse:
        adapter = AsyncHTTPSystemOneAdapter(
            api_key="test-key", transport=_transport_for(fixture)
        )
        return await adapter.system_one(
            request["state"], request["questions"], request["model"]
        )

    _assert_responses_equal(anyio.run(call), fake)


def _success_fixtures() -> list[dict[str, Any]]:
    """Return the fixtures whose expected outcome is a response."""
    return [f for f in get_fixtures() if f["expect"][0] == "response"]


def _scripted_answers(fixture: dict[str, Any]) -> dict[str, Answer]:
    """Build the fixture's expected answers with the replay port's constructors."""
    replay = _ReplayPort(fixture)
    expected = fixture["expect"][1]["answers"]
    return {name: replay._build_answer(data) for name, data in expected.items()}


def _assert_model_and_answers(real: SystemOneResponse, fake: SystemOneResponse) -> None:
    """Assert that the model and every answer agree between two responses."""
    assert real.model == fake.model, f"model: {real.model!r} != {fake.model!r}"
    assert set(real.answers) == set(fake.answers)
    for key in real.answers:
        _assert_answers_equal(real.answers[key], fake.answers[key])


@pytest.mark.contract
@pytest.mark.parametrize("fixture", _success_fixtures(), ids=lambda f: f["name"])
def test_scripted_fakes_match_real_adapter(fixture: dict[str, Any]) -> None:
    """Both public fakes, scripted with a fixture's answers, agree with the adapter."""
    request = fixture["request"]
    args = (request["state"], request["questions"], request["model"])
    sync_port: SystemOnePort = FakeSystemOnePort(answers=_scripted_answers(fixture))
    async_port: AsyncSystemOnePort = AsyncFakeSystemOnePort(
        answers=_scripted_answers(fixture)
    )
    with HTTPSystemOneAdapter(
        api_key="test-key", transport=_transport_for(fixture)
    ) as adapter:
        real = adapter.system_one(*args)

    async def call_async_fake() -> SystemOneResponse:
        return await async_port.system_one(*args)

    _assert_model_and_answers(real, sync_port.system_one(*args))
    _assert_model_and_answers(real, anyio.run(call_async_fake))
