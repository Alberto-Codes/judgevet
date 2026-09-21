"""Inbound MCP stdio server.

This module provides an MCP server that exposes a single tool, ``ask_noul``,
which takes a state and an instruction and returns the NoulAnswer as MCP
structured content.

The server implements the stateless 2026-07-28 spec: no ``initialize`` handshake,
no protocol session, and deprecated Roots/Sampling/Logging features.

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


    anyio.run(main)
    ```

See Also:
    - [judgevet.ports.SystemOnePort][]: Protocol definition
    - [judgevet.adapters.outbound.http][]: HTTP adapter implementation
    - [judgevet.domain.answers][]: Answer types
    - [judgevet.domain.response][]: Response types

Attributes:
    SERVER_NAME (str): The MCP server name.
    SERVER_VERSION (str): The MCP server version.

Note:
    ``mcp`` is an optional extra (``uv sync --extra mcp``). An import-linter
    contract forbids importing it outside this module; if that contract breaks,
    the import is in the wrong layer, so move the code rather than weakening
    the contract.
"""

from __future__ import annotations

from typing import Any

from judgevet.ports import SystemOnePort

SERVER_NAME = "judgevet-mcp"
"""str: The MCP server name."""

SERVER_VERSION = "0.1.0"
"""str: The MCP server version."""

__all__ = ["SERVER_NAME", "SERVER_VERSION", "create_mcp_server"]


def create_mcp_server(port: SystemOnePort) -> Any:
    """Create an MCP stdio server exposing the ask_noul tool.

    Args:
        port: The SystemOnePort implementation to use for API calls.
            The server does NOT construct an HTTPSystemOneAdapter.

    Returns:
        An MCP Server instance configured with the ask_noul tool.

    Note:
        This function imports mcp locally to respect the import-linter contract
        that forbids mcp outside this module.
    """
    import mcp.types as mcp_types
    from mcp.server import Server

    async def list_tools(
        ctx: Any,
        params: Any | None,
    ) -> Any:
        """List available tools."""
        return mcp_types.ListToolsResult(
            tools=[
                mcp_types.Tool(
                    name="ask_noul",
                    description=(
                        "Ask a yes/no question with a probability of true. "
                        "Takes a state (text or JSON) and an instruction, "
                        "returns the NoulAnswer."
                    ),
                    input_schema={
                        "type": "object",
                        "properties": {
                            "state": {
                                "type": ["string", "object"],
                                "description": (
                                    "The content to evaluate. Can be plain text "
                                    "or a JSON object/array."
                                ),
                            },
                            "instruction": {
                                "type": "string",
                                "description": (
                                    "The yes/no question or statement to evaluate "
                                    "about the state."
                                ),
                            },
                        },
                        "required": ["state", "instruction"],
                    },
                )
            ],
        )

    async def call_tool(
        ctx: Any,
        params: Any,
    ) -> Any:
        """Call a tool.

        Args:
            ctx: Server request context.
            params: Tool call parameters.

        Returns:
            The tool result with structured content.

        Raises:
            ValueError: If the tool name is unknown or arguments are missing.
        """
        if params.name != "ask_noul":
            raise ValueError(f"Unknown tool: {params.name}")

        arguments = params.arguments or {}
        state = arguments.get("state")
        instruction = arguments.get("instruction")

        if state is None:
            raise ValueError("Missing required argument: state")
        if instruction is None:
            raise ValueError("Missing required argument: instruction")

        # Build the questions payload for the Jev API
        questions = {
            "noul_question": {
                "type": "noul",
                "instructions": instruction,
            }
        }

        # Call the port
        response = port.system_one(
            state=state,
            questions=questions,
            model="jev-latest",
        )

        # Extract the NoulAnswer
        noul_answer = response.answers.get("noul_question")
        if noul_answer is None:
            raise ValueError("No answer returned for noul_question")

        if not hasattr(noul_answer, "noul"):
            raise ValueError(f"Expected NoulAnswer, got {type(noul_answer).__name__}")

        structured_content = {
            "noul": noul_answer.noul,
            "model": response.model,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }

        return mcp_types.CallToolResult(
            content=[
                mcp_types.TextContent(
                    type="text",
                    text=(
                        f"Probability of true: {noul_answer.noul:.4f}\n"
                        f"Model: {response.model}\n"
                        f"Usage: {response.usage.input_tokens} input tokens, "
                        f"{response.usage.output_tokens} output tokens"
                    ),
                )
            ],
            structured_content=structured_content,
        )

    # Create the server with stateless 2026-07-28 spec
    server = Server(
        name=SERVER_NAME,
        version=SERVER_VERSION,
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )

    return server
