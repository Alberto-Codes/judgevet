"""Response parser for Jev System One API.

This module provides functions to parse raw API responses into typed domain objects.

Examples:
    ```python
    from judgevet.domain.response_parser import parse_system_one_response

    raw_response = {
        "model": "jev-latest",
        "answers": {
            "q1": {
                "type": "noul",
                "noul": 0.75,
            }
        },
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
        },
    }

    response = parse_system_one_response("request-id", raw_response)
    assert response.model == "jev-latest"
    ```

See Also:
    - [judgevet.domain.response][]: Response types
    - [judgevet.domain.answers][]: Answer types
    - [judgevet.domain.errors][]: Error types

Raises:
    JevResponseError: If the response cannot be parsed due to missing fields,
        unknown types, or wrong value kinds.
"""

from __future__ import annotations

from typing import Any

from judgevet.domain.answers import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.errors import JevResponseError
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage


def parse_system_one_response(
    request_id: str, raw: dict[str, Any]
) -> SystemOneResponse:
    """Parse a raw API response into a typed SystemOneResponse.

    Args:
        request_id: The request identifier (for error messages).
        raw: Raw API response dictionary.

    Returns:
        Parsed SystemOneResponse with typed answer objects.

    Raises:
        JevResponseError: If parsing fails due to missing fields, unknown types,
            or wrong value kinds. The error message includes the question ID
            and what was wrong.
    """
    model = _get_string(raw, "model", request_id)
    usage_raw = _get_dict(raw, "usage", request_id)
    input_tokens = _get_int(usage_raw, "input_tokens", request_id)
    output_tokens = _get_int(usage_raw, "output_tokens", request_id)
    usage = Usage(input_tokens=input_tokens, output_tokens=output_tokens)
    answers_raw = _get_dict(raw, "answers", request_id)
    answers: dict[str, Answer] = {}
    for answer_id, answer_raw in answers_raw.items():
        answers[answer_id] = _parse_answer(answer_id, answer_raw)
    return SystemOneResponse(model=model, usage=usage, answers=answers)


def _parse_answer(answer_id: str, raw: dict[str, Any]) -> Answer:
    """Parse a raw answer into the appropriate Answer type.

    Args:
        answer_id: The answer identifier (for error messages).
        raw: Raw answer dictionary.

    Returns:
        Parsed Answer object.

    Raises:
        JevResponseError: If the answer type is unknown or fields are missing/wrong.
    """
    answer_type = _get_string(raw, "type", answer_id)

    if answer_type == "noul":
        return _parse_noul_answer(answer_id, raw)
    elif answer_type == "choice":
        return _parse_choice_answer(answer_id, raw)
    elif answer_type == "score":
        return _parse_score_answer(answer_id, raw)
    else:
        raise JevResponseError(
            f"Unknown answer type '{answer_type}' for question '{answer_id}'",
            200,
        )


def _parse_noul_answer(answer_id: str, raw: dict[str, Any]) -> NoulAnswer:
    """Parse a raw noul answer.

    Args:
        answer_id: The answer identifier (for error messages).
        raw: Raw answer dictionary.

    Returns:
        Parsed NoulAnswer.

    Raises:
        JevResponseError: If the noul field is missing or has wrong type.
    """
    noul = _get_float(raw, "noul", answer_id)
    return NoulAnswer(noul=noul)


def _parse_choice_answer(answer_id: str, raw: dict[str, Any]) -> ChoiceAnswer:
    """Parse a raw choice answer.

    Args:
        answer_id: The answer identifier (for error messages).
        raw: Raw answer dictionary.

    Returns:
        Parsed ChoiceAnswer.

    Raises:
        JevResponseError: If required fields are missing or have wrong types.
    """
    choice = _get_string(raw, "choice", answer_id)
    confidence = _get_float(raw, "confidence", answer_id)
    probabilities = _get_dict(raw, "probabilities", answer_id)

    for prob_id, prob_value in probabilities.items():
        if not isinstance(prob_value, (int, float)):
            raise JevResponseError(
                f"Probability value for '{prob_id}' in question '{answer_id}' "
                f"is not a number, got {type(prob_value).__name__}",
                200,
            )

    str_probabilities = {str(k): float(v) for k, v in probabilities.items()}

    return ChoiceAnswer(
        choice=choice,
        confidence=confidence,
        probabilities=str_probabilities,
    )


