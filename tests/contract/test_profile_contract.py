"""Contract test: the fakes and the hosted adapters refuse a profile breach alike.

A provider profile refusal happens before any request. The fake ports and both
hosted adapters must raise the same `ProviderRequestError` message for the same
questions, and the mock transport must see no request.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import anyio
import httpx
import pytest

from judgevet import RetryPolicy
from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain.provider_errors import ProviderRequestError
from judgevet.domain.provider_profiles import OLLAMA_PROFILE
from judgevet.domain.questions import Choice, Score
from judgevet.testing import AsyncFakeSystemOnePort, FakeSystemOnePort

BREACHES: dict[str, dict[str, Any]] = {
    "choice_27": {"queue": Choice(criteria={f"o{i}": "x" for i in range(27)})},
    "choice_1": {"queue": {"type": "choice", "criteria": {"only": "x"}}},
    "score_27": {"tone": Score(criteria=[f"l{i}" for i in range(27)])},
    "object_criteria": {"queue": Choice(criteria={"a": "x", "b": {"covers": "y"}})},
}
"""Question sets the Ollama profile refuses, keyed by test id."""


def _message(call: Callable[[], object]) -> str:
    """Run a call that must raise ProviderRequestError; return the message.

    Args:
        call: The zero-argument call.

    Returns:
        The error message.
    """
    with pytest.raises(ProviderRequestError) as info:
        call()
    return str(info.value)


@pytest.mark.contract
@pytest.mark.parametrize("name", sorted(BREACHES))
def test_fake_and_adapters_refuse_alike(name: str) -> None:
    """Fake, sync and async raise equal messages and send no request."""
    questions = BREACHES[name]
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)
    once = RetryPolicy(max_attempts=1)
    fake = FakeSystemOnePort(profile=OLLAMA_PROFILE)
    async_fake = AsyncFakeSystemOnePort(profile=OLLAMA_PROFILE)
    sync_adapter = HTTPSystemOneAdapter(
        api_key="test-key", transport=transport, retry=once, profile=OLLAMA_PROFILE
    )
    async_adapter = AsyncHTTPSystemOneAdapter(
        api_key="test-key", transport=transport, retry=once, profile=OLLAMA_PROFILE
    )

    async def call_async_adapter() -> None:
        async with async_adapter:
            await async_adapter.system_one("text", questions, "nimble")

    async def call_async_fake() -> None:
        await async_fake.system_one("text", questions, "nimble")

    with sync_adapter:
        expected = _message(
            lambda: sync_adapter.system_one("text", questions, "nimble")
        )
    assert _message(lambda: anyio.run(call_async_adapter)) == expected
    assert _message(lambda: fake.system_one("text", questions, "nimble")) == expected
    assert _message(lambda: anyio.run(call_async_fake)) == expected
    assert seen == []
    assert fake.calls == []
    assert async_fake.calls == []
