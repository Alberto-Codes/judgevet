"""Prove the installed MCP command over stdio and an offline HTTP service.

The HTTP fixture follows https://docs.typesafe.ai/api. The legacy initialize
path is exercised; this does not claim every SDK protocol era was tested.
"""

import asyncio
import json
import os
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import pytest

from judgevet.adapters.inbound.mcp import create_mcp_server
from tests.unit.test_mcp_entrypoint import RecordingPort

COMMAND = Path(sys.executable).parent / "judgevet-mcp"
ANSWERS: dict[str, dict[str, Any]] = {
    "noul": {"type": "noul", "noul": 0.42},
    "choice": {
        "type": "choice",
        "choice": "yes",
        "confidence": 0.8,
        "probabilities": {"yes": 0.8, "no": 0.2},
    },
    "score": {
        "type": "score",
        "score": 1.5,
        "confidence": 0.6,
        "legend": {"0": "Poor", "1": "Fair", "2": "Good", "3": "Excellent"},
        "probabilities": {"0": 0.1, "1": 0.4, "2": 0.4, "3": 0.1},
    },
}
USAGE = {"input_tokens": 3, "output_tokens": 2}
pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(find_spec("mcp") is None, reason="requires MCP extra"),
]


@pytest.fixture
def api_server() -> Iterator[tuple[str, list[dict[str, Any]]]]:
    """Serve deterministic answers and retain the production HTTP requests."""
    requests: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        """Implement only the fixture's documented HTTP operation."""

        def log_message(self, format: str, *args: object) -> None:
            """Keep test diagnostics free of request logging."""

        def handle_post(self) -> None:
            """Record the request and answer its single typed question."""
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(
                {"path": self.path, "body": body, "auth": self.headers["Authorization"]}
            )
            name, question = next(iter(body["questions"].items()))
            payload = json.dumps(
                {
                    "model": "jev-1.13.0",
                    "usage": USAGE,
                    "answers": {name: ANSWERS[question["type"]]},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_POST = handle_post

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def environment() -> dict[str, str]:
    """Forward only process basics, never inherited API configuration or secrets."""
    return {
        name: os.environ[name]
        for name in ("PATH", "HOME", "SYSTEMROOT", "LANG")
        if name in os.environ
    }


async def start(env: dict[str, str]) -> asyncio.subprocess.Process:
    """Launch the required installed command using its absolute path."""
    assert COMMAND.is_file(), "required judgevet-mcp executable is missing"
    return await asyncio.create_subprocess_exec(
        str(COMMAND),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )


async def stop(process: asyncio.subprocess.Process) -> None:
    """Reap a child on failure or timeout, escalating only when necessary."""
    if process.returncode is None:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), 2)
        except TimeoutError:
            process.kill()
            await process.wait()


async def exchange(
    process: asyncio.subprocess.Process,
    number: int,
    method: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Require every stdout line to be a protocol frame until this answer arrives."""
    assert process.stdin is not None and process.stdout is not None
    request = {"jsonrpc": "2.0", "id": number, "method": method, "params": params}
    process.stdin.write((json.dumps(request) + "\n").encode())
    await process.stdin.drain()
    while True:
        line = await process.stdout.readline()
        assert line, "server exited without a protocol answer"
        message = json.loads(line)
        assert isinstance(message, dict) and message.get("jsonrpc") == "2.0"
        assert "error" not in message
        if message.get("id") == number:
            return message["result"]


async def exercise(process: asyncio.subprocess.Process) -> None:
    """Discover unchanged schemas and validate all three HTTP-backed tool answers."""
    initialized = await exchange(
        process,
        1,
        "initialize",
        {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        },
    )
    assert initialized["serverInfo"]["name"] == "judgevet-mcp"
    assert initialized["serverInfo"]["version"] == version("judgevet")
    assert process.stdin is not None
    process.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
    await process.stdin.drain()
    listed = await exchange(process, 2, "tools/list", {})
    assert {tool["name"] for tool in listed["tools"]} == {
        "ask_noul",
        "ask_choice",
        "ask_score",
    }
    server = create_mcp_server(RecordingPort())
    expected = await server._request_handlers["tools/list"].handler(None, None)
    assert listed["tools"] == [
        tool.model_dump(by_alias=True, exclude_unset=True) for tool in expected.tools
    ]
    for number, (kind, answer) in enumerate(ANSWERS.items(), 3):
        result = await exchange(
            process,
            number,
            "tools/call",
            {
                "name": f"ask_{kind}",
                "arguments": {
                    "state": "offline-state",
                    "instruction": "offline-question",
                },
            },
        )
        assert not result.get("isError", False)
        content = {key: value for key, value in answer.items() if key != "type"}
        assert result["structuredContent"] == {
            **content,
            "model": "jev-1.13.0",
            "usage": USAGE,
        }


async def run_session(env: dict[str, str]) -> None:
    """Bound startup, calls, natural EOF and cleanup without stderr deadlock."""
    process = await start(env)
    assert process.stderr is not None
    stderr = asyncio.create_task(process.stderr.read())
    try:
        async with asyncio.timeout(15):
            await exercise(process)
            assert process.stdin is not None and process.stdout is not None
            process.stdin.close()
            await asyncio.wait_for(process.wait(), 5)
            assert process.returncode == 0
            assert await process.stdout.read() == b""
            assert await stderr == b""
    finally:
        await stop(process)
        await stderr


def test_installed_command_tools(api_server: tuple[str, list[dict[str, Any]]]) -> None:
    """Require stdio discovery, all tools, and actual outgoing HTTP requests."""
    base_url, requests = api_server
    env = environment()
    env.update(JEV_API__KEY="canary-key", JEV_API__BASE_URL=base_url)
    asyncio.run(run_session(env))
    assert len(requests) == 3
    for kind, request in zip(ANSWERS, requests, strict=True):
        assert request["path"] == "/v1/systemone"
        assert request["auth"] == "Bearer canary-key"
        assert request["body"]["state"] == "offline-state"
        assert request["body"]["model"] == "jev-latest"
        question = request["body"]["questions"][f"{kind}_question"]
        assert question["type"] == kind
        assert question["instructions"] == "offline-question"
        if kind == "choice":
            assert question["criteria"] == {"yes": "Yes", "no": "No"}
        elif kind == "score":
            assert question["criteria"] == ["Poor", "Fair", "Good", "Excellent"]


async def eof(env: dict[str, str]) -> tuple[int, bytes, bytes]:
    """Run one bounded EOF process and return its observed status and streams."""
    process = await start(env)
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(b""), 10)
        assert process.returncode is not None
        return process.returncode, stdout, stderr
    finally:
        await stop(process)


@pytest.mark.parametrize(
    ("values", "expected", "message"),
    [
        ({}, 2, b"JEV_API__KEY or TYPESAFE_API_KEY"),
        (
            {
                "JEV_API__KEY": "canary-key",
                "JEV_API__TIMEOUT_SECONDS": "canary-invalid",
            },
            2,
            b"invalid settings",
        ),
        ({"JEV_API__KEY": "canary-key"}, 0, b""),
    ],
)
def test_command_eof(values: dict[str, str], expected: int, message: bytes) -> None:
    """Require missing-key and invalid-config failures, and successful plain EOF."""
    env = environment()
    env.update(values)
    code, stdout, stderr = asyncio.run(eof(env))
    assert code == expected
    assert stdout == b""
    assert message in stderr
    assert b"canary" not in stderr
    if code == 0:
        assert stderr == b""
