"""Run trusted exact CLI documentation scripts against a loopback fixture.

Examples:
    The documentation parent invokes this child inside its isolated wheel install.

See Also:
    - [judgevet.adapters.inbound.cli][]: Installed command exercised here.
"""

import json
import os
import shutil
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from judgevet.adapters.inbound.cli import parse_questions
from judgevet.policy_json import parse_policy
from scripts.smoke_release import run_process

POLICY_UNMET = 3


def handler(probability: float, status: int) -> type[BaseHTTPRequestHandler]:
    """Create a local service handler with a controlled answer and status.

    Args:
        probability: Synthetic Noul value.
        status: HTTP status to return.

    Returns:
        A request handler without diagnostic logging.
    """

    class FixtureHandler(BaseHTTPRequestHandler):
        """Serve synthetic Noul answers to the installed CLI."""

        def log_message(self, format: str, *args: object) -> None:
            """Discard fixture server diagnostics."""

        def do_POST(self) -> None:
            """Read the real request and send a controlled wire answer."""
            size = int(self.headers["Content-Length"])
            payload = json.loads(self.rfile.read(size))
            body = {
                "model": "jev-1.13.0",
                "usage": {"input_tokens": 10, "output_tokens": 1},
                "answers": {
                    name: {"type": "noul", "noul": probability}
                    for name in payload["questions"]
                },
            }
            if status != HTTPStatus.OK:
                body = {
                    "detail": {"error_type": "synthetic", "message": "Fixture failure"}
                }
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

    return FixtureHandler


def execute(
    text: str, directory: Path, probability: float, status: int
) -> subprocess.CompletedProcess[str]:
    """Execute one unchanged shell block against a temporary local endpoint.

    Args:
        text: Trusted documentation block, not arbitrary user input.
        directory: Isolated directory containing documented input files.
        probability: Synthetic Noul probability.
        status: Synthetic HTTP status.

    Returns:
        Actual process status and captured streams.

    Raises:
        RuntimeError: If Bash is unavailable.
    """
    bash = shutil.which("bash")
    if bash is None:
        raise RuntimeError("Bash is required for CLI documentation checks")
    script = directory / "example.sh"
    script.write_text(text)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler(probability, status))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    environment = {
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
        "JEV_API__KEY": "synthetic-doc-key",
        "JEV_API__BASE_URL": f"http://127.0.0.1:{server.server_port}",
    }
    try:
        return run_process([bash, str(script)], environment, directory, timeout=60)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def verify(result: subprocess.CompletedProcess[str], kind: str, expected: int) -> None:
    """Validate exit and meaningful output from a documentation command.

    Args:
        result: Actual command outcome.
        kind: Judgment, state-file creation or automation example.
        expected: Expected underlying CLI status.

    Raises:
        ValueError: If status or streams violate the example contract.
    """
    if kind == "automation":
        phrases = {0: "Policy passed.", 3: "Policy unmet.", 1: "No policy verdict."}
        if (
            result.returncode != 0
            or phrases[expected] not in result.stdout + result.stderr
        ):
            raise ValueError("automation did not distinguish the expected status")
        return
    if result.returncode != expected:
        raise ValueError(f"expected exit {expected}, got {result.returncode}")
    if kind == "state":
        if result.stdout or result.stderr:
            raise ValueError("state-file creation emitted unexpected output")
        return
    if expected == 1:
        if result.stdout or "error" not in json.loads(result.stderr):
            raise ValueError("service failure did not produce the error envelope")
        return
    if result.stderr:
        raise ValueError("successful judgment emitted stderr")
    verify_answers(result.stdout, expected)


def verify_answers(output: str, expected: int) -> None:
    """Check each JSON answer and policy verdict in a multi-command block.

    Args:
        output: Captured stdout containing one or more JSON objects.
        expected: Expected CLI status.

    Raises:
        ValueError: If answer content or policy verdict is missing or wrong.
    """
    remaining = output.strip()
    if not remaining:
        raise ValueError("missing answer output")
    while remaining:
        body, offset = json.JSONDecoder().raw_decode(remaining)
        if not body.get("answers") or body.get("model") != "jev-1.13.0":
            raise ValueError("missing typed answer envelope")
        if "policy" in body and body["policy"]["result"] != (
            "fail" if expected == POLICY_UNMET else "pass"
        ):
            raise ValueError("wrong policy verdict")
        remaining = remaining[offset:].strip()


def verify_files(directory: Path, kind: str, expected: int) -> None:
    """Check the documented file outputs, including redirected automation output.

    Args:
        directory: Isolated example directory.
        kind: Selected example contract.
        expected: Expected underlying CLI status.

    Raises:
        ValueError: If the example did not produce its required file outcome.
    """
    if (
        kind == "state"
        and (directory / "document.txt").read_text() != "A short example.\n"
    ):
        raise ValueError("state file differs from the documented input")
    if kind == "automation":
        answer = (directory / "answer.json").read_text()
        error = (directory / "error.json").read_text()
        if expected == 1:
            if answer or "error" not in json.loads(error):
                raise ValueError("automation did not retain the service failure")
        else:
            verify_answers(answer, expected)
            if error:
                raise ValueError("automation retained unexpected stderr")


def main() -> int:
    """Run the parent's selected exact blocks with complete input files.

    Returns:
        One for a violated command contract, otherwise zero.
    """
    jobs = json.loads(Path("cli_examples.json").read_text())
    if not jobs:
        print("CLI documentation: empty execution inventory")
        return 1
    for index, job in enumerate(jobs):
        directory = Path(f"cli_{index}").resolve()
        directory.mkdir()
        for name, text in job["inputs"].items():
            (directory / name).write_text(text)
        try:
            questions = parse_questions(job["inputs"]["questions.json"])
            parse_policy(job["inputs"]["policy.json"], questions)
        except (ValueError, TypeError, KeyError) as error:
            print(f"{job['label']}: invalid input JSON: {type(error).__name__}")
            return 1
        if job["kind"] == "state":
            (directory / "document.txt").unlink()
        cases = [(0.85, 200, 0)]
        if job["kind"] in {"policy", "automation"}:
            cases += [(0.79, 200, 3), (0.85, 401, 1)]
        for probability, status, expected in cases:
            try:
                result = execute(job["text"], directory, probability, status)
                verify(result, job["kind"], expected)
                verify_files(directory, job["kind"], expected)
            except (
                ValueError,
                OSError,
                RuntimeError,
                subprocess.TimeoutExpired,
            ) as error:
                print(f"{job['label']}: {type(error).__name__}: {error}")
                return 1
    print(f"CLI documentation: {len(jobs)} exact shell blocks passed offline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
