"""Prove opt-in fields stay separate from diagnostics and direct defaults."""

import asyncio
from collections.abc import Iterator
from contextlib import ExitStack
from types import MappingProxyType

import httpx
import pytest
import structlog

from judgevet import (
    AsyncHTTPSystemOneAdapter,
    GatewayConfig,
    HTTPSystemOneAdapter,
    RequestMetadata,
    RetryPolicy,
    bind_request_id,
)
from judgevet.adapters.inbound.logs import LogSettings, configure
from tests.cli_process_support import SUCCESS
from tests.gateway_support import gateway_peer, observed_headers


@pytest.fixture(autouse=True)
def reset_logging() -> Iterator[None]:
    """Release diagnostic sinks before captured streams close."""
    configured = structlog.is_configured()
    previous = structlog.get_config()
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()
    if configured:
        structlog.configure(**previous)


@pytest.mark.parametrize("asynchronous", [False, True])
def test_direct_defaults_ignore_gateway_environment(asynchronous, monkeypatch) -> None:
    """Environment cannot turn on library metadata or replace direct authentication."""
    monkeypatch.setenv("JEV_API__AUTH_HEADER", "x-apikey")
    monkeypatch.setenv("JEV_API__HEADERS", '{"Example-Private": "private-canary"}')
    with gateway_peer() as peer, bind_request_id("default-local"):
        if asynchronous:

            async def call() -> None:
                async with AsyncHTTPSystemOneAdapter(
                    api_key="dummy", base_url=peer.url
                ) as adapter:
                    await adapter.system_one("synthetic", {})

            asyncio.run(call())
        else:
            with HTTPSystemOneAdapter(api_key="dummy", base_url=peer.url) as adapter:
                adapter.system_one("synthetic", {})
    assert observed_headers(peer)["authorization"] == "Bearer dummy"
    assert "example-request" not in observed_headers(peer)
    assert "private-canary" not in str(peer.requests)
    assert peer.requests[0][0] == "/v1/systemone"
    assert peer.requests[0][2] == {
        "state": "synthetic",
        "questions": {},
        "model": "jev-latest",
    }


def test_explicit_trace_fields_and_private_diagnostics(capsys) -> None:
    """Caller fields travel explicitly but are excluded from built-in events."""
    configure(LogSettings(level="debug", format="json"))
    fields = {
        "traceparent": "00-" + "1" * 32 + "-" + "2" * 16 + "-01",
        "tracestate": "example=synthetic",
        "baggage": "example=private-canary",
    }
    with (
        gateway_peer() as peer,
        HTTPSystemOneAdapter(
            api_key="credential-canary",
            base_url=peer.url,
            gateway=GatewayConfig(headers=fields),
        ) as adapter,
    ):
        adapter.system_one("state-canary", {})
    headers = observed_headers(peer)
    assert all(headers[name] == value for name, value in fields.items())
    captured = capsys.readouterr()
    assert '"event": "http.call"' in captured.err
    assert captured.out == ""
    assert all(
        value not in captured.err
        for value in ("private-canary", "credential-canary", "state-canary")
    )


@pytest.mark.parametrize("asynchronous", [False, True])
def test_retry_correlation_is_captured_once(asynchronous) -> None:
    """Changing a binding inside transport cannot change the logical call snapshot."""
    recorded = []
    with ExitStack() as stack:
        stack.enter_context(bind_request_id("original"))

        def handler(request: httpx.Request) -> httpx.Response:
            recorded.append(request.headers["example-request"])
            stack.enter_context(bind_request_id("changed"))
            return httpx.Response(503 if len(recorded) == 1 else 200, json=SUCCESS)

        gateway = GatewayConfig(request_id_header="Example-Request")
        if asynchronous:

            async def call() -> None:
                # Keep context tokens in the same task that acquired them.
                with ExitStack() as local:

                    def asynchronous_handler(request: httpx.Request) -> httpx.Response:
                        recorded.append(request.headers["example-request"])
                        local.enter_context(bind_request_id("changed"))
                        return httpx.Response(
                            503 if len(recorded) == 1 else 200, json=SUCCESS
                        )

                    async with AsyncHTTPSystemOneAdapter(
                        api_key="dummy",
                        gateway=gateway,
                        retry=RetryPolicy(2, 0, 0),
                        transport=httpx.MockTransport(asynchronous_handler),
                    ) as adapter:
                        await adapter.system_one("synthetic", {})

            asyncio.run(call())
        else:
            with HTTPSystemOneAdapter(
                api_key="dummy",
                gateway=gateway,
                retry=RetryPolicy(2, 0, 0),
                transport=httpx.MockTransport(handler),
            ) as adapter:
                adapter.system_one("synthetic", {})
    assert recorded == ["original", "original"]


def test_metadata_cannot_be_mutated() -> None:
    """Expose an immutable mapping rather than a caller-owned dictionary."""
    metadata = RequestMetadata(headers={"Example-Tenant": "synthetic"})
    assert isinstance(metadata.headers, MappingProxyType)
    assert metadata.headers["example-tenant"] == "synthetic"
