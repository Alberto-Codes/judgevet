"""Exercise MCP configuration, settings propagation, and real stdio EOF."""

import os
from contextlib import AbstractAsyncContextManager
from io import StringIO

import anyio
import pytest

from judgevet import NetworkConfig, RetryPolicy
from judgevet.adapters.inbound import mcp_entrypoint as entry
from judgevet.adapters.inbound.settings import Settings
from tests.unit.test_mcp_entrypoint import RecordingPort

try:
    from mcp.server.stdio import stdio_server as sdk_stdio
except ModuleNotFoundError:
    sdk_stdio = None

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove inherited API configuration without reading secret values."""
    for name in os.environ:
        if name.startswith(("JEV_", "TYPESAFE_")):
            monkeypatch.delenv(name)


@pytest.mark.parametrize(
    ("missing_runtime", "values", "message"),
    [
        (True, {}, "judgevet[mcp]"),
        (False, {}, "JEV_API__KEY or TYPESAFE_API_KEY"),
        (False, {"JEV_API__KEY": ""}, "JEV_API__KEY or TYPESAFE_API_KEY"),
        (
            False,
            {"JEV_API__KEY": "canary-key", "JEV_API__TIMEOUT_SECONDS": "canary-value"},
            "invalid settings",
        ),
    ],
)
def test_configuration_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    missing_runtime: bool,
    values: dict[str, str],
    message: str,
) -> None:
    """Require early failures to name the problem without caller values."""
    if missing_runtime:
        monkeypatch.setattr(entry, "stdio_server", None)
    elif sdk_stdio is None:
        pytest.skip("requires MCP extra")
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    assert entry.main() == 2
    captured = capsys.readouterr()
    assert message in captured.err
    assert captured.out == ""
    assert "canary" not in captured.err


@pytest.mark.skipif(sdk_stdio is None, reason="requires MCP extra")
def test_settings_once_and_constructor_propagation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require one settings read and exact arguments through real build_adapter."""
    monkeypatch.setenv("JEV_API__KEY", "canary-key")
    monkeypatch.setenv("JEV_API__BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("JEV_API__DEFAULT_MODEL", "test-model")
    monkeypatch.setenv("JEV_API__TIMEOUT_SECONDS", "7.5")
    settings_calls: list[Settings] = []
    constructor_calls: list[
        tuple[str | None, str, str, float, RetryPolicy, NetworkConfig]
    ] = []
    seen: list[RecordingPort] = []
    port = RecordingPort()

    def settings() -> Settings:
        configured = Settings()
        settings_calls.append(configured)
        return configured

    def adapter(
        api_key: str | None,
        base_url: str,
        default_model: str,
        timeout_seconds: float,
        retry: RetryPolicy,
        network: NetworkConfig,
    ) -> RecordingPort:
        constructor_calls.append(
            (api_key, base_url, default_model, timeout_seconds, retry, network)
        )
        return port

    async def serve(acquired: RecordingPort) -> None:
        seen.append(acquired)

    monkeypatch.setattr(entry, "Settings", settings)
    monkeypatch.setattr(entry, "HTTPSystemOneAdapter", adapter)
    monkeypatch.setattr(entry, "run_stdio", serve)
    assert entry.main() == 0
    assert len(settings_calls) == 1
    assert constructor_calls == [
        (
            "canary-key",
            "http://127.0.0.1:9",
            "test-model",
            7.5,
            RetryPolicy(),
            NetworkConfig(),
        )
    ]
    assert seen == [port]
    assert port.close_count == 1


@pytest.mark.skipif(sdk_stdio is None, reason="requires MCP extra")
def test_real_eof(monkeypatch: pytest.MonkeyPatch) -> None:
    """Require the real server and SDK transport to finish and close on EOF."""
    monkeypatch.setenv("JEV_API__KEY", "canary-key")
    output = StringIO()
    port = RecordingPort()

    def streams() -> AbstractAsyncContextManager[tuple[object, object]]:
        assert sdk_stdio is not None
        return sdk_stdio(
            stdin=anyio.wrap_file(StringIO("")), stdout=anyio.wrap_file(output)
        )

    def adapter(
        api_key: str | None,
        base_url: str,
        default_model: str,
        timeout_seconds: float,
        retry: RetryPolicy,
        network: NetworkConfig,
    ) -> RecordingPort:
        return port

    monkeypatch.setattr(entry, "HTTPSystemOneAdapter", adapter)
    monkeypatch.setattr(entry, "stdio_server", streams)
    assert entry.main() == 0
    assert port.close_count == 1
    assert output.getvalue() == ""
