"""Behavioral acceptance tests for bounded HTTP retries."""

import asyncio

import httpx
import pytest

from judgevet import RetryPolicy
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


def test_default_preserves_one_attempt() -> None:
    """Preserve existing single-request behavior without configuration."""
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
    assert len(calls) == 1


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
