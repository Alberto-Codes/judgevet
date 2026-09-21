"""Test that SystemOnePort is a structural protocol.

This test verifies that a class defined entirely within this test file,
without importing anything from judgevet.ports, can satisfy the
SystemOnePort protocol and work with both inbound adapters.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import anyio

from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.domain.answers import NoulAnswer
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage


class _FakePort:
    """Minimal class satisfying SystemOnePort without importing it.

    This class is defined entirely within this test to prove that
    SystemOnePort is a structural protocol - any class with the right
    signature can satisfy it, even one from outside the judgevet package.
    """

    def __init__(self) -> None:
        """Initialize the fake port."""
        self.state: str | dict[str, Any] | list[Any] | None = None
        self.questions: Mapping[str, Any] | None = None
        self.model: str | None = None

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Any],
        model: str,
    ) -> SystemOneResponse:
        """Return a minimal valid response for testing."""
        # Record the call for verification
        self.state = state
        self.questions = questions
        self.model = model

        # Build the response with the same question keys that were sent
        answers: dict[str, Any] = {}
        for name in questions:
            answers[name] = NoulAnswer(noul=0.75)

        return SystemOneResponse(
            model=model,
            usage=Usage(input_tokens=10, output_tokens=5),
            answers=answers,
        )


class MockParams:
    """Mock parameters for tool calls."""

    def __init__(
        self,
        name: str = "ask_noul",
        arguments: dict[str, Any] | None = None,
    ) -> None:
        """Initialize mock params."""
        self.name = name
        self.arguments = arguments or {}


class MockContext:
    """Mock context for tool calls."""


def test_structural_port_with_mcp() -> None:
    """Test that a minimal class satisfies SystemOnePort and drives MCP tools."""
    port = _FakePort()

    # Create an MCP server with the fake port
    server = create_mcp_server(port)

    # Get the call_tool handler
    call_tool_handler = server._request_handlers.get("tools/call")
    assert call_tool_handler is not None

    # Create mock params for ask_noul
    params = MockParams(
        name="ask_noul",
        arguments={
            "state": "test content",
            "instruction": "Is this true?",
        },
    )

    # Call the handler synchronously using anyio
    async def run_test() -> Any:
        return await call_tool_handler.handler(MockContext(), params)

    result = anyio.run(run_test)

    # Verify the fake port was called
    assert port.state == "test content"
    assert port.questions is not None
    assert "noul_question" in port.questions
    assert port.questions["noul_question"]["type"] == "noul"
    assert port.questions["noul_question"]["instructions"] == "Is this true?"
    assert port.model == "jev-latest"

    # Verify result structure and structured content
    assert hasattr(result, "content")
    assert hasattr(result, "structured_content")
    assert isinstance(result.content, list)
    assert len(result.content) > 0
    assert result.structured_content["noul"] == 0.75
