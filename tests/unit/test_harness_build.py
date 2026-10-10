"""Acceptance tests for scripts/harness_build.sh.

The script runs one builder brief on an external harness, Cursor or Codex,
inside an isolated worktree. These tests replace `cursor-agent` and `codex`
with logging shell shims, so they bill no pool and need no network. Each shim
records its arguments, performs one action chosen by `SHIM_ACTION`, and
prints the receipt shape the real CLI prints.

Examples:
    ```bash
    uv run pytest -q tests/unit/test_harness_build.py
    ```

See Also:
    - [tests.unit.test_vet_file_hook][]: Tests for another repository shell script.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "harness_build.sh"
DENY = '{"permissions":{"allow":[],"deny":["Shell(git)"]}}\n'
BRIEF = "Change nothing. Do not commit."

# Both shims read SHIM_ACTION: "commit" stages a new file and tries to commit,
# "exit" exits with status 3, and anything else writes one file.
CURSOR_SHIM = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$SHIM_LOG"
case "${SHIM_ACTION:-write}" in
  commit)
    printf 'shim\\n' > "$SHIM_WORKTREE/shim.txt"
    git -C "$SHIM_WORKTREE" add -A && git -C "$SHIM_WORKTREE" commit -q -m shim ;;
  exit) printf '{"type":"result","result":"gave up","session_id":"s-1"}\\n'; exit 3 ;;
  *) printf 'made\\n' > "$SHIM_WORKTREE/made.txt" ;;
esac
printf '{"type":"result","subtype":"success","is_error":false,'
printf '"result":"cursor done","session_id":"s-1"}\\n'
"""

CODEX_SHIM = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$SHIM_LOG"
brief=$(cat)
printf 'brief:%s\\n' "$brief" >> "$SHIM_LOG"
last=""
while [ $# -gt 0 ]; do
  case "$1" in -o) last="$2"; shift ;; esac
  shift
done
case "${SHIM_ACTION:-write}" in
  commit)
    printf 'shim\\n' > "$SHIM_WORKTREE/shim.txt"
    git -C "$SHIM_WORKTREE" add -A && git -C "$SHIM_WORKTREE" commit -q -m shim ;;
  exit) printf 'gave up\\n' > "$last"; exit 3 ;;
  *) printf 'made\\n' > "$SHIM_WORKTREE/made.txt" ;;
esac
printf 'codex done\\n' > "$last"
printf '{"type":"turn.completed","usage":{"input_tokens":7,"output_tokens":2}}\\n'
"""


def _which(name: str) -> str:
    """Return the full path of an installed executable.

    Args:
        name: The executable name.

    Returns:
        The absolute path.
    """
    path = shutil.which(name)
    assert path is not None, name
    return path


async def _exec(argv: list[str], env: dict[str, str]) -> tuple[int, str, str]:
    """Execute and reap one process with captured streams and a bounded runtime.

    Args:
        argv: The full command line, with an absolute executable.
        env: The complete child environment.

    Returns:
        The exit code, stdout and stderr.
    """
    child = await asyncio.create_subprocess_exec(
        *argv,
        env=env,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(child.communicate(), timeout=120)
    finally:
        if child.returncode is None:
            child.kill()
            await child.wait()
    assert child.returncode is not None
    return child.returncode, stdout.decode(), stderr.decode()


def _git(worktree: Path, *args: str) -> tuple[int, str]:
    """Run one git command inside the worktree.

    Args:
        worktree: The repository to run in.
        *args: The git arguments.

    Returns:
        The exit code and the stripped stdout.
    """
    env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"}
    code, out, _ = asyncio.run(_exec([_which("git"), "-C", str(worktree), *args], env))
    return code, out.strip()


def _git_ok(worktree: Path, *args: str) -> str:
    """Run one git command that must succeed and return its stdout.

    Args:
        worktree: The repository to run in.
        *args: The git arguments.

    Returns:
        The stripped stdout.
    """
    code, out = _git(worktree, *args)
    assert code == 0, args
    return out


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """Build a one-commit repository with the Cursor deny file committed.

    Args:
        tmp_path: The pytest temporary directory for this test.

    Returns:
        The repository root.
    """
    root = tmp_path / "wt"
    root.mkdir()
    _git_ok(root, "init", "-q", "-b", "main")
    _git_ok(root, "config", "user.email", "t@example.invalid")
    _git_ok(root, "config", "user.name", "t")
    (root / ".cursor").mkdir()
    (root / ".cursor" / "cli.json").write_text(DENY)
    (root / "a.txt").write_text("a\n")
    _git_ok(root, "add", "-A")
    _git_ok(root, "commit", "-q", "-m", "base")
    return root


@pytest.fixture
def shims(tmp_path: Path) -> tuple[Path, Path]:
    """Write the two shim binaries and return their directory and log path.

    Args:
        tmp_path: The pytest temporary directory for this test.

    Returns:
        The shim directory and the shim log path.
    """
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    for name, body in (("cursor-agent", CURSOR_SHIM), ("codex", CODEX_SHIM)):
        shim = shim_dir / name
        shim.write_text(body)
        shim.chmod(0o755)
    return shim_dir, tmp_path / "shim.log"


def _run(
    worktree: Path,
    shims: tuple[Path, Path],
    *args: str,
    action: str = "write",
    extra_env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Run the script with the shims first on PATH.

    Args:
        worktree: The repository the brief runs in.
        shims: The shim directory and log path.
        *args: The harness, then the script arguments after the brief file.
        action: The shim action.
        extra_env: Extra environment variables for the script.

    Returns:
        The exit code, stdout and stderr of the script.
    """
    shim_dir, log = shims
    brief = worktree.parent / "brief.md"
    brief.write_text(BRIEF + "\n")
    env = {
        **os.environ,
        "PATH": f"{shim_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "SHIM_LOG": str(log),
        "SHIM_ACTION": action,
        "SHIM_WORKTREE": str(worktree),
        "GIT_CONFIG_GLOBAL": "/dev/null",
    }
    env.pop("GIT_CONFIG_COUNT", None)
    env.update(extra_env or {})
    argv = [_which("bash"), str(SCRIPT), args[0], str(worktree), str(brief), *args[1:]]
    return asyncio.run(_exec(argv, env))


