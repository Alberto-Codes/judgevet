"""Prove gateway authentication, prefixes and explicit metadata on real requests."""

import asyncio

import httpx
import pytest
import structlog

from judgevet import (
    AsyncHTTPSystemOneAdapter,
    GatewayConfig,
    HTTPSystemOneAdapter,
    RequestMetadata,
    bind_request_id,
)
from tests.gateway_support import gateway_peer, observed_headers


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("suffix", ["/organization/jev", "/organization/jev/"])
@pytest.mark.parametrize(
    "auth,scheme",
    [("x-apikey", ""), ("Ocp-Apim-Subscription-Key", ""), ("Authorization", "Bearer")],
)
def test_gateway_wire_contract(asynchronous, suffix, auth, scheme) -> None:
    """Observe chosen auth, two fields, case-insensitive overrides and URL prefixes."""
    defaults = {"Example-Tenant": "synthetic", "Example-Route": "default"}
    overrides = {"EXAMPLE-ROUTE": "override"}
    gateway = GatewayConfig(auth_header=auth, auth_scheme=scheme, headers=defaults)
    metadata = RequestMetadata(headers=overrides)
    defaults["Example-Tenant"] = "mutated"
    overrides["EXAMPLE-ROUTE"] = "mutated"
    with gateway_peer() as peer:
        if asynchronous:

            async def call() -> None:
                async with AsyncHTTPSystemOneAdapter(
                    api_key="dummy-key", base_url=peer.url + suffix, gateway=gateway
                ) as adapter:
                    await adapter.system_one("synthetic", {}, metadata=metadata)

            asyncio.run(call())
        else:
            with HTTPSystemOneAdapter(
                api_key="dummy-key", base_url=peer.url + suffix, gateway=gateway
            ) as adapter:
                adapter.system_one("synthetic", {}, metadata=metadata)
    assert peer.requests[0][0] == "/organization/jev/v1/systemone"
    headers = observed_headers(peer)
    assert headers[auth.lower()] == (scheme + " " if scheme else "") + "dummy-key"
    assert headers["example-tenant"] == "synthetic"
    assert headers["example-route"] == "override"
    assert headers["content-type"] == "application/json"
    if auth != "Authorization":
        assert "authorization" not in headers


@pytest.mark.parametrize("propagate", [False, True])
def test_correlation_disclosure_is_explicit(propagate) -> None:
    """Forward only the selected scope and keep arbitrary logging context local."""
    gateway = GatewayConfig(request_id_header="Example-Request" if propagate else None)
    with (
        gateway_peer() as peer,
        structlog.contextvars.bound_contextvars(private="context-canary"),
        HTTPSystemOneAdapter(
            api_key="dummy", base_url=peer.url, gateway=gateway
        ) as adapter,
    ):
        with bind_request_id("outer"):
            with bind_request_id("inner"):
                adapter.system_one("synthetic", {})
            adapter.system_one("synthetic", {})
        adapter.system_one("synthetic", {})
    assert [observed_headers(peer, i).get("example-request") for i in range(3)] == (
        ["inner", "outer", None] if propagate else [None, None, None]
    )
    assert "context-canary" not in str(peer.requests)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("same_origin", [False, True])
def test_redirect_does_not_disclose(asynchronous, same_origin) -> None:
    """Observe zero redirected requests at an independent listener."""
    gateway = GatewayConfig(headers={"Example-Tenant": "canary"})
    with gateway_peer() as origin, gateway_peer() as destination:
        origin.status = 307
        origin.location = (origin.url if same_origin else destination.url) + "/capture"
        if asynchronous:

            async def call() -> None:
                async with AsyncHTTPSystemOneAdapter(
                    api_key="dummy", base_url=origin.url, gateway=gateway
                ) as adapter:
                    with pytest.raises(httpx.HTTPStatusError):
                        await adapter.system_one("synthetic", {})

            asyncio.run(call())
        else:
            with (
                HTTPSystemOneAdapter(
                    api_key="dummy", base_url=origin.url, gateway=gateway
                ) as adapter,
                pytest.raises(httpx.HTTPStatusError),
            ):
                adapter.system_one("synthetic", {})
        assert destination.requests == []
        assert len(origin.requests) == 1
