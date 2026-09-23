"""Serve synthetic judgments over loopback TLS and record proxy selection."""

import json
import ssl
import subprocess
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tests.cli_process_support import SUCCESS


@dataclass
class NetworkPeer:
    """Record observed requests without real customer data."""

    url: str = ""
    paths: list[str] = field(default_factory=list)


def make_certificate(directory: Path) -> tuple[Path, Path]:
    """Create a disposable certificate valid only for localhost."""
    certificate = directory / "certificate.pem"
    key = directory / "key.pem"
    subprocess.run(
        [
            "/usr/bin/openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "2",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost",
            "-keyout",
            "key.pem",
            "-out",
            "certificate.pem",
        ],
        cwd=directory,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=15,
    )
    return certificate, key


@contextmanager
def serve_network(
    certificate: Path | None = None, key: Path | None = None
) -> Iterator[NetworkPeer]:
    """Serve TLS judgments or reject recorded HTTP proxy CONNECT requests."""
    peer = NetworkPeer()

    class Handler(BaseHTTPRequestHandler):
        """Record only the request path and return a controlled response."""

        def log_message(self, format: str, *args: object) -> None:
            """Keep fixture diagnostics silent."""

        def handle_post(self) -> None:
            """Consume synthetic request bytes and return a typed answer body."""
            self.rfile.read(int(self.headers["Content-Length"]))
            peer.paths.append(self.path)
            body = json.dumps(SUCCESS).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def handle_connect(self) -> None:
            """Prove proxy routing without contacting the requested destination."""
            peer.paths.append(self.path)
            self.send_error(502, "Synthetic proxy refusal")

        do_POST = handle_post
        do_CONNECT = handle_connect

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    if certificate is not None:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certificate, key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    scheme = "https" if certificate is not None else "http"
    peer.url = f"{scheme}://localhost:{server.server_port}"
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
