"""Exercise selected MCP providers through SDK dispatch and the command root."""

import asyncio
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

import pytest
from mcp.types import CallToolRequestParams

from judgevet import NoulAnswer, SystemOnePort, SystemOneResponse, Usage
from judgevet.adapters.inbound import mcp_entrypoint as entry
from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.domain.questions import Question
from judgevet.providers import ProviderTransportError, ProviderUnavailableError


class RecordingProvider:
    """Record real synchronous calls and optionally block until released."""

    def __init__(self, *, block: bool = False, fail: bool = False) -> None:
        """Create an offline provider with an externally controlled barrier."""
        self.block = block
        self.fail = fail
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls: list[tuple[object, object, str]] = []
        self.threads: list[int] = []
        self.closed = 0

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Return a typed result after recording the actual request."""
        self.calls.append((state, questions, model))
        self.threads.append(threading.get_ident())
        self.started.set()
        if self.block and not self.release.wait(5):
            raise RuntimeError("event loop did not release the provider")
        if self.fail:
            raise ProviderTransportError("fixture transport failed")
        return SystemOneResponse(
            model="fixture-resolved",
            usage=Usage(19, None),
            answers={"noul_question": NoulAnswer(noul=0.9)},
        )

    def close(self) -> None:
        """Record explicit caller cleanup."""
        self.closed += 1


def params() -> CallToolRequestParams:
    """Return SDK parameters with nontrivial state and instructions."""
    return CallToolRequestParams(
        name="ask_noul",
        arguments={"state": {"items": ["exact"]}, "instruction": "Keep this text"},
    )


def test_selected_model_and_borrowed_lifetime() -> None:
    """Preserve SDK result shape, model selection and borrowed ownership."""
    provider = RecordingProvider()
    server = create_mcp_server(provider, model="fixture-selected")

    async def exercise() -> None:
        async with server.lifespan(server):
            result = await server._request_handlers["tools/call"].handler(
                None, params()
            )
            assert result.structured_content == {
                "noul": 0.9,
                "model": "fixture-resolved",
                "usage": {"input_tokens": 19, "output_tokens": None},
            }

    asyncio.run(exercise())
    assert provider.calls == [
        (
            {"items": ["exact"]},
            {"noul_question": {"type": "noul", "instructions": "Keep this text"}},
            "fixture-selected",
        )
    ]
    assert provider.closed == 0
    assert provider.threads[0] != threading.get_ident()


def test_cancellation_drains_running_and_skips_queued() -> None:
    """Keep the loop responsive and wait for running work despite cancellation."""
    provider = RecordingProvider(block=True)
    server = create_mcp_server(provider, model="fixture-selected")

    async def exercise() -> None:
        async with server.lifespan(server):
            handler = server._request_handlers["tools/call"].handler
            running = asyncio.create_task(handler(None, params()))
            try:
                started = await asyncio.to_thread(provider.started.wait, 2)
                assert started, "provider never started"
                assert not running.done(), "synchronous work blocked the event loop"
                queued = asyncio.create_task(handler(None, params()))
                await asyncio.sleep(0)
                queued.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await queued
                running.cancel()
                await asyncio.sleep(0.02)
                running.cancel()
                await asyncio.sleep(0.02)
                assert not running.done(), "cancellation abandoned live provider work"
                assert len(provider.calls) == 1
            finally:
                provider.release.set()
            with pytest.raises(asyncio.CancelledError):
                await running
        assert len(provider.calls) == 1
        assert provider.closed == 0

    asyncio.run(exercise())


@pytest.mark.parametrize("owned", [False, True])
@pytest.mark.parametrize("fail", [False, True])
def test_entrypoint_selection_and_thread_affinity(
    monkeypatch: pytest.MonkeyPatch,
    owned: bool,
    fail: bool,
) -> None:
    """Run the command root with explicit selection and observed cleanup.

    A declared provider failure is a tool error result, so serving continues.
    """
    provider = RecordingProvider(fail=fail)
    lifecycle: list[tuple[str, int]] = []
    results: list[Any] = []
    monkeypatch.setenv("JEV_API__TIMEOUT_SECONDS", "invalid-hosted-value")

    @contextmanager
    def factory() -> Iterator[RecordingProvider]:
        lifecycle.append(("enter", threading.get_ident()))
        try:
            yield provider
        finally:
            lifecycle.append(("exit", threading.get_ident()))
            provider.close()

    async def serve(port: SystemOnePort, *, model: str = "jev-latest") -> None:
        server = create_mcp_server(port, model=model)
        async with server.lifespan(server):
            handler = server._request_handlers["tools/call"].handler
            results.append(await handler(None, params()))

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("selected provider fell back to hosted construction")

    monkeypatch.setattr(entry, "run_stdio", serve)
    monkeypatch.setattr(entry, "build_adapter", forbidden)
    if owned:
        assert entry.main(provider_factory=factory, model="fixture-selected") == 0
    else:
        assert entry.main(port=provider, model="fixture-selected") == 0
    assert [result.is_error for result in results] == [fail]
    assert provider.calls[0][2] == "fixture-selected"
    assert provider.closed == int(owned)
    if owned:
        assert [name for name, _ in lifecycle] == ["enter", "exit"]
        assert len({thread for _, thread in lifecycle} | set(provider.threads)) == 1
        assert lifecycle[0][1] != threading.get_ident()


def test_unavailable_factory_never_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """Report setup failure without constructing the hosted adapter."""
    events: list[str] = []

    @contextmanager
    def unavailable() -> Iterator[RecordingProvider]:
        events.append("setup")
        try:
            raise ProviderUnavailableError("fixture unavailable")
            yield RecordingProvider()
        finally:
            events.append("rollback")

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("unavailable provider fell back to hosted construction")

    monkeypatch.setattr(entry, "build_adapter", forbidden)
    with pytest.raises(
        SystemExit,
        match=r"^judgevet-mcp: provider acquisition failed \(ProviderUnavailableError\)$",
    ):
        entry.main(provider_factory=unavailable, model="fixture-selected")
    assert events == ["setup", "rollback"]


def test_owned_entrypoint_drains_before_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep an owned provider alive until canceled synchronous work has ended."""
    provider = RecordingProvider(block=True)
    events: list[str] = []

    @contextmanager
    def factory() -> Iterator[RecordingProvider]:
        events.append("enter")
        try:
            yield provider
        finally:
            assert provider.release.is_set(), "closed while provider call was running"
            events.append("exit")
            provider.close()

    async def serve(port: SystemOnePort, *, model: str = "jev-latest") -> None:
        server = create_mcp_server(port, model=model)
        async with server.lifespan(server):
            running = asyncio.create_task(
                server._request_handlers["tools/call"].handler(None, params())
            )
            try:
                assert await asyncio.to_thread(provider.started.wait, 2)
                running.cancel()
                await asyncio.sleep(0.02)
                running.cancel()
                await asyncio.sleep(0.02)
                assert not running.done()
                assert provider.closed == 0
            finally:
                provider.release.set()
            await running

    monkeypatch.setattr(entry, "run_stdio", serve)
    with pytest.raises(asyncio.CancelledError):
        entry.main(provider_factory=factory, model="fixture-selected")
    assert events == ["enter", "exit"]
    assert provider.closed == 1


