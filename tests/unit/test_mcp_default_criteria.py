"""ask_score reports whether the server applied the default rubric.

Source: https://github.com/Alberto-Codes/judgevet/issues/228#issuecomment-5882662573
and https://google.aip.dev/129. `default_criteria` reports whether the server
filled `criteria`, not whether the list equals the default. Each test drives
the real server through the SDK's in-process client.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from mcp import Client

from judgevet.adapters.inbound.mcp import create_mcp_server
from tests.unit.test_mcp_noul import FakeSystemOnePort

pytestmark = pytest.mark.unit
FIXTURE = Path(__file__).parents[1] / "fixtures" / "mcp_contract.json"
ASK = {"state": "state", "instruction": "How good?"}
DEFAULT = ["Poor", "Fair", "Good", "Excellent"]


def _call(arguments: dict[str, Any]) -> Any:
    """Call ask_score once on a fresh server over one SDK client session.

    Args:
        arguments: Tool arguments.

    Returns:
        The SDK tool result the host receives.
    """

    async def exercise() -> Any:
        """Open one client session and call ask_score once.

        Returns:
            The SDK tool result.
        """
        server = create_mcp_server(FakeSystemOnePort())
        async with Client(server) as client:
            return await client.call_tool("ask_score", arguments)

    return asyncio.run(exercise())


def _listed_score_tool() -> dict[str, Any]:
    """Return the serialized ask_score definition from an SDK client listing.

    Returns:
        The ask_score tool definition as wire JSON.
    """

    async def exercise() -> Any:
        """Open one client session and list the tools.

        Returns:
            The SDK list result.
        """
        server = create_mcp_server(FakeSystemOnePort())
        async with Client(server) as client:
            return await client.list_tools()

    listed = asyncio.run(exercise()).model_dump(mode="json", by_alias=True)
    return next(tool for tool in listed["tools"] if tool["name"] == "ask_score")


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (ASK, True),
        ({**ASK, "criteria": ["Low", "High"]}, False),
        ({**ASK, "criteria": DEFAULT}, False),
    ],
)
def test_result_reports_default_criteria(
    arguments: dict[str, Any], expected: bool
) -> None:
    """Report true only when the call omitted criteria, in both result forms."""
    result = _call(arguments)
    assert result.is_error is False
    assert result.structured_content["default_criteria"] is expected
    assert json.loads(result.content[0].text)["default_criteria"] is expected


def test_output_schema_requires_default_criteria_boolean() -> None:
    """Advertise default_criteria as a required boolean in the output schema."""
    schema = _listed_score_tool()["outputSchema"]
    assert "default_criteria" in schema["required"]
    assert schema["properties"]["default_criteria"]["type"] == "boolean"
    assert schema["properties"]["default_criteria"]["description"]


def test_input_schema_is_unchanged() -> None:
    """Keep the ask_score input schema byte-identical to the pinned contract."""
    pinned = next(
        tool
        for tool in json.loads(FIXTURE.read_text())["tools"]["tools"]
        if tool["name"] == "ask_score"
    )
    listed = _listed_score_tool()
    assert json.dumps(listed["inputSchema"]) == json.dumps(pinned["inputSchema"])
    assert "default_criteria" not in json.dumps(listed["inputSchema"])
