"""Prove hosted Jev failures satisfy the provider error contract (#259)."""

import asyncio
from collections.abc import Callable

import httpx
import pytest

import judgevet
from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain import provider_errors
from judgevet.domain.errors import (
    JevAuthError,
    JevError,
    JevServiceError,
    JudgevetError,
)
from judgevet.providers import ProviderError
from judgevet.testing._conformance_probes import provider_error_problem

QUESTIONS = {"q": {"type": "noul"}}
STATE = "Synthetic state."
JEV_CLASSES = [
    getattr(judgevet, name)
    for name in judgevet.__all__
    if name.startswith("Jev") and name.endswith("Error")
]
FAILURES = [
    pytest.param(401, JevAuthError, id="401-JevAuthError"),
    pytest.param(503, JevServiceError, id="503-JevServiceError"),
]


def reply(status: int) -> Callable[[httpx.Request], httpx.Response]:
    """Return a mock transport handler that fails every request with one status.

    Args:
        status: The synthetic HTTP status to return.

    Returns:
        A handler for `httpx.MockTransport`.
    """

    def handle(request: httpx.Request) -> httpx.Response:
        """Build a fresh synthetic failure for each request.

        Returns:
            A failing response with the chosen status.
        """
        return httpx.Response(status, json={"detail": "Synthetic failure"})

    return handle


@pytest.mark.unit
@pytest.mark.parametrize(("status", "expected"), FAILURES)
def test_sync_hosted_failure_passes_kit_error_check(
    status: int, expected: type[JevError]
) -> None:
    """A failing sync hosted adapter raises the mapped error the kit accepts.

    The test pins the HTTP status code too.
    """
    adapter = HTTPSystemOneAdapter(
        api_key="synthetic", transport=httpx.MockTransport(reply(status))
    )
    with pytest.raises(expected) as caught:
        adapter.system_one(STATE, QUESTIONS, "jev-1.13.0")
    assert provider_error_problem(caught.value) is None
    assert caught.value.status_code == status


@pytest.mark.unit
@pytest.mark.parametrize(("status", "expected"), FAILURES)
def test_async_hosted_failure_passes_kit_error_check(
    status: int, expected: type[JevError]
) -> None:
    """A failing async hosted adapter raises the mapped error the kit accepts.

    The test pins the HTTP status code too.
    """

    async def call() -> None:
        """Run one failing judgment on a scoped async adapter."""
        async with AsyncHTTPSystemOneAdapter(
            api_key="synthetic", transport=httpx.MockTransport(reply(status))
        ) as adapter:
            await adapter.system_one(STATE, QUESTIONS, "jev-1.13.0")

    with pytest.raises(expected) as caught:
        asyncio.run(call())
    assert provider_error_problem(caught.value) is None
    assert caught.value.status_code == status


@pytest.mark.unit
def test_every_jev_error_is_a_provider_error() -> None:
    """The single spine runs from JudgevetError through ProviderError to Jev*."""
    assert len(JEV_CLASSES) >= 8
    for cls in JEV_CLASSES:
        assert issubclass(cls, ProviderError), cls.__name__
        assert issubclass(cls, JudgevetError), cls.__name__
    assert ProviderError.__mro__[1] is JudgevetError
    assert provider_errors.ProviderError is ProviderError
    assert not issubclass(ProviderError, JevError)
    assert not issubclass(provider_errors.ProviderTransportError, JevError)
