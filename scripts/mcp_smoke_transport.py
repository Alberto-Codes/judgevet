"""Exercise initialization, discovery and three typed tool calls over stdio.

Protocol framing and initialization follow
https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle.
Tool frames follow
https://modelcontextprotocol.io/specification/2025-03-26/server/tools.

Examples:
    ```python
    from scripts.mcp_smoke_transport import smoke

    # The release runner awaits smoke with an installed absolute command.
    callable(smoke)
    ```

See Also:
    - [judgevet.adapters.inbound.mcp][]: Served tool contract.
    - [judgevet.adapters.inbound.mcp_entrypoint][]: Installed command.
    - [scripts.mcp_smoke_checks][]: Validation helpers.
"""

import asyncio
import json
from contextlib import suppress
from typing import Any

from scripts.mcp_smoke_checks import (
    validate_server_info,
    validate_tool_call,
    validate_tool_list,
)


async def _read_line(stream: asyncio.StreamReader) -> str:
    """Read one strict UTF-8 protocol line.

    Args:
        stream: Piped child output.

    Returns:
        Decoded line without its newline.

    Raises:
        ValueError: An incomplete or overlong line prevents reading a frame.
        TypeError: The frame is not UTF-8.
    """
    line = await stream.readline()
    if not line.endswith(b"\n"):
        raise ValueError("mcp_smoke: incomplete stdout frame")
    try:
        return line.decode("utf-8").rstrip("\n")
    except UnicodeDecodeError as exc:
        raise TypeError("mcp_smoke: invalid UTF-8 in stdout") from exc


async def _write_json(
    process: asyncio.subprocess.Process, data: dict[str, Any]
) -> None:
    """Write a JSON-RPC frame to stdin and drain.

    Args:
        process: Owned child.
        data: Outgoing frame.

    Raises:
        RuntimeError: The input pipe is absent.
        OSError: The pipe cannot accept the frame.
    """
    if process.stdin is None:
        raise RuntimeError("mcp_smoke: stdin not available")
    payload = json.dumps(data) + "\n"
    process.stdin.write(payload.encode("utf-8"))
    await process.stdin.drain()


async def _read_response(
    process: asyncio.subprocess.Process,
    expected_id: int,
) -> dict[str, Any]:
    """Read one JSON-RPC answer with the expected identifier.

    Args:
        process: Owned child.
        expected_id: Outstanding request identifier.

    Returns:
        The object carried in the result field.

    Raises:
        RuntimeError: Output is unavailable or the frame reports an error.
        TypeError: Framing or answer shape is invalid.
        ValueError: EOF or a line limit prevents reading.
    """
    if process.stdout is None:
        raise RuntimeError("mcp_smoke: stdout not available")
    line = await _read_line(process.stdout)
    try:
        message = json.loads(line)
    except json.JSONDecodeError as exc:
        raise TypeError("mcp_smoke: malformed JSON") from exc
    if not isinstance(message, dict):
        raise TypeError("mcp_smoke: JSON not object")
    if message.get("jsonrpc") != "2.0":
        raise TypeError("mcp_smoke: not JSON-RPC 2.0")
    if "error" in message:
        raise RuntimeError("mcp_smoke: error response")
    if "method" in message:
        raise TypeError("mcp_smoke: unexpected notification or request")
    msg_id = message.get("id")
    if not isinstance(msg_id, int) or isinstance(msg_id, bool):
        raise TypeError("mcp_smoke: id not integer")
    if msg_id != expected_id:
        raise TypeError("mcp_smoke: id mismatch")
    result = message.get("result")
    if not isinstance(result, dict):
        raise TypeError("mcp_smoke: result must be an object")
    return result


async def _initialize(
    process: asyncio.subprocess.Process,
    expected_version: str,
) -> None:
    """Initialize the server and require exact tool discovery.

    Args:
        process: Owned child.
        expected_version: Installed distribution version.

    Raises:
        RuntimeError: Identity or tool discovery validation fails.
        TypeError: Protocol data has an invalid shape.
        ValueError: A protocol frame cannot be read.
    """
    # id 1: initialize
    await _write_json(
        process,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "judgevet-smoke", "version": "1"},
            },
        },
    )
    result = await _read_response(process, 1)
    validate_server_info(result.get("serverInfo", {}), expected_version)

    # notifications/initialized
    await _write_json(
        process,
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
    )

    # id 2: tools/list
    await _write_json(
        process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )
    result = await _read_response(process, 2)
    tools = result.get("tools", [])
    validate_tool_list(tools)


