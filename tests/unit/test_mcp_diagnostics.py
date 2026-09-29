"""Verify judgevet-mcp names the failed stage and exception type, never its text."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest

from judgevet.adapters.inbound import mcp_entrypoint as entry
from judgevet.adapters.inbound.settings import Settings
from judgevet.domain.errors import JevAuthError
from judgevet.ports import SystemOnePort
from judgevet.providers import ProviderFactory, ProviderUnavailableError
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


class FailingClosePort(FakeSystemOnePort):
    """Offline hosted adapter double whose close fails after serving ends."""

    def close(self) -> None:
        """Fail cleanup with canary text.

        Raises:
            OSError: Always, carrying the canary.
        """
        raise OSError(CANARY)


async def serve_cleanly(port: SystemOnePort, *, model: str = "jev-latest") -> None:
    """Return at once, as a stdio run that ends without error."""


def test_hosted_shutdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Name shutdown when the hosted adapter's close fails after clean serving."""
    monkeypatch.setenv("JEV_API__KEY", CANARY)
    monkeypatch.setattr(entry, "build_adapter", lambda settings: FailingClosePort())
    monkeypatch.setattr(entry, "run_stdio", serve_cleanly)
    assert fatal(capsys, entry.main) == "judgevet-mcp: shutdown failed (OSError)"


def test_selected_shutdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Name shutdown when the provider factory's exit fails after clean serving."""

    @contextmanager
    def failing_exit() -> Iterator[FakeSystemOnePort]:
        yield FakeSystemOnePort()
        raise RuntimeError(CANARY)

    monkeypatch.setattr(entry, "run_stdio", serve_cleanly)
    message = fatal(capsys, lambda: entry.main(provider_factory=failing_exit))
    assert message == "judgevet-mcp: shutdown failed (RuntimeError)"


async def serve_failing(port: SystemOnePort, *, model: str = "jev-latest") -> None:
    """Fail the stdio run with canary text.

    Raises:
        RuntimeError: Always, carrying the canary.
    """
    raise RuntimeError(CANARY)


def failing_teardown(error: type[Exception]) -> ProviderFactory:
    """Build a provider factory whose exit raises over any body failure.

    Args:
        error: Exception type the factory's exit raises.

    Returns:
        A context manager factory that yields a fake provider.
    """

    @contextmanager
    def factory() -> Iterator[SystemOnePort]:
        """Yield a fake provider, then fail on exit.

        Yields:
            A fake provider.

        Raises:
            Exception: The chosen type, on every exit.
        """
        try:
            yield FakeSystemOnePort()
        finally:
            raise error(CANARY)

    return factory


def test_hosted_serving_and_teardown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Name the serving type, then the close type, when both fail."""
    monkeypatch.setenv("JEV_API__KEY", CANARY)
    monkeypatch.setattr(entry, "build_adapter", lambda settings: FailingClosePort())
    monkeypatch.setattr(entry, "run_stdio", serve_failing)
    assert (
        fatal(capsys, entry.main)
        == "judgevet-mcp: serving failed (RuntimeError, OSError)"
    )


@pytest.mark.parametrize(
    ("teardown", "names"),
    [(OSError, "RuntimeError, OSError"), (RuntimeError, "RuntimeError")],
)
def test_selected_serving_and_teardown(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    teardown: type[Exception],
    names: str,
) -> None:
    """Name the serving type, then a distinct factory exit type, when both fail."""
    monkeypatch.setattr(entry, "run_stdio", serve_failing)
    factory = failing_teardown(teardown)
    message = fatal(capsys, lambda: entry.main(provider_factory=factory))
    assert message == f"judgevet-mcp: serving failed ({names})"
