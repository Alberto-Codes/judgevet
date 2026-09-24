"""Observe synthetic gateway requests on an actual loopback listener."""

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tests.cli_process_support import SUCCESS


@dataclass
class GatewayPeer:
    """Retain actual paths, header pairs and decoded payloads."""

    url: str = ""
    requests: list[tuple[str, list[tuple[str, str]], object]] = field(
        default_factory=list
    )
    status: int = 200
    body: object = field(default_factory=lambda: SUCCESS)
    location: str | None = None


@contextmanager
def gateway_peer() -> Iterator[GatewayPeer]:
    """Serve synthetic JSON or text without contacting any upstream service."""
    peer = GatewayPeer()

    class Handler(BaseHTTPRequestHandler):
        """Record every request before replying with the selected fixture."""

        def log_message(self, format: str, *args: object) -> None:
            """Keep fixture diagnostics silent."""

        def handle_post(self) -> None:
            """Record the actual wire boundary and send a bounded response."""
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            peer.requests.append((self.path, list(self.headers.items()), payload))
            body = peer.body if isinstance(peer.body, str) else json.dumps(peer.body)
            encoded = body.encode()
            self.send_response(peer.status)
            self.send_header("Content-Length", str(len(encoded)))
            if peer.location is not None:
                self.send_header("Location", peer.location)
            self.end_headers()
            self.wfile.write(encoded)

        do_POST = handle_post
        do_GET = handle_post

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


def observed_headers(peer: GatewayPeer, index: int = 0) -> dict[str, str]:
    """Normalize recorded names while rejecting duplicate fields on the wire."""
    pairs = peer.requests[index][1]
    headers = {name.lower(): value for name, value in pairs}
    assert len(headers) == len(pairs)
    return headers
