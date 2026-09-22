"""Execute file-input acceptance cases through the installed console.

Examples:
    ```python
    from tests.cli_file_support import invoke_files

    assert callable(invoke_files)
    ```

See Also:
    - [tests.cli_process_support][]: Observed local HTTP peer.
    - [judgevet.adapters.inbound.cli][]: Console under test.
"""

import asyncio
import os
import sys
from pathlib import Path

from tests.cli_process_support import CANARY


def invoke_files(url: str, args: list[str], stdin: bytes = b"") -> tuple[int, str, str]:
    """Run the installed console with isolated credentials and bounded input.

    Args:
        url: Observed local HTTP peer URL.
        args: Exact command arguments, including empty positional strings.
        stdin: Bytes supplied to standard input.

    Returns:
        Actual process status, stdout and stderr.

    Raises:
        TimeoutError: If the child exceeds ten seconds.
    """
    return asyncio.run(_invoke(url, args, stdin))


async def _invoke(url: str, args: list[str], stdin: bytes) -> tuple[int, str, str]:
    """Run one child and reap it on timeout or cancellation.

    Args:
        url: Local peer URL.
        args: Exact console arguments.
        stdin: Standard input bytes.

    Returns:
        Process status and decoded streams.

    Raises:
        TimeoutError: If the child exceeds ten seconds.
    """
    executable = Path(sys.executable).parent / "judgevet"
    assert executable.is_file()
    env = {name: os.environ[name] for name in ("PATH", "LANG") if name in os.environ}
    env.update({"JEV_API__KEY": CANARY, "JEV_API__BASE_URL": url})
    process = await asyncio.create_subprocess_exec(
        str(executable),
        *args,
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(stdin), timeout=10)
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
    assert process.returncode is not None
    return process.returncode, stdout.decode(), stderr.decode()
