"""Consume network environment settings through the three composition roots."""

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from judgevet.adapters.inbound import cli
from judgevet.adapters.inbound.mcp_entrypoint import build_adapter
from judgevet.adapters.inbound.settings import Settings
from judgevet.domain.errors import JevServiceError
from tests.network_support import make_certificate, serve_network
from tests.unit.test_cli_rate_limit import arguments


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch) -> None:
    """Isolate settings and HTTPX environment defaults from caller credentials."""
    for name in os.environ:
        if name.startswith(("JEV_", "TYPESAFE_")) or name.upper() in {
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "NO_PROXY",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
        }:
            monkeypatch.delenv(name)
    monkeypatch.setenv("JEV_API__KEY", "synthetic")


def invoke_root(root: str, tmp_path: Path, failure: bool) -> None:
    """Run the real production factory or CLI command with current settings."""
    if root == "mcp":
        with build_adapter(Settings()) as adapter:
            if failure:
                with pytest.raises(JevServiceError):
                    adapter.system_one("synthetic", {})
            else:
                assert adapter.system_one("synthetic", {}).model == "jev-1.13.0"
    else:
        result = CliRunner().invoke(
            cli.app, arguments(tmp_path, root == "policy", True)
        )
        assert result.exit_code == (1 if failure else 0), result.output


@pytest.mark.parametrize("root", ["cli", "policy", "mcp"])
@pytest.mark.parametrize("mode", ["ca", "insecure"])
def test_tls_settings_consumed(
    tmp_path: Path, monkeypatch, root: str, mode: str
) -> None:
    """Observe an accepted TLS request with private CA or explicit test override."""
    certificate, key = make_certificate(tmp_path)
    if mode == "ca":
        monkeypatch.setenv("JEV_API__CA_BUNDLE", str(certificate))
    else:
        monkeypatch.setenv("JEV_API__VERIFY", "false")
    with serve_network(certificate, key) as peer:
        monkeypatch.setenv("JEV_API__BASE_URL", peer.url)
        invoke_root(root, tmp_path, False)
    assert peer.paths == ["/v1/systemone"]


@pytest.mark.parametrize("root", ["cli", "policy", "mcp"])
def test_proxy_settings_consumed(tmp_path: Path, monkeypatch, root: str) -> None:
    """Observe CONNECT at the explicitly configured proxy for every root."""
    monkeypatch.setenv("JEV_API__BASE_URL", "https://example.invalid")
    with serve_network() as proxy:
        monkeypatch.setenv("JEV_API__PROXY", proxy.url)
        invoke_root(root, tmp_path, True)
    assert proxy.paths == ["example.invalid:443"]


def test_verify_default_and_invalid_input(monkeypatch) -> None:
    """Keep verification on and reject an unknown boolean setting."""
    assert Settings().api.verify is True
    monkeypatch.setenv("JEV_API__VERIFY", "sometimes")
    with pytest.raises(ValueError):
        Settings()


@pytest.mark.parametrize("root", ["cli", "policy", "mcp"])
def test_roots_verify_tls_by_default(tmp_path: Path, monkeypatch, root: str) -> None:
    """Reject an untrusted certificate through each unmodified composition root."""
    certificate, key = make_certificate(tmp_path)
    with serve_network(certificate, key) as peer:
        monkeypatch.setenv("JEV_API__BASE_URL", peer.url)
        invoke_root(root, tmp_path, True)
    assert peer.paths == []
