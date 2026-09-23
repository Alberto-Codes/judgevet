"""MCP stdio entry point for judgevet.

This module provides the composition root for the MCP stdio server.
It reads Settings once, configures stderr logging, builds the HTTP adapter, and runs the MCP server
over stdio. It closes the acquired HTTP adapter when serving ends.

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
from judgevet.adapters.inbound.settings import Settings
from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from judgevet.ports import SystemOnePort

try:
    from mcp.server.stdio import stdio_server
except ModuleNotFoundError as exc:
    if exc.name == "mcp":
        stdio_server = None
    else:
        raise

__all__ = ["main"]


def build_adapter(settings: Settings) -> HTTPSystemOneAdapter:
    """Build HTTPSystemOneAdapter with network, connection and retry settings.

    Args:
        settings: The Settings instance.

    Returns:
        HTTPSystemOneAdapter configured with settings.

    Raises:
        ValueError: If the configured key is absent or timeout is invalid.
    """
    return HTTPSystemOneAdapter(
        api_key=settings.api.key.get_secret_value() if settings.api.key else None,
        base_url=settings.api.base_url,
        default_model=settings.api.default_model,
        timeout_seconds=settings.api.timeout_seconds,
        retry=settings.api.retry_policy,
        network=settings.api.network_config,
    )


async def run_stdio(port: SystemOnePort) -> None:
    """Run MCP stdio server with the given port.

    Args:
        port: The port used for API calls.

    Raises:
        RuntimeError: If MCP runtime is not available.
    """
    if stdio_server is None:
        raise RuntimeError("MCP runtime not available")
    server = create_mcp_server(port)
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> int:
    """MCP stdio server entry point.

    Reads Settings once, configures logging, validates the key and runs MCP,
    and ensures adapter cleanup.

    Returns:
        Exit code: 0 for success, 2 for configuration failures.

    Raises:
        SystemExit: If startup or serving raises an IO, runtime, value, type,
            or grouped exception. Its details are omitted from the diagnostic.
    """
    if stdio_server is None:
        print(
            "judgevet-mcp: install judgevet[mcp] to use this command",
            file=sys.stderr,
        )
        return 2

    try:
        try:
            settings = Settings()
        except ValidationError:
            print(
                "judgevet-mcp: invalid settings",
                file=sys.stderr,
            )
            return 2

        configure(settings.log)
        configure_mcp_logging()
        if settings.api.key is None or not settings.api.key:
            print(
                "judgevet-mcp: set JEV_API__KEY or TYPESAFE_API_KEY",
                file=sys.stderr,
            )
            return 2

        adapter = build_adapter(settings)
        try:
            asyncio.run(run_stdio(adapter))
        finally:
            adapter.close()
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeError, ValueError, TypeError, ExceptionGroup):
        raise SystemExit("judgevet-mcp: startup or runtime failure") from None

    return 0
