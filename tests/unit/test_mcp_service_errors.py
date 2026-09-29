"""Service failures and spend cap trips in MCP tools are tool execution errors.

Source: https://modelcontextprotocol.io/specification/2025-11-25/server/tools#error-handling
and https://github.com/Alberto-Codes/judgevet/issues/56#issuecomment-5882417323.
Each test drives the real server through the SDK's in-process client into the
production HTTP adapter and a loopback peer.
"""

import asyncio
from typing import Any

import pytest
from mcp import Client

from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from judgevet.adapters.outbound.retries import RetryPolicy
from judgevet.domain.spend import SpendCap
from tests.cli_process_support import CANARY, serve
from tests.unit.test_cli_media import QUESTIONS
from tests.unit.test_cli_rate_limit import PAYLOAD

ASK = {"state": "private-state-canary", "instruction": "Is it true?"}


def _adapter(url: str, cap: SpendCap | None = None) -> HTTPSystemOneAdapter:
    """Build the production adapter with one attempt per call.

    Args:
        url: Loopback peer URL.
        cap: Optional spend cap shared by every call.

    Returns:
        An adapter that sends each call once.
    """
    return HTTPSystemOneAdapter(
        api_key=CANARY, base_url=url, retry=RetryPolicy(1), spend_cap=cap
    )


def _rate_limit(url: str) -> str:
    """Build the declared rate limit diagnostic the adapter raises.

    Args:
        url: Loopback peer URL.

    Returns:
        The exact JevRateLimitError text for the fixture payload.
    """
    return (
        f"Client error '429 Too Many Requests' for url '{url}/v1/systemone'\n"
        "For more information check: "
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429; "
        "rate_limit: Slow down (status 429)"
    )


def _calls(adapter: HTTPSystemOneAdapter, tool: str, arguments: Any, count: int):
    """Send repeated tools/call requests to one server over one session.

    Args:
        adapter: Production adapter the server borrows.
        tool: Tool name.
        arguments: Tool arguments.
        count: Number of calls.

    Returns:
        The SDK tool results in call order.
    """

    async def exercise() -> list[Any]:
        """Open one client session and call the tool in sequence.

        Returns:
            The SDK tool results in call order.
        """
        async with Client(create_mcp_server(adapter)) as client:
            return [await client.call_tool(tool, arguments) for _ in range(count)]

    return asyncio.run(exercise())


def _leaves(group: BaseException) -> list[BaseException]:
    """Flatten nested exception groups into their leaf exceptions.

    Args:
        group: A raised exception, possibly a nested group.

    Returns:
        The leaf exceptions in order.
    """
    if not isinstance(group, BaseExceptionGroup):
        return [group]
    return [leaf for inner in group.exceptions for leaf in _leaves(inner)]


@pytest.mark.parametrize("tool", ["ask_noul", "ask_choice", "ask_score"])
def test_ask_service_error_is_tool_error(tool: str) -> None:
    """Return a service error under an ask tool as an isError tool result."""
    with serve(429, PAYLOAD) as peer, _adapter(peer.url) as adapter:
        (result,) = _calls(adapter, tool, ASK, 1)
    assert result.is_error is True
    assert result.content[0].text == _rate_limit(peer.url)
    assert not result.structured_content
    assert len(peer.requests) == 1


POLICY = {
    "state": "private-state-canary",
    "questions": QUESTIONS,
    "policy": {"rules": [{"question": "choice", "pass": {"choice": "yes"}}]},
}
MEDIA = {**POLICY, "evidence": '{"images":[],"by_question":{}}'}
TRIPPED = "Spend cap reached: attempts spent 1 of 1; restart the server to continue."


@pytest.mark.parametrize(
    ("tool", "arguments", "first"),
    [
        ("ask_noul", ASK, None),
        ("ask_choice", ASK, None),
        ("ask_score", ASK, None),
        ("evaluate_policy", POLICY, None),
        ("evaluate_policy", MEDIA, "JevRateLimitError: media evaluation failed"),
    ],
)
def test_cap_trip_is_tool_error(tool: str, arguments: Any, first: str | None) -> None:
    """Report a tripped cap as isError with a restart message and no request."""
    with serve(429, PAYLOAD) as peer, _adapter(peer.url, SpendCap(1)) as adapter:
        results = _calls(adapter, tool, arguments, 3)
    assert [result.is_error for result in results] == [True, True, True]
    assert [result.content[0].text for result in results] == [
        first or _rate_limit(peer.url),
        TRIPPED,
        TRIPPED,
    ]
    assert len(peer.requests) == 1
