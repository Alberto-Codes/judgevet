"""Exercise configuration hooks in disposable tracked repositories.

Each hook child resolves uv against the session cache and pre-commit against
a store owned by the test run, never the user-level ``~/.cache/pre-commit``.

Examples:
    ```bash
    uv run pytest -q tests/unit/test_configuration_gates.py
    ```

See Also:
    - [tests.unit.pre_commit_home_support][]: The run's pre-commit stores.
    - [scripts.smoke_release][]: The session uv cache helper.
"""

import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.smoke_release import SESSION_CACHE_VAR, uv_cache_env
from tests.unit.pre_commit_home_support import pre_commit_home_env

ROOT = Path(__file__).resolve().parents[2]


def hook_configuration(hook_id: str, stage: str) -> str:
    """Select the actual configured hook and retain its upstream repository pin.

    Args:
        hook_id: The configured hook to select.
        stage: The stage the hook must run at.

    Returns:
        The whole configuration source, unchanged.
    """
    source = (ROOT / ".pre-commit-config.yaml").read_text()
    configuration = yaml.safe_load(source)
    for repo in configuration["repos"]:
        for hook in repo["hooks"]:
            if hook["id"] != hook_id:
                continue
            assert stage in hook.get("stages", configuration["default_stages"])
            if hook_id == "uv-lock":
                assert configuration["repos"][0]["hooks"][0]["id"] == "uv-lock"
                assert hook["files"] == r"^(uv\.lock|pyproject\.toml|uv\.toml)$"
                assert hook["entry"] == "uv lock --check"
                assert hook["pass_filenames"] is False
            if hook_id == "actionlint":
                assert repo["repo"] == "https://github.com/rhysd/actionlint"
                assert repo["rev"] == "v1.7.12"
            return source
    pytest.fail(f"Missing required {hook_id} hook")


def prepare_fixture(tmp_path: Path, hook_id: str, broken: bool) -> None:
    """Write a valid or invalid configuration for the selected real tool."""
    for name in ("README.md", "LICENSE"):
        shutil.copyfile(ROOT / name, tmp_path / name)
    shutil.copytree(ROOT / "src", tmp_path / "src")
    if hook_id == "uv-lock":
        project = (ROOT / "pyproject.toml").read_text()
        if broken:
            project = project.replace('version = "', 'version = "99.', 1)
        (tmp_path / "pyproject.toml").write_text(project)
        (tmp_path / "uv.lock").write_bytes((ROOT / "uv.lock").read_bytes())
    else:
        project = (ROOT / "pyproject.toml").read_text()
        (tmp_path / "pyproject.toml").write_text(project)
        (tmp_path / "uv.lock").write_bytes((ROOT / "uv.lock").read_bytes())
        directory = tmp_path / ".github/workflows"
        directory.mkdir(parents=True)
        expression = "${{ nonexistent.value }}" if broken else "hello"
        workflow = (
            '---\nname: Fixture\n"on": push\njobs:\n  example:\n'
            "    runs-on: ubuntu-latest\n    steps:\n"
            f'      - run: echo "{expression}"\n'
        )
        if hook_id == "yamllint" and broken:
            workflow = workflow.replace(
                "name: Fixture\n", "name: Fixture\nname: Other\n"
            )
        (directory / "fixture.yml").write_text(workflow)


def hook_child_env() -> dict[str, str]:
    """Build the hook child's environment around the run's caches.

    Returns:
        The inherited environment with the uv cache variables and a
        test-owned ``PRE_COMMIT_HOME`` merged in.
    """
    return os.environ | uv_cache_env() | pre_commit_home_env()


UV_CACHE_KEYS = ("UV_CACHE_DIR", "UV_NO_CACHE")


