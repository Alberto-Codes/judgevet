"""Observe gateway settings through CLI, policy CLI and MCP composition."""

import json
import os

import pytest
from typer.testing import CliRunner

from judgevet import bind_request_id
from judgevet.adapters.inbound import cli, mcp_entrypoint
from judgevet.ports import SystemOnePort
from tests.gateway_support import gateway_peer, observed_headers
from tests.unit.test_cli_rate_limit import arguments


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch) -> None:
    """Isolate gateway settings and proxy configuration from the user's environment."""
    for name in os.environ:
        if name.startswith(("JEV_", "TYPESAFE_")) or name.upper() in {
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
        }:
            monkeypatch.delenv(name)
    monkeypatch.setenv("JEV_API__KEY", "dummy")


@pytest.mark.parametrize("root", ["cli", "policy", "mcp"])
@pytest.mark.parametrize("invalid", [False, True])
def test_roots_use_gateway_config(root, invalid, tmp_path, monkeypatch) -> None:
    """Each root sends configured fields or rejects them without transmission."""
    monkeypatch.setenv("JEV_API__AUTH_HEADER", "x-apikey")
    monkeypatch.setenv("JEV_API__AUTH_SCHEME", "")
    monkeypatch.setenv("JEV_API__REQUEST_ID_HEADER", "Example-Request")
    monkeypatch.setenv(
        "JEV_API__HEADERS",
        json.dumps(
            {
                "Example-Tenant": "$NO_EXPANSION",
                "Example-Command": "!not-a-command",
                **({"Host": "private-canary"} if invalid else {}),
            }
        ),
    )

    async def run_stdio(port: SystemOnePort) -> None:
        assert port.system_one("synthetic", {}, "jev-latest").model == "jev-1.13.0"

    with gateway_peer() as peer, bind_request_id("root-call"):
        monkeypatch.setenv("JEV_API__BASE_URL", peer.url + "/organization/jev")
        if root == "mcp":
            monkeypatch.setattr(mcp_entrypoint, "run_stdio", run_stdio)
            if invalid:
                with pytest.raises(SystemExit, match="startup or runtime failure"):
                    mcp_entrypoint.main()
            else:
                assert mcp_entrypoint.main() == 0
        else:
            result = CliRunner().invoke(
                cli.app, arguments(tmp_path, root == "policy", True)
            )
            assert result.exit_code == (1 if invalid else 0), result.output
            assert "private-canary" not in result.output
        if invalid:
            assert peer.requests == []
        else:
            headers = observed_headers(peer)
            assert peer.requests[0][0] == "/organization/jev/v1/systemone"
            assert headers["x-apikey"] == "dummy"
            assert "authorization" not in headers
            assert headers["example-tenant"] == "$NO_EXPANSION"
            assert headers["example-command"] == "!not-a-command"
            assert headers["example-request"] == "root-call"
