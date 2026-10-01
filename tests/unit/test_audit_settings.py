"""Opt in to the JSONL audit sink through settings at every hosted root.

``JEV_API__AUDIT_PATH`` names the file. Unset means no sink. The CLI judge
command, the CLI policy command and the installed ``judgevet-mcp`` command
each append one line per call, and none of them writes the key or the state.
Source: https://github.com/Alberto-Codes/judgevet/issues/54#issuecomment-5931714089
and https://github.com/Alberto-Codes/judgevet/issues/54#issuecomment-5931981669.
The synthetic answer shape follows https://docs.typesafe.ai/api.md.
"""

import asyncio
import json
from importlib.util import find_spec
from pathlib import Path

import pytest
from typer.testing import CliRunner

from judgevet.adapters.inbound import cli
from tests.cli_process_support import CANARY, SUCCESS, serve
from tests.unit.test_cli_rate_limit import arguments
from tests.unit.test_mcp_subprocess import environment, exchange, start, stop

pytestmark = pytest.mark.unit
STATE = "private-state-canary"
MCP_STATE = "offline-state"
NOUL = {
    "model": "jev-1.13.0",
    "usage": {"input_tokens": 3, "output_tokens": 2},
    "answers": {"noul_question": {"type": "noul", "noul": 0.42}},
}
requires_mcp = pytest.mark.skipif(find_spec("mcp") is None, reason="requires MCP")


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Set the synthetic key and clear any inherited audit path.

    Args:
        monkeypatch: Environment patcher.

    Returns:
        The same patcher, for further variables.
    """
    monkeypatch.setenv("JEV_API__KEY", CANARY)
    monkeypatch.delenv("JEV_API__AUDIT_PATH", raising=False)
    return monkeypatch


def audit_lines(path: Path, secrets: tuple[str, ...]) -> list[dict[str, object]]:
    """Read every audit line and require that no secret reached the file.

    Args:
        path: Audit file the root wrote.
        secrets: Values that must not appear anywhere in the file.

    Returns:
        One decoded record per line.
    """
    text = path.read_text(encoding="utf-8")
    for secret in secrets:
        assert secret not in text
    return [json.loads(line) for line in text.splitlines()]


@pytest.mark.parametrize("policy", [False, True], ids=["judge", "policy"])
def test_cli_root_appends_one_line(
    tmp_path: Path, offline: pytest.MonkeyPatch, policy: bool
) -> None:
    """Append one success record per CLI call, without the key or the state."""
    path = tmp_path / "audit.jsonl"
    offline.setenv("JEV_API__AUDIT_PATH", str(path))
    with serve(200, SUCCESS) as peer:
        offline.setenv("JEV_API__BASE_URL", peer.url)
        result = CliRunner().invoke(cli.app, arguments(tmp_path, policy, True))
    assert result.exit_code == 0, result.stderr
    assert len(peer.requests) == 1
    records = audit_lines(path, (CANARY, STATE))
    assert [record["outcome"] for record in records] == ["success"]
    assert records[0]["resolved_model"] == "jev-1.13.0"


@pytest.mark.parametrize("policy", [False, True], ids=["judge", "policy"])
def test_cli_unset_path_writes_nothing(
    tmp_path: Path, offline: pytest.MonkeyPatch, policy: bool
) -> None:
    """Install no sink and create no file when the setting is absent."""
    with serve(200, SUCCESS) as peer:
        offline.setenv("JEV_API__BASE_URL", peer.url)
        result = CliRunner().invoke(cli.app, arguments(tmp_path, policy, True))
    assert result.exit_code == 0, result.stderr
    assert len(peer.requests) == 1
    assert sorted(item.name for item in tmp_path.iterdir()) == (
        ["policy.json"] if policy else []
    )


@pytest.mark.parametrize("as_json", [False, True], ids=["text", "json"])
@pytest.mark.parametrize("policy", [False, True], ids=["judge", "policy"])
def test_cli_unopenable_path_exits_before_request(
    tmp_path: Path, offline: pytest.MonkeyPatch, policy: bool, as_json: bool
) -> None:
    """Exit 1 with a stderr diagnostic and no request for a missing directory."""
    path = tmp_path / "missing" / "audit.jsonl"
    offline.setenv("JEV_API__AUDIT_PATH", str(path))
    with serve(200, SUCCESS) as peer:
        offline.setenv("JEV_API__BASE_URL", peer.url)
        result = CliRunner().invoke(cli.app, arguments(tmp_path, policy, as_json))
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "JEV_API__AUDIT_PATH" in result.stderr
    assert CANARY not in result.stderr
    assert peer.requests == []
    assert not path.parent.exists()


def mcp_environment(url: str, path: Path) -> dict[str, str]:
    """Build the child environment with the synthetic key and the audit path.

    Args:
        url: Loopback peer URL.
        path: Audit file for the server.

    Returns:
        Process basics plus the three judgevet variables.
    """
    env = environment()
    env.update(
        JEV_API__KEY=CANARY, JEV_API__BASE_URL=url, JEV_API__AUDIT_PATH=str(path)
    )
    return env


async def mcp_session(env: dict[str, str], calls: int) -> int:
    """Initialize the installed server, call ask_noul, then close stdin.

    Args:
        env: Child environment.
        calls: Number of tool calls to make.

    Returns:
        The server's exit status after EOF.
    """
    process = await start(env)
    try:
        async with asyncio.timeout(15):
            info = {"name": "test", "version": "1"}
            params = {"protocolVersion": "2025-03-26", "capabilities": {}}
            await exchange(process, 1, "initialize", {**params, "clientInfo": info})
            for number in range(2, calls + 2):
                arguments = {"state": MCP_STATE, "instruction": "offline-question"}
                result = await exchange(
                    process,
                    number,
                    "tools/call",
                    {"name": "ask_noul", "arguments": arguments},
                )
                assert not result.get("isError", False)
            assert process.stdin is not None
            process.stdin.close()
            return await process.wait()
    finally:
        await stop(process)


@requires_mcp
@pytest.mark.e2e
def test_mcp_appends_one_line_per_call(tmp_path: Path) -> None:
    """Append one record per tool call from the installed stdio server."""
    path = tmp_path / "audit.jsonl"
    with serve(200, NOUL) as peer:
        code = asyncio.run(mcp_session(mcp_environment(peer.url, path), 2))
    assert code == 0
    assert len(peer.requests) == 2
    records = audit_lines(path, (CANARY, MCP_STATE))
    assert [record["outcome"] for record in records] == ["success", "success"]


async def mcp_eof(env: dict[str, str]) -> tuple[int | None, bytes, bytes]:
    """Start the installed server and send EOF at once.

    Args:
        env: Child environment.

    Returns:
        Exit status, stdout and stderr.
    """
    process = await start(env)
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(b""), 10)
        return process.returncode, stdout, stderr
    finally:
        await stop(process)


@requires_mcp
@pytest.mark.e2e
def test_mcp_unopenable_path_names_audit_stage(tmp_path: Path) -> None:
    """Report the audit sink stage and send no request for a missing directory."""
    path = tmp_path / "missing" / "audit.jsonl"
    with serve(200, NOUL) as peer:
        code, stdout, stderr = asyncio.run(mcp_eof(mcp_environment(peer.url, path)))
    assert code == 1
    assert stdout == b""
    assert stderr == b"judgevet-mcp: audit sink failed (FileNotFoundError)\n"
    assert peer.requests == []
