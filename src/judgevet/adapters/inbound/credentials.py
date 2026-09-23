"""Select credential sources without putting resolved secrets in diagnostics.

Settings construction performs no IO. Composition roots call the resolver once
and unwrap the result only in the adapter constructor expression.

Examples:
    ```python
    from pydantic import SecretStr
    from judgevet.adapters.inbound.credentials import resolve_key

    assert resolve_key(SecretStr("literal"), None, 5.0) == SecretStr("literal")
    ```

See Also:
    - [judgevet.adapters.inbound.settings][]: Credential source configuration.
    - [judgevet.adapters.inbound.credential_command][]: Bounded command execution.
"""

import os
import stat

from pydantic import SecretBytes, SecretStr

from judgevet.adapters.inbound.credential_command import MAX_KEY_BYTES, run_command

_MIN_TOKEN_CHAR = 33
_MAX_TOKEN_CHAR = 126


def _decode(data: SecretBytes) -> SecretStr:
    """Validate source output before constructing an HTTP authorization header.

    Args:
        data: Wrapped bytes from a bounded source read.

    Returns:
        Wrapped printable ASCII token with trailing CR/LF removed.

    Raises:
        ValueError: If the source is empty, oversized or contains invalid characters.
    """
    if len(data.get_secret_value()) > MAX_KEY_BYTES:
        raise ValueError("API key source output exceeds limit")
    try:
        value = SecretStr(data.get_secret_value().decode("utf-8").rstrip("\r\n"))
    except UnicodeError:
        value = None
    if not value or any(
        not _MIN_TOKEN_CHAR <= ord(char) <= _MAX_TOKEN_CHAR
        for char in value.get_secret_value()
    ):
        raise ValueError("Invalid API key source output")
    return value


def _read_file(path: str) -> SecretStr:
    """Read at most one bounded token from a regular credential file.

    Args:
        path: Caller-selected file, including mounted-secret symlinks.

    Returns:
        Wrapped validated file content.

    Raises:
        ValueError: If the file cannot be read or contains invalid output.
    """
    data = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            if stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                data = SecretBytes(stream.read(MAX_KEY_BYTES + 1))
    except (OSError, ValueError):
        pass
    if data is None:
        raise ValueError("Cannot read API key file")
    return _decode(data)


def resolve_key(
    key: SecretStr | None,
    key_file: str | None,
    timeout: float,
    explicit: str | None = None,
) -> SecretStr | None:
    """Resolve explicit, literal, file and command sources in that order.

    Args:
        key: Wrapped literal key or exclamation-prefixed command.
        key_file: Optional mounted credential file.
        timeout: Validated command deadline in seconds.
        explicit: Optional literal override; None leaves settings in control.

    Returns:
        Wrapped credential, or None when no source is configured.

    Raises:
        ValueError: If the selected file or command source fails.
    """
    if explicit is not None:
        return SecretStr(explicit)
    if key and not key.get_secret_value().startswith("!"):
        return key
    if key_file is not None:
        return _read_file(key_file)
    if key:
        return _decode(run_command(key, timeout))
    return None