def _parse_score_answer(answer_id: str, raw: dict[str, Any]) -> ScoreAnswer:
    """Parse a raw score answer.

    Args:
        answer_id: The answer identifier (for error messages).
        raw: Raw answer dictionary.

    Returns:
        Parsed ScoreAnswer.

    Raises:
        JevResponseError: If required fields are missing or have wrong types.
    """
    score = _get_float(raw, "score", answer_id)
    confidence = _get_float(raw, "confidence", answer_id)
    legend = _get_dict(raw, "legend", answer_id)
    probabilities = _get_dict(raw, "probabilities", answer_id)

    parsed_legend = _parse_int_key_dict(legend, answer_id, "legend")
    parsed_probabilities = _parse_int_key_dict(
        probabilities, answer_id, "probabilities"
    )

    return ScoreAnswer(
        score=score,
        confidence=confidence,
        legend=parsed_legend,
        probabilities=parsed_probabilities,
    )


def _parse_int_key_dict(
    raw_dict: dict[str, Any], answer_id: str, field_name: str
) -> dict[int, Any]:
    """Parse a dict with integer keys.

    Args:
        raw_dict: The raw dictionary.
        answer_id: The answer identifier (for error messages).
        field_name: The field name (for error messages).

    Returns:
        Dictionary with integer keys.

    Raises:
        JevResponseError: If keys cannot be parsed as integers.
    """
    parsed: dict[int, Any] = {}
    for key, value in raw_dict.items():
        try:
            int_key = int(key)
        except (ValueError, TypeError) as exc:
            raise JevResponseError(
                f"{field_name.capitalize()} key '{key}' in question '{answer_id}' "
                f"is not an integer, got {type(key).__name__}",
                200,
            ) from exc
        parsed[int_key] = value
    return parsed


def _get_string(raw: dict[str, Any], key: str, context: str) -> str:
    """Get a string value from a dictionary.

    Args:
        raw: The dictionary to read from.
        key: The key to look up.
        context: The context (for error messages).

    Returns:
        The string value.

    Raises:
        JevResponseError: If the key is missing or the value is not a string.
    """
    if key not in raw:
        raise JevResponseError(
            f"Missing required field '{key}' in {context}",
            200,
        )
    value = raw[key]
    if not isinstance(value, str):
        raise JevResponseError(
            f"Field '{key}' in {context} is not a string, got {type(value).__name__}",
            200,
        )
    return value


def _get_int(raw: dict[str, Any], key: str, context: str) -> int:
    """Get an int value from a dictionary.

    Args:
        raw: The dictionary to read from.
        key: The key to look up.
        context: The context (for error messages).

    Returns:
        The int value.

    Raises:
        JevResponseError: If the key is missing or the value is not an int.
    """
    if key not in raw:
        raise JevResponseError(
            f"Missing required field '{key}' in {context}",
            200,
        )
    value = raw[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise JevResponseError(
            f"Field '{key}' in {context} is not an integer, got {type(value).__name__}",
            200,
        )
    return value


def _get_float(raw: dict[str, Any], key: str, context: str) -> float:
    """Get a float value from a dictionary.

    Args:
        raw: The dictionary to read from.
        key: The key to look up.
        context: The context (for error messages).

    Returns:
        The float value.

    Raises:
        JevResponseError: If the key is missing or the value is not a number.
    """
    if key not in raw:
        raise JevResponseError(
            f"Missing required field '{key}' in {context}",
            200,
        )
    value = raw[key]
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise JevResponseError(
            f"Field '{key}' in {context} is not a number, got {type(value).__name__}",
            200,
        )
    return float(value)


def _get_dict(raw: dict[str, Any], key: str, context: str) -> dict[str, Any]:
    """Get a dict value from a dictionary.

    Args:
        raw: The dictionary to read from.
        key: The key to look up.
        context: The context (for error messages).

    Returns:
        The dict value.

    Raises:
        JevResponseError: If the key is missing or the value is not a dict.
    """
    if key not in raw:
        raise JevResponseError(
            f"Missing required field '{key}' in {context}",
            200,
        )
    value = raw[key]
    if not isinstance(value, dict):
        raise JevResponseError(
            f"Field '{key}' in {context} is not an object, got {type(value).__name__}",
            200,
        )
    return value
