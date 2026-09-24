"""Check redactor failure boundaries and unchanged default serialization."""

import asyncio
from typing import Any, Self

import httpx
import pytest

from judgevet import AsyncHTTPSystemOneAdapter, HTTPSystemOneAdapter, StateRedactor
from tests.cli_process_support import SUCCESS
from tests.gateway_support import gateway_peer
from tests.redaction_support import State, SyntheticRedactor, invoke


class CopyFailure(dict[str, Any]):
    """Fail copying a caller-provided dictionary before invoking its redactor."""

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        """Expose a synthetic copy failure without permitting transmission."""
        raise ValueError("synthetic copy failure")


@pytest.mark.parametrize("asynchronous", [False, True])
def test_copy_failure_prevents_redactor_and_transport(asynchronous) -> None:
    """Copy failures must not leak into retry or fallback paths."""
    redactor = SyntheticRedactor()
    with gateway_peer() as peer:
        with pytest.raises(ValueError, match="synthetic copy failure"):
            invoke(
                asynchronous,
                redactor,
                CopyFailure(content="state-canary"),
                url=peer.url,
            )
        assert peer.requests == []
    assert redactor.calls == 0


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("output", [None, 42, True, ("tuple",)])
def test_untyped_callback_root_is_rejected(asynchronous, output) -> None:
    """A dynamically typed application can violate the protocol at runtime."""

    class UntypedApplicationRedactor:
        """Model an untyped plugin with a deliberately invalid output root."""

        calls = 0

        def redact(self, state):
            """Return the supplied invalid runtime value."""
            self.calls += 1
            return output

    redactor = UntypedApplicationRedactor()
    with gateway_peer() as peer:
        with pytest.raises(TypeError, match="State redactor must return"):
            invoke(asynchronous, redactor, "state-canary", url=peer.url)
        assert peer.requests == []
    assert redactor.calls == 1


class IdentityRedactor:
    """Keep copied Unicode JSON data unchanged for a wire-equivalence check."""

    def redact(self, state: State) -> State:
        """Return the supplied copy without changing content."""
        return state


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("redactor", [None, IdentityRedactor()])
def test_default_and_identity_match_httpx_bytes(
    asynchronous, redactor: StateRedactor | None
) -> None:
    """Omitted/default paths and opt-in identity output share UTF-8 wire semantics."""
    state = {"content": ["café", "λ", 1.25, True, None]}
    payload = {"state": state, "questions": {}, "model": "jev-latest"}
    expected = httpx.Request("POST", "https://example.invalid", json=payload).content
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.content)
        return httpx.Response(200, json=SUCCESS)

    if asynchronous:

        async def call() -> None:
            async with AsyncHTTPSystemOneAdapter(
                api_key="dummy",
                redactor=redactor,
                transport=httpx.MockTransport(handler),
            ) as adapter:
                await adapter.system_one(state, {})

        asyncio.run(call())
    else:
        with HTTPSystemOneAdapter(
            api_key="dummy", redactor=redactor, transport=httpx.MockTransport(handler)
        ) as adapter:
            adapter.system_one(state, {})
    assert captured == [expected]


def test_default_path_does_not_copy_state() -> None:
    """The no-op default does not introduce new copy behavior for callers."""
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.content)
        return httpx.Response(200, json=SUCCESS)

    with HTTPSystemOneAdapter(
        api_key="dummy", transport=httpx.MockTransport(handler)
    ) as adapter:
        adapter.system_one(CopyFailure(content="synthetic"), {})
    assert len(captured) == 1
    assert b"synthetic" in captured[0]
