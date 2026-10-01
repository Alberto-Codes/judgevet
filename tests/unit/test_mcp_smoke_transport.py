"""Exercise the checker's owned subprocess, including real offline HTTP calls.

Examples:
    Run the offline transport regression tests::

        uv run pytest -q tests/unit/test_mcp_smoke_transport.py

See Also:
    - [scripts.mcp_smoke_transport][]: Checker under test.
    - [tests.unit.mcp_smoke_peer][]: Controlled faulty subprocess.
"""

import asyncio
import os
import sys
from importlib.metadata import version
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import pytest

from scripts.mcp_smoke_transport import smoke
from tests.unit import mcp_smoke_peer
from tests.unit.test_mcp_subprocess import environment

pytest_plugins = ["tests.unit.test_mcp_subprocess"]
pytestmark = pytest.mark.unit
PEER = Path(__file__).with_name("mcp_smoke_peer.py")


def record_spawns(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Wrap the checker's spawn call so a test learns each child's pid.

    Args:
        monkeypatch: Fixture that restores the real spawn call afterwards.

    Returns:
        List that receives the pid of every child the checker spawns.
    """
    spawned: list[int] = []
    original = asyncio.create_subprocess_exec

    async def spy(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        process = await original(*args, **kwargs)
        spawned.append(process.pid)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spy)
    return spawned


def require_reaped(pid_path: Path, spawned: list[int]) -> None:
    """Require the checker-owned fixture to have existed and now be reaped.

    The pid file is optional: a child reaped before it records its pid leaves
    none. A present file must name the child the checker spawned.

    Args:
        pid_path: Pid file the fixture writes once it starts.
        spawned: Pids that [record_spawns][] captured from the checker.
    """
    assert spawned, "checker never launched the fixture"
    pid = spawned[-1]
    if pid_path.is_file():
        assert int(pid_path.read_text()) == pid
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


@pytest.mark.e2e
@pytest.mark.skipif(find_spec("mcp") is None, reason="requires optional MCP runtime")
def test_real_command_calls_all_tools(
    api_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Exercise the real installed command and require three outgoing calls."""
    base_url, requests = api_server
    command = Path(sys.executable).parent / "judgevet-mcp"
    assert command.is_file(), "installed MCP command is required"
    env = environment()
    env.update(JEV_API__KEY="canary-key", JEV_API__BASE_URL=base_url)
    assert asyncio.run(smoke([str(command)], version("judgevet"), env)) is None
    assert len(requests) == 3
    for kind, request in zip(("noul", "choice", "score"), requests, strict=True):
        assert request["path"] == "/v1/systemone"
        assert request["auth"] == "Bearer canary-key"
        assert request["body"]["state"] == "Two checks passed."
        question = request["body"]["questions"][f"{kind}_question"]
        assert question["type"] == kind
        assert question["instructions"] == "Did the checks pass?"
        if kind == "choice":
            assert question["criteria"] == {"yes": "Yes", "no": "No"}
        elif kind == "score":
            assert question["criteria"] == ["Poor", "Fair", "Good", "Excellent"]


@pytest.mark.parametrize(
    "mode", ["success", "stderr_pressure", "integer_probability", "omit_error"]
)
def test_peer_success_reaped(
    mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Require success and cleanup despite arbitrarily noisy stderr."""
    spawned = record_spawns(monkeypatch)
    pid_path = tmp_path / "pid"
    command = [sys.executable, str(PEER), mode, str(pid_path), "9.8.7"]
    assert asyncio.run(smoke(command, "9.8.7", environment(), 3.0)) is None
    require_reaped(pid_path, spawned)


@pytest.mark.parametrize(
    "mode",
    [
        "malformed",
        "wrong_id",
        "stale_version",
        "missing_tool",
        "duplicate_tool",
        "tool_error",
        "bad_shape",
        "bad_usage",
        "empty_model",
        "bool_number",
        "nan_number",
        "bad_distribution",
        "bad_legend",
        "early_eof",
        "nonzero_exit",
        "trailing_noise",
        "stalled_handshake",
        "stalled_exit",
        "negative_probability",
        "nan_probability",
        "bool_probability",
        "is_error_string",
        "huge_number",
        "bool_id",
        "extra_method",
        "invalid_utf8",
        "missing_newline",
    ],
)
def test_peer_failure_reaped_and_safe(
    mode: str,
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inject defects into the same child the checker launches and owns."""
    spawned = record_spawns(monkeypatch)
    pid_path = tmp_path / "pid"
    command = [sys.executable, str(PEER), mode, str(pid_path), "9.8.7"]
    with pytest.raises(RuntimeError, match=r"^mcp_smoke:") as caught:
        asyncio.run(smoke(command, "9.8.7", environment(), 1.0))
    require_reaped(pid_path, spawned)
    captured = capfd.readouterr()
    assert "canary-output" not in str(caught.value)
    assert "canary-output" not in repr(caught.value)
    assert "canary-output" not in captured.out + captured.err


def test_missing_executable_fails(tmp_path: Path) -> None:
    """Missing installed executable is a failure, never a skip or success."""
    with pytest.raises(RuntimeError, match=r"^mcp_smoke:"):
        asyncio.run(smoke([str(tmp_path / "absent")], "9.8.7", environment()))


def test_cancellation_reaps_child(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Cancellation propagates only after the checker reaps its owned process."""
    original = asyncio.create_subprocess_exec
    processes: list[asyncio.subprocess.Process] = []

    async def exercise() -> None:
        started = asyncio.Event()

        async def launch(*args: str, **kwargs: Any) -> asyncio.subprocess.Process:
            process = await original(*args, **kwargs)
            processes.append(process)
            started.set()
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", launch)
        command = [
            sys.executable,
            str(PEER),
            "stalled_handshake",
            str(tmp_path / "pid"),
            "9.8.7",
        ]
        task = asyncio.create_task(smoke(command, "9.8.7", environment(), 30.0))
        try:
            await asyncio.wait_for(started.wait(), 2.0)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert len(processes) == 1
            assert processes[0].returncode is not None
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            for process in processes:
                if process.returncode is None:
                    process.kill()
                    await process.wait()

    asyncio.run(exercise())


def test_deadline_includes_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    """A blocked spawn uses the requested deadline rather than a separate one."""
    original = asyncio.create_subprocess_exec

    async def exercise() -> None:
        blocked = asyncio.Event()

        async def spawn(*args: str, **kwargs: Any) -> asyncio.subprocess.Process:
            await blocked.wait()
            return await original(*args, **kwargs)

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        with pytest.raises(RuntimeError, match=r"^mcp_smoke:"):
            await asyncio.wait_for(smoke([sys.executable], "9.8.7", {}, 0.01), 1.0)

    asyncio.run(exercise())


def test_stdout_flood_is_drained(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A blocked output pipe must not prevent complete child cleanup."""
    original = asyncio.create_subprocess_exec
    processes: list[asyncio.subprocess.Process] = []

    async def spawn(*args: str, **kwargs: Any) -> asyncio.subprocess.Process:
        process = await original(*args, **kwargs)
        processes.append(process)
        return process

    async def exercise() -> None:
        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        command = [
            sys.executable,
            str(PEER),
            "stdout_flood",
            str(tmp_path / "pid"),
            "9.8.7",
        ]
        try:
            with pytest.raises(RuntimeError, match=r"^mcp_smoke:"):
                await asyncio.wait_for(smoke(command, "9.8.7", environment(), 1.0), 5.0)
            assert len(processes) == 1
            process = processes[0]
            assert process.returncode is not None
            assert process.stdout is not None and process.stdout.at_eof()
        finally:
            for process in processes:
                if process.returncode is None:
                    process.kill()
                if process.stdout is not None:
                    await asyncio.wait_for(process.stdout.read(), 2.0)
                await asyncio.wait_for(process.wait(), 2.0)

    asyncio.run(exercise())


def test_pid_file_is_never_observed_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pid path holds no file until the complete pid replaces onto it."""
    pid_path = tmp_path / "pid"
    real_replace = os.replace
    seen: list[str] = []

    def checked_replace(source: str | Path, destination: str | Path) -> None:
        """Require a complete source and an absent destination, then replace.

        Args:
            source: Temporary file the peer wrote.
            destination: Pid path the checker's tests read.
        """
        assert Path(source).read_text() == "4242"
        assert not Path(destination).exists()
        seen.append(str(destination))
        real_replace(source, destination)

    monkeypatch.setattr(mcp_smoke_peer.os, "replace", checked_replace)
    mcp_smoke_peer.write_pid(pid_path, 4242)
    assert seen == [str(pid_path)]
    assert pid_path.read_text() == "4242"
    assert sorted(tmp_path.iterdir()) == [pid_path]
