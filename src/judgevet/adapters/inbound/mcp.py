"""Inbound MCP stdio server.

This module provides an MCP server that exposes three tools, ``ask_noul``,
``ask_choice``, and ``ask_score``, each taking a state and an instruction and
returning the corresponding answer as MCP structured content.

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

from importlib.metadata import version
from typing import Any

from judgevet.domain.answers import (
    ChoiceAnswer,
    NoulAnswer,
    ScoreAnswer,
)
from judgevet.ports import SystemOnePort

SERVER_NAME = "judgevet-mcp"
"""str: The MCP server name."""

SERVER_VERSION = version("judgevet")
"""str: The MCP server version."""

__all__ = ["SERVER_NAME", "SERVER_VERSION", "create_mcp_server"]


def create_mcp_server(port: SystemOnePort) -> Any:
    """Create an MCP stdio server exposing ask_noul, ask_choice, and ask_score tools.

    Args:
        port: The SystemOnePort implementation to use for API calls.
            The server does NOT construct an HTTPSystemOneAdapter.

    Returns:
        An MCP Server instance configured with the three tools.

    Note:
        This function imports mcp locally to respect the import-linter contract
        that forbids mcp in ``judgevet.domain``, ``judgevet.ports`` and
        ``judgevet.adapters.outbound``. Factory and stdio entrypoint are inbound
        adapters.
    """
    import mcp.types as mcp_types
    from mcp.server import Server

    async def list_tools(
        ctx: Any,
        params: Any | None,
    ) -> Any:
        """List available tools.

        Returns:
            ListToolsResult with ask_noul, ask_choice, and ask_score tools.
        """
        return mcp_types.ListToolsResult(
            tools=[
                _create_noul_tool(),
                _create_choice_tool(),
                _create_score_tool(),
            ],
        )

    async def call_tool(
        ctx: Any,
        params: Any,
    ) -> Any:
        """Dispatch one tool call to the port and return its structured result.

        Dispatches to ask_noul, ask_choice, or ask_score based on the tool name.
        Each tool validates required arguments (state, instruction), calls the
        SystemOnePort with the appropriate question type, and returns structured
        content with the answer, model, and token usage.

        Args:
            ctx: Server request context.
            params: Tool call parameters with name and arguments.

        Returns:
            The tool result with structured content.

        Raises:
            ValueError: If the tool name is unknown or arguments are missing.
            TypeError: If the answer type does not match the expected answer type.
        """
        match params.name:
            case "ask_noul":
                return await _handle_ask_noul(params)
            case "ask_choice":
                return await _handle_ask_choice(params)
            case "ask_score":
                return await _handle_ask_score(params)
            case _:
                raise ValueError(f"Unknown tool: {params.name}")

    def _create_noul_tool() -> Any:
        """Create the ask_noul tool definition.

        Returns:
            Tool definition for ask_noul.
        """
        return mcp_types.Tool(
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

    def _create_choice_tool() -> Any:
        """Create the ask_choice tool definition.

        Returns:
            Tool definition for ask_choice.
        """
        return mcp_types.Tool(
            name="ask_choice",
            description=(
                "Ask a multiple-choice question. Takes a state (text or "
                "JSON) and an instruction, returns the ChoiceAnswer with "
                "choice name, confidence, and probabilities."
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
                            "The multiple-choice question or statement "
                            "to evaluate about the state."
                        ),
                    },
                    "criteria": {
                        "type": "object",
                        "description": (
                            "Mapping of choice names to descriptions. "
                            'If omitted, defaults to {"yes": "Yes", "no": "No"}.'
                        ),
                    },
                },
                "required": ["state", "instruction"],
            },
        )

    def _create_score_tool() -> Any:
        """Create the ask_score tool definition.

        Returns:
            Tool definition for ask_score.
        """
        return mcp_types.Tool(
            name="ask_score",
            description=(
                "Ask a scored question. Takes a state (text or JSON) "
                "and an instruction, returns the ScoreAnswer with score, "
                "confidence, legend, and probabilities."
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
                            "The scored question or statement to evaluate "
                            "about the state."
                        ),
                    },
                    "criteria": {
                        "type": "array",
                        "description": (
                            "Ordered list of rubric level descriptions. "
                            'If omitted, defaults to ["Poor", "Fair", '
                            '"Good", "Excellent"].'
                        ),
                    },
                },
                "required": ["state", "instruction"],
            },
        )

    async def _handle_ask_noul(params: Any) -> Any:
        """Handle the ask_noul tool.

        Args:
            params: Tool call parameters.

        Returns:
            CallToolResult with structured content containing noul, model, usage.

        Raises:
            ValueError: If arguments are missing or answer is invalid.
        """
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

        if not isinstance(noul_answer, NoulAnswer):
            raise TypeError(f"Expected NoulAnswer, got {type(noul_answer).__name__}")

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

    async def _handle_ask_choice(params: Any) -> Any:
        """Handle the ask_choice tool.

        Args:
            params: Tool call parameters.

        Returns:
            CallToolResult with structured content containing choice, probabilities,
            confidence, model, usage.

        Raises:
            ValueError: If arguments are missing or answer is invalid.
        """
        arguments = params.arguments or {}
        state = arguments.get("state")
        instruction = arguments.get("instruction")
        criteria = arguments.get("criteria")

        if state is None:
            raise ValueError("Missing required argument: state")
        if instruction is None:
            raise ValueError("Missing required argument: instruction")

        # Build the questions payload for the Jev API
        question_data: dict[str, Any] = {
            "type": "choice",
            "instructions": instruction,
        }
        if criteria is not None:
            question_data["criteria"] = criteria
        else:
            # Default to yes/no choices if criteria not provided
            question_data["criteria"] = {"yes": "Yes", "no": "No"}

        questions = {
            "choice_question": question_data,
        }

        # Call the port
        response = port.system_one(
            state=state,
            questions=questions,
            model="jev-latest",
        )

        # Extract the ChoiceAnswer
        choice_answer = response.answers.get("choice_question")
        if choice_answer is None:
            raise ValueError("No answer returned for choice_question")

        if not isinstance(choice_answer, ChoiceAnswer):
            raise TypeError(
                f"Expected ChoiceAnswer, got {type(choice_answer).__name__}"
            )

        structured_content = {
            "choice": choice_answer.choice,
            "confidence": choice_answer.confidence,
            "probabilities": choice_answer.probabilities,
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
                        f"Choice: {choice_answer.choice}\n"
                        f"Confidence: {choice_answer.confidence:.4f}\n"
                        f"Model: {response.model}\n"
                        f"Usage: {response.usage.input_tokens} input tokens, "
                        f"{response.usage.output_tokens} output tokens"
                    ),
                )
            ],
            structured_content=structured_content,
        )

    async def _handle_ask_score(params: Any) -> Any:
        """Handle the ask_score tool.

        Args:
            params: Tool call parameters.

        Returns:
            CallToolResult with structured content containing score, legend,
            probabilities, confidence, model, usage.

        Raises:
            ValueError: If arguments are missing or answer is invalid.
        """
        arguments = params.arguments or {}
        state = arguments.get("state")
        instruction = arguments.get("instruction")
        criteria = arguments.get("criteria")

        if state is None:
            raise ValueError("Missing required argument: state")
        if instruction is None:
            raise ValueError("Missing required argument: instruction")

        # Build the questions payload for the Jev API
        question_data: dict[str, Any] = {
            "type": "score",
            "instructions": instruction,
        }
        if criteria is not None:
            question_data["criteria"] = criteria
        else:
            # Default to 4-level rubric if criteria not provided
            question_data["criteria"] = ["Poor", "Fair", "Good", "Excellent"]

        questions = {
            "score_question": question_data,
        }

        # Call the port
        response = port.system_one(
            state=state,
            questions=questions,
            model="jev-latest",
        )

        # Extract the ScoreAnswer
        score_answer = response.answers.get("score_question")
        if score_answer is None:
            raise ValueError("No answer returned for score_question")

        if not isinstance(score_answer, ScoreAnswer):
            raise TypeError(f"Expected ScoreAnswer, got {type(score_answer).__name__}")

        structured_content = {
            "score": score_answer.score,
            "legend": score_answer.legend,
            "probabilities": score_answer.probabilities,
            "confidence": score_answer.confidence,
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
                        f"Score: {score_answer.score:.4f}\n"
                        f"Confidence: {score_answer.confidence:.4f}\n"
                        f"Model: {response.model}\n"
                        f"Usage: {response.usage.input_tokens} input tokens, "
                        f"{response.usage.output_tokens} output tokens"
                    ),
                )
            ],
            structured_content=structured_content,
        )

    # Create the SDK server with the tool handlers.
    server = Server(
        name=SERVER_NAME,
        version=SERVER_VERSION,
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )

    return server
