"""Unit tests for the transport-neutral response translation module.

These tests feed raw body bytes and a status line, so they need no HTTP client.
"""

import json

import pytest

from judgevet.adapters.outbound.response_translation import (
    parse_success,
    translate_status,
)
from judgevet.domain.answers import ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.errors import (
    JevAuthError,
    JevMaxTokensExceededError,
    JevRequestError,
    JevResponseError,
)

pytestmark = pytest.mark.unit

# Real 401 body from the live API on 2026-09-21; see tests/contract/fixtures.py.
_AUTH_BODY = {
    "detail": {
        "error_type": "authentication_error",
        "message": "Cannot authenticate with the server...",
    }
}

_MIXED_QUESTIONS = {
    "is_refund": {"type": "noul", "instructions": "Is this about a refund?"},
    "queue": {
        "type": "choice",
        "instructions": "Which team handles this?",
        "criteria": {"billing": "Money issues", "technical": "Bugs"},
    },
    "satisfaction": {
        "type": "score",
        "instructions": "Rate your satisfaction",
        "criteria": {1: "poor", 2: "fair", 3: "good", 4: "excellent"},
    },
}

_MIXED_BODY = {
    "model": "jev-1.13.0",
    "usage": {"input_tokens": 200, "output_tokens": 20},
    "answers": {
        "is_refund": {"type": "noul", "noul": 0.75},
        "queue": {
            "type": "choice",
            "choice": "billing",
            "confidence": 0.8,
            "probabilities": {"billing": 0.8, "technical": 0.2},
        },
        "satisfaction": {
            "type": "score",
            "score": 2.5,
            "confidence": 0.9,
            "legend": {"1": "poor", "2": "fair", "3": "good", "4": "excellent"},
            "probabilities": {"1": 0.1, "2": 0.2, "3": 0.3, "4": 0.4},
        },
    },
}


def test_401_body_becomes_auth_error_with_detail() -> None:
    """A 401 body maps to JevAuthError and appends its detail message."""
    error = translate_status(401, json.dumps(_AUTH_BODY).encode(), "Unauthorized")

    assert isinstance(error, JevAuthError)
    assert error.status_code == 401
    assert str(error) == (
        "Unauthorized; authentication_error: "
        "Cannot authenticate with the server... (status 401)"
    )


def test_400_max_tokens_exceeded_body_becomes_its_own_error() -> None:
    """A 400 body naming max_tokens_exceeded maps to JevMaxTokensExceededError."""
    body = json.dumps({"detail": {"error_type": "max_tokens_exceeded"}}).encode()

    error = translate_status(400, body, "Bad Request")

    assert isinstance(error, JevMaxTokensExceededError)
    assert error.status_code == 400
    assert str(error) == "Bad Request; max_tokens_exceeded (status 400)"


def test_400_without_marker_stays_a_request_error() -> None:
    """A 400 body without the marker maps to plain JevRequestError."""
    error = translate_status(400, b"not json", "Bad Request")

    assert type(error) is JevRequestError
    assert str(error) == "Bad Request (status 400)"


def test_3xx_status_is_left_untranslated() -> None:
    """A 3xx status returns None so the caller re-raises the transport error."""
    assert translate_status(302, b"", "Found") is None


def test_invalid_json_200_body_raises_response_error() -> None:
    """A 200 body that is not JSON raises JevResponseError with status 200."""
    with pytest.raises(JevResponseError) as exc_info:
        parse_success(200, b"<html>not json</html>", {})

    assert exc_info.value.status_code == 200
    assert str(exc_info.value).startswith("Failed to parse response body: ")


def test_mixed_200_body_parses_every_answer() -> None:
    """A 200 body with noul, choice and score answers parses each one."""
    parsed = parse_success(200, json.dumps(_MIXED_BODY).encode(), _MIXED_QUESTIONS)

    assert parsed.model == "jev-1.13.0"
    assert parsed.usage.input_tokens == 200
    assert parsed.answers["is_refund"] == NoulAnswer(noul=0.75)
    queue = parsed.answers["queue"]
    assert isinstance(queue, ChoiceAnswer)
    assert queue.choice == "billing"
    assert isinstance(parsed.answers["satisfaction"], ScoreAnswer)


def test_off_list_choice_raises_response_error() -> None:
    """A choice outside the request's criteria raises JevResponseError."""
    body = json.loads(json.dumps(_MIXED_BODY))
    body["answers"]["queue"]["choice"] = "sales"

    with pytest.raises(JevResponseError):
        parse_success(200, json.dumps(body).encode(), _MIXED_QUESTIONS)
