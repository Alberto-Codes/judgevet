"""Tests for the docvet exclude handling in scripts/vet_file.sh.

The PostToolUse hook passes one explicit path to docvet. An explicit path
overrides the `[tool.docvet] exclude` list, so the hook must skip docvet
itself for excluded paths. The shim tests replace `uv` with a logging shell
script, so they need no real tool. The last test runs the real tools against
the repository's own `pyproject.toml`.

Examples:
    ```bash
    uv run pytest -q tests/unit/test_vet_file_hook.py
    ```

See Also:
    - [tests.unit.test_check_test_hygiene][]: Tests for another repository script.
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
HOOK = REPO_ROOT / "scripts" / "vet_file.sh"
FINDING = "SYNTHETIC-DOCVET-FINDING"
WORKTREE = ".claude/worktrees/w1"
SHIM = f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$SHIM_LOG"
case " $* " in *" docvet "*) printf '%s\\n' "{FINDING}" ;; esac
exit 0
"""


def _project(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Build a temp project root, a `uv` shim directory and the shim log path.

    Args:
        tmp_path: The pytest temporary directory for this test.

    Returns:
        The project root, the shim directory and the shim log path.
    """
    root = tmp_path / "project"
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "pyproject.toml").write_text(
        '[tool.docvet]\nexclude = ["tests", "scripts"]\n'
    )
    (root / "src" / "pkg" / "mod.py").write_text("X = 1\n")
    (root / "tests" / "test_mod.py").write_text("Y = 2\n")
    for prefix in (WORKTREE, f"{WORKTREE}/w2"):
        (root / prefix / "src" / "pkg").mkdir(parents=True)
        (root / prefix / "tests").mkdir()
        (root / prefix / "src" / "pkg" / "mod.py").write_text("X = 1\n")
        (root / prefix / "tests" / "test_mod.py").write_text("Y = 2\n")
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    shim = shim_dir / "uv"
    shim.write_text(SHIM)
    shim.chmod(0o755)
    return root, shim_dir, tmp_path / "shim.log"


async def _hook(env: dict[str, str], payload: str) -> tuple[int, str, str]:
    """Execute and reap the hook with captured streams and a bounded runtime.

    Args:
        env: The complete child environment.
        payload: The hook JSON written to stdin.

    Returns:
        The exit code, stdout and stderr of the hook.
    """
    bash = shutil.which("bash")
    assert bash is not None
    child = await asyncio.create_subprocess_exec(
        bash,
        str(HOOK),
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            child.communicate(payload.encode()), timeout=120
        )
    finally:
        if child.returncode is None:
            child.kill()
            await child.wait()
    assert child.returncode is not None
    return child.returncode, stdout.decode(), stderr.decode()


def _run_hook(
    root: Path, file_path: str, extra_path: Path | None = None, log: Path | None = None
) -> tuple[int, str, str]:
    """Run the hook for one Edit of `file_path` under project root `root`.

    Args:
        root: The project root passed as CLAUDE_PROJECT_DIR.
        file_path: The edited file, relative to the root.
        extra_path: A directory placed first on PATH, or None.
        log: The shim log path, or None.

    Returns:
        The exit code, stdout and stderr of the hook.
    """
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
    if extra_path is not None:
        env["PATH"] = f"{extra_path}{os.pathsep}{env.get('PATH', '')}"
    if log is not None:
        env["SHIM_LOG"] = str(log)
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": file_path}})
    return asyncio.run(_hook(env, payload))


def test_excluded_path_skips_docvet(tmp_path: Path) -> None:
    """A path under an excluded directory gets ruff but never docvet."""
    root, shim_dir, log = _project(tmp_path)
    code, stdout, stderr = _run_hook(root, "tests/test_mod.py", shim_dir, log)
    assert code == 0, stderr
    assert stdout == ""
    calls = log.read_text().splitlines()
    assert not [c for c in calls if "docvet" in c]
    assert len([c for c in calls if "ruff" in c]) == 2


def test_included_path_runs_docvet(tmp_path: Path) -> None:
    """A path outside the exclude list still reports docvet findings."""
    root, shim_dir, log = _project(tmp_path)
    code, stdout, stderr = _run_hook(root, "src/pkg/mod.py", shim_dir, log)
    assert code == 0, stderr
    context = json.loads(stdout)["hookSpecificOutput"]["additionalContext"]
    assert "docvet:" in context
    assert FINDING in context
    assert [c for c in log.read_text().splitlines() if "docvet" in c]


def test_repository_exclude_list_is_read() -> None:
    """The real hook reads the repository's own docvet exclude list."""
    code, stdout, stderr = _run_hook(REPO_ROOT, "tests/unit/test_cli_help.py")
    assert code == 0, stderr
    assert "docvet:" not in stdout


def test_worktree_excluded_path_skips_docvet(tmp_path: Path) -> None:
    """An excluded path inside an Agent-tool worktree never reaches docvet."""
    root, shim_dir, log = _project(tmp_path)
    code, stdout, stderr = _run_hook(
        root, f"{WORKTREE}/tests/test_mod.py", shim_dir, log
    )
    assert code == 0, stderr
    assert "docvet:" not in stdout
    calls = log.read_text().splitlines()
    assert not [c for c in calls if "docvet" in c]
    assert len([c for c in calls if "ruff" in c]) == 2


def test_worktree_included_path_runs_docvet(tmp_path: Path) -> None:
    """A worktree path outside the exclude list still reports docvet findings."""
    root, shim_dir, log = _project(tmp_path)
    code, stdout, stderr = _run_hook(root, f"{WORKTREE}/src/pkg/mod.py", shim_dir, log)
    assert code == 0, stderr
    context = json.loads(stdout)["hookSpecificOutput"]["additionalContext"]
    assert "docvet:" in context
    assert FINDING in context


def test_worktree_prefix_is_stripped_once(tmp_path: Path) -> None:
    """Only one worktree component is stripped, so `w2/tests` is not excluded."""
    root, shim_dir, log = _project(tmp_path)
    code, stdout, stderr = _run_hook(
        root, f"{WORKTREE}/w2/tests/test_mod.py", shim_dir, log
    )
    assert code == 0, stderr
    context = json.loads(stdout)["hookSpecificOutput"]["additionalContext"]
    assert "docvet:" in context
    assert [c for c in log.read_text().splitlines() if "docvet" in c]
