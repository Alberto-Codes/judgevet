"""Execute the owned pre-push and CI audit interfaces with controlled outcomes."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def audit_command() -> str:
    """Read the owned workflow contract and reject optional audit execution."""
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    job = workflow["jobs"]["audit"]
    assert "if" not in job
    assert not job.get("continue-on-error", False)
    steps = job["steps"]
    setup = next(
        step for step in steps if step.get("uses", "").startswith("astral-sh/setup-uv@")
    )
    assert setup["with"]["version"] == "0.11.20"
    step = next(step for step in steps if "run" in step and "audit" in step["run"])
    assert "if" not in step
    assert not step.get("continue-on-error", False)
    return step["run"]


def fake_uv(tmp_path: Path, status: int) -> tuple[dict[str, str], Path]:
    """Record actual argv and return a controlled process status."""
    executable = tmp_path / "uv"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json,os,pathlib,sys\n"
        "pathlib.Path(os.environ['AUDIT_RECORD']).write_text(json.dumps(sys.argv[1:]))\n"
        "sys.exit(int(os.environ['AUDIT_STATUS']))\n"
    )
    executable.chmod(0o755)
    record = tmp_path / "arguments.json"
    environment = dict(
        os.environ,
        PATH=str(tmp_path) + os.pathsep + os.environ["PATH"],
        AUDIT_RECORD=str(record),
        AUDIT_STATUS=str(status),
    )
    return environment, record


@pytest.mark.parametrize("status", [0, 23])
def test_pre_push_audit_propagates_status(tmp_path: Path, status: int) -> None:
    """Run the actual selected hook even when the scratch checkout has no files."""
    configuration = (ROOT / ".pre-commit-config.yaml").read_text()
    hook = next(
        (
            hook
            for repo in yaml.safe_load(configuration)["repos"]
            for hook in repo["hooks"]
            if hook["id"] == "dependency-audit"
        ),
        None,
    )
    assert hook is not None, "Missing required dependency-audit hook"
    assert hook["stages"] == ["pre-push"]
    assert hook["always_run"] is True
    assert hook["pass_filenames"] is False
    (tmp_path / ".pre-commit-config.yaml").write_text(configuration)
    subprocess.run(
        ["/usr/bin/git", "init", "-q"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        timeout=10,
    )
    environment, record = fake_uv(tmp_path, status)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pre_commit",
            "run",
            "dependency-audit",
            "--hook-stage",
            "pre-push",
            "--all-files",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == (0 if status == 0 else 1), result.stdout + result.stderr
    assert json.loads(record.read_text()) == [
        "audit",
        "--locked",
        "--preview-features",
        "audit-command",
    ]


@pytest.mark.parametrize("status", [0, 23])
def test_ci_audit_propagates_status(tmp_path: Path, status: int) -> None:
    """Execute the configured CI shell command and require failing status to survive."""
    command = audit_command()
    (tmp_path / "audit.sh").write_text(command)
    environment, record = fake_uv(tmp_path, status)
    result = subprocess.run(
        ["/usr/bin/bash", "-e", "-o", "pipefail", "audit.sh"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == status, result.stdout + result.stderr
    assert json.loads(record.read_text()) == [
        "audit",
        "--locked",
        "--preview-features",
        "audit-command",
    ]
