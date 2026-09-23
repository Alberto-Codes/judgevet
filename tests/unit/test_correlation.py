"""Prove caller correlation lifetime through real rendered HTTP diagnostics."""

import asyncio
import json

import httpx
import pytest

import judgevet
from tests.cli_process_support import SUCCESS
from tests.unit.test_event_contract import call, last_event

pytest_plugins = ["tests.unit.test_event_contract"]


def test_nested_and_exceptional_scope_restores(stream) -> None:
    """Restore the outer request identifier after normal and exceptional exits."""
    with judgevet.bind_request_id("outer"):
        call()
        with judgevet.bind_request_id("inner"):
            call()
        with judgevet.bind_request_id(None):
            call()
        with (
            pytest.raises(RuntimeError, match="deliberate"),
            judgevet.bind_request_id("failed"),
        ):
            call()
            raise RuntimeError("deliberate")
        call()
    call()
    assert [
        json.loads(line)["request_id"] for line in stream.getvalue().splitlines()
    ] == [
        "outer",
        "inner",
        None,
        "failed",
        "outer",
        None,
    ]


@pytest.mark.parametrize("value", ["", "a b", "a\nb", "é", "x" * 129, 1])
def test_invalid_identifier_keeps_outer_binding(stream, value) -> None:
    """Reject invalid syntax without exposing the value or changing scope."""
    with judgevet.bind_request_id("outer"):
        with (
            pytest.raises(ValueError, match="Invalid request identifier"),
            judgevet.bind_request_id(value),
        ):
            pytest.fail("invalid binding entered")
        call()
    assert last_event(stream)["request_id"] == "outer"


def test_concurrent_tasks_are_isolated(stream) -> None:
    """Interleave two bindings and observe separate terminal request identifiers."""

    async def run_case() -> None:
        ready = asyncio.Event()
        first_finished = asyncio.Event()
        entered = []

        async def task(identifier: str) -> None:
            with judgevet.bind_request_id(identifier):
                entered.append(identifier)
                if len(entered) == 2:
                    ready.set()
                await ready.wait()
                if identifier == "two":
                    await first_finished.wait()
                async with judgevet.AsyncHTTPSystemOneAdapter(
                    api_key="credential-canary",
                    transport=httpx.MockTransport(
                        lambda request: httpx.Response(200, json=SUCCESS)
                    ),
                ) as adapter:
                    await adapter.system_one("state-canary", {})
            if identifier == "one":
                first_finished.set()

        await asyncio.gather(task("one"), task("two"))
        assert {
            json.loads(line)["request_id"] for line in stream.getvalue().splitlines()
        } == {"one", "two"}
        call()
        assert last_event(stream)["request_id"] is None

    asyncio.run(run_case())


def test_child_task_inherits_creation_context(stream) -> None:
    """A child inherits the caller binding without mutating its parent's scope."""

    async def run_case() -> None:
        async def child() -> None:
            call()
            with judgevet.bind_request_id("child"):
                call()

        with judgevet.bind_request_id("parent"):
            await asyncio.create_task(child())
            call()
        assert [
            json.loads(line)["request_id"] for line in stream.getvalue().splitlines()
        ] == ["parent", "child", "parent"]

    asyncio.run(run_case())


def test_cancellation_logs_once_and_restores_scope(stream) -> None:
    """Cancellation propagates, records a terminal error and restores context."""

    async def run_case() -> None:
        assert hasattr(judgevet, "bind_request_id")
        entered = asyncio.Event()

        async def respond(request: httpx.Request) -> httpx.Response:
            entered.set()
            await asyncio.Event().wait()
            return httpx.Response(200, json=SUCCESS)

        async def task() -> None:
            try:
                with judgevet.bind_request_id("cancelled"):
                    async with judgevet.AsyncHTTPSystemOneAdapter(
                        api_key="credential-canary",
                        transport=httpx.MockTransport(respond),
                    ) as adapter:
                        await adapter.system_one("state-canary", {})
            finally:
                call()

        running = asyncio.create_task(task())
        await asyncio.wait_for(entered.wait(), 2)
        running.cancel()
        with pytest.raises(asyncio.CancelledError):
            await running
        events = [json.loads(line) for line in stream.getvalue().splitlines()]
        assert len(events) == 2
        assert events[0]["request_id"] == "cancelled"
        assert events[0]["outcome"] == "error"
        assert events[0]["status_code"] is None
        assert events[0]["resolved_model"] is None
        assert events[1]["request_id"] is None

    asyncio.run(run_case())
