"""Run trusted credential commands with bounded output and process cleanup.

Commands execute argv directly with no implicit shell. POSIX process groups
allow cleanup of descendants that retain the command's pipes.

Examples:
    ```python
    from judgevet.adapters.inbound.credential_command import MAX_KEY_BYTES

    assert MAX_KEY_BYTES == 4096
    ```

See Also:
    - [judgevet.adapters.inbound.credentials][]: Source selection and decoding.
    - [judgevet.adapters.inbound.settings][]: Command deadline configuration.
"""

import os
import selectors
import shlex
import signal
import subprocess
import time
from contextlib import suppress

from pydantic import SecretBytes, SecretStr

MAX_KEY_BYTES = 4096
COMMANDS_SUPPORTED = os.name == "posix"


class _CredentialProcess(subprocess.Popen[bytes]):
    """Hide command arguments from process representations in diagnostics.

    Attributes:
        pid (int): Child process and process-group identifier.
        stdout (BinaryIO): Bounded reader's pipe; configured during construction.

    Examples:
        ```python
        from judgevet.adapters.inbound.credential_command import MAX_KEY_BYTES

        assert MAX_KEY_BYTES == 4096
        ```
    """

    def __repr__(self) -> str:
        """Omit potentially sensitive argv values.

        Returns:
            A fixed process label without command text.
        """
        return "<credential process>"


def _spawn(command: SecretStr) -> _CredentialProcess:
    """Parse trusted configuration and start a separate process group.

    Args:
        command: Wrapped command beginning with an exclamation mark.

    Returns:
        Child with stdout piped and stdin/stderr discarded.

    Raises:
        ValueError: If tokenization or process creation fails.
    """
    try:
        arguments = [
            SecretStr(arg) for arg in shlex.split(command.get_secret_value()[1:])
        ]
        if arguments:
            return _CredentialProcess(
                [arg.get_secret_value() for arg in arguments],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
    except (OSError, ValueError):
        pass
    raise ValueError("API key command could not start")


def _wait(process: _CredentialProcess, timeout: float) -> None:
    """Require successful termination within the remaining deadline.

    Args:
        process: Owned child.
        timeout: Remaining execution time in seconds.

    Raises:
        ValueError: If the child fails or exceeds its execution deadline.
    """
    try:
        status = process.wait(timeout=max(timeout, 0))
    except subprocess.TimeoutExpired:
        pass
    else:
        if status != 0:
            raise ValueError("API key command failed")
        return
    raise ValueError("API key command timed out")


def _read_output(process: _CredentialProcess, timeout: float) -> SecretBytes:
    """Wait on stdout readiness while enforcing a deadline and byte limit.

    Args:
        process: Owned child with stdout piped.
        timeout: Execution budget after process creation.

    Returns:
        Wrapped stdout after successful command exit.

    Raises:
        ValueError: If output exceeds limits or the command fails.
    """
    deadline = time.monotonic() + timeout
    output = SecretBytes(b"")
    if process.stdout is None:
        raise ValueError("API key command has no output pipe")
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise ValueError("API key command timed out")
            chunk = SecretBytes(
                os.read(
                    process.stdout.fileno(),
                    MAX_KEY_BYTES + 1 - len(output.get_secret_value()),
                )
            )
            if not chunk.get_secret_value():
                break
            output = SecretBytes(output.get_secret_value() + chunk.get_secret_value())
            if len(output.get_secret_value()) > MAX_KEY_BYTES:
                raise ValueError("API key command output exceeds limit")
    _wait(process, deadline - time.monotonic())
    return output


def _cleanup(process: _CredentialProcess) -> None:
    """Terminate the owned process group, close stdout and reap the child.

    Args:
        process: Owned command process.

    Raises:
        ValueError: If the OS does not reap the killed child within one second.
    """
    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)
    if process.stdout is not None:
        process.stdout.close()
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass
    else:
        return
    raise ValueError("API key command cleanup failed")


def run_command(command: SecretStr, timeout: float) -> SecretBytes:
    """Resolve a trusted POSIX command without disclosing its streams or argv.

    Args:
        command: Wrapped command specification with the leading exclamation mark.
        timeout: Finite positive deadline supplied by validated settings.

    Returns:
        Wrapped bounded stdout.

    Raises:
        ValueError: If commands are unsupported or execution fails.
    """
    if not COMMANDS_SUPPORTED:
        raise ValueError("API key commands require POSIX")
    process = _spawn(command)
    try:
        return _read_output(process, timeout)
    except OSError:
        pass
    finally:
        _cleanup(process)
    raise ValueError("API key command failed")
