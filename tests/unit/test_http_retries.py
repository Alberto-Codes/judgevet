"""Behavioral acceptance tests for bounded HTTP retries."""

import asyncio

import httpx
import pytest

from judgevet import JevBudgetExceededError, RetryPolicy, SpendCap
from judgevet.adapters.inbound.settings import ApiSettings
from judgevet.adapters.outbound import retries
from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain.errors import (
    JevAuthError,
    JevError,
    JevRateLimitError,
    JevServiceError,
)
from tests.unit.test_audit_sink import RecordingSink


def success() -> httpx.Response:
    """Return a synthetic successful judgment."""
    return httpx.Response(
        200,
        json={
            "model": "jev-1.13.0",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "answers": {"q": {"type": "noul", "noul": 0.8}},
        },
    )


@pytest.fixture
def no_sleep(monkeypatch) -> list[float]:
    """Record the default policy's backoff delays instead of sleeping them."""
    delays: list[float] = []

    async def pause(seconds: float) -> None:
        delays.append(seconds)

    monkeypatch.setattr(retries.time, "sleep", delays.append)
    monkeypatch.setattr(retries.asyncio, "sleep", pause)
    return delays


def unavailable_then_success() -> tuple[list[httpx.Request], httpx.MockTransport]:
    """Answer 503 on the first request and a valid judgment afterwards."""
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(503) if len(calls) == 1 else success()

    return calls, httpx.MockTransport(handle)


def test_default_policy_has_three_attempts() -> None:
    """The library default makes three attempts, as the vendor SDK does."""
    assert RetryPolicy().max_attempts == 3


def test_settings_default_attempts_is_three(monkeypatch) -> None:
    """The CLI and MCP settings share the library default of three attempts."""
    monkeypatch.delenv("JEV_API__MAX_ATTEMPTS", raising=False)
    assert ApiSettings().max_attempts == 3


def test_default_sync_adapter_retries_503_then_200(no_sleep) -> None:
    """An adapter built with no retry argument recovers from a transient 503."""
    calls, transport = unavailable_then_success()
    sink = RecordingSink()
    with HTTPSystemOneAdapter(
        api_key="synthetic", transport=transport, audit=sink
    ) as adapter:
        answer = adapter.system_one("synthetic", {"q": {"type": "noul"}})
    assert answer.model == "jev-1.13.0"
    assert len(calls) == 2
    assert len(sink.records) == 1
    assert sink.records[0].outcome == "success"


def test_default_async_adapter_retries_503_then_200(no_sleep) -> None:
    """An async adapter built with no retry argument recovers from a 503."""
    calls, transport = unavailable_then_success()
    sink = RecordingSink()

    async def run() -> None:
        async with AsyncHTTPSystemOneAdapter(
            api_key="synthetic", transport=transport, audit=sink
        ) as adapter:
            answer = await adapter.system_one("synthetic", {"q": {"type": "noul"}})
        assert answer.model == "jev-1.13.0"

    asyncio.run(run())
    assert len(calls) == 2
    assert len(sink.records) == 1
    assert sink.records[0].outcome == "success"


def test_spend_cap_of_one_stops_the_default_retry(no_sleep) -> None:
    """A one-attempt spend cap refuses the default policy's second send."""
    calls, transport = unavailable_then_success()
    sink = RecordingSink()
    with (
        HTTPSystemOneAdapter(
            api_key="synthetic",
            transport=transport,
            audit=sink,
            spend_cap=SpendCap(max_attempts=1),
        ) as adapter,
        pytest.raises(JevBudgetExceededError),
    ):
        adapter.system_one("synthetic", {"q": {"type": "noul"}})
    assert len(calls) == 1
    assert len(sink.records) == 1
    assert sink.records[0].error_type == "JevBudgetExceededError"


@pytest.mark.parametrize("status", [429, 529])
def test_retryable_status_recovers(status: int) -> None:
    """Retry an HTTP failure and return the later successful answer."""
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(status) if len(calls) == 1 else success()

    with HTTPSystemOneAdapter(
        api_key="synthetic",
        transport=httpx.MockTransport(handle),
        retry=RetryPolicy(max_attempts=3, retry_base_delay=0),
    ) as adapter:
        answer = adapter.system_one("synthetic", {"q": {"type": "noul"}})
    assert answer.model == "jev-1.13.0"
    assert len(calls) == 2
    assert calls[0].content == calls[1].content


