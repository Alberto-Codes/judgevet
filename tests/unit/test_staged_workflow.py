"""Prove the staged-diff example through Git, the installed CLI and a local peer."""

import asyncio
import copy
import json
import os
import shlex
import shutil
import sys
from pathlib import Path

import pytest

from tests.cli_process_support import CANARY, SUCCESS, Peer, serve

pytestmark = pytest.mark.unit
EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "staged-review"


async def _run(
    command: list[str], cwd: Path, env: dict[str, str]
) -> tuple[int, str, str]:
    """Execute and reap a child with captured streams and a bounded runtime."""
    child = await asyncio.create_subprocess_exec(
        *command,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(child.communicate(), timeout=10)
    finally:
        if child.returncode is None:
            child.kill()
            await child.wait()
    assert child.returncode is not None
    return child.returncode, stdout.decode(), stderr.decode()


def _call(command: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str, str]:
    """Run the async process boundary from a synchronous test."""
    return asyncio.run(_run(command, cwd, env))


def _setup(tmp_path: Path, url: str, staged: bool) -> tuple[Path, Path, dict[str, str]]:
    """Create a repository independent of the checkout and copy the example."""
    repo = tmp_path / "repository with spaces"
    repo.mkdir()
    bundle = tmp_path / "example with spaces"
    shutil.copytree(EXAMPLE, bundle)
    env = {
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
        "LANG": "C.UTF-8",
        "JEV_API__KEY": CANARY,
        "JEV_API__BASE_URL": url,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    git = shutil.which("git", path=env["PATH"])
    assert git is not None
    assert _call([git, "init", "-q"], repo, env)[0] == 0
    (repo / "staged.txt").write_text("staged-review-marker\n", encoding="utf-8")
    if staged:
        assert _call([git, "add", "staged.txt"], repo, env)[0] == 0
    (repo / "staged.txt").write_text("unstaged-private-marker\n", encoding="utf-8")
    return repo, bundle, env


def _trace_cli(tmp_path: Path, env: dict[str, str]) -> Path:
    """Record exact CLI arguments while forwarding to the real installed command."""
    shim = tmp_path / "cli-shim"
    shim.mkdir()
    trace = tmp_path / "cli-arguments"
    wrapper = shim / "judgevet"
    wrapper.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$@" > '
        + shlex.quote(str(trace))
        + "\nexec "
        + shlex.quote(str(Path(sys.executable).parent / "judgevet"))
        + ' "$@"\n'
    )
    wrapper.chmod(0o755)
    env["PATH"] = str(shim) + os.pathsep + env["PATH"]
    return trace


def _break_producer(tmp_path: Path, env: dict[str, str]) -> None:
    """Emit partial output then fail the producer independently of the consumer."""
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    fakegit = fakebin / "git"
    fakegit.write_text("#!/bin/sh\nprintf 'partial-diff-marker\\n'\nexit 7\n")
    fakegit.chmod(0o755)
    env["PATH"] = str(fakebin) + os.pathsep + env["PATH"]


def _assert_judgment(
    scenario: str, stdout: str, stderr: str, trace: Path, bundle: Path, peer: Peer
) -> None:
    """Check exact CLI wiring and the observed real-adapter judgment envelope."""
    assert trace.read_text().splitlines() == [
        "--state-file",
        "-",
        "--questions-file",
        str(bundle / "questions.json"),
        "--policy",
        str(bundle / "policy.json"),
        "--json",
    ]
    assert len(peer.requests) == 1
    body = peer.requests[0]["body"]
    assert "staged-review-marker" in body["state"]
    assert "unstaged-private-marker" not in body["state"]
    assert body["questions"] == json.loads((bundle / "questions.json").read_text())
    if scenario == "auth":
        assert stdout == ""
        assert json.loads(stderr)["error"]
    else:
        answer = json.loads(stdout)
        assert answer["policy"]["result"] == ("pass" if scenario == "pass" else "fail")
        assert set(answer["answers"]) == {"approve"}
        assert stderr == ""


@pytest.mark.parametrize(
    "scenario",
    [
        "pass",
        "unmet",
        "auth",
        "clean",
        "producer",
        "partial-producer",
        "invalid-policy",
        "usage",
    ],
)
def test_staged_workflow(tmp_path: Path, scenario: str) -> None:
    """Keep policy status, staged bytes and producer failure independently observable."""
    payload = copy.deepcopy(SUCCESS)
    payload["answers"] = {"approve": copy.deepcopy(SUCCESS["answers"]["noul"])}
    payload["answers"]["approve"]["noul"] = 0.9 if scenario != "unmet" else 0.1
    status = 401 if scenario == "auth" else 200
    if scenario == "auth":
        payload = {"detail": {"error_type": "auth", "message": "denied"}}
    with serve(status, payload) as peer:
        repo, bundle, env = _setup(tmp_path, peer.url, scenario != "clean")
        if scenario == "producer":
            repo = tmp_path
        if scenario == "partial-producer":
            _break_producer(tmp_path, env)
        if scenario == "invalid-policy":
            (bundle / "policy.json").write_text('{"rules":[]}', encoding="utf-8")
        scratch = tmp_path / "scratch"
        scratch.mkdir()
        env["TMPDIR"] = str(scratch)
        trace = _trace_cli(tmp_path, env)
        command = bundle / "review-staged.sh"
        assert command.stat().st_mode & 0o111
        args = [str(command)] + (["unexpected"] if scenario == "usage" else [])
        code, stdout, stderr = _call(args, repo, env)
        assert list(scratch.iterdir()) == []
    expected = {
        "pass": 0,
        "unmet": 3,
        "auth": 1,
        "clean": 0,
        "producer": 1,
        "partial-producer": 1,
        "invalid-policy": 1,
        "usage": 2,
    }
    assert code == expected[scenario], (stdout, stderr)
    if scenario in {"clean", "producer", "partial-producer", "invalid-policy", "usage"}:
        assert not peer.requests
        assert stdout == ""
        assert stderr
    else:
        _assert_judgment(scenario, stdout, stderr, trace, bundle, peer)
    assert CANARY not in stdout + stderr
    assert "unstaged-private-marker" not in stdout + stderr
