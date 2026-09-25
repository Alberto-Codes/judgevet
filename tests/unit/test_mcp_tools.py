"""Unit tests for MCP ask_choice and ask_score tools."""

from __future__ import annotations

from collections.abc import Mapping
from importlib.util import find_spec
from typing import Any

import anyio
import pytest

from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.domain.answers import ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.errors import JevMaxTokensExceededError
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
        name: str = "ask_choice",
        arguments: dict[str, Any] | None = None,
    ) -> None:
        """Initialize mock params."""
        self.name = name
        self.arguments = arguments or {}


class MockContext:
    """Mock context for tool calls."""


@pytest.mark.skipif(not HAS_MCP, reason="mcp not installed")
class TestAskChoiceTool:
    """Tests for the ask_choice tool."""

    def test_ask_choice_calls_port_with_correct_arguments(self) -> None:
        """Test that ask_choice tool calls the port with correct arguments."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        call_tool_handler = server._request_handlers.get("tools/call")
        assert call_tool_handler is not None

        params = MockParams(
            name="ask_choice",
            arguments={
                "state": "test content",
                "instruction": "Which option?",
            },
        )

        async def run_test() -> Any:
            return await call_tool_handler.handler(MockContext(), params)

        result = anyio.run(run_test)

        # Verify the port was called with correct arguments
        assert len(port.calls) == 1
        call = port.calls[0]
        assert call["state"] == "test content"
        assert "choice_question" in call["questions"]
        assert call["questions"]["choice_question"]["type"] == "choice"
        assert call["questions"]["choice_question"]["instructions"] == "Which option?"
        assert call["questions"]["choice_question"]["criteria"] == {
            "yes": "Yes",
            "no": "No",
        }
        assert call["model"] == "jev-latest"

        # Verify result structure
        assert hasattr(result, "content")
        assert hasattr(result, "structured_content")
        assert isinstance(result.content, list)
        assert len(result.content) > 0

    def test_ask_choice_returns_structured_content(self) -> None:
        """Test that ask_choice returns structured content with correct fields."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        call_tool_handler = server._request_handlers.get("tools/call")
        assert call_tool_handler is not None

        params = MockParams(
            name="ask_choice",
            arguments={
                "state": "test content",
                "instruction": "Which option?",
            },
        )

        async def run_test() -> Any:
            return await call_tool_handler.handler(MockContext(), params)

        result = anyio.run(run_test)

        # Verify structured content
        structured = result.structured_content
        assert structured["choice"] == "yes"
        assert structured["confidence"] == 0.8
        assert structured["probabilities"] == {"yes": 0.8, "no": 0.2}
        assert structured["model"] == "jev-latest"
        assert structured["usage"]["input_tokens"] == 100
        assert structured["usage"]["output_tokens"] == 10

    def test_ask_choice_custom_criteria(self) -> None:
        """Test that ask_choice uses custom criteria when provided."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        call_tool_handler = server._request_handlers.get("tools/call")
        assert call_tool_handler is not None

        params = MockParams(
            name="ask_choice",
            arguments={
                "state": "test content",
                "instruction": "Which option?",
                "criteria": {"a": "Option A", "b": "Option B"},
            },
        )

        async def run_test() -> Any:
            return await call_tool_handler.handler(MockContext(), params)

        anyio.run(run_test)

        # Verify the port was called with custom criteria
        call = port.calls[0]
        assert call["questions"]["choice_question"]["criteria"] == {
            "a": "Option A",
            "b": "Option B",
        }

    def test_ask_choice_missing_state_raises(self) -> None:
        """Test that ask_choice raises ValueError if state is missing."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        call_tool_handler = server._request_handlers.get("tools/call")
        assert call_tool_handler is not None

        params = MockParams(
            name="ask_choice",
            arguments={"instruction": "test"},
        )

        async def run_test() -> Any:
            return await call_tool_handler.handler(MockContext(), params)

        with pytest.raises(ValueError, match="Missing required argument: state"):
            anyio.run(run_test)

    def test_ask_choice_missing_instruction_raises(self) -> None:
        """Test that ask_choice raises ValueError if instruction is missing."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        call_tool_handler = server._request_handlers.get("tools/call")
        assert call_tool_handler is not None

        params = MockParams(
            name="ask_choice",
            arguments={"state": "test"},
        )

        async def run_test() -> Any:
            return await call_tool_handler.handler(MockContext(), params)

        with pytest.raises(ValueError, match="Missing required argument: instruction"):
            anyio.run(run_test)


@pytest.mark.skipif(not HAS_MCP, reason="mcp not installed")
class TestAskScoreTool:
    """Tests for the ask_score tool."""

    def test_ask_score_calls_port_with_correct_arguments(self) -> None:
        """Test that ask_score tool calls the port with correct arguments."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        call_tool_handler = server._request_handlers.get("tools/call")
        assert call_tool_handler is not None

        params = MockParams(
            name="ask_score",
            arguments={
                "state": "test content",
                "instruction": "Rate this:",
            },
        )

        async def run_test() -> Any:
            return await call_tool_handler.handler(MockContext(), params)

        result = anyio.run(run_test)

        # Verify the port was called with correct arguments
        assert len(port.calls) == 1
        call = port.calls[0]
        assert call["state"] == "test content"
        assert "score_question" in call["questions"]
        assert call["questions"]["score_question"]["type"] == "score"
        assert call["questions"]["score_question"]["instructions"] == "Rate this:"
        assert call["questions"]["score_question"]["criteria"] == [
            "Poor",
            "Fair",
            "Good",
            "Excellent",
        ]
        assert call["model"] == "jev-latest"

        # Verify result structure
        assert hasattr(result, "content")
        assert hasattr(result, "structured_content")
        assert isinstance(result.content, list)
        assert len(result.content) > 0

    def test_ask_score_returns_structured_content(self) -> None:
        """Test that ask_score returns structured content with correct fields."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        call_tool_handler = server._request_handlers.get("tools/call")
        assert call_tool_handler is not None

        params = MockParams(
            name="ask_score",
            arguments={
                "state": "test content",
                "instruction": "Rate this:",
            },
        )

        async def run_test() -> Any:
            return await call_tool_handler.handler(MockContext(), params)

        result = anyio.run(run_test)

        # Verify structured content
        structured = result.structured_content
        assert structured["score"] == 3.5
        assert structured["confidence"] == 0.9
        assert structured["legend"] == {1: "poor", 2: "fair", 3: "good", 4: "excellent"}
        assert structured["probabilities"] == {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4}
        assert structured["model"] == "jev-latest"
        assert structured["usage"]["input_tokens"] == 100
        assert structured["usage"]["output_tokens"] == 10

    def test_ask_score_custom_criteria(self) -> None:
        """Test that ask_score uses custom criteria when provided."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        call_tool_handler = server._request_handlers.get("tools/call")
        assert call_tool_handler is not None

        params = MockParams(
            name="ask_score",
            arguments={
                "state": "test content",
                "instruction": "Rate this:",
                "criteria": ["Bad", "Average", "Good"],
            },
        )

        async def run_test() -> Any:
            return await call_tool_handler.handler(MockContext(), params)

        anyio.run(run_test)

        # Verify the port was called with custom criteria
        call = port.calls[0]
        assert call["questions"]["score_question"]["criteria"] == [
            "Bad",
            "Average",
            "Good",
        ]

    def test_ask_score_missing_state_raises(self) -> None:
        """Test that ask_score raises ValueError if state is missing."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        call_tool_handler = server._request_handlers.get("tools/call")
        assert call_tool_handler is not None

        params = MockParams(
            name="ask_score",
            arguments={"instruction": "test"},
        )

        async def run_test() -> Any:
            return await call_tool_handler.handler(MockContext(), params)

        with pytest.raises(ValueError, match="Missing required argument: state"):
            anyio.run(run_test)

    def test_ask_score_missing_instruction_raises(self) -> None:
        """Test that ask_score raises ValueError if instruction is missing."""
        port = FakeSystemOnePort()
        server = create_mcp_server(port)

        call_tool_handler = server._request_handlers.get("tools/call")
        assert call_tool_handler is not None

        params = MockParams(
            name="ask_score",
            arguments={"state": "test"},
        )

        async def run_test() -> Any:
            return await call_tool_handler.handler(MockContext(), params)

        with pytest.raises(ValueError, match="Missing required argument: instruction"):
            anyio.run(run_test)


class OversizedPort(SystemOnePort):
    """Port that rejects every call as an oversized request (#39)."""

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Any],
        model: str,
    ) -> SystemOneResponse:
        """Raise the oversized-payload error from the probe 1 body.

        Args:
            state: Input state.
            questions: Typed questions.
            model: Selected model.

        Raises:
            JevMaxTokensExceededError: Always.
        """
        raise JevMaxTokensExceededError("Client error; max_tokens_exceeded", 400)


@pytest.mark.skipif(not HAS_MCP, reason="mcp not installed")
@pytest.mark.parametrize("tool", ["ask_noul", "ask_choice", "ask_score"])
def test_tool_error_text_names_max_tokens_exceeded(tool: str) -> None:
    """Each tool call surfaces the wire marker in its error text."""
    server = create_mcp_server(OversizedPort())
    call_tool_handler = server._request_handlers.get("tools/call")
    assert call_tool_handler is not None
    params = MockParams(
        name=tool, arguments={"state": "test content", "instruction": "Fits?"}
    )

    async def run_test() -> Any:
        """Dispatch the tool call.

        Returns:
            The tool result; the port raises first.
        """
        return await call_tool_handler.handler(MockContext(), params)

    with pytest.raises(JevMaxTokensExceededError, match="max_tokens_exceeded"):
        anyio.run(run_test)
