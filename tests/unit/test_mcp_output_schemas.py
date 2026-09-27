"""Each MCP tool declares an outputSchema that its successful structured content meets.

Source: https://github.com/Alberto-Codes/judgevet/issues/211#issuecomment-5860666386
and https://modelcontextprotocol.io/specification/2025-11-25/server/tools#output-schema.
"""

import asyncio
import json
from collections.abc import Mapping
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from mcp.types import CallToolRequestParams

from judgevet.adapters.inbound.cli import parse_questions
from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.domain.questions import Question
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage
from judgevet.testing import FakeSystemOnePort

pytestmark = pytest.mark.unit
TOOLS = ("ask_noul", "ask_choice", "ask_score", "evaluate_policy")
QUESTIONS = {
    "clear": {"type": "noul"},
    "tone": {"type": "choice", "criteria": {"calm": "Calm", "angry": "Angry"}},
    "quality": {"type": "score", "criteria": ["Poor", "Fair", "Good"]},
}
PASSING = {"rules": [{"question": "clear", "pass": {"noul": {"min": 0}}}]}
IMPOSSIBLE = {"rules": [{"question": "clear", "pass": {"noul": {"min": 1.0}}}]}
CALLS = [
    ("ask_noul", {"state": "text", "instruction": "Is it clear?"}),
    ("ask_choice", {"state": "text", "instruction": "Which tone?"}),
    (
        "ask_choice",
        {
            "state": {"text": "hello"},
            "instruction": "Which tone?",
            "criteria": {"calm": "Calm", "angry": "Angry", "flat": "Flat"},
        },
    ),
    ("ask_score", {"state": "text", "instruction": "How good?"}),
    (
        "ask_score",
        {"state": "text", "instruction": "How urgent?", "criteria": ["Low", "High"]},
    ),
    (
        "evaluate_policy",
        {"state": "text", "questions": QUESTIONS, "policy": PASSING},
    ),
    (
        "evaluate_policy",
        {"state": ["a", "b"], "questions": QUESTIONS, "policy": IMPOSSIBLE},
    ),
]
USAGES = [Usage(), Usage(input_tokens=12, output_tokens=None), Usage(3, 4)]


class TypedFake(FakeSystemOnePort):
    """Seeded fake that types the raw question mappings the ask tools send."""

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Parse raw questions with the CLI grammar, then answer them.

        Args:
            state: The content to judge.
            questions: Question names mapped to typed or raw questions.
            model: The model name.

        Returns:
            The seeded response.
        """
        raw = {name: q for name, q in questions.items() if isinstance(q, Mapping)}
        typed = {**questions, **parse_questions(json.dumps(raw))} if raw else questions
        return super().system_one(state, typed, model)


def _listed_tools() -> dict[str, dict[str, Any]]:
    """Return the wire form of every listed tool, keyed by name.

    Returns:
        Serialized tool definitions from the registered tools/list handler.
    """
    server = create_mcp_server(FakeSystemOnePort(seed=1))

    async def exercise() -> Any:
        """Call the registered tools/list handler.

        Returns:
            The SDK list tools result.
        """
        return await server._request_handlers["tools/list"].handler(None, None)

    listed = asyncio.run(exercise()).model_dump(mode="json", by_alias=True)
    return {tool["name"]: tool for tool in listed["tools"]}


def _call(name: str, arguments: dict[str, Any], usage: Usage) -> dict[str, Any]:
    """Call one tool through the real server and return the wire result.

    Args:
        name: Tool name.
        arguments: Tool arguments.
        usage: Usage the fake port reports.

    Returns:
        The serialized CallToolResult.
    """
    server = create_mcp_server(TypedFake(seed=7, usage=usage))

    async def exercise() -> Any:
        """Run the tools/call handler inside the server lifespan.

        Returns:
            The SDK call tool result.
        """
        async with server.lifespan(server):
            return await server._request_handlers["tools/call"].handler(
                None, CallToolRequestParams(name=name, arguments=arguments)
            )

    return asyncio.run(exercise()).model_dump(mode="json", by_alias=True)


@pytest.mark.parametrize("name", TOOLS)
def test_each_tool_declares_an_object_output_schema(name: str) -> None:
    """tools/list carries a valid, closed object outputSchema for every tool."""
    schema = _listed_tools()[name]["outputSchema"]
    assert schema is not None
    Draft202012Validator.check_schema(schema)
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert "$schema" not in schema
    assert set(schema["required"]) <= set(schema["properties"])
    for field, definition in schema["properties"].items():
        assert definition.get("description"), field


@pytest.mark.parametrize("usage", USAGES, ids=["null", "partial", "counted"])
@pytest.mark.parametrize(("name", "arguments"), CALLS)
def test_structured_content_matches_output_schema(
    name: str, arguments: dict[str, Any], usage: Usage
) -> None:
    """Every successful structured content validates against the listed schema."""
    schema = _listed_tools()[name]["outputSchema"]
    assert schema is not None
    result = _call(name, arguments, usage)
    assert result["isError"] is False
    errors = [
        error.message
        for error in Draft202012Validator(schema).iter_errors(
            result["structuredContent"]
        )
    ]
    assert errors == []


@pytest.mark.parametrize(
    ("policy", "verdict"), [(PASSING, "pass"), (IMPOSSIBLE, "fail")]
)
def test_policy_cases_cover_both_verdicts(policy: dict[str, Any], verdict: str) -> None:
    """The evaluate_policy cases above exercise a passing and a failing policy."""
    arguments = {"state": "text", "questions": QUESTIONS, "policy": policy}
    result = _call("evaluate_policy", arguments, Usage())
    assert result["structuredContent"]["policy"]["result"] == verdict


def test_schema_rejects_a_renamed_field() -> None:
    """A renamed structured field fails validation, so the check is not vacuous."""
    schema = _listed_tools()["ask_score"]["outputSchema"]
    content = _call("ask_score", CALLS[3][1], Usage())["structuredContent"]
    content["legends"] = content.pop("legend")
    assert list(Draft202012Validator(schema).iter_errors(content))


def test_error_results_carry_no_structured_content() -> None:
    """Error results stay outside the schema and carry no structured content."""
    result = _call("ask_noul", {"state": "text"}, Usage())
    assert result["isError"] is True
    assert result["structuredContent"] is None
