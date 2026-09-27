"""Argument validation in the ask tools returns tool errors, not protocol errors.

Source: https://github.com/Alberto-Codes/judgevet/issues/209#issuecomment-5858719960
and https://modelcontextprotocol.io/specification/2025-11-25/server/tools#error-handling.
"""

import asyncio
from typing import Any

import pytest
from mcp.types import CallToolRequestParams

from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.testing import FakeSystemOnePort

TOOLS = ("ask_noul", "ask_choice", "ask_score")


def _call(port: FakeSystemOnePort, tool: str, arguments: dict[str, Any]) -> Any:
    """Send one tools/call request through the server's registered handler.

    Args:
        port: Fake judgment port that records calls.
        tool: Tool name.
        arguments: Tool arguments.

    Returns:
        The SDK tool result.
    """
    server = create_mcp_server(port)

    async def exercise() -> Any:
        async with server.lifespan(server):
            return await server._request_handlers["tools/call"].handler(
                None, CallToolRequestParams(name=tool, arguments=arguments)
            )

    return asyncio.run(exercise())


@pytest.mark.parametrize("tool", TOOLS)
@pytest.mark.parametrize("missing", ["state", "instruction"])
def test_missing_argument_is_tool_error(tool: str, missing: str) -> None:
    """Report a missing required argument as isError without a provider call."""
    port = FakeSystemOnePort(seed=1)
    arguments = {"state": "text", "instruction": "Is it true?"}
    del arguments[missing]
    result = _call(port, tool, arguments)
    assert result.is_error is True
    assert result.content[0].text == f"Missing required argument: {missing}"
    assert not result.structured_content
    assert port.calls == []


@pytest.mark.parametrize(
    ("tool", "criteria", "message"),
    [
        ("ask_choice", ["yes", "no"], "choice criteria must be a non-empty object"),
        ("ask_choice", {}, "choice criteria must be a non-empty object"),
        ("ask_score", {"a": "b"}, "score criteria must be a non-empty array"),
        ("ask_score", [], "score criteria must be a non-empty array"),
    ],
)
def test_wrong_criteria_is_tool_error(tool: str, criteria: Any, message: str) -> None:
    """Report wrongly typed criteria as isError without a provider call."""
    port = FakeSystemOnePort(seed=1)
    arguments = {"state": "text", "instruction": "Rate it", "criteria": criteria}
    result = _call(port, tool, arguments)
    assert result.is_error is True
    assert result.content[0].text == message
    assert port.calls == []
