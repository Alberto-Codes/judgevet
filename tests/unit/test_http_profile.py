"""Unit tests for the opt-in provider profile on the hosted adapters."""

from __future__ import annotations

from typing import Any

import anyio
import httpx
import pytest

from judgevet import RetryPolicy
from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain.audit import JudgmentRecord
from judgevet.domain.provider_errors import ProviderRequestError
from judgevet.domain.provider_profiles import OLLAMA_PROFILE
from judgevet.domain.questions import Choice, Noul
from judgevet.testing import FakeSystemOnePort

OVERSIZED = {"queue": Choice(criteria={f"o{index}": "x" for index in range(27)})}
"""A Choice with 27 options, one more than the Ollama profile accepts."""


class _Sink:
    """Collect audit records in memory.

    Attributes:
        records (list[JudgmentRecord]): Records in arrival order.
    """

    def __init__(self) -> None:
        """Start with no records."""
        self.records: list[JudgmentRecord] = []

    def record(self, record: JudgmentRecord) -> None:
        """Keep one record.

        Args:
            record: The finished record.
        """
        self.records.append(record)


def _counting_transport() -> tuple[list[httpx.Request], httpx.MockTransport]:
    """Return a request list and a transport that answers one Noul.

    Returns:
        The list each request is appended to, and the mock transport.
    """
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        body = {
            "model": "nimble",
            "usage": {"input_tokens": 3, "output_tokens": 1},
            "answers": {"q1": {"type": "noul", "noul": 0.5, "confidence": 0.5}},
        }
        return httpx.Response(200, json=body)

    return seen, httpx.MockTransport(handler)


def _sync(transport: httpx.MockTransport, **kwargs: Any) -> HTTPSystemOneAdapter:
    """Build a sync adapter with one attempt over the transport.

    Args:
        transport: The mock transport.
        **kwargs: Extra constructor arguments.

    Returns:
        The adapter.
    """
    return HTTPSystemOneAdapter(
        api_key="test-key",
        transport=transport,
        retry=RetryPolicy(max_attempts=1),
        **kwargs,
    )


def _async(transport: httpx.MockTransport, **kwargs: Any) -> AsyncHTTPSystemOneAdapter:
    """Build an async adapter with one attempt over the transport.

    Args:
        transport: The mock transport.
        **kwargs: Extra constructor arguments.

    Returns:
        The adapter.
    """
    return AsyncHTTPSystemOneAdapter(
        api_key="test-key",
        transport=transport,
        retry=RetryPolicy(max_attempts=1),
        **kwargs,
    )


@pytest.mark.unit
def test_sync_profile_refuses_before_request_and_audit() -> None:
    """The sync adapter refuses before any request and writes no record."""
    seen, transport = _counting_transport()
    sink = _Sink()
    with (
        _sync(transport, profile=OLLAMA_PROFILE, audit=sink) as adapter,
        pytest.raises(ProviderRequestError, match="'ollama'"),
    ):
        adapter.system_one("text", OVERSIZED, "nimble")
    assert seen == []
    assert sink.records == []


@pytest.mark.unit
def test_async_profile_refuses_before_request_and_audit() -> None:
    """The async adapter refuses before any request and writes no record."""
    seen, transport = _counting_transport()
    sink = _Sink()

    async def main() -> None:
        async with _async(transport, profile=OLLAMA_PROFILE, audit=sink) as adapter:
            await adapter.system_one("text", OVERSIZED, "nimble")

    with pytest.raises(ProviderRequestError, match="'queue'"):
        anyio.run(main)
    assert seen == []
    assert sink.records == []


@pytest.mark.unit
def test_profile_allows_a_valid_request() -> None:
    """A request inside the profile's limits is sent once."""
    seen, transport = _counting_transport()
    with _sync(transport, profile=OLLAMA_PROFILE) as adapter:
        response = adapter.system_one("text", {"q1": Noul()}, "nimble")
    assert response.nouls["q1"].noul == 0.5
    assert len(seen) == 1


@pytest.mark.unit
def test_no_profile_sends_an_oversized_request() -> None:
    """Without a profile, the adapters check nothing and send the request."""
    seen, transport = _counting_transport()
    with _sync(transport) as adapter:
        adapter.system_one("text", OVERSIZED, "nimble")

    async def main() -> None:
        async with _async(transport, profile=None) as adapter:
            await adapter.system_one("text", OVERSIZED, "nimble")

    anyio.run(main)
    assert len(seen) == 2


@pytest.mark.unit
def test_fake_rejects_an_unknown_option() -> None:
    """An untyped caller's misspelled fake keyword fails at construction."""
    options: dict[str, Any] = {"profil": OLLAMA_PROFILE}
    with pytest.raises(TypeError, match="Unknown fake port option"):
        FakeSystemOnePort(**options)
