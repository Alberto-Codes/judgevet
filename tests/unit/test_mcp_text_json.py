"""Each ask tool's text block is the serialized JSON of its structured content.

Source: https://modelcontextprotocol.io/specification/2025-11-25/server/tools#structured-content
and https://github.com/Alberto-Codes/judgevet/issues/225#issuecomment-5882417514.
Each test drives the real server through the SDK's in-process client and
asserts on the result the host receives.
"""

import asyncio
import json
from typing import Any

import pytest
from mcp import Client

from judgevet.adapters.inbound.mcp import create_mcp_server
from tests.unit.test_mcp_noul import FakeSystemOnePort

ASK = {"state": "state", "instruction": "Is it true?"}
CASES = [
    ("ask_noul", ASK),
    ("ask_choice", ASK),
    ("ask_choice", {**ASK, "criteria": {"yes": "Oui, café", "no": "Non"}}),
    ("ask_score", ASK),
    ("ask_score", {**ASK, "criteria": ["Low", "High"]}),
]


def _call(tool: str, arguments: dict[str, Any]) -> Any:
    """Call one tool on a fresh server over one SDK client session.

    Args:
        tool: Tool name.
        arguments: Tool arguments.

    Returns:
        The SDK tool result the host receives.
    """

    async def exercise() -> Any:
        """Open one client session and call the tool once.

        Returns:
            The SDK tool result.
        """
        server = create_mcp_server(FakeSystemOnePort())
        async with Client(server) as client:
            return await client.call_tool(tool, arguments)

    return asyncio.run(exercise())


@pytest.mark.parametrize(("tool", "arguments"), CASES)
def test_text_is_structured_content_json(tool: str, arguments: dict[str, Any]) -> None:
    """Carry exactly one text block whose JSON equals the structured content."""
    result = _call(tool, arguments)
    assert result.is_error is False
    assert result.structured_content
    assert [item.type for item in result.content] == ["text"]
    assert json.loads(result.content[0].text) == result.structured_content
