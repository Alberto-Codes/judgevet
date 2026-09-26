"""MCP stdio entry point for judgevet.

This module provides the composition root for the MCP stdio server.
The hosted path reads Settings once, configures stderr logging, builds the HTTP
adapter and serves stdio. Explicit provider selection bypasses hosted settings.
An application factory acquires and closes its provider on the dispatch worker.
Borrowed providers remain open when serving ends.

Examples:
    ```python
    from judgevet.adapters.inbound import mcp_entrypoint as entry

    assert callable(entry.main)
    ```

See Also:
    - [judgevet.adapters.inbound.settings][]: Settings for configuration
    - [judgevet.adapters.outbound.http][]: HTTP adapter
    - [judgevet.adapters.inbound.mcp][]: MCP server factory
    - [judgevet.ports][]: Port protocol

Attributes:
    __all__ (list): Public API exports.
"""

from __future__ import annotations

import asyncio
import sys

from pydantic import ValidationError

from judgevet.adapters.inbound.logs import configure, configure_mcp_logging
from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.adapters.inbound.mcp_dispatch import ProviderDispatch
from judgevet.adapters.inbound.settings import Settings
from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from judgevet.domain.errors import JudgevetError
from judgevet.ports import SystemOnePort
from judgevet.providers import ProviderFactory

try:
    from mcp.server.stdio import stdio_server
except ModuleNotFoundError as exc:
    if exc.name == "mcp":
        stdio_server = None
    else:
        raise

__all__ = ["main"]


def build_adapter(settings: Settings) -> HTTPSystemOneAdapter:
    """Resolve one wrapped credential and apply host-selected gateway configuration.

    Args:
        settings: The Settings instance.

    Returns:
        HTTPSystemOneAdapter configured with settings.

    Raises:
        ValueError: If credential resolution or connection configuration fails.
    """
    key = settings.api.resolve_key()
    return HTTPSystemOneAdapter(
        api_key=key.get_secret_value() if key is not None else None,
        base_url=settings.api.base_url,
        default_model=settings.api.default_model,
        timeout_seconds=settings.api.timeout_seconds,
        retry=settings.api.retry_policy,
        network=settings.api.network_config,
        gateway=settings.api.gateway_config,
    )


async def run_stdio(port: SystemOnePort, *, model: str = "jev-latest") -> None:
    """Run MCP stdio server with the given port.

    Args:
        port: The port used for API calls.
        model: Host-selected model.

    Raises:
        RuntimeError: If MCP runtime is not available.
    """
    if stdio_server is None:
        raise RuntimeError("MCP runtime not available")
    server = (
        create_mcp_server(port)
        if model == "jev-latest"
        else create_mcp_server(port, model=model)
    )
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main(
    *,
    port: SystemOnePort | None = None,
    provider_factory: ProviderFactory | None = None,
    model: str = "jev-latest",
) -> int:
    """MCP stdio server entry point.

    The hosted path reads Settings once and owns its HTTP adapter. Explicit
    selection borrows a provider or enters an application factory context.
    Both paths configure logging and serve MCP with the host-selected model.

    Args:
        port: Borrowed application provider.
        provider_factory: Owning application factory.
        model: Host-selected model.

    Returns:
        Exit code: 0 for success, 2 for configuration failures.

    Raises:
        ValueError: Both provider selection arguments are supplied.
        SystemExit: If startup or serving raises a declared library error or an
            IO, runtime, value, type or grouped exception. Its details are omitted
            from the diagnostic.
    """
    if port is not None and provider_factory is not None:
        raise ValueError("Supply at most one of port or provider_factory")
    if stdio_server is None:
        print(
            "judgevet-mcp: install judgevet[mcp] to use this command",
            file=sys.stderr,
        )
        return 2

    try:
        if port is not None or provider_factory is not None:
            configure_mcp_logging()
            asyncio.run(_run_selected(port, provider_factory, model))
            return 0
        return _run_hosted(model)
    except KeyboardInterrupt:
        return 130
    except (
        JudgevetError,
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        ExceptionGroup,
    ):
        raise SystemExit("judgevet-mcp: startup or runtime failure") from None


def _run_hosted(model: str) -> int:
    """Preserve hosted settings and existing composition seams.

    Args:
        model: Host-selected model.

    Returns:
        Zero on success or two on configuration failure.
    """
    try:
        settings = Settings()
    except ValidationError:
        print("judgevet-mcp: invalid settings", file=sys.stderr)
        return 2
    configure(settings.log)
    configure_mcp_logging()
    if not settings.api.has_key_source:
        print(
            "judgevet-mcp: set JEV_API__KEY or TYPESAFE_API_KEY, or JEV_API__KEY_FILE",
            file=sys.stderr,
        )
        return 2
    adapter = build_adapter(settings)
    try:
        if model == "jev-latest":
            asyncio.run(run_stdio(adapter))
        else:
            asyncio.run(run_stdio(adapter, model=model))
    finally:
        adapter.close()
    return 0


async def _run_selected(
    port: SystemOnePort | None,
    factory: ProviderFactory | None,
    model: str,
) -> None:
    """Serve an explicit provider inside its worker-owned context.

    Args:
        port: Borrowed provider.
        factory: Owning application factory.
        model: Host-selected model.

    Raises:
        RuntimeError: Provider acquisition yielded no port.
    """
    dispatch = ProviderDispatch(port=port, factory=factory)
    async with dispatch.session():
        if dispatch.port is None:
            raise RuntimeError("Provider acquisition did not return a port")
        await run_stdio(dispatch.port, model=model)
