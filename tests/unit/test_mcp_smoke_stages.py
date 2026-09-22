"""Require safe failure stages from real faulty subprocesses.

Examples:
    ```bash
    uv run pytest tests/unit/test_mcp_smoke_stages.py
    ```

See Also:
    - [scripts.mcp_smoke_transport][]: Probe under test.
"""

import asyncio
import sys
from pathlib import Path

import pytest

from scripts import mcp_smoke_transport as probe
from tests.unit.test_mcp_smoke_transport import PEER, require_reaped
from tests.unit.test_mcp_subprocess import environment

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "mode,stage,reason",
    [
        ("malformed", "initialization", "invalid_data"),
        ("stale_version", "initialization", "validation"),
        ("missing_tool", "discovery", "validation"),
        ("tool_error", "call:ask_noul", "validation"),
        ("bad_distribution", "call:ask_choice", "validation"),
        ("bad_legend", "call:ask_score", "validation"),
        ("nonzero_exit", "shutdown", "validation"),
        ("stalled_handshake", "initialization", "timeout"),
        ("stalled_exit", "shutdown", "timeout"),
    ],
)
def test_fault_stage(
    mode: str,
    stage: str,
    reason: str,
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """Faults expose fixed stage/category strings and still reap the real child."""
    pid = tmp_path / "pid"
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(
            probe.smoke(
                [sys.executable, str(PEER), mode, str(pid), "9.8.7"],
                "9.8.7",
                environment(),
                0.5,
            )
        )
    require_reaped(pid)
    assert str(caught.value) == f"mcp_smoke: stage={stage} reason={reason}"
    output = capfd.readouterr()
    assert "canary-output" not in output.out + output.err + repr(caught.value)


def test_missing_executable_stage(tmp_path: Path) -> None:
    """Missing executables identify resolution without disclosing the path."""
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(probe.smoke([str(tmp_path / "private-canary")], "1", {}))
    assert str(caught.value) == "mcp_smoke: stage=spawn reason=executable_not_found"


@pytest.mark.parametrize("mode", ["success", "malformed"])
def test_cleanup_diagnostic_preserves_first_failure(
    mode: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cleanup faults remain distinct and cannot replace an earlier protocol fault."""
    original = probe._cleanup

    async def cleanup(process: asyncio.subprocess.Process) -> None:
        await original(process)
        raise RuntimeError("private-cleanup-canary")

    monkeypatch.setattr(probe, "_cleanup", cleanup)
    pid = tmp_path / "pid"
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(
            probe.smoke(
                [sys.executable, str(PEER), mode, str(pid), "9.8.7"],
                "9.8.7",
                environment(),
                2,
            )
        )
    require_reaped(pid)
    message = str(caught.value)
    expected = "stage=cleanup reason=validation"
    if mode == "malformed":
        expected = "stage=initialization reason=invalid_data; cleanup=failed"
    assert message == f"mcp_smoke: {expected}"
    assert "private-cleanup-canary" not in repr(caught.value)


def test_spawn_permission_stage(tmp_path: Path) -> None:
    """An existing nonexecutable file reports spawn failure without its path."""
    command = tmp_path / "private-command-canary"
    command.write_text("not executable")
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(probe.smoke([str(command)], "1", {}))
    assert str(caught.value) == "mcp_smoke: stage=spawn reason=os_error"


def test_spawn_timeout_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    """A blocked spawn retains its stage when the session deadline expires."""

    async def spawn(*args: object, **kwargs: object) -> asyncio.subprocess.Process:
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(probe.smoke(["private-command-canary"], "1", {}, 0.01))
    assert str(caught.value) == "mcp_smoke: stage=spawn reason=timeout"