def test_auth_never_retries() -> None:
    """Do not repeat a non-retryable authentication failure."""
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(401)

    with (
        HTTPSystemOneAdapter(
            api_key="synthetic",
            transport=httpx.MockTransport(handle),
            retry=RetryPolicy(max_attempts=3, retry_base_delay=0),
        ) as adapter,
        pytest.raises(JevAuthError),
    ):
        adapter.system_one("synthetic", {})
    assert len(calls) == 1


def test_exhaustion_raises_last_error() -> None:
    """Bound attempts and retain the final HTTP failure as the cause."""
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(429, json={"detail": {"message": str(len(calls))}})

    with (
        HTTPSystemOneAdapter(
            api_key="synthetic",
            transport=httpx.MockTransport(handle),
            retry=RetryPolicy(max_attempts=3, retry_base_delay=0),
        ) as adapter,
        pytest.raises(JevRateLimitError) as caught,
    ):
        adapter.system_one("synthetic", {})
    assert len(calls) == 3
    assert isinstance(caught.value.__cause__, httpx.HTTPStatusError)
    assert caught.value.__cause__.response.json()["detail"]["message"] == "3"


@pytest.mark.parametrize("enabled,expected", [(False, 1), (True, 3)])
def test_transport_requires_opt_in(enabled: bool, expected: int) -> None:
    """Replay transport errors only with explicit authorization."""
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ReadTimeout("synthetic", request=request)

    with (
        HTTPSystemOneAdapter(
            api_key="synthetic",
            transport=httpx.MockTransport(handle),
            retry=RetryPolicy(
                max_attempts=3, retry_base_delay=0, retry_transport=enabled
            ),
        ) as adapter,
        pytest.raises(JevServiceError),
    ):
        adapter.system_one("synthetic", {})
    assert len(calls) == expected


def test_default_makes_three_attempts(no_sleep) -> None:
    """Exhaust three attempts on a persistent 429 without configuration."""
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(429)

    with (
        HTTPSystemOneAdapter(
            api_key="synthetic",
            transport=httpx.MockTransport(handle),
        ) as adapter,
        pytest.raises(JevRateLimitError),
    ):
        adapter.system_one("synthetic", {})
    assert len(calls) == 3


def test_async_retry_recovers() -> None:
    """Apply the attempt budget to asynchronous calls too."""
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(429) if len(calls) == 1 else success()

    async def run() -> None:
        async with AsyncHTTPSystemOneAdapter(
            api_key="synthetic",
            transport=httpx.MockTransport(handle),
            retry=RetryPolicy(max_attempts=3, retry_base_delay=0),
        ) as adapter:
            answer = await adapter.system_one("synthetic", {})
        assert answer.model == "jev-1.13.0"

    asyncio.run(run())
    assert len(calls) == 2


@pytest.mark.parametrize("status,attempts", [(401, 1), (422, 1), (429, 3), (529, 3)])
def test_async_exhaustion_and_classification(status: int, attempts: int) -> None:
    """Apply identical retry classification and exhaustion to async requests."""
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(status)

    async def run() -> None:
        async with AsyncHTTPSystemOneAdapter(
            api_key="synthetic",
            transport=httpx.MockTransport(handle),
            retry=RetryPolicy(max_attempts=3, retry_base_delay=0),
        ) as adapter:
            with pytest.raises(JevError) as caught:
                await adapter.system_one("synthetic", {})
            assert caught.value.status_code == status
            assert isinstance(caught.value.__cause__, httpx.HTTPStatusError)

    asyncio.run(run())
    assert len(calls) == attempts


@pytest.mark.parametrize("enabled,expected", [(False, 1), (True, 3)])
def test_async_transport_opt_in(enabled: bool, expected: int) -> None:
    """Require separate transport authorization on the async path."""
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ReadTimeout("synthetic", request=request)

    async def run() -> None:
        async with AsyncHTTPSystemOneAdapter(
            api_key="synthetic",
            transport=httpx.MockTransport(handle),
            retry=RetryPolicy(
                max_attempts=3, retry_base_delay=0, retry_transport=enabled
            ),
        ) as adapter:
            with pytest.raises(JevServiceError):
                await adapter.system_one("synthetic", {})

    asyncio.run(run())
    assert len(calls) == expected


def test_async_request_cancellation() -> None:
    """Cancellation from the transport is never translated or retried."""
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise asyncio.CancelledError

    async def run() -> None:
        async with AsyncHTTPSystemOneAdapter(
            api_key="synthetic",
            transport=httpx.MockTransport(handle),
            retry=RetryPolicy(max_attempts=3, retry_base_delay=0, retry_transport=True),
        ) as adapter:
            with pytest.raises(asyncio.CancelledError):
                await adapter.system_one("synthetic", {})

    asyncio.run(run())
    assert len(calls) == 1
