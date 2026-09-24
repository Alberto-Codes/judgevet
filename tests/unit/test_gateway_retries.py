"""Check gateway errors, retry snapshots and task isolation with synthetic data."""

import asyncio

import httpx
import pytest

from judgevet import (
    AsyncHTTPSystemOneAdapter,
    GatewayConfig,
    HTTPSystemOneAdapter,
    RequestMetadata,
    RetryPolicy,
    bind_request_id,
)
from judgevet.domain.errors import (
    JevAuthError,
    JevRateLimitError,
    JevRequestError,
    JevServiceError,
)
from tests.cli_process_support import SUCCESS
from tests.gateway_support import gateway_peer


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    "status,error,count",
    [
        (401, JevAuthError, 1),
        (403, JevAuthError, 1),
        (422, JevRequestError, 1),
        (429, JevRateLimitError, 2),
        (503, JevServiceError, 2),
    ],
)
@pytest.mark.parametrize(
    "body", [{"gateway_error": "private-canary"}, "<html>private-canary</html>"]
)
def test_gateway_error_body_is_not_assumed(
    asynchronous, status, error, count, body
) -> None:
    """Classify status and retry limits independently of vendor error envelopes."""
    with gateway_peer() as peer:
        peer.status, peer.body = status, body
        if asynchronous:

            async def call() -> None:
                async with AsyncHTTPSystemOneAdapter(
                    api_key="dummy",
                    base_url=peer.url,
                    gateway=GatewayConfig(),
                    retry=RetryPolicy(2, 0, 0),
                ) as adapter:
                    with pytest.raises(error) as caught:
                        await adapter.system_one("synthetic", {})
                    assert "private-canary" not in str(caught.value)

            asyncio.run(call())
        else:
            with HTTPSystemOneAdapter(
                api_key="dummy",
                base_url=peer.url,
                gateway=GatewayConfig(),
                retry=RetryPolicy(2, 0, 0),
            ) as adapter:
                with pytest.raises(error) as caught:
                    adapter.system_one("synthetic", {})
                assert "private-canary" not in str(caught.value)
        assert len(peer.requests) == count


@pytest.mark.parametrize("asynchronous", [False, True])
def test_retry_reuses_metadata_snapshot(asynchronous) -> None:
    """Mutating caller maps after the first attempt cannot change later headers."""
    defaults = {"Example-Tenant": "initial"}
    overrides = {"Example-Route": "initial"}
    gateway = GatewayConfig(headers=defaults)
    metadata = RequestMetadata(headers=overrides)
    recorded = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded.append(dict(request.headers))
        defaults["Example-Tenant"] = "changed"
        overrides["Example-Route"] = "changed"
        return httpx.Response(503 if len(recorded) == 1 else 200, json=SUCCESS)

    if asynchronous:

        async def call() -> None:
            async with AsyncHTTPSystemOneAdapter(
                api_key="dummy",
                gateway=gateway,
                transport=httpx.MockTransport(handler),
                retry=RetryPolicy(2, 0, 0),
            ) as adapter:
                await adapter.system_one("synthetic", {}, metadata=metadata)

        asyncio.run(call())
    else:
        with HTTPSystemOneAdapter(
            api_key="dummy",
            gateway=gateway,
            transport=httpx.MockTransport(handler),
            retry=RetryPolicy(2, 0, 0),
        ) as adapter:
            adapter.system_one("synthetic", {}, metadata=metadata)
    assert len(recorded) == 2
    assert recorded[0] == recorded[1]
    assert recorded[1]["example-tenant"] == "initial"
    assert recorded[1]["example-route"] == "initial"


def test_concurrent_scopes_do_not_share_headers() -> None:
    """Interleave tasks on one adapter and keep per-call fields isolated."""
    recorded = []

    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0)
        recorded.append(
            (request.headers["example-request"], request.headers["example-task"])
        )
        return httpx.Response(200, json=SUCCESS)

    async def run() -> None:
        async with AsyncHTTPSystemOneAdapter(
            api_key="dummy",
            gateway=GatewayConfig(request_id_header="Example-Request"),
            transport=httpx.MockTransport(handler),
        ) as adapter:

            async def call(name: str) -> None:
                with bind_request_id(name):
                    await adapter.system_one(
                        "synthetic",
                        {},
                        metadata=RequestMetadata(headers={"Example-Task": name}),
                    )

            await asyncio.gather(call("first"), call("second"))

    asyncio.run(run())
    assert sorted(recorded) == [("first", "first"), ("second", "second")]
