"""Prove exact-wheel orchestration and bounded setup subprocess behavior.

Examples:
    Run the offline acceptance checks::

        uv run pytest -q tests/unit/test_smoke_mcp_release.py

See Also:
    - [scripts.smoke_mcp_release][]: Artifact checker under test.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from scripts import smoke_mcp_release as runner

pytestmark = pytest.mark.unit


class Commands:
    """Record commands invoked by the checker and inject one controlled failure.

    Attributes:
        mode: Defect to inject.
        calls: Commands, environment copies and work directories observed.
        served: Installed executable and metadata passed to transport.
    """

    def __init__(self, mode: str = "success") -> None:
        """Initialize the defect selection and observed calls."""
        self.mode = mode
        self.calls: list[tuple[list[str], dict[str, str], Path]] = []
        self.served: list[tuple[list[str], str, dict[str, str], Path]] = []

    async def run(
        self,
        command: list[str],
        env: dict[str, str],
        workdir: Path,
        timeout: float = 120.0,
    ) -> str:
        """Record an actual checker invocation and simulate its setup effect."""
        self.calls.append((command.copy(), env.copy(), workdir))
        venv = workdir / "venv"
        if command[1:4] == ["-I", "-m", "venv"]:
            assert command == [sys.executable, "-I", "-m", "venv", str(venv)]
            (venv / "bin").mkdir(parents=True)
            (venv / "bin" / "python").touch()
            return ""
        if command[1:3] == ["pip", "install"]:
            if self.mode == "install_failure":
                raise RuntimeError("canary-output install failure")
            if self.mode != "missing_command":
                (venv / "bin" / "judgevet-mcp").touch()
            return ""
        assert command[:3] == [str(venv / "bin" / "python"), "-I", "-c"]
        assert len(command) == 4
        if self.mode == "probe_failure":
            raise RuntimeError("canary-output probe failure")
        if self.mode == "invalid_json":
            return "canary-output"
        imported = venv / "lib/python3.12/site-packages/judgevet/__init__.py"
        if self.mode == "outside_import":
            imported = workdir / "site-packages/judgevet/__init__.py"
        if self.mode == "not_site_packages":
            imported = venv / "judgevet/__init__.py"
        return json.dumps(
            {
                "file": str(imported),
                "prefix": str(workdir if self.mode == "wrong_prefix" else venv),
                "version": "" if self.mode == "empty_version" else "9.8.7",
            }
        )

    async def smoke(
        self,
        command: list[str],
        expected_version: str,
        env: dict[str, str],
        timeout: float = 30.0,
    ) -> None:
        """Record the command actually passed by the artifact checker."""
        self.served.append((command.copy(), expected_version, env.copy(), Path.cwd()))
        if self.mode == "server_failure":
            raise RuntimeError("canary-output server failure")
        if self.mode == "server_timeout":
            raise TimeoutError("canary-output server timeout")
        if self.mode == "cancel":
            raise asyncio.CancelledError


def install_recorder(monkeypatch: pytest.MonkeyPatch, mode: str) -> Commands:
    """Attach observers to the checker instead of invoking standalone fakes."""
    commands = Commands(mode)
    monkeypatch.setattr(runner, "run_command", commands.run)
    monkeypatch.setattr(runner, "smoke", commands.smoke)
    return commands


def test_exact_wheel_and_isolated_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Require exact arguments, independent environment and restored cwd."""
    commands = install_recorder(monkeypatch, "success")
    wheel = tmp_path / "candidate.whl"
    wheel.touch()
    env = {"TYPESAFE_API_KEY": "canary-key", "PYTHONPATH": "/bad", "PYTHONHOME": "/bad"}
    before = env.copy()
    cwd = Path.cwd()
    assert asyncio.run(runner.check_wheel(wheel, env)) is None
    assert len(commands.calls) == 3
    create, install, probe = commands.calls
    workdir = create[2]
    assert workdir != tmp_path and not workdir.is_relative_to(cwd)
    assert install[0][1:] == [
        "pip",
        "install",
        "--python",
        str(workdir / "venv/bin/python"),
        f"{wheel}[mcp]",
    ]
    assert Path(install[0][0]).is_absolute()
    assert probe[0][:3] == [str(workdir / "venv/bin/python"), "-I", "-c"]
    for _, passed_env, passed_cwd in commands.calls:
        assert passed_cwd == workdir
        assert passed_env == {"TYPESAFE_API_KEY": "canary-key"}
    assert commands.served == [
        (
            [str(workdir / "venv/bin/judgevet-mcp")],
            "9.8.7",
            {"TYPESAFE_API_KEY": "canary-key"},
            workdir,
        )
    ]
    assert env == before
    assert Path.cwd() == cwd
    assert not workdir.exists()


