"""Live tests that provoke real error responses from the Jev System One API.

These tests call the live Jev API with intentionally invalid inputs to verify
that the adapter correctly maps HTTP error responses to domain error types.

Requirements:
    TYPESAFE_API_KEY must be set in the environment for the 422 test.
    The 401 test uses a deliberately wrong key so it runs anywhere.

Skip conditions:
    test_live_401_unauthorized: runs with any key (or none) because it uses a
        fixed invalid key. No skip.
    test_live_422_unprocessable: skips if TYPESAFE_API_KEY is absent because
        it must call the real API with a valid key but omits questions.

Note on 429 and 529:
    Rate limit (429) and overload (529) errors are not covered here because
    they cannot be provoked on demand. 429 would require hammering a paid
    service, and 529 is an internal overload condition nobody controls. Both
    remain covered by unit and contract tests against fixtures.

Usage rule:
    A secret stays wrapped (SecretStr) until the moment it is used. The unwrap
    happens inside the call expression, never in a binding. A binding puts the
    plaintext in a frame local, and pytest prints frame locals of every frame in a
    failing traceback — to the terminal, to CI logs, and to any transcript
    capturing the output. The conftest guard in `tests/conftest.py` redacts the
    configured key from report output as a backstop; it cannot reach `-s`/`--capture=no`
    output, so the rule is the primary defence. Note that the guard is necessary
    here because `--showlocals` is in `addopts`, so pytest prints every frame
    local, not just arguments.

Examples:
    ```bash
    # Run all tests except live
    pytest

    # Run live error tests only
    pytest -m live tests/live/test_error_live.py

    # Run with a specific key
    TYPESAFE_API_KEY="your-key" pytest -m live tests/live/test_error_live.py
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: HTTP adapter that maps errors
    - [judgevet.domain.errors][]: Domain error types
    - [judgevet.adapters.inbound.settings][]: Settings for configuration
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from judgevet.adapters.inbound.settings import Settings
from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from judgevet.domain.errors import JevAuthError, JevRequestError


def _call_adapter(adapter: HTTPSystemOneAdapter) -> None:
    """Call adapter.system_one with a valid question.

    Args:
        adapter: HTTPSystemOneAdapter instance.

    Raises:
        JevAuthError: If the API key is invalid.
    """
    adapter.system_one(
        state="Test content.",
        questions={
            "noul_q": {
                "type": "noul",
                "instructions": "Is 2+2 equal to 4?",
                "criteria": {"true": "Correct", "false": "Incorrect"},
            }
        },
        model="jev-latest",
    )


def _assert_401_error(exc: JevAuthError, invalid_key: str) -> None:
    """Assert that a 401 error meets all expectations.

    Args:
        exc: The caught JevAuthError.
        invalid_key: The key that was used (must not appear in output).

    Raises:
        AssertionError: If any assertion fails.
    """
    assert exc.status_code == 401
    assert exc.retryable is False

    exc_str = str(exc)
    assert "authentication_error" in exc_str
    assert invalid_key not in exc_str
    assert invalid_key not in repr(exc)


def _make_422_request(adapter: HTTPSystemOneAdapter, test_state: str) -> None:
    """Call adapter.system_one with empty questions to provoke 422.

    Args:
        adapter: HTTPSystemOneAdapter instance.
        test_state: State value to include in the request body.

    Raises:
        JevRequestError: Expected when the API returns 422.
    """
    # Passing an empty dict for questions provokes 422 because the API
    # requires at least one question.
    adapter.system_one(
        state=test_state,
        questions={},
        model="jev-latest",
    )


@pytest.mark.live
def test_live_401_unauthorized() -> None:
    """Test that a 401 response from the live API becomes JevAuthError.

    Provokes a 401 by sending a deliberately invalid API key to the live
    System One endpoint. The adapter must raise JevAuthError with
    retryable=False, and the error_type "authentication_error" must appear
    in the error string.

    This test does not require TYPESAFE_API_KEY: it uses a fixed invalid key
    ("judgevet-live-test-invalid-key"). A wrong key is rejected at authentication
    before any model inference, so it consumes no tokens and costs nothing.

    Raises:
        JevAuthError: Expected. Asserted on status_code, retryable, and
            error_type in the message.
        AssertionError: If any assertion fails.
    """
    invalid_key = "judgevet-live-test-invalid-key"

    adapter = HTTPSystemOneAdapter(
        api_key=invalid_key,
        base_url="https://api.typesafe.ai",
        default_model="jev-latest",
    )

    try:
        with pytest.raises(JevAuthError) as exc_info:
            _call_adapter(adapter)

        _assert_401_error(exc_info.value, invalid_key)
    finally:
        adapter.close()


@pytest.mark.live
def test_live_422_unprocessable() -> None:
    """Test that a 422 response from the live API becomes JevRequestError.

    Provokes a 422 by omitting the questions field from a valid request body.
    The adapter must raise JevRequestError with retryable=False, and the
    missing field name "questions" must appear in the error string.

    The adapter deliberately drops the "input" field from the 422 body to
    avoid echoing caller data back in error messages.

    Skip conditions:
        Skips if TYPESAFE_API_KEY is absent because this test must call the
        real API with a valid key.

    Raises:
        JevRequestError: Expected. Asserted on status_code, retryable, and
            the missing field name in the message.
        AssertionError: If any assertion fails.
    """
    settings = Settings()
    key = settings.api.key

    if key is None:
        pytest.skip("Missing TYPESAFE_API_KEY environment variable")

    # Use a distinctive marker for the state value so we can assert it does
    # not appear in the error string (proving the adapter drops the "input").
    test_state = "CANARY-STATE-7f3a"

    adapter = HTTPSystemOneAdapter(
        api_key=key.get_secret_value(),
        base_url="https://api.typesafe.ai",
        default_model="jev-latest",
    )

    try:
        with pytest.raises(JevRequestError) as exc_info:
            _make_422_request(adapter, test_state)

        _assert_422_error(exc_info.value, key, test_state)
    finally:
        adapter.close()


def _assert_422_error(
    exc: JevRequestError, api_key: SecretStr, test_state: str
) -> None:
    """Assert that a 422 error meets all expectations.

    Args:
        exc: The caught JevRequestError.
        api_key: The API key used, kept wrapped. Unwrapping it into a
            local would put the plaintext key in the frame, and pytest
            prints frame locals when an assertion fails.
        test_state: The state value used (must not appear in output).

    Raises:
        AssertionError: If any assertion fails.
    """
    assert exc.status_code == 422
    assert exc.retryable is False

    exc_str = str(exc)
    assert "questions" in exc_str
    assert api_key.get_secret_value() not in exc_str
    assert api_key.get_secret_value() not in repr(exc)
    assert test_state not in exc_str
    assert test_state not in repr(exc)
