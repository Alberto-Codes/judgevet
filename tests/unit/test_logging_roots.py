"""Require one configuration call per CLI or MCP composition.

Examples:
    ```bash
    uv run pytest tests/unit/test_logging_roots.py
    ```

See Also:
    - [judgevet.adapters.inbound.logs][]: Shared configuration.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from judgevet.adapters.inbound import cli, cli_policy_run, logs, mcp_entrypoint
from judgevet.ports import SystemOnePort
from tests.unit.test_cli_exit_lifecycle import QUESTIONS, RecordingPort

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("root", ["legacy", "policy", "mcp"])
def test_configure_once(
    root: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each owned-adapter composition configures once and retains cleanup."""
    if root == "mcp" and mcp_entrypoint.stdio_server is None:
        pytest.skip("requires MCP extra")
    calls: list[logs.LogSettings] = []
    port = RecordingPort(False)

    def configure(settings: logs.LogSettings) -> None:
        calls.append(settings)

    def factory(**kwargs: object) -> RecordingPort:
        return port

    async def run_stdio(adapter: SystemOnePort) -> None:
        assert adapter is port

    module = {"legacy": cli, "policy": cli_policy_run, "mcp": mcp_entrypoint}[root]
    monkeypatch.setattr(module, "configure", configure)
    monkeypatch.setenv("JEV_API__KEY", "private-key-canary")
    if root == "mcp":
        monkeypatch.setattr(mcp_entrypoint, "build_adapter", lambda settings: port)
        monkeypatch.setattr(mcp_entrypoint, "run_stdio", run_stdio)
        assert mcp_entrypoint.main() == 0
    else:
        monkeypatch.setattr(module, "HTTPSystemOneAdapter", factory)
        args = ["text", QUESTIONS, "--json"]
        if root == "policy":
            path = tmp_path / "policy.json"
            path.write_text('{"rules":[{"question":"q","pass":{"noul":{"min":0}}}]}')
            args.extend(["--policy", str(path)])
        assert CliRunner().invoke(cli.app, args).exit_code == 0
    assert len(calls) == 1
    assert port.closes == 1
