"""Check public help independently of developer docstrings and credentials.

Examples:
    Run the offline help checks::

        uv run pytest -q tests/unit/test_cli_help.py

See Also:
    - [judgevet.adapters.inbound.cli][]: CLI composition and help metadata.
"""

import asyncio
import inspect
import os
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from judgevet.adapters.inbound import cli

pytestmark = pytest.mark.unit


def _assert_help(output: str) -> None:
    """Validate the public usage text without depending on terminal decoration.

    Args:
        output: Captured CLI help text.
    """
    text = " ".join(output.split())
    for expected in (
        "Usage:",
        "state",
        "questions",
        "--model",
        "--api-key",
        "--json",
        "--help",
        "State to evaluate",
        "Questions as JSON string",
        "Model to use",
        "TypeSafe API key",
        "Output as JSON",
        "jev-latest",
    ):
        assert expected in text
    for internal in (
        "Args:",
        "Returns:",
        "Raises:",
        "Settings",
        "HTTPSystemOneAdapter",
        "run_cli",
        "finally",
    ):
        assert internal not in text


def test_public_help_does_not_construct_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Help prints without application settings, credentials or an adapter."""
    calls: list[bool] = []

    def forbidden_settings() -> None:
        calls.append(True)
        raise AssertionError("help constructed application settings")

    monkeypatch.setattr(cli, "Settings", forbidden_settings)
    answer = CliRunner().invoke(
        cli.app,
        ["--help"],
        color=False,
        terminal_width=120,
        env={"NO_COLOR": "1", "TERM": "dumb", "COLUMNS": "120"},
    )
    assert answer.exit_code == 0, answer.output
    assert not calls
    _assert_help(answer.output)


async def _installed_help() -> str:
    """Run the environment's installed console script without API keys.

    Returns:
        Its captured help output after a successful exit.
    """
    command = Path(sys.executable).parent / "judgevet"
    assert command.is_file()
    env = dict(os.environ)
    for name in ("JEV_API__KEY", "TYPESAFE_API_KEY"):
        env.pop(name, None)
    env.update({"NO_COLOR": "1", "TERM": "dumb", "COLUMNS": "120"})
    process = await asyncio.create_subprocess_exec(
        str(command),
        "--help",
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
    assert process.returncode == 0, stderr.decode()
    assert stderr == b""
    return stdout.decode()


def test_installed_command_help() -> None:
    """Exercise the actual console entry point with no credential."""
    _assert_help(asyncio.run(_installed_help()))


def test_developer_docstring_preserved() -> None:
    """Public help must not be repaired by deleting developer documentation."""
    doc = inspect.getdoc(cli.main)
    assert doc is not None
    for section in ("Args:", "Returns:", "Settings", "HTTPSystemOneAdapter", "finally"):
        assert section in doc
