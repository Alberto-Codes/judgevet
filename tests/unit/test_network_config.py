"""Observe TLS and proxy behavior through real sync and async adapters."""

import asyncio
import os
from pathlib import Path

import pytest

from judgevet import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
    JevServiceError,
    NetworkConfig,
)
from judgevet.adapters.inbound.settings import Settings
from tests.network_support import make_certificate, serve_network


@pytest.fixture(autouse=True)
def clean_network_environment(monkeypatch) -> None:
    """Remove ambient proxies and trust roots from these loopback tests."""
    for name in os.environ:
        if name.upper() in {
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "NO_PROXY",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
        }:
            monkeypatch.delenv(name)


@pytest.fixture(scope="module")
def certificates(tmp_path_factory) -> tuple[Path, Path]:
    """Create one temporary localhost certificate for this module."""
    return make_certificate(tmp_path_factory.mktemp("tls"))


def call_adapter(url: str, asynchronous: bool, **options) -> None:
    """Drive one real adapter request and release its connections."""

    async def run() -> None:
        async with AsyncHTTPSystemOneAdapter(
            api_key="synthetic", base_url=url, **options
        ) as adapter:
            answer = await adapter.system_one("synthetic", {})
            assert answer.model == "jev-1.13.0"

    if asynchronous:
        asyncio.run(run())
    else:
        with HTTPSystemOneAdapter(
            api_key="synthetic", base_url=url, **options
        ) as adapter:
            answer = adapter.system_one("synthetic", {})
            assert answer.model == "jev-1.13.0"


@pytest.mark.parametrize("asynchronous", [False, True])
def test_default_rejects_private_ca(certificates, asynchronous) -> None:
    """Keep verification enabled without new configuration."""
    with serve_network(*certificates) as peer, pytest.raises(JevServiceError):
        call_adapter(peer.url, asynchronous)
    assert peer.paths == []


@pytest.mark.parametrize("asynchronous", [False, True])
def test_custom_ca_allows_verified_request(
    certificates, asynchronous, monkeypatch
) -> None:
    """Use the explicit trust bundle despite an invalid environment bundle."""
    monkeypatch.setenv("SSL_CERT_FILE", "/nonexistent/environment-bundle.pem")
    with serve_network(*certificates) as peer:
        call_adapter(
            peer.url,
            asynchronous,
            network=NetworkConfig(ca_bundle=str(certificates[0])),
        )
    assert peer.paths == ["/v1/systemone"]


@pytest.mark.parametrize("asynchronous", [False, True])
def test_custom_ca_still_checks_hostname(certificates, asynchronous) -> None:
    """Trusting a CA must not disable hostname verification."""
    with serve_network(*certificates) as peer, pytest.raises(JevServiceError):
        call_adapter(
            peer.url.replace("localhost", "127.0.0.1"),
            asynchronous,
            network=NetworkConfig(ca_bundle=str(certificates[0])),
        )
    assert peer.paths == []


@pytest.mark.parametrize("asynchronous", [False, True])
def test_explicit_verification_off(certificates, asynchronous) -> None:
    """Honor explicit test-only insecure TLS configuration."""
    with serve_network(*certificates) as peer:
        call_adapter(peer.url, asynchronous, network=NetworkConfig(verify=False))
    assert peer.paths == ["/v1/systemone"]


@pytest.mark.parametrize("asynchronous", [False, True])
def test_standard_proxy_environment(monkeypatch, asynchronous) -> None:
    """Retain HTTPS_PROXY routing without explicit network settings."""
    with serve_network() as proxy:
        monkeypatch.setenv("HTTPS_PROXY", proxy.url)
        with pytest.raises(JevServiceError):
            call_adapter("https://example.invalid", asynchronous)
    assert proxy.paths == ["example.invalid:443"]


@pytest.mark.parametrize("asynchronous", [False, True])
def test_explicit_proxy_wins(monkeypatch, asynchronous) -> None:
    """Route through the explicit proxy despite environment routing and bypass."""
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "*")
    with serve_network() as proxy, pytest.raises(JevServiceError):
        call_adapter(
            "https://example.invalid",
            asynchronous,
            network=NetworkConfig(proxy=proxy.url),
        )
    assert proxy.paths == ["example.invalid:443"]


@pytest.mark.parametrize("asynchronous", [False, True])
def test_standard_ca_environment(certificates, asynchronous, monkeypatch) -> None:
    """Retain SSL_CERT_FILE trust configuration by default."""
    monkeypatch.setenv("SSL_CERT_FILE", str(certificates[0]))
    with serve_network(*certificates) as peer:
        call_adapter(peer.url, asynchronous)
    assert peer.paths == ["/v1/systemone"]


@pytest.mark.parametrize(
    "adapter_type", [HTTPSystemOneAdapter, AsyncHTTPSystemOneAdapter]
)
@pytest.mark.parametrize("kind", ["missing", "malformed", "empty"])
def test_bad_ca_fails_construction(tmp_path: Path, adapter_type, kind) -> None:
    """Never downgrade certificate validation after a CA loading failure."""
    path = tmp_path / "ca.pem"
    if kind == "malformed":
        path.write_text("not a certificate")
    elif kind == "empty":
        path.write_text("")
    with pytest.raises(ValueError, match="Cannot load CA bundle"):
        adapter_type(api_key="synthetic", network=NetworkConfig(ca_bundle=str(path)))


def test_contradictory_tls_settings_rejected() -> None:
    """Require users to choose verification or the explicit test-only override."""
    with pytest.raises(ValueError, match="ca_bundle requires verify=True"):
        NetworkConfig(ca_bundle="synthetic.pem", verify=False)


@pytest.mark.parametrize("value", [0, "false"])
def test_verify_must_be_boolean(value) -> None:
    """Reject an integer that could accidentally disable verification."""
    with pytest.raises(TypeError, match="verify must be a boolean"):
        NetworkConfig(verify=value)


def test_proxy_repr_omits_credentials(monkeypatch) -> None:
    """Mask proxy credentials in both settings and network representations."""
    monkeypatch.setenv("JEV_API__PROXY", "http://user:proxy-canary@localhost:8080")
    settings = Settings()
    assert "proxy-canary" not in repr(settings)
    assert "proxy-canary" not in repr(settings.api.network_config)


def test_empty_ca_path_rejected() -> None:
    """Never silently select platform roots for an empty explicit bundle path."""
    with pytest.raises(ValueError, match="Cannot load CA bundle"):
        HTTPSystemOneAdapter(api_key="synthetic", network=NetworkConfig(ca_bundle=""))
