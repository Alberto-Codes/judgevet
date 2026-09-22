"""Prove HTTP logging metadata and real stderr isolation in fresh processes.

Examples:
    ```bash
    uv run pytest tests/unit/test_logging_streams.py
    ```

See Also:
    - [judgevet.adapters.inbound.logs][]: Existing logging configuration.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.cli_process_support import CANARY, QUESTIONS, SUCCESS, serve
from tests.unit.test_mcp_subprocess import environment

pytestmark = pytest.mark.unit


def run(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run an owned child with real captured pipes and a bounded deadline.

    Args:
        args: Executable and argument list, never a shell command.
        env: Isolated child configuration.

    Returns:
        Exit status and decoded output streams.
    """
    return asyncio.run(_run(args, env))


async def _run(
    args: list[str], env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Capture a child and always kill/reap it when communication fails.

    Args:
        args: Executable and arguments.
        env: Isolated configuration.

    Returns:
        Captured exit status and streams.

    Raises:
        TimeoutError: Child exceeds the communication deadline.
    """
    process = await asyncio.create_subprocess_exec(
        *args,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), 10)
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
    assert process.returncode is not None
    return subprocess.CompletedProcess(
        args, process.returncode, stdout.decode(), stderr.decode()
    )


def event_fields(event: dict, status: int | None, count: int, outcome: str) -> None:
    """Require useful terminal metadata and no unexpected diagnostic payload.

    Args:
        event: Parsed diagnostic line.
        status: Expected HTTP status.
        count: Expected question count.
        outcome: Expected terminal outcome.
    """
    assert set(event) == {
        "event",
        "model",
        "question_count",
        "status_code",
        "outcome",
        "level",
        "timestamp",
    }
    assert event["event"] == "http.call"
    assert event["model"] == "jev-latest"
    assert event["question_count"] == count
    assert event["status_code"] == status
    assert event["outcome"] == outcome
    assert event["level"] == "debug"


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize(
    "outcome", ["success", "parse", "transport", "401", "422", "429", "503"]
)
def test_http_real_streams(mode: str, outcome: str) -> None:
    """Configured sync/async calls emit exactly one safe terminal line to stderr."""
    result = run(
        [sys.executable, "-m", "tests.unit.logging_probe", mode, outcome],
        env=environment(),
    )
    assert result.returncode == 0
    assert result.stdout == ""
    assert "private-logging-canary" not in result.stderr
    lines = result.stderr.splitlines()
    assert len(lines) == 1
    status = (
        None
        if outcome == "transport"
        else 200
        if outcome in {"success", "parse"}
        else int(outcome)
    )
    event_fields(
        json.loads(lines[0]), status, 1, "success" if outcome == "success" else "error"
    )


@pytest.mark.parametrize("mode", ["sync", "async"])
def test_unconfigured_library_stays_silent(mode: str) -> None:
    """Library calls never trigger structlog's default stdout renderer."""
    result = run(
        [sys.executable, "-m", "tests.unit.logging_probe", mode, "success", "silent"],
        env=environment(),
    )
    assert result.returncode == 0
    assert result.stdout == result.stderr == ""


def test_library_import_preserves_configuration() -> None:
    """Importing public library types does not alter global logging state."""
    code = (
        "import logging, structlog; before=structlog.get_config().copy(); "
        "handlers=list(logging.root.handlers); import judgevet; "
        "from judgevet.adapters.inbound import cli, cli_policy_run, mcp_entrypoint; "
        "assert structlog.get_config()==before; "
        "assert logging.root.handlers==handlers; assert not structlog.is_configured()"
    )
    result = run([sys.executable, "-c", code], env=environment())
    assert result.returncode == 0


@pytest.mark.parametrize("policy", [False, True])
@pytest.mark.parametrize("status", [200, 429])
def test_installed_cli_debug(tmp_path: Path, policy: bool, status: int) -> None:
    """Both real CLI paths keep JSON stdout valid when debug logging is enabled."""
    args = [
        str(Path(sys.executable).parent / "judgevet"),
        "private-state-canary",
        json.dumps(QUESTIONS),
        "--json",
    ]
    if policy:
        path = tmp_path / "policy.json"
        path.write_text('{"rules":[{"question":"noul","pass":{"noul":{"min":0}}}]}')
        args.extend(["--policy", str(path)])
    payload = SUCCESS if status == 200 else {"detail": {"message": "Limited"}}
    with serve(status, payload) as peer:
        env = environment()
        env.update(
            JEV_API__KEY=CANARY,
            JEV_API__BASE_URL=peer.url,
            JEV_LOG__LEVEL="debug",
            JEV_LOG__FORMAT="json",
        )
        result = run(args, env=env)
    assert result.returncode == (0 if status == 200 else 1)
    assert len(peer.requests) == 1
    if status == 200:
        assert set(json.loads(result.stdout)["answers"]) == set(QUESTIONS)
    else:
        assert result.stdout == ""
    lines = [json.loads(line) for line in result.stderr.splitlines()]
    assert len(lines) == (1 if status == 200 else 2)
    event_fields(lines[0], status, 3, "success" if status == 200 else "error")
    if status != 200:
        assert set(lines[1]) == {"error"}
    for secret in (CANARY, "private-state-canary", "Is this true?", "Traceback"):
        assert secret not in result.stderr
