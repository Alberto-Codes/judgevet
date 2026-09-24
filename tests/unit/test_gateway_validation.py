"""Reject unsafe metadata before it reaches the transport."""

import asyncio

import pytest

from judgevet import (
    AsyncHTTPSystemOneAdapter,
    GatewayConfig,
    HTTPSystemOneAdapter,
    RequestMetadata,
    bind_request_id,
)
from tests.gateway_support import gateway_peer, observed_headers

PROTECTED = [
    "Authorization",
    "Proxy-Authorization",
    "Host",
    "Content-Type",
    "Content-Length",
    "Content-Encoding",
    "Transfer-Encoding",
    "Connection",
    "Keep-Alive",
    "TE",
    "Trailer",
    "Upgrade",
    "Expect",
    "Cookie",
    "Set-Cookie",
    "x-apikey",
]
INVALID = [
    {"": "value"},
    {"Bad Name": "value"},
    {"Bad:Name": "value"},
    {"A": "one", "a": "two"},
    {"A" * 129: "value"},
    {"A": "\r\ninjected: canary"},
    {"A": "\0"},
    {"A": "\t"},
    {"A": "\x7f"},
    {"A": "é"},
    {"A": " space"},
    {"A": "space "},
    {"A": "v" * 2049},
    {str(i): "x" for i in range(33)},
    {str(i): "v" * 2048 for i in range(4)},
]


@pytest.mark.parametrize(
    "headers", INVALID + [{name.swapcase(): "sentinel-canary"} for name in PROTECTED]
)
@pytest.mark.parametrize("per_call", [False, True])
def test_invalid_fields_never_transmit(headers, per_call) -> None:
    """Reject each unsafe input with value-free exceptions and zero requests."""
    with gateway_peer() as peer:
        with pytest.raises(ValueError) as caught:
            gateway = GatewayConfig(
                auth_header="x-apikey",
                auth_scheme="",
                headers=None if per_call else headers,
            )
            with HTTPSystemOneAdapter(
                api_key="dummy", base_url=peer.url, gateway=gateway
            ) as adapter:
                adapter.system_one(
                    "synthetic",
                    {},
                    metadata=RequestMetadata(headers=headers) if per_call else None,
                )
        assert peer.requests == []
    assert "sentinel-canary" not in str(caught.value)


@pytest.mark.parametrize(
    "name", ["Host", "Content-Type", "traceparent", "tracestate", "baggage", "Bad Name"]
)
def test_invalid_auth_header(name) -> None:
    """Reject routing, payload and trace fields as authentication names."""
    with pytest.raises(ValueError):
        GatewayConfig(auth_header=name)


@pytest.mark.parametrize("scheme", ["Bearer canary", "Bearer\n", "é"])
def test_invalid_scheme(scheme) -> None:
    """Reject non-token scheme prefixes."""
    with pytest.raises(ValueError):
        GatewayConfig(auth_scheme=scheme)


@pytest.mark.parametrize(
    "key", ["canary\r\nx: y", "canary\0", "canaryé", " canary", "canary "]
)
def test_invalid_credentials_never_transmit(key) -> None:
    """Reject unsafe credential values even with direct defaults."""
    with gateway_peer() as peer:
        with pytest.raises(ValueError) as caught:
            HTTPSystemOneAdapter(api_key=key, base_url=peer.url)
        assert peer.requests == []
    assert "canary" not in str(caught.value)


@pytest.mark.parametrize(
    "name",
    ["Authorization", "x-apikey", "traceparent", "tracestate", "baggage", "Host"],
)
def test_invalid_correlation_header(name) -> None:
    """Prevent correlation from overwriting authentication or tracing."""
    with pytest.raises(ValueError):
        GatewayConfig(auth_header="x-apikey", request_id_header=name)


