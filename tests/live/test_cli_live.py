"""Exercise the installed CLI with one opt-in live mixed request.

Question and answer shapes follow https://docs.typesafe.ai/api.md.
The default suite deselects this test. Missing credentials skip before spawn.

Examples:
    ```bash
    direnv exec . uv run pytest -q -m live tests/live/test_cli_live.py
    ```

See Also:
    - [judgevet.domain.response][]: Typed answers and accessors.
    - [judgevet.adapters.inbound.settings][]: Wrapped credential configuration.
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest

from judgevet.adapters.inbound.settings import Settings
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.response_parser import parse_system_one_response

QUESTIONS = {
    "noul": {
        "type": "noul",
        "instructions": "Is this content clear?",
        "criteria": {"true": "Clear", "false": "Unclear"},
    },
    "choice": {
        "type": "choice",
        "instructions": "Is this content clear?",
        "criteria": {"yes": "Clear", "no": "Unclear"},
    },
    "score": {
        "type": "score",
        "instructions": "Rate clarity.",
        "criteria": ["Poor", "Fair", "Good", "Excellent"],
    },
}
STATE_ARG = "Test content."
EXPLICIT_MODEL = "jev-1.13.0"


def api_key_configured() -> bool:
    """Check credential presence without unwrapping the secret.

    Returns:
        Whether settings contain a configured key.

    Raises:
        ValueError: If settings are invalid.
    """
    return Settings().api.key is not None


def validate_cli_output(
    exit_code: int, stdout: bytes, stderr: bytes
) -> SystemOneResponse:
    """Validate CLI output and return parsed SystemOneResponse.

    Args:
        exit_code: Process exit code.
        stdout: Standard output bytes.
        stderr: Standard error bytes.

    Returns:
        Parsed SystemOneResponse object.

    Raises:
        AssertionError: If process or answer contract checks fail.
        ValueError: If JSON or domain values are invalid.
        TypeError: If domain field types are invalid.
        JevResponseError: If the answer shape cannot be parsed.
    """
    assert exit_code == 0 and stderr == b""
    raw = json.loads(stdout)
    assert isinstance(raw, dict)
    response = parse_system_one_response("installed-cli-live", raw)
    assert set(raw["answers"]) == {"noul", "choice", "score"}
    assert set(response.nouls.keys()) == {"noul"}
    assert set(response.choices.keys()) == {"choice"}
    assert set(response.scores.keys()) == {"score"}
    for key in raw["answers"]:
        assert raw["answers"][key]["name"] == key
    assert response.model == EXPLICIT_MODEL
    assert type(response.usage.input_tokens) is int and response.usage.input_tokens >= 0
    assert (
        type(response.usage.output_tokens) is int and response.usage.output_tokens >= 0
    )
    # Validate NoulAnswer
    noul_val = response.nouls["noul"].noul
    assert 0.0 <= noul_val <= 1.0
    # Validate ChoiceAnswer
    choice_ans = response.choices["choice"]
    assert choice_ans.choice in ("yes", "no")
    assert 0.0 <= choice_ans.confidence <= 1.0
    assert set(choice_ans.probabilities.keys()) == {"yes", "no"}
    for p in choice_ans.probabilities.values():
        assert 0.0 <= p <= 1.0
    # Validate ScoreAnswer
    score_ans = response.scores["score"]
    assert 0.0 <= score_ans.score <= 3.0
    assert 0.0 <= score_ans.confidence <= 1.0
    assert score_ans.legend == {0: "Poor", 1: "Fair", 2: "Good", 3: "Excellent"}
    assert set(score_ans.probabilities.keys()) == {0, 1, 2, 3}
    for p in score_ans.probabilities.values():
        assert 0.0 <= p <= 1.0
    return response


async def run_capped(
    argv: list[str], timeout_s: float = 45.0
) -> tuple[int, bytes, bytes]:
    """Execute a subprocess with capped execution time and guaranteed cleanup.

    Args:
        argv: Command-line arguments as a list of strings.
        timeout_s: Maximum execution time in seconds.

    Returns:
        A tuple of (exit_code, stdout, stderr).

    Raises:
        TimeoutError: If execution exceeds the specified timeout.
    """
    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()
    assert proc.returncode is not None
    return (proc.returncode, stdout, stderr)


@pytest.mark.live
def test_installed_cli_mixed_live() -> None:
    """Test the installed CLI with mixed questions using live API.

    This test requires a valid API key to be configured via JEV_API__KEY or
    TYPESAFE_API_KEY environment variables. If no key is configured, the test
    is skipped.

    The test validates the CLI's ability to process mixed question types (noul,
    choice, score) against the Jev API.

    Raises:
        pytest.skip: If no API key is configured.
        AssertionError: If the executable is missing or the output is invalid.
    """
    if not api_key_configured():
        pytest.skip("Missing JEV_API__KEY or TYPESAFE_API_KEY")

    console = Path(sys.executable).parent / "judgevet"
    assert console.is_file()

    result = asyncio.run(
        run_capped(
            [
                str(console),
                STATE_ARG,
                json.dumps(QUESTIONS),
                "--model",
                EXPLICIT_MODEL,
                "--json",
            ]
        )
    )

    validate_cli_output(*result)