@pytest.mark.parametrize(
    "mode",
    [
        "outside_import",
        "not_site_packages",
        "wrong_prefix",
        "empty_version",
        "missing_command",
        "install_failure",
        "probe_failure",
        "invalid_json",
        "server_failure",
        "server_timeout",
    ],
)
def test_artifact_failure_cleans_up(
    mode: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Require each injected defect to fail through the real checker."""
    commands = install_recorder(monkeypatch, mode)
    wheel = tmp_path / "candidate.whl"
    wheel.touch()
    cwd = Path.cwd()
    with pytest.raises(RuntimeError, match=r"^mcp_release:") as caught:
        asyncio.run(runner.check_wheel(wheel, {"TYPESAFE_API_KEY": "canary-key"}))
    assert commands.calls
    assert not commands.calls[0][2].exists()
    assert Path.cwd() == cwd
    captured = capsys.readouterr()
    assert (
        "canary"
        not in str(caught.value) + repr(caught.value) + captured.out + captured.err
    )
    if mode in ("server_failure", "server_timeout"):
        assert len(commands.served) == 1
    else:
        assert commands.served == []


@pytest.mark.parametrize("env", [{}, {"TYPESAFE_API_KEY": ""}])
def test_key_required_before_commands(
    env: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A missing key fails before creating a process."""
    commands = install_recorder(monkeypatch, "success")
    wheel = tmp_path / "candidate.whl"
    wheel.touch()
    with pytest.raises(RuntimeError, match=r"^mcp_release:"):
        asyncio.run(runner.check_wheel(wheel, env))
    assert commands.calls == []
    assert commands.served == []


def test_cancellation_removes_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Cancellation propagates after removing owned temporary files."""
    commands = install_recorder(monkeypatch, "cancel")
    (tmp_path / "candidate.whl").touch()
    cwd = Path.cwd()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            runner.check_wheel(
                tmp_path / "candidate.whl", {"TYPESAFE_API_KEY": "canary"}
            )
        )
    assert len(commands.served) == 1
    assert not commands.calls[0][2].exists()
    assert Path.cwd() == cwd


def test_real_command_success(tmp_path: Path) -> None:
    """Read stdout from the actual subprocess."""
    command = [sys.executable, "-I", "-c", "print('observed')"]
    assert asyncio.run(runner.run_command(command, {}, tmp_path)) == "observed\n"


def test_real_command_failure_is_safe(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Fail nonzero children without exposing their diagnostics."""
    command = [
        sys.executable,
        "-I",
        "-c",
        "import sys; print('canary-output'); print('canary-output', file=sys.stderr); sys.exit(7)",
    ]
    with pytest.raises(RuntimeError, match=r"^mcp_release:") as caught:
        asyncio.run(runner.run_command(command, {}, tmp_path))
    captured = capsys.readouterr()
    assert (
        "canary-output"
        not in str(caught.value) + repr(caught.value) + captured.out + captured.err
    )


def test_real_command_timeout_reaps(tmp_path: Path) -> None:
    """A timed-out child is demonstrably reaped."""
    pid_file = tmp_path / "pid"
    program = (
        "import os,sys,time; from pathlib import Path; "
        "Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)"
    )
    command = [sys.executable, "-I", "-c", program, str(pid_file)]
    with pytest.raises(RuntimeError, match=r"^mcp_release:"):
        asyncio.run(runner.run_command(command, {}, tmp_path, timeout=0.5))
    assert pid_file.is_file()
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid_file.read_text()), 0)


@pytest.mark.parametrize(
    "argv", [[], ["--wheel"], ["--wheel", "/missing.whl"], ["--build"], ["x", "y", "z"]]
)
def test_invalid_arguments_fail(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """Invalid invocation never falls back to building a wheel."""
    assert runner.main(argv) == 1
    assert "mcp_release: FAIL" in capsys.readouterr().out


@pytest.mark.parametrize("fails", [False, True])
def test_main_runs_checker_and_reports_safely(
    fails: bool,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The synchronous entry point observes the actual async checker verdict."""
    calls: list[Path] = []

    async def check(wheel: Path, env: dict[str, str]) -> None:
        calls.append(wheel)
        if fails:
            raise RuntimeError("canary-output")

    monkeypatch.setattr(runner, "check_wheel", check)
    wheel = tmp_path / "candidate.whl"
    wheel.touch()
    assert runner.main(["--wheel", str(wheel)]) == int(fails)
    assert calls == [wheel]
    captured = capsys.readouterr()
    assert ("mcp_release: FAIL" if fails else "mcp_release: PASS") in captured.out
    assert "canary-output" not in captured.out + captured.err


def test_existing_nonwheel_is_rejected(tmp_path: Path) -> None:
    """An existing file is not enough when its suffix is not .whl."""
    path = tmp_path / "candidate.txt"
    path.touch()
    assert runner.main(["--wheel", str(path)]) == 1