def test_correlation_conflict_and_merged_bounds() -> None:
    """Validate conflicts and limits after combining individually valid maps."""
    with gateway_peer() as peer:
        config = GatewayConfig(request_id_header="Example-Request")
        with (
            HTTPSystemOneAdapter(
                api_key="dummy", base_url=peer.url, gateway=config
            ) as adapter,
            bind_request_id("scope"),
            pytest.raises(ValueError),
        ):
            adapter.system_one(
                "synthetic",
                {},
                metadata=RequestMetadata(headers={"example-request": "other"}),
            )
        config = GatewayConfig(headers={str(i): "x" for i in range(32)})
        with (
            HTTPSystemOneAdapter(
                api_key="dummy", base_url=peer.url, gateway=config
            ) as adapter,
            pytest.raises(ValueError),
        ):
            adapter.system_one(
                "synthetic", {}, metadata=RequestMetadata(headers={"extra": "x"})
            )
        assert peer.requests == []


def test_exact_valid_boundaries_and_private_repr() -> None:
    """Accept exact length limits, empty values and printable token punctuation."""
    headers = {"N" * 128: "v" * 2048, "B": "v" * 2048, "C": "v" * 2048, "D": "v" * 1917}
    assert sum(len(k) + len(v) for k, v in headers.items()) == 8192
    config = GatewayConfig(headers=headers)
    metadata = RequestMetadata(headers={"Example-Secret": "sentinel-canary"})
    assert "sentinel-canary" not in repr(metadata)
    assert "sentinel-canary" not in repr(GatewayConfig(headers=metadata.headers))
    with gateway_peer() as peer:
        with HTTPSystemOneAdapter(
            api_key="dummy", base_url=peer.url, gateway=config
        ) as adapter:
            adapter.system_one("synthetic", {})
        with HTTPSystemOneAdapter(api_key="dummy", base_url=peer.url) as adapter:
            adapter.system_one(
                "synthetic",
                {},
                metadata=RequestMetadata(headers={"!#$%&'*+-.^_`|~": ""}),
            )
    assert observed_headers(peer)["n" * 128] == "v" * 2048
    assert observed_headers(peer, 1)["!#$%&'*+-.^_`|~"] == ""


@pytest.mark.parametrize("headers", INVALID + [{name: "canary"} for name in PROTECTED])
def test_async_invalid_fields_never_transmit(headers) -> None:
    """Exercise async validation before opening a connection."""

    async def call(url: str) -> None:
        with pytest.raises(ValueError):
            async with AsyncHTTPSystemOneAdapter(
                api_key="dummy",
                base_url=url,
                gateway=GatewayConfig(auth_header="x-apikey"),
            ) as adapter:
                await adapter.system_one(
                    "synthetic", {}, metadata=RequestMetadata(headers=headers)
                )

    with gateway_peer() as peer:
        asyncio.run(call(peer.url))
        assert peer.requests == []


def test_exact_field_count_and_merged_byte_limit() -> None:
    """Accept 32 fields and reject oversized merged maps and added correlation."""
    with gateway_peer() as peer:
        config = GatewayConfig(headers={str(i): "x" for i in range(32)})
        with HTTPSystemOneAdapter(
            api_key="dummy", base_url=peer.url, gateway=config
        ) as adapter:
            adapter.system_one("synthetic", {})
        config = GatewayConfig(headers={str(i): "x" * 2048 for i in range(3)})
        with (
            HTTPSystemOneAdapter(
                api_key="dummy", base_url=peer.url, gateway=config
            ) as adapter,
            pytest.raises(ValueError),
        ):
            adapter.system_one(
                "synthetic",
                {},
                metadata=RequestMetadata(headers={"extra": "x" * 2048}),
            )
        config = GatewayConfig(
            headers={str(i): "x" for i in range(32)},
            request_id_header="Example-Request",
        )
        with (
            HTTPSystemOneAdapter(
                api_key="dummy", base_url=peer.url, gateway=config
            ) as adapter,
            bind_request_id("bounded"),
            pytest.raises(ValueError),
        ):
            adapter.system_one("synthetic", {})
        assert len(peer.requests) == 1
