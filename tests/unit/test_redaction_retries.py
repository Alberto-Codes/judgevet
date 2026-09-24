"""Prove redaction ownership across retries, separate calls and async tasks."""

import asyncio
import json

import httpx
import pytest

from judgevet import AsyncHTTPSystemOneAdapter, GatewayConfig, HTTPSystemOneAdapter
from tests.cli_process_support import SUCCESS
from tests.redaction_support import State, SyntheticRedactor, invoke


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("failure", ["service", "transport"])
def test_redaction_snapshot_reused_across_retries(asynchronous, failure) -> None:
    """Retained callback output and original input cannot rewrite retries."""
    state = {"content": "state-canary"}
    redactor = SyntheticRedactor()
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request.content)
        if len(sent) == 1:
            state["content"] = "late-input"
            assert isinstance(redactor.output, dict)
            redactor.output["content"] = "late-output"
            if failure == "transport":
                raise httpx.ReadTimeout("synthetic timeout", request=request)
            return httpx.Response(503, json={"gateway_error": "synthetic"})
        return httpx.Response(200, json=SUCCESS)

    invoke(
        asynchronous,
        redactor,
        state,
        url="https://gateway.example/prefix",
        transport=httpx.MockTransport(handler),
    )
    assert redactor.calls == 1
    assert len(sent) == 2
    assert sent[0] == sent[1]
    assert json.loads(sent[1])["state"] == {"content": "removed"}
    assert b"state-canary" not in sent[1]


@pytest.mark.parametrize("asynchronous", [False, True])
def test_separate_calls_transform_again(asynchronous) -> None:
    """One adapter invokes its redactor once per logical call, not per lifetime."""
    redactor = SyntheticRedactor()
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content)["state"])
        return httpx.Response(200, json=SUCCESS)

    if asynchronous:

        async def call() -> None:
            async with AsyncHTTPSystemOneAdapter(
                api_key="dummy",
                redactor=redactor,
                transport=httpx.MockTransport(handler),
            ) as adapter:
                await adapter.system_one("first state-canary", {})
                await adapter.system_one("second state-canary", {})

        asyncio.run(call())
    else:
        with HTTPSystemOneAdapter(
            api_key="dummy", redactor=redactor, transport=httpx.MockTransport(handler)
        ) as adapter:
            adapter.system_one("first state-canary", {})
            adapter.system_one("second state-canary", {})
    assert redactor.calls == 2
    assert sent == ["first removed", "second removed"]


def test_concurrent_calls_use_distinct_snapshots() -> None:
    """Shared async adapters retain request-local copies before yielding to IO."""
    redactor = SyntheticRedactor()
    inputs = [{"task": name, "content": "state-canary"} for name in ("first", "second")]
    sent = []

    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0)
        sent.append(json.loads(request.content)["state"])
        return httpx.Response(200, json=SUCCESS)

    async def call() -> None:
        async with AsyncHTTPSystemOneAdapter(
            api_key="dummy", redactor=redactor, transport=httpx.MockTransport(handler)
        ) as adapter:
            await asyncio.gather(*(adapter.system_one(state, {}) for state in inputs))

    asyncio.run(call())
    assert redactor.calls == 2
    assert sorted(sent, key=lambda state: state["task"]) == [
        {"task": name, "content": "removed"} for name in ("first", "second")
    ]
    assert all(state["content"] == "state-canary" for state in inputs)


class CancelRedactor:
    """Cancel an async logical call before its first transmission."""

    def redact(self, state: State) -> State:
        """Propagate cancellation without retry or original-state fallback."""
        raise asyncio.CancelledError


def test_cancellation_prevents_transport() -> None:
    """Cancellation during redaction must not become a transport retry."""
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json=SUCCESS)

    with pytest.raises(asyncio.CancelledError):
        invoke(
            True,
            CancelRedactor(),
            "state-canary",
            url="https://gateway.example",
            transport=httpx.MockTransport(handler),
        )
    assert sent == []


def test_state_redaction_does_not_transform_other_fields() -> None:
    """The same sentinel in explicit question/header channels remains caller-owned."""
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=SUCCESS)

    with HTTPSystemOneAdapter(
        api_key="dummy",
        redactor=SyntheticRedactor(),
        gateway=GatewayConfig(headers={"Example-Explicit": "state-canary"}),
        transport=httpx.MockTransport(handler),
    ) as adapter:
        adapter.system_one(
            "state-canary", {"q": {"type": "noul", "instructions": "state-canary"}}
        )
    assert json.loads(captured[0].content)["state"] == "removed"
    assert (
        json.loads(captured[0].content)["questions"]["q"]["instructions"]
        == "state-canary"
    )
    assert captured[0].headers["example-explicit"] == "state-canary"
