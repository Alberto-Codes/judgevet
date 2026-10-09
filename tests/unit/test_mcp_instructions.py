"""Prove the default, an override and an addendum reach the initialize result.

Source: https://modelcontextprotocol.io/specification/2026-07-28/schema.
"""

import json
from contextlib import AbstractAsyncContextManager
from io import StringIO
from pathlib import Path

import anyio
import pytest

from judgevet.adapters.inbound import mcp_entrypoint as entry
from tests.unit.test_mcp_entrypoint import RecordingPort

try:
    from mcp.server.stdio import stdio_server as sdk_stdio
except ModuleNotFoundError:
    sdk_stdio = None

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(sdk_stdio is None, reason="requires MCP extra"),
]

FIXTURE = Path(__file__).parents[1] / "fixtures" / "mcp_contract.json"
ADDENDUM = "A local model answers. Jev calibration does not apply."
OVERRIDE = "Use these tools only for spam triage."
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
}


def initialize(
    monkeypatch: pytest.MonkeyPatch,
    addendum: str | None = None,
    instructions: str | None = None,
) -> dict:
    """Serve one initialize request over the real SDK stdio transport.

    Args:
        monkeypatch: Fixture that swaps in in-memory standard streams.
        addendum: Instructions addendum passed to the entry point, or None.
        instructions: Base instructions override passed to the entry point,
            or None for the default.

    Returns:
        The initialize result the server wrote.
    """
    output = StringIO()

    def streams() -> AbstractAsyncContextManager[tuple[object, object]]:
        assert sdk_stdio is not None
        stdin = StringIO(json.dumps(INITIALIZE) + "\n")
        return sdk_stdio(stdin=anyio.wrap_file(stdin), stdout=anyio.wrap_file(output))

    monkeypatch.setattr(entry, "stdio_server", streams)
    code = entry.main(
        port=RecordingPort(),
        model="local-model",
        instructions_addendum=addendum,
        instructions=instructions,
    )
    assert code == 0
    (line,) = output.getvalue().splitlines()
    return json.loads(line)["result"]


def test_default_sends_base_instructions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Require the pinned base text alone when the launcher adds nothing."""
    base = json.loads(FIXTURE.read_text())["instructions"]
    assert initialize(monkeypatch)["instructions"] == base


def test_addendum_follows_base_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Require the addendum after the unchanged base text and one blank line."""
    base = json.loads(FIXTURE.read_text())["instructions"]
    result = initialize(monkeypatch, ADDENDUM)
    assert result["instructions"] == f"{base}\n\n{ADDENDUM}"


def test_addendum_must_be_text() -> None:
    """Reject a non-string addendum, such as a decoded JSON number, before serving."""
    decoded = json.loads("7")
    with pytest.raises(TypeError, match="instructions_addendum must be a str"):
        entry.main(port=RecordingPort(), instructions_addendum=decoded)


def test_default_fits_the_client_budget() -> None:
    """Require the default under 1,500 characters, inside a 2,048 truncation."""
    base = json.loads(FIXTURE.read_text())["instructions"]
    assert len(base) < 1500
    assert base.index("Never use it") < base.index("ask_noul")


def test_override_replaces_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Require the override alone in place of the default text."""
    assert initialize(monkeypatch, instructions=OVERRIDE)["instructions"] == OVERRIDE


def test_addendum_follows_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Require the addendum after the override and one blank line."""
    result = initialize(monkeypatch, ADDENDUM, instructions=OVERRIDE)
    assert result["instructions"] == f"{OVERRIDE}\n\n{ADDENDUM}"


def test_override_must_be_text() -> None:
    """Reject a non-string override before serving."""
    with pytest.raises(TypeError, match="instructions must be a str"):
        entry.main(port=RecordingPort(), instructions=json.loads("7"))
