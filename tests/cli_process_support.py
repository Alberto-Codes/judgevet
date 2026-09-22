"""Run installed CLI processes against an observed local HTTP peer.

Synthetic answer shapes follow https://docs.typesafe.ai/api.md.

Examples:
    ```python
    from tests.cli_process_support import QUESTIONS

    assert set(QUESTIONS) == {"noul", "choice", "score"}
    ```

See Also:
    - [judgevet.adapters.inbound.cli][]: The process boundary under test.
"""

import asyncio
import json
import os
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

CANARY = "offline-cli-canary"
QUESTIONS = {
    "noul": {"type": "noul", "instructions": "Is this true?"},
    "choice": {"type": "choice", "criteria": {"yes": "Yes", "no": "No"}},
    "score": {"type": "score", "criteria": ["Poor", "Fair", "Good", "Excellent"]},
}
SUCCESS: dict[str, Any] = {
    "model": "jev-1.13.0",
    "usage": {"input_tokens": 3, "output_tokens": 2},
    "answers": {
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
    },
}


@dataclass
class Peer:
    """Record the requests received by the actual production HTTP adapter.

    Attributes:
        url: Bound loopback endpoint.
        requests: Captured path, canary authorization and parsed request body.
    """

    url: str = ""
    requests: list[dict[str, Any]] = field(default_factory=list)


@contextmanager
def serve(status: int, payload: dict[str, Any]) -> Iterator[Peer]:
    """Serve a fixed answer and retain every request until cleanup.

    Args:
        status: HTTP status emitted by the peer.
        payload: Synthetic JSON answer or error body.

    Yields:
        Peer with the actual URL and observed requests.
    """
    peer = Peer()

    class Handler(BaseHTTPRequestHandler):
        """Handle only the fixture's POST operation."""

        def log_message(self, format: str, *args: object) -> None:
            """Keep default HTTP logging out of captured command diagnostics."""

        def handle_post(self) -> None:
            """Record the production request and send the controlled answer."""
            peer.requests.append(
                {
                    "path": self.path,
                    "auth": self.headers.get("Authorization"),
                    "body": json.loads(
                        self.rfile.read(int(self.headers["Content-Length"]))
                    ),
                }
            )
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_POST = handle_post

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    peer.url = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}
    )
    thread.start()
    try:
        yield peer
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


async def invoke(
    url: str,
    state: str,
    questions: str,
    as_json: bool,
    command: Path | None = None,
) -> tuple[int, str, str]:
    """Run the real console with isolated canary configuration and bounded cleanup.

    Args:
        url: Local peer URL.
        state: CLI state argument.
        questions: CLI questions argument.
        as_json: Whether to select machine output.
        command: Optional exact installed artifact console path.

    Returns:
        Process status, stdout and stderr.
    """
    executable = command or Path(sys.executable).parent / "judgevet"
    assert executable.is_file()
    env = {name: os.environ[name] for name in ("PATH", "LANG") if name in os.environ}
    env.update({"JEV_API__KEY": CANARY, "JEV_API__BASE_URL": url})
    args = [str(executable), state, questions, "--model", "jev-1.13.0"]
    if as_json:
        args.append("--json")
    process = await asyncio.create_subprocess_exec(
        *args,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
    assert process.returncode is not None
    return process.returncode, stdout.decode(), stderr.decode()
