"""Verify spend cap settings through actual CLI and MCP consumption paths.

Source: https://github.com/Alberto-Codes/judgevet/issues/56#issuecomment-5873077469.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from judgevet.adapters.inbound import cli
from judgevet.adapters.inbound.mcp_entrypoint import build_adapter
from judgevet.adapters.inbound.settings import Settings
from judgevet.domain.errors import JevBudgetExceededError, JevRateLimitError
from tests.cli_process_support import CANARY, serve
from tests.unit.test_cli_rate_limit import PAYLOAD, arguments


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Set a canary key and remove every retry delay.

    Args:
        monkeypatch: Environment patcher.

    Returns:
        The same patcher, for further variables.
    """
    monkeypatch.setenv("JEV_API__KEY", CANARY)
    monkeypatch.setenv("JEV_API__RETRY_BASE_DELAY", "0")
    monkeypatch.setenv("JEV_API__RETRY_MAX_DELAY", "0")
    return monkeypatch


@pytest.mark.parametrize("root", ["cli", "policy", "mcp"])
def test_cap_stops_real_requests(
    tmp_path: Path, offline: pytest.MonkeyPatch, root: str
) -> None:
    """Stop each composition root at the attempt cap below its retry limit."""
    offline.setenv("JEV_API__MAX_ATTEMPTS", "3")
    offline.setenv("JEV_API__SPEND_MAX_ATTEMPTS", "2")
    with serve(429, PAYLOAD) as peer:
        offline.setenv("JEV_API__BASE_URL", peer.url)
        if root == "mcp":
            with (
                build_adapter(Settings()) as adapter,
                pytest.raises(JevBudgetExceededError, match="attempts spent 2 of 2"),
            ):
                adapter.system_one("synthetic", {})
        else:
            result = CliRunner().invoke(
                cli.app, arguments(tmp_path, root == "policy", False)
            )
            assert result.exit_code == 1
            assert result.stderr == "Error: Spend cap reached: attempts spent 2 of 2\n"
        assert len(peer.requests) == 2


def test_mcp_cap_spans_server_lifetime(offline: pytest.MonkeyPatch) -> None:
    """Refuse a later call on the same MCP adapter without a request."""
    offline.setenv("JEV_API__MAX_ATTEMPTS", "1")
    offline.setenv("JEV_API__SPEND_MAX_ATTEMPTS", "1")
    with serve(429, PAYLOAD) as peer:
        offline.setenv("JEV_API__BASE_URL", peer.url)
        with build_adapter(Settings()) as adapter:
            with pytest.raises(JevRateLimitError):
                adapter.system_one("synthetic", {})
            with pytest.raises(JevBudgetExceededError, match="attempts spent 1 of 1"):
                adapter.system_one("synthetic", {})
        assert len(peer.requests) == 1


def test_spend_cap_property(monkeypatch: pytest.MonkeyPatch) -> None:
    """Build no cap when both limits are unset and a new cap otherwise."""
    assert Settings().api.spend_cap is None
    monkeypatch.setenv("JEV_API__SPEND_MAX_ATTEMPTS", "4")
    monkeypatch.setenv("JEV_API__SPEND_MAX_INPUT_TOKENS", "900")
    api = Settings().api
    cap = api.spend_cap
    assert cap is not None
    assert (cap.max_attempts, cap.max_input_tokens) == (4, 900)
    assert api.spend_cap is not cap


@pytest.mark.parametrize("field", ["SPEND_MAX_ATTEMPTS", "SPEND_MAX_INPUT_TOKENS"])
@pytest.mark.parametrize("value", ["0", "-1", "abc", "true"])
def test_bad_value_fails_settings(
    monkeypatch: pytest.MonkeyPatch, field: str, value: str
) -> None:
    """Reject a non-positive, non-numeric or boolean limit at Settings()."""
    monkeypatch.setenv(f"JEV_API__{field}", value)
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("field", ["spend_max_attempts", "spend_max_input_tokens"])
def test_settings_reject_boolean_spend_limit(field: str) -> None:
    """Do not interpret an explicit Python boolean as a spend limit."""
    with pytest.raises(ValidationError):
        Settings(api={field: True})