async def _call_tools(
    process: asyncio.subprocess.Process,
) -> None:
    """Call each supported tool once and validate its answer.

    Args:
        process: Initialized child.

    Raises:
        RuntimeError: A tool answer violates its contract.
        TypeError: Protocol data has an invalid shape.
        ValueError: A frame or probability is invalid.
    """
    state = "Two checks passed."
    instruction = "Did the checks pass?"
    calls = [
        ("ask_noul", {}),
        ("ask_choice", {"criteria": {"yes": "Yes", "no": "No"}}),
        ("ask_score", {"criteria": ["Poor", "Fair", "Good", "Excellent"]}),
    ]

    for call_id, (name, criteria) in enumerate(calls, start=3):
        await _write_json(
            process,
            {
                "jsonrpc": "2.0",
                "id": call_id,
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": {
                        "state": state,
                        "instruction": instruction,
                        **criteria,
                    },
                },
            },
        )
        result = await _read_response(process, call_id)
        validate_tool_call(result, name)


async def _finish(process: asyncio.subprocess.Process) -> None:
    """Close input and require clean protocol EOF and successful exit.

    Args:
        process: Owned child with piped standard streams.

    Raises:
        RuntimeError: Output continues or the child exits unsuccessfully.
    """
    if process.stdin is not None:
        process.stdin.close()
    if process.stdout is not None and await process.stdout.read(1):
        raise RuntimeError("mcp_smoke: trailing stdout")
    if await process.wait() != 0:
        raise RuntimeError("mcp_smoke: unsuccessful exit")


async def _drain_stdout(process: asyncio.subprocess.Process) -> None:
    """Discard remaining output in bounded chunks.

    Args:
        process: Owned child whose pipe must reach EOF.
    """
    if process.stdout is not None:
        while await process.stdout.read(8192):
            pass


async def _reap(process: asyncio.subprocess.Process) -> None:
    """Terminate the child, escalating to kill after a bounded wait.

    Args:
        process: Owned child to reap.

    Raises:
        TimeoutError: The killed child does not exit within two seconds.
        OSError: Signaling or waiting fails.
    """
    if process.returncode is None:
        with suppress(ProcessLookupError):
            process.terminate()
    try:
        await asyncio.wait_for(process.wait(), 2.0)
    except TimeoutError:
        with suppress(ProcessLookupError):
            process.kill()
        await asyncio.wait_for(process.wait(), 2.0)


async def _cleanup(process: asyncio.subprocess.Process) -> None:
    """Drain output concurrently with bounded termination and reaping.

    Args:
        process: Owned child, including one that has already exited.

    Raises:
        RuntimeError: Cleanup fails or exceeds its bounded waits.
    """
    if process.stdin is not None:
        process.stdin.close()
    drain = asyncio.create_task(_drain_stdout(process))
    try:
        await _reap(process)
        await asyncio.wait_for(drain, 2.0)
    except (OSError, TimeoutError):
        raise RuntimeError("mcp_smoke: cleanup failed") from None
    finally:
        if not drain.done():
            drain.cancel()
        await asyncio.gather(drain, return_exceptions=True)


async def smoke(
    command: list[str],
    expected_version: str,
    env: dict[str, str],
    timeout: float = 30.0,
) -> None:
    """Exercise initialization, discovery and three typed tool calls.

    Args:
        command: Installed executable and optional arguments.
        expected_version: Version from installed distribution metadata.
        env: Child environment supplied by its owner.
        timeout: Total spawn and session deadline in seconds.

    Raises:
        RuntimeError: Startup, framing, validation, timeout or cleanup fails.
    """
    process: asyncio.subprocess.Process | None = None
    try:
        async with asyncio.timeout(timeout):
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env=env,
            )
            await _initialize(process, expected_version)
            await _call_tools(process)
            await _finish(process)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        raise RuntimeError("mcp_smoke: transport validation failed") from None
    finally:
        if process is not None:
            await _cleanup(process)
