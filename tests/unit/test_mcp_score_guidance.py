"""The ask_score discovery schema tells callers to fit `criteria` to the question.

Source: https://github.com/Alberto-Codes/judgevet/issues/212#issuecomment-5858726837.
The test reads the schema through the server's tools/list handler, as
`tests/unit/test_mcp_state_schema.py` does.
"""

import asyncio
import re
from typing import Any

import pytest

from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.testing import FakeSystemOnePort


def _score_tool() -> dict[str, Any]:
    """Return the serialized ask_score definition from tools/list.

    Returns:
        The ask_score tool definition.
    """
    server = create_mcp_server(FakeSystemOnePort(seed=1))

    async def exercise() -> Any:
        """Call the registered tools/list handler.

        Returns:
            The SDK list tools result.
        """
        return await server._request_handlers["tools/list"].handler(None, None)

    listed = asyncio.run(exercise()).model_dump(mode="json", by_alias=True)
    return next(tool for tool in listed["tools"] if tool["name"] == "ask_score")


def _descriptions() -> list[tuple[str, str]]:
    """Return the tool description and the `criteria` description.

    Returns:
        Pairs of a label and its description text.
    """
    tool = _score_tool()
    criteria = tool["inputSchema"]["properties"]["criteria"]
    return [("tool", tool["description"]), ("criteria", criteria["description"])]


@pytest.mark.parametrize(("where", "text"), _descriptions())
def test_names_a_domain_example(where: str, text: str) -> None:
    """Give an urgency scale as an example of question-specific levels."""
    assert re.search(r"\burgen", text, flags=re.IGNORECASE), where
    assert "Critical" in text, where


@pytest.mark.parametrize(("where", "text"), _descriptions())
def test_calls_the_default_a_quality_rubric(where: str, text: str) -> None:
    """Name the default levels and say they rate generic quality."""
    assert '"Poor"' in text and '"Excellent"' in text, where
    assert re.search(r"\bquality\b", text, flags=re.IGNORECASE), where
