"""Exercise retry timing, rejection, and cancellation contracts."""

import asyncio

import httpx
import pytest

from judgevet import RetryPolicy
from judgevet.adapters.inbound.settings import Settings
from judgevet.adapters.outbound import retries
from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain.errors import JevRateLimitError, JevRequestError, JevResponseError


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
@pytest.mark.parametrize(
    "adapter_type", [HTTPSystemOneAdapter, AsyncHTTPSystemOneAdapter]
)
def test_invalid_attempt_limit(adapter_type, value) -> None:
    """Reject invalid attempt counts before acquiring a client."""
    with pytest.raises(ValueError, match="max_attempts"):
        adapter_type(api_key="synthetic", retry=RetryPolicy(max_attempts=value))


@pytest.mark.parametrize("name", ["retry_base_delay", "retry_max_delay"])
@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_delay(name, value) -> None:
    """Reject delays that cannot provide a finite bounded wait."""
    with pytest.raises(ValueError, match=name):
        RetryPolicy(**{name: value})


@pytest.mark.parametrize(
    "status,error",
    [
        (422, JevRequestError),
        (408, JevRequestError),
        (302, httpx.HTTPStatusError),
        (200, JevResponseError),
    ],
)
def test_unretryable_outcomes(status, error) -> None:
    """Never replay invalid requests, redirects, or invalid successful bodies."""
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(status, content=b"not-json")

    with (
        HTTPSystemOneAdapter(
            api_key="synthetic",
            transport=httpx.MockTransport(handle),
            retry=RetryPolicy(max_attempts=3, retry_base_delay=0),
        ) as adapter,
        pytest.raises(error),
    ):
        adapter.system_one("synthetic", {})
    assert len(calls) == 1


@pytest.mark.parametrize("fraction", [0.0, 1.0])
def test_exponential_jitter_and_cap(monkeypatch, fraction) -> None:
    """Sleep between attempts only, with capped exponential subtractive jitter."""
    delays = []
    monkeypatch.setattr(retries.time, "sleep", delays.append)
    monkeypatch.setattr(retries.random, "random", lambda: fraction)
    with (
        HTTPSystemOneAdapter(
            api_key="synthetic",
            transport=httpx.MockTransport(lambda _: httpx.Response(429)),
            retry=RetryPolicy(max_attempts=5, retry_base_delay=2, retry_max_delay=5),
        ) as adapter,
        pytest.raises(JevRateLimitError),
    ):
        adapter.system_one("synthetic", {})
    assert delays == [n * (1 - 0.25 * fraction) for n in [2, 4, 5, 5]]


def test_async_cancel_during_backoff(monkeypatch) -> None:
    """Propagate cancellation from an awaited delay without another request."""
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(429)

    async def cancel(delay: float) -> None:
        raise asyncio.CancelledError

    async def run() -> None:
        async with AsyncHTTPSystemOneAdapter(
            api_key="synthetic",
            transport=httpx.MockTransport(handle),
            retry=RetryPolicy(max_attempts=3),
        ) as adapter:
            with pytest.raises(asyncio.CancelledError):
                await adapter.system_one("synthetic", {})

    monkeypatch.setattr(retries.asyncio, "sleep", cancel)
    asyncio.run(run())
    assert len(calls) == 1


@pytest.mark.parametrize(
    "name,value",
    [
        ("MAX_ATTEMPTS", "0"),
        ("MAX_ATTEMPTS", "true"),
        ("RETRY_BASE_DELAY", "nan"),
        ("RETRY_MAX_DELAY", "-1"),
    ],
)
def test_settings_reject_invalid_limits(monkeypatch, name, value) -> None:
    """Validate environment limits before a root creates its adapter."""
    monkeypatch.setenv(f"JEV_API__{name}", value)
    with pytest.raises(ValueError):
        Settings()


def test_settings_reject_boolean_attempts() -> None:
    """Do not interpret an explicit boolean as a request budget."""
    with pytest.raises(ValueError, match="max_attempts"):
        Settings(api={"max_attempts": True})
