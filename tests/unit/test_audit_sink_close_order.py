"""Close the settings-opened audit sink once, after the adapter, at each root.

``JEV_API__AUDIT_PATH`` opens one ``JsonlAuditSink`` before the adapter. The
CLI judge command, the CLI policy command and the hosted ``judgevet-mcp``
path each close the adapter first and the sink second. A recording wrapper on
both ``close`` methods captures the order, and a probe record proves the file
descriptor is closed rather than merely announced.
Source: https://github.com/Alberto-Codes/judgevet/issues/282#issuecomment-5934569159.
The synthetic answer shape follows https://docs.typesafe.ai/api.md.

Examples:
    ```python
    events: list[str] = []
    events.append("adapter")
    events.append("sink")
    assert events == ["adapter", "sink"]
    ```

See Also:
    - [judgevet.adapters.outbound.audit_jsonl][]: The sink under test.
    - [judgevet.adapters.inbound.cli][]: The judge command root.
    - [judgevet.adapters.inbound.cli_policy_run][]: The policy command root.
    - [judgevet.adapters.inbound.mcp_entrypoint][]: The hosted MCP root.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from judgevet.adapters.inbound import cli
from judgevet.adapters.inbound import mcp_entrypoint as entry
from judgevet.adapters.outbound.audit_jsonl import JsonlAuditSink
from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from judgevet.domain.audit import JudgmentRecord
from judgevet.ports import SystemOnePort
from tests.cli_process_support import CANARY, SUCCESS, serve
from tests.unit.test_cli_rate_limit import arguments

pytestmark = pytest.mark.unit
PROBE = JudgmentRecord(datetime.now(UTC), "success", "requested", {"claim": "noul"})


class CloseLog:
    """Record adapter and sink closes in call order.

    Attributes:
        events (list[str]): ``"adapter"`` or ``"sink"`` per close call.
        sinks (list[JsonlAuditSink]): Each sink whose close was called.
    """

    def __init__(self) -> None:
        """Start with no recorded closes."""
        self.events: list[str] = []
        self.sinks: list[JsonlAuditSink] = []

    def assert_closed_once_after_adapter(self) -> None:
        """Require one adapter close, then one sink close that took effect.

        Raises:
            AssertionError: If the order differs or the sink still accepts a
                record after its close.
        """
        assert self.events == ["adapter", "sink"]
        with pytest.raises(ValueError, match="audit sink is closed"):
            self.sinks[0].record(PROBE)


@pytest.fixture
def close_log(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> CloseLog:
    """Wrap both close methods and point the audit path into ``tmp_path``.

    Args:
        monkeypatch: Attribute and environment patcher.
        tmp_path: Isolated directory for the audit file.

    Returns:
        The log the wrappers append to.
    """
    log = CloseLog()
    sink_close = JsonlAuditSink.close
    adapter_close = HTTPSystemOneAdapter.close

    def record_sink(self: JsonlAuditSink) -> None:
        log.events.append("sink")
        log.sinks.append(self)
        sink_close(self)

    def record_adapter(self: HTTPSystemOneAdapter) -> None:
        log.events.append("adapter")
        adapter_close(self)

    monkeypatch.setattr(JsonlAuditSink, "close", record_sink)
    monkeypatch.setattr(HTTPSystemOneAdapter, "close", record_adapter)
    monkeypatch.setenv("JEV_API__KEY", CANARY)
    monkeypatch.setenv("JEV_API__AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    return log


@pytest.mark.parametrize("policy", [False, True], ids=["judge", "policy"])
def test_cli_root_closes_sink_after_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    close_log: CloseLog,
    policy: bool,
) -> None:
    """Close the adapter, then the sink, once each, from a CLI command."""
    with serve(200, SUCCESS) as peer:
        monkeypatch.setenv("JEV_API__BASE_URL", peer.url)
        result = CliRunner().invoke(cli.app, arguments(tmp_path, policy, True))
    assert result.exit_code == 0, result.stderr
    assert len(peer.requests) == 1
    close_log.assert_closed_once_after_adapter()


@pytest.mark.skipif(entry.stdio_server is None, reason="requires MCP extra")
def test_mcp_root_closes_sink_after_adapter(
    monkeypatch: pytest.MonkeyPatch, close_log: CloseLog
) -> None:
    """Close the adapter, then the sink, once each, from the hosted MCP path."""
    served: list[SystemOnePort] = []

    async def serve_nothing(port: SystemOnePort, *, model: str = "") -> None:
        served.append(port)

    monkeypatch.setattr(entry, "run_stdio", serve_nothing)
    assert entry.main() == 0
    assert [type(port) for port in served] == [HTTPSystemOneAdapter]
    close_log.assert_closed_once_after_adapter()
