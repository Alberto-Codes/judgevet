"""Prove adapter TLS contexts use system roots or the explicit CA bundle.

The HTTPX2 SSL contract is documented at
https://pydantic.dev/docs/httpx2/advanced/ssl/.

Examples:
    ```python
    from judgevet import NetworkConfig

    assert NetworkConfig().verification() is True
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: Both HTTP adapters.
    - [judgevet.adapters.outbound.network][]: Explicit CA configuration.
"""

import os
import ssl
from pathlib import Path

import httpcore2
import httpx2
import pytest
import truststore

from judgevet import AsyncHTTPSystemOneAdapter, HTTPSystemOneAdapter, NetworkConfig
from tests.network_support import make_certificate

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clean_network_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in tuple(os.environ):
        if name.upper() in {
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "NO_PROXY",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
        }:
            monkeypatch.delenv(name)


def _network(custom_ca: bool, directory: Path) -> NetworkConfig:
    """Select the default roots or a real temporary CA certificate.

    Args:
        custom_ca: Whether to use an explicit bundle.
        directory: Directory for the disposable certificate.

    Returns:
        The adapter's explicit network configuration.
    """
    if custom_ca:
        certificate, _ = make_certificate(directory)
        return NetworkConfig(ca_bundle=str(certificate))
    return NetworkConfig()


@pytest.mark.parametrize("custom_ca", [False, True])
def test_sync_tls_context(custom_ca: bool, tmp_path: Path) -> None:
    with HTTPSystemOneAdapter(
        api_key="synthetic", network=_network(custom_ca, tmp_path)
    ) as adapter:
        transport = adapter._client._transport
        assert isinstance(transport, httpx2.HTTPTransport)
        assert isinstance(transport._pool, httpcore2.ConnectionPool)
        context = transport._pool._ssl_context
        if custom_ca:
            assert type(context) is ssl.SSLContext
        else:
            assert isinstance(context, truststore.SSLContext)
        assert context.check_hostname
        assert context.verify_mode == ssl.CERT_REQUIRED


@pytest.mark.asyncio
@pytest.mark.parametrize("custom_ca", [False, True])
async def test_async_tls_context(custom_ca: bool, tmp_path: Path) -> None:
    async with AsyncHTTPSystemOneAdapter(
        api_key="synthetic", network=_network(custom_ca, tmp_path)
    ) as adapter:
        transport = adapter._client._transport
        assert isinstance(transport, httpx2.AsyncHTTPTransport)
        assert isinstance(transport._pool, httpcore2.AsyncConnectionPool)
        context = transport._pool._ssl_context
        if custom_ca:
            assert type(context) is ssl.SSLContext
        else:
            assert isinstance(context, truststore.SSLContext)
        assert context.check_hostname
        assert context.verify_mode == ssl.CERT_REQUIRED
