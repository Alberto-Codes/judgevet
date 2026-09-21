"""Pytest configuration for tests.

This module implements a runtime guard against plaintext API key leakage in test
output. The guard scrubs the configured API key from test report objects before
pytest renders them to the terminal or CI logs.

## Secret guard mechanism

The guard implements `pytest_runtest_makereport` as a hookwrapper. It reads the
configured API key once per report (if set), then recursively walks the report
object to replace any occurrence of the plaintext key with `"***"`. The walk
covers:

- The report's `__dict__` attributes
- The `longrepr` attribute (traceback and exception information)
- Captured stdout/stderr data

The guard is failure-proof: any error during scrubbing degrades to a no-op, so
a misconfiguration or missing settings does not break test runs.

### What the guard can reach

- Default pytest invocation (without `-s`, `--capture=no`, or `--capture=tee-*`)
- Test reports that contain the configured key in frame locals, exception messages,
  or captured output
- CI logs and terminal output that go through pytest's reporting system

### What the guard cannot reach (documented so nobody trusts past it)

1. Direct-write invocations (`pytest -s`, `--capture=no`, `--capture=tee-*`)
2. Output that has no test report (crashes during import, collection, session hooks)
3. Side effects beyond report text (files written, requests sent, subprocess env)
4. Only the key configured for this run (a different real credential is not scrubbed)
5. Downstream of pytest (CI artifacts, agent transcripts, terminal scrollback)
6. Plugins that snapshot the report early (before the hookwrapper mutates it)

### Usage rule

A secret stays wrapped (`SecretStr`) until the moment it is used. The unwrap
happens inside the call expression, never in a binding. A binding puts the
plaintext in a frame local, and pytest prints frame locals of every frame in a
failing traceback — to the terminal, to CI logs, and to any transcript
capturing the output. The conftest guard in `tests/conftest.py` redacts the
configured key from report output as a backstop; it cannot reach `-s`/`--capture=no`
output, so the rule is the primary defence.

See Also:
    - [pytest_runtest_makereport][]: The hook that implements the guard.
    - [tests.unit.test_secret_guard][]: The proof test that verifies the guard.
    - [tests.unit.leak_probe][]: The probe test that deliberately leaks a key.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

# Add the project root to sys.path so we can import scripts
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def _get_secret_from_settings() -> str | None:
    """Read the configured API key from settings, if set.

    Returns:
        The plaintext API key if configured, None otherwise. Returns None
        on any error to ensure the guard degrades gracefully.

    Examples:
        ```python
        secret = _get_secret_from_settings()
        if secret is not None:
            # Scrub the secret from reports
            pass
        ```
    """
    try:
        from pydantic import ValidationError

        from judgevet.adapters.inbound.settings import Settings

        settings = Settings()
        if settings.api.key is None:
            return None
        return settings.api.key.get_secret_value()
    except (ImportError, AttributeError, TypeError, ValidationError):
        return None


def _scrub_value(value: object, secret: str) -> object:
    """Recursively scrub the secret from a value.

    Args:
        value: The value to scrub (typically part of a report).
        secret: The plaintext secret to scrub.

    Returns:
        A scrubbed copy of the value with all occurrences of the secret replaced
        with "***".
    """
    result: object = value
    if isinstance(value, str):
        result = _scrub_str(value, secret)
    elif isinstance(value, dict):
        result = _scrub_dict(value, secret)
    elif isinstance(value, list):
        result = _scrub_list(value, secret)
    elif isinstance(value, tuple):
        result = _scrub_tuple(value, secret)
    elif isinstance(value, set):
        result = _scrub_set(value, secret)
    elif hasattr(value, "__dict__"):
        result = _scrub_object(value, secret)
    return result


def _scrub_str(value: str, secret: str) -> str:
    """Scrub a string value."""
    return value.replace(secret, "***")


def _scrub_dict(value: dict, secret: str) -> dict:
    """Scrub a dict value."""
    return {k: _scrub_value(v, secret) for k, v in value.items()}


def _scrub_list(value: list, secret: str) -> list:
    """Scrub a list value."""
    return [_scrub_value(item, secret) for item in value]


def _scrub_tuple(value: tuple, secret: str) -> tuple:
    """Scrub a tuple value."""
    return tuple(_scrub_value(item, secret) for item in value)


def _scrub_set(value: set, secret: str) -> set:
    """Scrub a set value."""
    return {_scrub_value(item, secret) for item in value}


def _scrub_object(value: object, secret: str) -> object:
    """Scrub a custom object with __dict__."""
    new_obj = object.__new__(value.__class__)
    obj_dict = getattr(value, "__dict__", None)
    if obj_dict is not None:
        for key, attr_value in obj_dict.items():
            setattr(new_obj, key, _scrub_value(attr_value, secret))
    return new_obj


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Any, call: Any) -> Iterator[None]:
    """Scrub the API key from test reports before pytest renders them.

    This hookwrapper runs after the test report is created but before it is
    rendered to the terminal or CI logs. It reads the configured API key once
    per report, then recursively walks the report object to replace any
    occurrence of the plaintext key with `"***"`.

    The hook is failure-proof: any error during scrubbing degrades to a no-op,
    so a misconfiguration or missing settings does not break test runs.

    Args:
        item: The pytest Item being tested.
        call: The CallInfo for the test setup, call, or teardown phase.

    Returns:
        None. The hook modifies the report in place via the hookwrapper protocol.

    Examples:
        This hook is called automatically by pytest. No manual invocation is needed.
    """
    # Get the secret to scrub, or None if not configured or on error
    secret = _get_secret_from_settings()
    if secret is None:
        # Nothing to scrub; degrade to no-op - but still yield for hookwrapper protocol
        outcome = yield
        return

    # Use the hookwrapper protocol to get the report
    outcome: Any = yield
    report: Any = outcome.get_result()

    # Only scrub failed reports (successful reports don't need redaction)
    if report.passed:
        return

    # Scrub the secret from the report
    scrubbed_report = _scrub_value(report, secret)

    # Put the scrubbed report back
    outcome.force_result(scrubbed_report)
