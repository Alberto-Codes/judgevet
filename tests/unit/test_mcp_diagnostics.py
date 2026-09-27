"""Verify judgevet-mcp names the failed stage and exception type, never its text."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest

from judgevet.adapters.inbound import mcp_entrypoint as entry
from judgevet.adapters.inbound.settings import Settings
from judgevet.domain.errors import JevAuthError
from judgevet.ports import SystemOnePort
from judgevet.providers import ProviderUnavailableError
from judgevet.testing import FakeSystemOnePort

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(entry.stdio_server is None, reason="requires MCP extra"),
]

CANARY = "sk-live-SECRET123"


class ClosingPort(FakeSystemOnePort):
    """Offline hosted adapter double that accepts the composition root's close."""

    def close(self) -> None:
        """Accept cleanup after serving ends."""


def fatal(capsys: pytest.CaptureFixture[str], run: Callable[[], object]) -> str:
    """Require exit 1 without the canary or a cause chain, and return the message.

    Args:
        capsys: Captured process streams.
        run: Call that must end the command.

    Returns:
        The SystemExit message.
    """
    with pytest.raises(SystemExit) as caught:
        run()
    output = capsys.readouterr()
    message = caught.value.code
    assert isinstance(message, str)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    assert output.out == ""
    assert CANARY not in message + output.err
    return message


def test_credential_resolution(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Name credential resolution when the hosted adapter cannot be built."""
    monkeypatch.setenv("JEV_API__KEY", CANARY)

    def fail(settings: Settings) -> ClosingPort:
        raise ValueError(CANARY)

    monkeypatch.setattr(entry, "build_adapter", fail)
    assert (
        fatal(capsys, entry.main)
        == "judgevet-mcp: credential resolution failed (ValueError)"
    )


def test_provider_acquisition(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Name provider acquisition when an application factory cannot supply one."""

    @contextmanager
    def unavailable() -> Iterator[FakeSystemOnePort]:
        raise ProviderUnavailableError(CANARY)
        yield FakeSystemOnePort()

    async def forbidden(port: SystemOnePort, *, model: str = "jev-latest") -> None:
        pytest.fail("serving started without a provider")

    monkeypatch.setattr(entry, "run_stdio", forbidden)
    message = fatal(capsys, lambda: entry.main(provider_factory=unavailable))
    assert message == (
        "judgevet-mcp: provider acquisition failed (ProviderUnavailableError)"
    )


@pytest.mark.parametrize("hosted", [True, False])
def test_serving(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    hosted: bool,
) -> None:
    """Name serving when the stdio run fails after a provider is available."""
    monkeypatch.setenv("JEV_API__KEY", CANARY)

    async def serve(port: SystemOnePort, *, model: str = "jev-latest") -> None:
        raise OSError(CANARY)

    monkeypatch.setattr(entry, "build_adapter", lambda settings: ClosingPort())
    monkeypatch.setattr(entry, "run_stdio", serve)
    run = entry.main if hosted else lambda: entry.main(port=FakeSystemOnePort())
    assert fatal(capsys, run) == "judgevet-mcp: serving failed (OSError)"


def test_grouped_leaves(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """List distinct grouped leaf types in order of first appearance."""

    async def serve(port: SystemOnePort, *, model: str = "jev-latest") -> None:
        raise ExceptionGroup(
            CANARY,
            [
                JevAuthError(CANARY, 401),
                ExceptionGroup(CANARY, [OSError(CANARY), JevAuthError(CANARY, 403)]),
                OSError(CANARY),
            ],
        )

    monkeypatch.setattr(entry, "run_stdio", serve)
    message = fatal(capsys, lambda: entry.main(port=FakeSystemOnePort()))
    assert message == "judgevet-mcp: serving failed (JevAuthError, OSError)"
