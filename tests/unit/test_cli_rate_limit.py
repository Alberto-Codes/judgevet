"""Exercise synthetic rate limits through both CLI composition paths.

HTTP status reference: https://docs.typesafe.ai/api.md. These fixtures are offline.

Examples:
    ```bash
    uv run pytest tests/unit/test_cli_rate_limit.py
    ```

See Also:
    - [judgevet.adapters.inbound.cli][]: Installed command.
    - [judgevet.adapters.inbound.cli_policy_run][]: Policy composition.
"""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from judgevet.adapters.inbound import cli, cli_policy_run
from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from tests.cli_file_support import invoke_files
from tests.cli_process_support import CANARY, QUESTIONS, serve

pytestmark = pytest.mark.unit
PAYLOAD = {"detail": {"error_type": "rate_limit", "message": "Slow down"}}


def arguments(tmp_path: Path, policy: bool, as_json: bool) -> list[str]:
    """Build valid inputs for either composition path.

    Args:
        tmp_path: Isolated policy directory.
        policy: Select explicit policy evaluation.
        as_json: Select machine diagnostics.

    Returns:
        Installed command arguments.
    """
    args = ["private-state-canary", json.dumps(QUESTIONS)]
    if policy:
        path = tmp_path / "policy.json"
        path.write_text('{"rules":[{"question":"noul","pass":{"noul":{"min":0}}}]}')
        args.extend(["--policy", str(path)])
    if as_json:
        args.append("--json")
    return args


def assert_error(code: int, stdout: str, stderr: str, as_json: bool) -> None:
    """Assert handled failure streams without caller data or traceback.

    Args:
        code: Actual exit status.
        stdout: Captured standard output.
        stderr: Captured standard error.
        as_json: Selected diagnostic mode.
    """
    assert code == 1
    assert stdout == ""
    assert stderr
    for secret in (CANARY, "private-state-canary", "Is this true?", "Traceback"):
        assert secret not in stderr
    if as_json:
        data = json.loads(stderr)
        assert set(data) == {"error"}
        message = data["error"]
    else:
        assert stderr.startswith("Error: ")
        message = stderr
    assert "rate_limit: Slow down" in message
    assert "(status 429)" in message


@pytest.mark.parametrize("policy", [False, True])
@pytest.mark.parametrize("as_json", [False, True])
def test_installed_rate_limit(tmp_path: Path, policy: bool, as_json: bool) -> None:
    """Real installed commands handle a synthetic HTTP rate limit."""
    args = arguments(tmp_path, policy, as_json)
    with serve(429, PAYLOAD) as peer:
        code, stdout, stderr = invoke_files(peer.url, args)
    assert len(peer.requests) == 1
    assert_error(code, stdout, stderr, as_json)


@pytest.mark.parametrize("policy", [False, True])
@pytest.mark.parametrize("as_json", [False, True])
def test_rate_limit_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, policy: bool, as_json: bool
) -> None:
    """Both roots close the real HTTP client exactly once after rate limiting."""
    closed: list[bool] = []
    original = HTTPSystemOneAdapter.close

    def close(adapter: HTTPSystemOneAdapter) -> None:
        original(adapter)
        closed.append(adapter._client.is_closed)

    monkeypatch.setattr(HTTPSystemOneAdapter, "close", close)
    monkeypatch.setenv("JEV_API__KEY", CANARY)
    assert cli_policy_run.HTTPSystemOneAdapter is HTTPSystemOneAdapter
    with serve(429, PAYLOAD) as peer:
        monkeypatch.setenv("JEV_API__BASE_URL", peer.url)
        result = CliRunner().invoke(cli.app, arguments(tmp_path, policy, as_json))
    assert closed == [True]
    assert len(peer.requests) == 1
    assert_error(result.exit_code, result.stdout, result.stderr, as_json)
    assert isinstance(result.exception, SystemExit)