def _log(shims: tuple[Path, Path]) -> str:
    """Return the shim log, or an empty string when no shim ran.

    Args:
        shims: The shim directory and log path.

    Returns:
        The log text.
    """
    log = shims[1]
    return log.read_text() if log.exists() else ""


HARNESSES = [("cursor", ""), ("codex", "gpt-6-luna")]


@pytest.mark.parametrize(("harness", "model"), HARNESSES)
def test_commit_inside_the_run_is_refused(
    worktree: Path, shims: tuple[Path, Path], harness: str, model: str
) -> None:
    """A commit the agent attempts is refused by the hook and HEAD stays put."""
    args = (harness, model) if model else (harness,)
    _, _, err = _run(worktree, shims, *args, action="commit")
    assert "commits are blocked" in err
    assert _git_ok(worktree, "rev-list", "--count", "HEAD") == "1"
    assert "A  shim.txt" in _git_ok(worktree, "status", "--short")


def test_preset_git_config_count_is_refused(
    worktree: Path, shims: tuple[Path, Path]
) -> None:
    """The script refuses to overwrite a caller's GIT_CONFIG_COUNT."""
    code, _, err = _run(worktree, shims, "cursor", extra_env={"GIT_CONFIG_COUNT": "1"})
    assert code == 1
    assert "GIT_CONFIG_COUNT" in err
    assert _log(shims) == ""


def test_codex_requires_a_named_model(worktree: Path, shims: tuple[Path, Path]) -> None:
    """Codex has no routing, so a run with no model never starts."""
    code, _, err = _run(worktree, shims, "codex")
    assert code == 2
    assert "model" in err
    assert _log(shims) == ""


def test_cursor_requires_the_deny_file(
    worktree: Path, shims: tuple[Path, Path]
) -> None:
    """Cursor runs only behind the committed deny file."""
    (worktree / ".cursor" / "cli.json").unlink()
    code, _, err = _run(worktree, shims, "cursor")
    assert code == 1
    assert "cli.json" in err
    assert _log(shims) == ""


@pytest.mark.parametrize(("harness", "model"), HARNESSES)
def test_exit_code_propagates_with_the_receipt(
    worktree: Path, shims: tuple[Path, Path], harness: str, model: str
) -> None:
    """The agent's exit code is the script's, and the receipt is printed."""
    args = (harness, model) if model else (harness,)
    code, out, _ = _run(worktree, shims, *args, action="exit")
    assert code == 3
    for heading in ("result:", "usage:", "status:", "diff:"):
        assert heading in out
    assert "gave up" in out


def test_cursor_launch_arguments(worktree: Path, shims: tuple[Path, Path]) -> None:
    """Cursor runs in print mode on the worktree with the default pool model."""
    code, out, _ = _run(worktree, shims, "cursor")
    assert code == 0
    log = _log(shims)
    assert "-p" in log.split()
    assert "--output-format json" in log
    assert f"--workspace {worktree}" in log
    assert "--model cursor-grok-4.6-medium" in log
    assert BRIEF in log
    assert "cursor done" in out
    assert "s-1" in out
    assert (worktree / "made.txt").exists()
    assert "made.txt" in out


def test_codex_launch_arguments(worktree: Path, shims: tuple[Path, Path]) -> None:
    """Codex runs sandboxed in the worktree with the named model and effort."""
    code, out, _ = _run(worktree, shims, "codex", "gpt-6-luna", "low")
    assert code == 0
    log = _log(shims)
    assert f"-C {worktree}" in log
    assert "-s workspace-write" in log
    assert "-m gpt-6-luna" in log
    assert "model_reasoning_effort=low" in log
    assert "approval_policy=never" in log
    assert f"brief:{BRIEF}" in log
    assert "codex done" in out
    usage_line = next(line for line in out.splitlines() if line.startswith("{"))
    assert json.loads(usage_line) == {"input_tokens": 7, "output_tokens": 2}


def test_repository_config_is_untouched(
    worktree: Path, shims: tuple[Path, Path]
) -> None:
    """The hook path lives in the environment, never in the repository config."""
    code, _, _ = _run(worktree, shims, "cursor")
    assert code == 0
    probe_code, probe_out = _git(worktree, "config", "--local", "core.hooksPath")
    assert probe_code == 1
    assert probe_out == ""
