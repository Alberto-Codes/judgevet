"""Proof test for the secret guard mechanism.

This test verifies that the conftest guard correctly scrubs the configured API
key from test report output.

The guard is proven end-to-end via a real pytest subprocess, real terminal
rendering, and a fake key:

1. Run a probe test in a subprocess with `TYPESAFE_API_KEY` set to a distinctive
   fake key.
2. Assert the probe actually failed (returncode != 0).
3. Assert the plaintext fake key does not appear in stdout/stderr.
4. Assert the mask token `"***"` is present in the output, proving scrubbing
   occurred rather than output suppression.

The probe deliberately creates a failing frame whose local variables contain
the API key, which is exactly the shape of the original incident where an
unwrapped `SecretStr` was bound to a local named `secret`.

Examples:
    ```bash
    uv run pytest -q tests/unit/test_secret_guard.py
    ```

See Also:
    - [tests.conftest][]: The conftest that contains the secret guard hook.
    - [tests.unit.leak_probe][]: The probe test that deliberately leaks a key.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

MASK = "***"  # Mask token used by the conftest guard (not a secret, just a marker)

# A sentinel value used by the leak probe test to verify the guard.
# This is not a real key; the token "PROBE" makes it clear this is a test artifact.
PROBE_SENTINEL = "fakekey_0123456789abcdef"

# Path to the leak probe (relative to repo root)
LEAK_PROBE_PATH = Path("tests/unit/leak_probe.py")


def test_secret_guard_redacts_fake_key() -> None:
    """Verify the secret guard redacts the configured API key from report output.

    Runs a subprocess with the leak probe test and the fake key in the environment.
    The probe creates a failing frame whose local contains the key, which the
    guard should scrub.

    Asserts:
        1. The probe test failed (returncode != 0).
        2. The plaintext fake key does not appear in stdout/stderr.
        3. The mask token "***" appears in the output, proving scrubbing occurred.
    """
    env = os.environ.copy()
    env["TYPESAFE_API_KEY"] = PROBE_SENTINEL

    repo_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(LEAK_PROBE_PATH),
            "-p",
            "no:cacheprovider",
            "-q",
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    # 1. Assert the probe actually failed
    assert result.returncode != 0, "Probe test did not fail; key might not be in output"

    # 2. Assert the plaintext fake key does not appear
    output = result.stdout + result.stderr
    assert PROBE_SENTINEL not in output, "Fake key found in output; guard did not scrub"

    # 3. Assert the mask token is present, proving scrubbing occurred
    assert MASK in output, "Mask token not found; guard did not run or scrub"
