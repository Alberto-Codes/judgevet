"""Probe file to demonstrate and verify the secret guard mechanism.

This file is deliberately named `leak_probe.py` (not `test_*.py`) so pytest's
normal collection never runs it. It is a fixture for the proof test in
`test_secret_guard.py`.

The test inside creates a failing frame whose local variables contain the API
key, which is exactly the shape of the original incident where an unwrapped
`SecretStr` was bound to a local named `secret`.

Examples:
    This file is not meant to be run directly. Use the proof test:

    ```bash
    uv run pytest -q tests/unit/test_secret_guard.py
    ```

See Also:
    - [tests.unit.test_secret_guard][]: The proof test that uses this probe.
    - [tests.conftest][]: The conftest that contains the secret guard hook.
"""

from __future__ import annotations

import os


def _explode(api_key: str) -> None:
    """Raise an exception with the key in the frame local.

    Args:
        api_key: The API key to expose in the frame local.

    Raises:
        RuntimeError: Always raised with a fixed message.
    """
    raise RuntimeError("probe failure")


def test_probe_leak() -> None:
    """Deliberately leak the API key in a frame local.

    This test is designed to fail and expose the key in the traceback locals.
    The conftest guard should redact the key from the report output.

    The key comes from the environment variable `TYPESAFE_API_KEY`, which the
    proof test sets to a fake key before invoking pytest.

    Raises:
        RuntimeError: Always raised; the test's purpose is to observe the
            frame local rendering in the failure report.
    """
    api_key = os.environ["TYPESAFE_API_KEY"]
    _explode(api_key)
