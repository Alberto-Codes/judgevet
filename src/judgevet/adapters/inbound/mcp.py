"""Inbound MCP stdio server.

This module provides an MCP server with three tools: ``ask_noul``,
``ask_choice``, and ``ask_score``. Each takes a state and an instruction,
then returns the corresponding answer as MCP structured content.
The factory wires module-level schemas and handlers and resolves the optional
SDK only when a caller constructs a server.

The server was tested with MCP Python SDK v2.2.0. Its
[Server.run](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/src/mcp/server/lowlevel/server.py)
delegates to the
[compatibility loop](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/src/mcp/server/runner.py).
The client's first request selects the legacy initialization path or the modern
per-request-envelope path. judgevet's subprocess test exercises the legacy
[2025-03-26 lifecycle](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle):
initialize, list tools and call all three tools. The modern path has not been
exercised here. The floor ``mcp>=2.2`` reflects the tested SDK baseline.

Examples:
    ```python
    from judgevet.adapters.inbound.mcp import create_mcp_server
    from judgevet.adapters.outbound.http import HTTPSystemOneAdapter

    # The server takes a SystemOnePort, it does NOT construct an HTTP adapter
    port = HTTPSystemOneAdapter(api_key="your-key")
    server = create_mcp_server(port)

    # Run the server over stdio
    import anyio
    from mcp.server.stdio import stdio_server


    async def main():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())


    try:
        anyio.run(main)
    finally:
        port.close()
    ```

    The SDK uses snake_case for Python attributes (``server_info``,
    ``structured_content``, ``is_error``) and camelCase for wire JSON fields
    (``serverInfo``, ``structuredContent``, ``isError``). See the tagged
    [SDK type definitions](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/src/mcp-types/mcp_types/_types.py).

See Also:
    - [judgevet.ports.SystemOnePort][]: Protocol definition
    - [judgevet.adapters.outbound.http][]: HTTP adapter implementation
    - [judgevet.domain.answers][]: Answer types
    - [judgevet.domain.response][]: Response types

Attributes:
    SERVER_NAME (str): The MCP server name.
    SERVER_VERSION (str): The MCP server version, sourced from installed distribution metadata.

Note:
    ``mcp`` is an optional extra (``uv sync --extra mcp``). An import-linter
    contract forbids importing it in ``judgevet.domain``, ``judgevet.ports`` and
    ``judgevet.adapters.outbound``. Factory and stdio entrypoint are inbound
    adapters.
"""

from __future__ import annotations

from functools import partial
from importlib import import_module
from importlib.metadata import version
from typing import Any

from judgevet.adapters.inbound.mcp_handlers import (
    handle_ask_choice,
    handle_ask_noul,
    handle_ask_score,
)
from judgevet.adapters.inbound.mcp_schemas import (
    create_choice_tool,
    create_noul_tool,
    create_score_tool,
)
from judgevet.ports import SystemOnePort

SERVER_NAME = "judgevet-mcp"
"""str: The MCP server name."""

SERVER_VERSION = version("judgevet")
"""str: The MCP server version."""

__all__ = ["SERVER_NAME", "SERVER_VERSION", "create_mcp_server"]


async def _list_tools(mcp_types: Any, ctx: Any, params: Any | None) -> Any:
    """Return the existing discovery schema for all three tools.

    Args:
        mcp_types: SDK type constructors.
        ctx: Server request context.
        params: Optional list parameters.

    Returns:
        SDK tool list.
    """
    return mcp_types.ListToolsResult(
        tools=[
            create_noul_tool(mcp_types),
            create_choice_tool(mcp_types),
            create_score_tool(mcp_types),
        ],
    )


async def _call_tool(port: SystemOnePort, mcp_types: Any, ctx: Any, params: Any) -> Any:
    """Dispatch one tool call through the injected judgment port.

    Args:
        port: Judgment port.
        mcp_types: SDK type constructors.
        ctx: Server request context.
        params: Tool call parameters.

    Returns:
        SDK tool result.

    Raises:
        ValueError: If the tool is unknown, arguments are missing or an answer is absent.
        TypeError: If the answer has the wrong type.
    """
    match params.name:
        case "ask_noul":
            return await handle_ask_noul(port, mcp_types, params)
        case "ask_choice":
            return await handle_ask_choice(port, mcp_types, params)
        case "ask_score":
            return await handle_ask_score(port, mcp_types, params)
        case _:
            raise ValueError(f"Unknown tool: {params.name}")


def create_mcp_server(port: SystemOnePort) -> Any:
    """Create an MCP stdio server exposing the three judgment tools.

    Args:
        port: Judgment port used for API calls.

    Returns:
        An SDK server with discovery and tool handlers.

    Raises:
        ModuleNotFoundError: If the optional MCP runtime is unavailable.

    Note:
        Resolve SDK modules only when constructing a server. Library and CLI
        imports do not require the optional runtime. Architecture contracts
        keep MCP dependencies inside inbound adapters.
    """
    mcp_types = import_module("mcp.types")
    server_type = import_module("mcp.server").Server
    return server_type(
        name=SERVER_NAME,
        version=SERVER_VERSION,
        on_list_tools=partial(_list_tools, mcp_types),
        on_call_tool=partial(_call_tool, port, mcp_types),
    )