def test_hook_child_env_names_the_session_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Require the hook child to resolve uv against the session cache."""
    cache = tmp_path / "session-cache"
    monkeypatch.setenv(SESSION_CACHE_VAR, str(cache))
    monkeypatch.delenv("UV_CACHE_DIR", raising=False)
    monkeypatch.delenv("UV_NO_CACHE", raising=False)
    seen: list[dict[str, str | None] | None] = []

    def _record(command: list[str], **options: Any) -> subprocess.CompletedProcess[str]:
        # Keep only the cache keys: --showlocals would print a whole child env.
        env: Mapping[str, str] | None = options.get("env")
        seen.append(
            None if env is None else {key: env.get(key) for key in UV_CACHE_KEYS}
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _record)
    work = tmp_path / "work"
    work.mkdir()
    test_configuration_hook_executes(work, "uv-lock", "pre-commit", False)
    assert len(seen) == 1
    passed = seen[0]
    assert passed is not None
    assert passed["UV_CACHE_DIR"] == str(cache)
    monkeypatch.delenv(SESSION_CACHE_VAR)
    assert hook_child_env()["UV_NO_CACHE"] == "1"


def test_hook_child_env_owns_its_pre_commit_home(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Keep the hook child's pre-commit store under the run's temporary directory.

    The user-level ``~/.cache/pre-commit/db.db`` is shared with every other
    process on the machine. See issue #232.
    """
    home = hook_child_env().get("PRE_COMMIT_HOME")
    assert home is not None
    basetemp = tmp_path_factory.getbasetemp().resolve()
    run = basetemp.parent if os.environ.get("PYTEST_XDIST_WORKER") else basetemp
    assert Path(home).resolve().is_relative_to(run)
    assert not Path(home).resolve().is_relative_to(Path.home() / ".cache")
    assert (Path(home) / "db.db").is_file()


@pytest.mark.parametrize("stage", ["pre-commit", "pre-push"])
@pytest.mark.parametrize("hook_id", ["uv-lock", "yamllint", "actionlint"])
@pytest.mark.parametrize("broken", [False, True])
def test_configuration_hook_executes(
    tmp_path: Path, hook_id: str, stage: str, broken: bool
) -> None:
    """Require real hooks to distinguish valid inputs from their failure fixtures."""
    configuration = hook_configuration(hook_id, stage)
    (tmp_path / ".pre-commit-config.yaml").write_text(configuration)
    prepare_fixture(tmp_path, hook_id, broken)
    lock = (tmp_path / "uv.lock").read_bytes()
    (tmp_path / "check.sh").write_text(
        "set -eu\ngit init -q\ngit add .\n"
        + shlex.join(
            [
                sys.executable,
                "-m",
                "pre_commit",
                "run",
                hook_id,
                "--hook-stage",
                stage,
                "--all-files",
            ]
        )
        + "\n"
    )
    result = subprocess.run(
        ["/usr/bin/bash", "check.sh"],
        cwd=tmp_path,
        env=hook_child_env(),
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    output = result.stdout + result.stderr
    assert result.returncode == (1 if broken else 0), output
    assert "Skipped" not in output
    if broken:
        diagnostic = {
            "uv-lock": "needs to be updated",
            "yamllint": "duplication of key",
            "actionlint": 'undefined variable "nonexistent"',
        }[hook_id]
        assert diagnostic in output
    assert (tmp_path / "uv.lock").read_bytes() == lock


def test_ci_uses_shared_configuration_hooks() -> None:
    """Keep the CI checks required and sourced from the same hook configuration."""
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    job = workflow["jobs"]["lint"]
    assert "if" not in job and not job.get("continue-on-error", False)
    steps = job["steps"]
    commands = [step["run"] for step in steps if "run" in step]
    assert commands.count("uv lock --check") == 1
    assert commands.index("uv lock --check") < commands.index("uv sync --locked --dev")
    for hook_id in ("yamllint", "actionlint"):
        command = f"uv run pre-commit run {hook_id} --all-files"
        assert command in commands
        step = next(step for step in steps if step.get("run") == command)
        assert "if" not in step and not step.get("continue-on-error", False)
