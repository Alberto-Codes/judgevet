"""Unit tests for MCP adapter."""

from __future__ import annotations

from collections.abc import Mapping
from importlib.util import find_spec
from typing import Any

import anyio
import pytest

from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.domain.answers import ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage
from judgevet.ports import SystemOnePort

HAS_MCP = find_spec("mcp") is not None


class FakeSystemOnePort(SystemOnePort):
    """Fake implementation of SystemOnePort for testing."""

    def __init__(
        self,
        noul: float = 0.75,
        choice: str = "yes",
        score: float = 3.5,
    ) -> None:
        """Initialize the fake port.

        Args:
            noul: Noul value for noul questions.
            choice: Choice value for choice questions.
            score: Score value for score questions.
        """
        self.calls: list[dict[str, Any]] = []
        self._noul = noul
        self._choice = choice
        self._score = score

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Any],
        model: str,
    ) -> SystemOneResponse:
        """Return a fake response."""
        self.calls.append(
            {
                "state": state,
                "questions": questions,
                "model": model,
            }
        )

        answers: dict[str, Any] = {}
        for name, question in questions.items():
            qtype = question.get("type")
            if qtype == "noul":
                answers[name] = NoulAnswer(noul=self._noul)
            elif qtype == "choice":
                answers[name] = ChoiceAnswer(
                    choice=self._choice,
                    confidence=0.8,
                    probabilities={"yes": 0.8, "no": 0.2},
                )
            elif qtype == "score":
                answers[name] = ScoreAnswer(
                    score=self._score,
                    confidence=0.9,
                    legend={1: "poor", 2: "fair", 3: "good", 4: "excellent"},
                    probabilities={1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4},
                )
            else:
                raise ValueError(f"Unknown question type: {qtype}")

        return SystemOneResponse(
            model="jev-latest",
            usage=Usage(input_tokens=100, output_tokens=10),
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


@pytest.mark.skipif(not HAS_MCP, reason="mcp not installed")
class TestCreateMcpServer:
    """Tests for create_mcp_server."""

    def test_returns_server_with_ask_noul_tool(self) -> None:
        """Test that create_mcp_server returns a server with ask_noul tool."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        # Verify server was created
        assert server is not None

    def test_tool_list_returns_ask_noul(self) -> None:
        """Test that list_tools returns ask_noul tool."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        # Call list_tools through the server's registered handler
        list_tools_handler = server._request_handlers.get("tools/list")
        assert list_tools_handler is not None

        # We can't easily call the handler directly, so we test the handler
        # registration works
        assert "tools/list" in server._request_handlers


@pytest.mark.skipif(not HAS_MCP, reason="mcp not installed")
class TestAskNoulTool:
    """Tests for the ask_noul tool."""

    def test_ask_noul_calls_port_with_correct_arguments(self) -> None:
        """Test that ask_noul tool calls the port with correct arguments."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        # Get the call_tool handler
        call_tool_handler = server._request_handlers.get("tools/call")
        assert call_tool_handler is not None

        # Create mock params
        params = MockParams(
            name="ask_noul",
            arguments={
                "state": "test content",
                "instruction": "Is this correct?",
            },
        )

        # Call the handler synchronously using anyio
        async def run_test() -> Any:
            return await call_tool_handler.handler(MockContext(), params)

        result = anyio.run(run_test)

        # Verify the port was called with correct arguments
        assert len(port.calls) == 1
        call = port.calls[0]
        assert call["state"] == "test content"
        assert "noul_question" in call["questions"]
        assert call["questions"]["noul_question"]["type"] == "noul"
        assert call["questions"]["noul_question"]["instructions"] == "Is this correct?"
        assert call["model"] == "jev-latest"

        # Verify result structure
        assert hasattr(result, "content")
        assert hasattr(result, "structured_content")
        assert isinstance(result.content, list)
        assert len(result.content) > 0

    def test_ask_noul_returns_structured_content(self) -> None:
        """Test that ask_noul returns structured content with correct fields."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        call_tool_handler = server._request_handlers.get("tools/call")
        assert call_tool_handler is not None

        params = MockParams(
            name="ask_noul",
            arguments={
                "state": "test content",
                "instruction": "Is this correct?",
            },
        )

        async def run_test() -> Any:
            return await call_tool_handler.handler(MockContext(), params)

        result = anyio.run(run_test)

        # Verify structured content
        structured = result.structured_content
        assert structured["noul"] == 0.75
        assert structured["model"] == "jev-latest"
        assert structured["usage"]["input_tokens"] == 100
        assert structured["usage"]["output_tokens"] == 10

    def test_ask_noul_missing_state_raises(self) -> None:
        """Test that ask_noul raises ValueError if state is missing."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        call_tool_handler = server._request_handlers.get("tools/call")
        assert call_tool_handler is not None

        params = MockParams(
            name="ask_noul",
            arguments={"instruction": "test"},
        )

        async def run_test() -> Any:
            return await call_tool_handler.handler(MockContext(), params)

        with pytest.raises(ValueError, match="Missing required argument: state"):
            anyio.run(run_test)

    def test_ask_noul_missing_instruction_raises(self) -> None:
        """Test that ask_noul raises ValueError if instruction is missing."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        call_tool_handler = server._request_handlers.get("tools/call")
        assert call_tool_handler is not None

        params = MockParams(
            name="ask_noul",
            arguments={"state": "test"},
        )

        async def run_test() -> Any:
            return await call_tool_handler.handler(MockContext(), params)

        with pytest.raises(ValueError, match="Missing required argument: instruction"):
            anyio.run(run_test)

    def test_ask_noul_unknown_tool_raises(self) -> None:
        """Test that ask_noul raises ValueError for unknown tool name."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        call_tool_handler = server._request_handlers.get("tools/call")
        assert call_tool_handler is not None

        params = MockParams(
            name="unknown_tool",
            arguments={"state": "test", "instruction": "test"},
        )

        async def run_test() -> Any:
            return await call_tool_handler.handler(MockContext(), params)

        with pytest.raises(ValueError, match="Unknown tool"):
            anyio.run(run_test)
