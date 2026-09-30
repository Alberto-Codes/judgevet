"""Prove that uv subprocesses in the suite never write the shared uv cache.

A pytest session owns one private uv cache. The helpers name it to the child
with ``--cache-dir``, and fall back to ``--no-cache`` when no session cache is
set. The caller's own ``UV_CACHE_DIR`` never changes. See issue #243.

Examples:
    Run the offline checks::

        uv run pytest -q tests/unit/test_uv_session_cache.py

See Also:
    - [scripts.smoke_release][]: The helpers that build and install wheels.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from scripts import smoke_release

pytestmark = pytest.mark.unit

SESSION_VAR = "JUDGEVET_TEST_UV_CACHE_DIR"
CALLER_CACHE = "/caller/own/uv-cache"


class Recorder:
    """Record each subprocess call a helper makes instead of running it.

    Attributes:
        calls: The command and keyword arguments of every call.
    """

    def __init__(self) -> None:
        """Start with no recorded calls."""
        self.calls: list[tuple[list[str], dict[str, Any]]] = []

    def __call__(
        self, command: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        """Record one call and report success."""
        self.calls.append((list(command), kwargs))
        return subprocess.CompletedProcess(command, 0, "", "")


def _build(tmp_path: Path) -> None:
    smoke_release._build_wheel_subprocess(tmp_path / "out")


def _install(tmp_path: Path) -> None:
    smoke_release.install_wheel(tmp_path / "python", tmp_path / "candidate.whl")


HELPERS: dict[str, Callable[[Path], None]] = {"build": _build, "install": _install}


def _run(helper: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    recorder = Recorder()
    monkeypatch.setattr(smoke_release.subprocess, "run", recorder)
    monkeypatch.setenv("UV_CACHE_DIR", CALLER_CACHE)
    HELPERS[helper](tmp_path)
    assert len(recorder.calls) == 1
    command, kwargs = recorder.calls[0]
    child_env = kwargs.get("env")
    if child_env is not None:
        assert child_env.get("UV_CACHE_DIR") in (None, CALLER_CACHE)
    assert os.environ["UV_CACHE_DIR"] == CALLER_CACHE
    return command


@pytest.mark.parametrize("helper", sorted(HELPERS))
def test_helper_names_session_cache(
    helper: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pass the session cache to the uv child when a session sets one."""
    session = tmp_path / "session-cache"
    monkeypatch.setenv(SESSION_VAR, str(session))
    command = _run(helper, tmp_path, monkeypatch)
    position = command.index("--cache-dir")
    assert command[position + 1] == str(session)
    assert "--no-cache" not in command


@pytest.mark.parametrize("helper", sorted(HELPERS))
def test_helper_disables_cache_without_session(
    helper: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Disable the uv cache for scripts and release smoke outside pytest."""
    monkeypatch.delenv(SESSION_VAR, raising=False)
    command = _run(helper, tmp_path, monkeypatch)
    assert "--no-cache" in command
    assert "--cache-dir" not in command


def test_child_env_names_session_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give an env-only uv child the session cache, or no cache outside pytest."""
    helper = getattr(smoke_release, "uv_cache_env", None)
    assert helper is not None, "smoke_release.uv_cache_env is missing"
    monkeypatch.setenv("UV_CACHE_DIR", CALLER_CACHE)
    monkeypatch.setenv(SESSION_VAR, "/session/cache")
    assert helper() == {"UV_CACHE_DIR": "/session/cache"}
    monkeypatch.delenv(SESSION_VAR)
    assert helper() == {"UV_NO_CACHE": "1"}
    assert os.environ["UV_CACHE_DIR"] == CALLER_CACHE


def test_session_owns_private_cache() -> None:
    """Require the session fixture to provide a private, existing cache."""
    session = os.environ.get(SESSION_VAR)
    assert session, f"{SESSION_VAR} is not set for this session"
    assert Path(session).is_dir()
    shared = Path.home() / ".cache" / "uv"
    assert not Path(session).resolve().is_relative_to(shared.resolve())
    assert os.environ.get("UV_CACHE_DIR") != session
