"""Verify MCP composition owns cleanup and keeps failure diagnostics safe."""

import asyncio
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any

import pytest

from judgevet.adapters.inbound import mcp_entrypoint as entry
from judgevet.adapters.inbound.settings import Settings
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(entry.stdio_server is None, reason="requires MCP extra"),
]


class RecordingPort:
    """Record closure of the port acquired by the composition root."""

    def __init__(self) -> None:
        """Start with no recorded closes."""
        self.close_count = 0

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Any],
        model: str,
    ) -> SystemOneResponse:
        """Return an offline answer envelope if the server asks a question."""
        return SystemOneResponse(model="jev-1.13.0", answers={}, usage=Usage(0, 0))

    def close(self) -> None:
        """Record the composition root closing its acquired port."""
        self.close_count += 1


def test_success_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Require successful serving to close the exact acquired port once."""
    monkeypatch.setenv("JEV_API__KEY", "judgevet-canary-25")
    port = RecordingPort()
    seen: list[RecordingPort] = []

    def build(settings: Settings) -> RecordingPort:
        return port

    async def serve(acquired: RecordingPort) -> None:
        seen.append(acquired)

    monkeypatch.setattr(entry, "build_adapter", build)
    monkeypatch.setattr(entry, "run_stdio", serve)
    assert entry.main() == 0
    assert seen == [port]
    assert port.close_count == 1


def test_constructor_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Require constructor failure to cross the safe error boundary."""
    canary = "judgevet-canary-25"
    monkeypatch.setenv("JEV_API__KEY", canary)

    def fail(settings: Settings) -> RecordingPort:
        raise RuntimeError(canary)

    monkeypatch.setattr(entry, "build_adapter", fail)
    with pytest.raises(
        SystemExit, match="judgevet-mcp: startup or runtime failure"
    ) as exc:
        entry.main()
    output = capsys.readouterr()
    assert output.out == ""
    assert canary not in str(exc.value) + output.out + output.err


class FailingServer:
    """Raise from serving after the stdio context has been entered."""

    def create_initialization_options(self) -> object:
        """Return a sentinel accepted by this server double."""
        return self

    async def run(self, read: object, write: object, options: object) -> None:
        """Fail after validating that the runner supplied our options."""
        assert options is self
        raise RuntimeError("canary-run")


@pytest.mark.parametrize("stage", ["factory", "stdio", "run"])
def test_serving_failure_closes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], stage: str
) -> None:
    """Require real runner failures to close the acquired port and hide details."""
    monkeypatch.setenv("JEV_API__KEY", "canary-key")
    port = RecordingPort()
    events: list[str] = []

    def build(settings: Settings) -> RecordingPort:
        return port

    def factory(acquired: RecordingPort) -> FailingServer:
        assert acquired is port
        events.append("factory")
        if stage == "factory":
            raise RuntimeError("canary-factory")
        return FailingServer()

    @asynccontextmanager
    async def streams() -> AsyncIterator[tuple[object, object]]:
        events.append("stdio")
        if stage == "stdio":
            raise OSError("canary-stdio")
        yield object(), object()
        pytest.fail("run failure did not propagate through the context")

    monkeypatch.setattr(entry, "build_adapter", build)
    monkeypatch.setattr(entry, "create_mcp_server", factory)
    monkeypatch.setattr(entry, "stdio_server", streams)
    with pytest.raises(SystemExit, match="startup or runtime failure") as exc:
        entry.main()
    assert events == (["factory"] if stage == "factory" else ["factory", "stdio"])
    assert port.close_count == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "canary" not in str(exc.value) + output.err


def test_interrupt_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Require interruption to close the port before returning exit 130."""
    monkeypatch.setenv("JEV_API__KEY", "canary-key")
    port = RecordingPort()

    def build(settings: Settings) -> RecordingPort:
        return port

    async def interrupt(acquired: RecordingPort) -> None:
        assert acquired is port
        raise KeyboardInterrupt

    monkeypatch.setattr(entry, "build_adapter", build)
    monkeypatch.setattr(entry, "run_stdio", interrupt)
    assert entry.main() == 130
    assert port.close_count == 1


def test_runner_requires_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """Require a direct runner call to reject an absent SDK."""
    monkeypatch.setattr(entry, "stdio_server", None)
    with pytest.raises(RuntimeError, match="MCP runtime not available"):
        asyncio.run(entry.run_stdio(RecordingPort()))
