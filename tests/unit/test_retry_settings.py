"""Verify retry settings through actual CLI and MCP consumption paths."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from judgevet.adapters.inbound import cli
from judgevet.adapters.inbound.mcp_entrypoint import build_adapter
from judgevet.adapters.inbound.settings import Settings
from judgevet.domain.errors import JevRateLimitError
from tests.cli_process_support import CANARY, serve
from tests.unit.test_cli_rate_limit import PAYLOAD, arguments


@pytest.mark.parametrize("root", ["cli", "policy", "mcp"])
def test_settings_reach_real_requests(tmp_path: Path, monkeypatch, root: str) -> None:
    """Observe three requests through each configured composition root."""
    monkeypatch.setenv("JEV_API__KEY", CANARY)
    monkeypatch.setenv("JEV_API__MAX_ATTEMPTS", "3")
    monkeypatch.setenv("JEV_API__RETRY_BASE_DELAY", "0")
    monkeypatch.setenv("JEV_API__RETRY_MAX_DELAY", "0")
    with serve(429, PAYLOAD) as peer:
        monkeypatch.setenv("JEV_API__BASE_URL", peer.url)
        if root == "mcp":
            with build_adapter(Settings()) as adapter, pytest.raises(JevRateLimitError):
                adapter.system_one("synthetic", {})
        else:
            result = CliRunner().invoke(
                cli.app, arguments(tmp_path, root == "policy", True)
            )
            assert result.exit_code == 1
        assert len(peer.requests) == 3
