"""Translate a raw Jev response into a parsed answer or a JevError.

The functions take a status code, the raw body bytes and a status line, so
they need no HTTP client. An HTTP adapter passes `response.content` and the
string form of its status error.

The API error `detail` field is polymorphic:

- Array for validation errors (422): [{"type", "loc", "msg", "input"}]
- Object for auth errors (401/403): {"error_type", "message"}
- Object for an oversized request (400 observed): {"error_type"} equal to
  "max_tokens_exceeded", returned as JevMaxTokensExceededError
- Absent, malformed or unrecognised: falls back to the status line alone.

The `input` key in validation errors contains the caller's request payload
and is deliberately excluded from error messages to avoid leaking user data.

Examples:
    ```python
    from judgevet.adapters.outbound.response_translation import (
        parse_success,
        translate_status,
    )

    error = translate_status(302, b"", "Found")
    assert error is None

    body = (
        b'{"model": "jev-1.13.0", "answers": {}, '
        b'"usage": {"input_tokens": 10, "output_tokens": 0}}'
    )
    parsed = parse_success(200, body, {})
    assert parsed.model == "jev-1.13.0"
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: The adapters that call this module
    - [judgevet.domain.errors][]: Error types
    - [judgevet.domain.response_parser][]: Response parsing
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from judgevet.domain.choice_options import check_choice_options
from judgevet.domain.errors import (
    JevAuthError,
    JevError,
    JevMaxTokensExceededError,
    JevRateLimitError,
    JevRequestError,
    JevResponseError,
    JevServiceError,
)
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.response_parser import parse_system_one_response


def _extract_error_detail(detail: Any) -> str:
    """Extract a message only from recognized, well-formed diagnostic fields.

    The detail field can be:
    - An array of validation errors: [{"type", "loc", "msg", "input"}]
    - An object for auth errors: {"error_type", "message"}
    - Something else (treat as unknown)

    Never includes the "input" field as it contains caller content. Invalid
    field shapes discard the entire detail rather than stringify containers.

    Args:
        detail: The detail field from the error response body.

    Returns:
        A formatted error message, or empty string if detail is unknown.
    """
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if not isinstance(item, dict):
                return ""
            type_part = item.get("type", "unknown_type")
            location = item.get("loc", [])
            msg_part = item.get("msg", "no message")
            if (
                not isinstance(type_part, str)
                or not isinstance(msg_part, str)
                or not isinstance(location, list)
                or any(type(part) not in (str, int) for part in location)
            ):
                return ""
            loc_part = ".".join(str(part) for part in location)
            if loc_part:
                parts.append(f"{type_part} at {loc_part}: {msg_part}")
            else:
                parts.append(f"{type_part}: {msg_part}")
        return "; ".join(parts)
    if isinstance(detail, dict):
        error_type = detail.get("error_type", "")
        message = detail.get("message", "")
        if not isinstance(error_type, str) or not isinstance(message, str):
            return ""
        return ": ".join(part for part in (error_type, message) if part)
    return ""


def _read_error_detail(content: bytes, message: str) -> tuple[str, str]:
    """Read the error message and the wire error type from an error body.

    Jev bodies carry `detail`. When `detail` is absent, a non-empty string
    `error` field is appended instead, because Ollama's `/v1/systemone`
    returns errors as `{"error": "<string>"}`.
    Source: https://docs.ollama.com/api/systemone.

    Args:
        content: The raw error response body.
        message: The status line the message starts with.

    Returns:
        The message, with any extracted detail appended, and the string
        `detail.error_type`, or an empty string when the body carries none.
    """
    error_message = message
    error_type = ""
    try:
        body = json.loads(content)
    except ValueError:
        return error_message, error_type  # Body is not JSON
    detail = body.get("detail") if isinstance(body, dict) else None
    if detail is not None:
        extracted = _extract_error_detail(detail)
        if extracted:
            error_message = f"{message}; {extracted}"
    elif isinstance(body, dict) and isinstance(body.get("error"), str):
        if body["error"]:
            error_message = f"{message}; {body['error']}"
    if isinstance(detail, dict) and isinstance(detail.get("error_type"), str):
        error_type = detail["error_type"]
    return error_message, error_type


def parse_success(
    status_code: int, content: bytes, questions: Mapping[str, Any]
) -> SystemOneResponse:
    """Parse a successful JSON body and bind it to the request's questions.

    Args:
        status_code: The HTTP status code of the response.
        content: The raw response body.
        questions: The request's questions, which bound each Choice option.

    Returns:
        A parsed SystemOneResponse.

    Raises:
        JevResponseError: If the body is not valid JSON, does not parse, or
            names a Choice option outside its question's criteria.
    """
    try:
        raw = json.loads(content)
    except ValueError as exc:
        raise JevResponseError(
            f"Failed to parse response body: {exc}",
            status_code,
        ) from exc
    parsed = parse_system_one_response("system-one", raw)
    check_choice_options(questions, parsed.answers)
    return parsed


def translate_status(status_code: int, content: bytes, message: str) -> JevError | None:
    """Translate an error status and its body to a JevError subclass.

    A 4xx body whose `detail.error_type` is `max_tokens_exceeded` becomes
    JevMaxTokensExceededError. One live call returned that marker with 400.
    Source: https://github.com/Alberto-Codes/judgevet/issues/39#issuecomment-5825759575.

    Args:
        status_code: The HTTP status code of the response.
        content: The raw error response body.
        message: The status line the error message starts with.

    Returns:
        A JevError subclass instance for status codes 429, 401, 403, 4xx, or 5xx.
        None for unhandled status codes (e.g., 3xx).
    """
    error_message, error_type = _read_error_detail(content, message)

    if status_code == JevError.HTTP_STATUS_429_TOO_MANY_REQUESTS:
        return JevRateLimitError(error_message, status_code)
    elif status_code in (
        JevError.HTTP_STATUS_401_UNAUTHORIZED,
        JevError.HTTP_STATUS_403_FORBIDDEN,
    ):
        return JevAuthError(error_message, status_code)
    elif JevError.HTTP_STATUS_400_MIN <= status_code < JevError.HTTP_STATUS_500_MIN:
        if error_type == JevMaxTokensExceededError.WIRE_ERROR_TYPE:
            return JevMaxTokensExceededError(error_message, status_code)
        return JevRequestError(error_message, status_code)
    elif status_code >= JevError.HTTP_STATUS_500_MIN:
        return JevServiceError(error_message, status_code)
    # Unhandled status code (e.g., 3xx)
    return None