def test_canceled_acquisition_unwinds_on_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drain canceled factory entry and exit its context on the same worker."""
    started = threading.Event()
    release = threading.Event()
    lifecycle: list[tuple[str, int]] = []
    provider = RecordingProvider()

    @contextmanager
    def factory() -> Iterator[RecordingProvider]:
        lifecycle.append(("enter", threading.get_ident()))
        started.set()
        if not release.wait(5):
            raise RuntimeError("test did not release factory acquisition")
        try:
            yield provider
        finally:
            lifecycle.append(("exit", threading.get_ident()))
            provider.close()

    async def forbidden(port: SystemOnePort, *, model: str = "jev-latest") -> None:
        pytest.fail("canceled acquisition proceeded to serving")

    async def exercise() -> None:
        stage = entry._Stage("provider acquisition")
        acquiring = asyncio.create_task(
            entry._run_selected(None, factory, "fixture", stage)
        )
        try:
            assert await asyncio.to_thread(started.wait, 2)
            acquiring.cancel()
            await asyncio.sleep(0.02)
            acquiring.cancel()
            await asyncio.sleep(0.02)
            assert not acquiring.done()
            assert provider.closed == 0
        finally:
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await acquiring
        assert stage.name == "provider acquisition"

    monkeypatch.setattr(entry, "run_stdio", forbidden)
    asyncio.run(exercise())
    assert [name for name, _ in lifecycle] == ["enter", "exit"]
    assert lifecycle[0][1] == lifecycle[1][1] != threading.get_ident()
    assert provider.closed == 1
