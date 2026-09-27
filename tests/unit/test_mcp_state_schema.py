"""Each MCP `state` description names only JSON types its `type` union accepts.

Source: https://github.com/Alberto-Codes/judgevet/issues/210#issuecomment-5858726709
and https://json-schema.org/understanding-json-schema/reference/type.
"""

import asyncio
import re
from typing import Any

import pytest

from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.testing import FakeSystemOnePort

JSON_TYPES = ("string", "object", "array", "number", "integer", "boolean", "null")


def _discovery() -> list[dict[str, Any]]:
    """Return every tool definition from the server's tools/list handler.

    Returns:
        Serialized tool definitions.
    """
    server = create_mcp_server(FakeSystemOnePort(seed=1))

    async def exercise() -> Any:
        """Call the registered tools/list handler.

        Returns:
            The SDK list tools result.
        """
        return await server._request_handlers["tools/list"].handler(None, None)

    listed = asyncio.run(exercise()).model_dump(mode="json", by_alias=True)
    return listed["tools"]


def _state_schemas() -> list[tuple[str, dict[str, Any]]]:
    """Return the name and `state` schema of every tool that declares one.

    Returns:
        Pairs of tool name and `state` property schema.
    """
    return [
        (tool["name"], tool["inputSchema"]["properties"]["state"])
        for tool in _discovery()
        if "state" in tool["inputSchema"].get("properties", {})
    ]


def _named_types(description: str) -> set[str]:
    """Return the JSON type names a description mentions as whole words.

    Args:
        description: Schema description text.

    Returns:
        Lower-case JSON type names found in the text.
    """
    return {
        name
        for name in JSON_TYPES
        if re.search(rf"\b{name}\b", description, flags=re.IGNORECASE)
    }


def test_every_state_tool_is_checked() -> None:
    """Find a `state` property on each ask tool and the policy tool."""
    names = {name for name, _ in _state_schemas()}
    assert {"ask_noul", "ask_choice", "ask_score", "evaluate_policy"} <= names


@pytest.mark.parametrize(("tool", "schema"), _state_schemas())
def test_state_description_matches_type(tool: str, schema: dict[str, Any]) -> None:
    """Fail when a `state` description names a type the `type` union excludes."""
    declared = schema["type"]
    accepted = {declared} if isinstance(declared, str) else set(declared)
    excluded = _named_types(schema.get("description", "")) - accepted
    assert not excluded, f"{tool} state description names {sorted(excluded)}"
