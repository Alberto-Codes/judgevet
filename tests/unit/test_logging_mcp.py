"""Verify debug diagnostics alongside actual MCP stdio frames.

Examples:
    ```bash
    uv run pytest tests/unit/test_logging_mcp.py
    ```

See Also:
    - [judgevet.adapters.inbound.mcp_entrypoint][]: MCP composition root.
"""

import asyncio
import json
from importlib.metadata import version
from importlib.util import find_spec
from typing import Any

import pytest

from scripts.mcp_smoke_transport import _discover, _initialize, _write_json
from tests.cli_process_support import serve
from tests.unit.test_logging_streams import event_fields
from tests.unit.test_mcp_subprocess import environment, exercise, start, stop

pytest_plugins = ["tests.unit.test_mcp_subprocess"]
pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(find_spec("mcp") is None, reason="requires MCP extra"),
]


async def session(url: str, success: bool) -> str:
    """Exercise real frames while draining and retaining only test stderr.

    Args:
        url: Offline API peer.
        success: Select all success calls or one error call.

    Returns:
        Captured diagnostics after clean server shutdown.
    """
    env = environment()
    env.update(
        JEV_API__KEY="private-key-canary",
        JEV_API__BASE_URL=url,
        JEV_LOG__LEVEL="debug",
        JEV_LOG__FORMAT="json",
    )
    process = await start(env)
    assert process.stderr is not None
    stderr = asyncio.create_task(process.stderr.read())
    try:
        async with asyncio.timeout(15):
            if success:
                await exercise(process)
            else:
                await _initialize(process, version("judgevet"))
                await _discover(process)
                await _write_json(
                    process,
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "ask_noul",
                            "arguments": {
                                "state": "private-state-canary",
                                "instruction": "private-question-canary",
                            },
                        },
                    },
                )
                assert process.stdout is not None
                answer = json.loads(await process.stdout.readline())
                assert answer["jsonrpc"] == "2.0" and answer["id"] == 3
                assert "error" in answer and "result" not in answer
            assert process.stdin is not None and process.stdout is not None
            process.stdin.close()
            await process.wait()
            assert process.returncode == 0
            assert await process.stdout.read() == b""
            return (await stderr).decode()
    finally:
        await stop(process)
        await stderr


def assert_diagnostics(stderr: str, status: int, count: int) -> None:
    """Check the exact log count and exclude caller/credential canaries.

    Args:
        stderr: Captured child diagnostics.
        status: Expected HTTP status.
        count: Number of calls made.
    """
    events = [json.loads(line) for line in stderr.splitlines()]
    assert len(events) == count + int(status != 200)
    if status != 200:
        runtime = events.pop()
        assert set(runtime) == {"event", "level", "timestamp"}
        assert runtime["event"] == "mcp.runtime"
        assert runtime["level"] == "error"
    for event in events:
        event_fields(event, status, 1, "success" if status == 200 else "error")
    for secret in (
        "private-key-canary",
        "private-state-canary",
        "private-question-canary",
        "offline-state",
        "offline-question",
        "Authorization",
        "Traceback",
    ):
        assert secret not in stderr


def test_mcp_debug_success(api_server: tuple[str, list[dict[str, Any]]]) -> None:
    """Discovery and every typed tool remain valid alongside stderr diagnostics."""
    url, requests = api_server
    stderr = asyncio.run(session(url, True))
    assert len(requests) == 3
    assert_diagnostics(stderr, 200, 3)


def test_mcp_debug_error() -> None:
    """A failed tool preserves MCP framing and emits one safe debug event."""
    with serve(429, {"detail": {"message": "private-key-canary"}}) as peer:
        stderr = asyncio.run(session(peer.url, False))
    assert len(peer.requests) == 1
    assert_diagnostics(stderr, 429, 1)
