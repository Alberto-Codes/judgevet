"""Verify release credential scope and execute the workflow identity guard.

Examples:
    ```bash
    uv run pytest tests/unit/test_release_credentials.py
    ```

See Also:
    - [tests.unit.test_logging_streams][]: Bounded isolated child execution.
"""

from pathlib import Path

import pytest

from tests.unit.test_logging_streams import run
from tests.unit.test_mcp_subprocess import environment

pytestmark = pytest.mark.unit
CANARY = "private-token-canary"
WORKFLOW = Path(".github/workflows/release-please.yml")


@pytest.mark.parametrize("job", ["release-please", "update-lockfile"])
def test_both_jobs_use_release_environment(job: str) -> None:
    """Every credential consumer binds to the protected destination environment."""
    block = (
        WORKFLOW.read_text()
        .split(f"  {job}:\n", 1)[1]
        .split("\n  update-lockfile:", 1)[0]
    )
    assert "\n    environment: release\n" in block


def test_no_token_fallback() -> None:
    """Both action credentials name only the PAT, so a missing secret cannot degrade."""
    source = WORKFLOW.read_text()
    assert "secrets.GITHUB_TOKEN" not in source
    assert source.count("token: ${{ secrets.RELEASE_PLEASE_TOKEN }}") == 2


def guard_script() -> str:
    """Extract the actual preflight script rather than duplicate its behavior.

    Returns:
        Shell program from the release job.
    """
    source = WORKFLOW.read_text()
    marker = "      - name: Verify release credential\n"
    assert marker in source, "release identity preflight is missing"
    step = source.split(marker, 1)[1].split("\n      - ", 1)[0]
    assert "GH_TOKEN: ${{ secrets.RELEASE_PLEASE_TOKEN }}" in step
    program = step.split("        run: |\n", 1)[1]
    return "\n".join(line[10:] for line in program.splitlines())


@pytest.mark.parametrize(
    "present,identity,status,success",
    [
        ("true", "Alberto-Codes", 0, True),
        ("false", "Alberto-Codes", 0, False),
        ("true", "github-actions[bot]", 0, False),
        ("true", "private-identity-canary", 0, False),
        ("true", "Alberto-Codes", 1, False),
    ],
)
def test_actual_identity_guard(
    tmp_path: Path,
    present: str,
    identity: str,
    status: int,
    success: bool,
) -> None:
    """Execute the real guard with deterministic API identities and token presence."""
    program = guard_script()
    gh = tmp_path / "gh"
    gh.write_text("""#!/bin/sh
[ "$*" = "api user --jq .login" ] || exit 4
printf x >> "$CALL_MARKER"
printf '%s\\n' "$MOCK_IDENTITY"
exit "$MOCK_STATUS"
""")
    gh.chmod(0o700)
    marker = tmp_path / "calls"
    env = environment()
    env.update(
        PATH=f"{tmp_path}:/usr/bin:/bin",
        HAS_PAT=present,
        GH_TOKEN=CANARY,
        MOCK_IDENTITY=identity,
        MOCK_STATUS=str(status),
        CALL_MARKER=str(marker),
    )
    result = run(["/bin/bash", "-e", "-o", "pipefail", "-c", program], env)
    assert (result.returncode == 0) is success
    assert marker.exists() is (present == "true")
    if success:
        assert "HAS_PAT=true" in result.stdout
        assert "PAT_IDENTITY=Alberto-Codes" in result.stdout
    for canary in (CANARY, "private-identity-canary"):
        assert canary not in result.stdout + result.stderr
