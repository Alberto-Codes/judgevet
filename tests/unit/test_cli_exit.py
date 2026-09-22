"""Prove failure status at the installed console boundary.

Examples:
    ```python
    import sys
    from pathlib import Path

    command = Path(sys.executable).parent / "judgevet"
    assert command.name == "judgevet"
    ```

See Also:
    - [judgevet.adapters.inbound.cli][]: Command composition and port helper.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


async def _invalid_command(
    state: str, questions: str, as_json: bool
) -> tuple[int, str, str]:
    """Run the installed command with malformed input and a dummy credential.

    Args:
        state: State argument passed to the command.
        questions: Question JSON argument passed to the command.
        as_json: Whether to request JSON output.

    Returns:
        Actual process exit code, stdout and stderr.
    """
    command = Path(sys.executable).parent / "judgevet"
    assert command.is_file()
    env = {name: os.environ[name] for name in ("PATH", "LANG") if name in os.environ}
    env.update(
        {
            "JEV_API__KEY": "offline-cli-canary",
            "JEV_API__BASE_URL": "http://127.0.0.1:9",
        }
    )
    args = [str(command), state, questions]
    if as_json:
        args.append("--json")
    process = await asyncio.create_subprocess_exec(
        *args,
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
    assert process.returncode is not None
    return process.returncode, stdout.decode(), stderr.decode()


@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize("state,questions", [("test", "{"), ("{", "{}")])
def test_installed_parse_error_is_process_failure(
    state: str, questions: str, as_json: bool
) -> None:
    """A local parse error must not look like success to a shell script.

    Args:
        state: State containing either valid text or malformed JSON.
        questions: Valid or malformed question JSON.
        as_json: Whether to require the machine-readable diagnostic.
    """
    code, stdout, stderr = asyncio.run(_invalid_command(state, questions, as_json))
    assert stdout == ""
    assert "offline-cli-canary" not in stderr
    message = json.loads(stderr)["error"] if as_json else stderr
    assert "Expecting property name" in message
    assert code == 1
