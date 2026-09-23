"""Observe selected credentials at the HTTP boundary of every composition root."""

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from judgevet.adapters.inbound import cli, mcp_entrypoint
from judgevet.ports import SystemOnePort
from tests.cli_process_support import SUCCESS, serve
from tests.unit.test_cli_rate_limit import arguments
from tests.unit.test_credential_sources import command


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch) -> None:
    """Keep each invocation independent of inherited credential sources."""
    for name in os.environ:
        if name.startswith(("JEV_", "TYPESAFE_")):
            monkeypatch.delenv(name)


@pytest.mark.parametrize("root", ["cli", "policy", "mcp"])
@pytest.mark.parametrize("source", ["file", "command"])
def test_resolved_key_reaches_authorization(
    tmp_path: Path, monkeypatch, root, source
) -> None:
    """Resolve once before requests and send the actual selected key."""
    marker = tmp_path / "calls"
    if source == "file":
        path = tmp_path / "key"
        path.write_text("source-canary\n")
        monkeypatch.setenv("JEV_API__KEY_FILE", str(path))
    else:
        code = (
            "import pathlib,sys; p=pathlib.Path(sys.argv[1]); "
            "p.write_text(p.read_text()+'x' if p.exists() else 'x'); "
            "print('source-canary')"
        )
        monkeypatch.setenv("JEV_API__KEY", command(tmp_path, code, str(marker)))

    async def run_stdio(port: SystemOnePort) -> None:
        for _ in range(2):
            assert port.system_one("synthetic", {}, "jev-latest").model == "jev-1.13.0"

    with serve(200, SUCCESS) as peer:
        monkeypatch.setenv("JEV_API__BASE_URL", peer.url)
        if root == "mcp":
            monkeypatch.setattr(mcp_entrypoint, "run_stdio", run_stdio)
            assert mcp_entrypoint.main() == 0
        else:
            result = CliRunner().invoke(
                cli.app, arguments(tmp_path, root == "policy", True)
            )
            assert result.exit_code == 0, result.output
        assert peer.requests
        assert all(
            request["auth"] == "Bearer source-canary" for request in peer.requests
        )
    if source == "command":
        assert marker.read_text() == "x"


@pytest.mark.parametrize("root", ["cli", "policy"])
def test_command_failure_has_no_traceback(tmp_path: Path, monkeypatch, root) -> None:
    """Render source failure without provider output or a traceback."""
    source = command(
        tmp_path,
        "import sys; print('output-canary'); sys.stderr.write('error-canary'); sys.exit(7)",
    )
    monkeypatch.setenv("JEV_API__KEY", source)
    with serve(200, SUCCESS) as peer:
        monkeypatch.setenv("JEV_API__BASE_URL", peer.url)
        result = CliRunner().invoke(
            cli.app, arguments(tmp_path, root == "policy", True)
        )
    assert peer.requests == []
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert result.stdout == ""
    assert result.stderr
    for value in ("output-canary", "error-canary", source, "Traceback"):
        assert value not in result.stderr


@pytest.mark.parametrize("root", ["cli", "policy"])
def test_explicit_override_skips_resolution(tmp_path: Path, monkeypatch, root) -> None:
    """Do not evaluate lower-priority sources when a CLI key was explicit."""
    marker = tmp_path / "called"
    code = "import pathlib,sys; pathlib.Path(sys.argv[1]).touch(); print('wrong-key')"
    monkeypatch.setenv("JEV_API__KEY", command(tmp_path, code, str(marker)))
    monkeypatch.setenv("JEV_API__KEY_FILE", str(tmp_path / "missing"))
    with serve(200, SUCCESS) as peer:
        monkeypatch.setenv("JEV_API__BASE_URL", peer.url)
        args = [
            *arguments(tmp_path, root == "policy", True),
            "--api-key",
            "explicit-canary",
        ]
        result = CliRunner().invoke(cli.app, args)
        assert result.exit_code == 0, result.output
    assert peer.requests[0]["auth"] == "Bearer explicit-canary"
    assert not marker.exists()


def test_mcp_source_failure_is_private(tmp_path: Path, monkeypatch, capsys) -> None:
    """A provider failure must not become MCP stdout or a detailed startup error."""
    source = command(
        tmp_path,
        "import sys; print('output-canary'); sys.stderr.write('error-canary'); sys.exit(7)",
    )
    monkeypatch.setenv("JEV_API__KEY", source)
    with pytest.raises(SystemExit, match="startup or runtime failure") as caught:
        mcp_entrypoint.main()
    assert capsys.readouterr() == ("", "")
    assert "canary" not in str(caught.value)
