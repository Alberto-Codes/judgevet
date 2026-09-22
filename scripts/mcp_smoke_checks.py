"""Validation helpers for JSON-RPC2.0 frames and tool results.

Examples:
    ```python
    from scripts.mcp_smoke_checks import validate_server_info, validate_tool_call

    # Validate server info after initialization
    info = {"name": "judgevet-mcp", "version": "1.0.0"}
    validate_server_info(info, "1.0.0")

    # Validate a tool call response
    result = {
        "structuredContent": {
            "model": "m",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "noul": 0.5,
        },
        "isError": False,
    }
    validate_tool_call(result, "ask_noul")
    ```

See Also:
    - [scripts.mcp_smoke_transport][]: Entry point that owns subprocess and protocol.
"""

import math
from typing import Any, TypeGuard


def is_finite_number(value: object) -> TypeGuard[int | float]:
    """Check value is a finite numeric (int or float, excluding bool and NaN).

    Integers are finite without converting to float; math.isfinite applies to floats.
    This avoids OverflowError for huge out-of-range integers.

    Args:
        value: Untrusted numeric value.

    Returns:
        Whether the value is an integer or a finite float, excluding booleans.
    """
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return not (math.isnan(value) or math.isinf(value))
    return False


_TOLERANCE = 1e-6
_SCORE_MIN = 0
_SCORE_MAX = 3
_SCORE_KEYS = {"0", "1", "2", "3"}


def validate_server_info(server_info: dict[str, Any], expected_version: str) -> None:
    """Require serverInfo matches expected name and version.

    Args:
        server_info: Value from initialize response.
        expected_version: Version string from installed metadata.

    Raises:
        RuntimeError: Name or version do not match.
    """
    if server_info.get("name") != "judgevet-mcp":
        raise RuntimeError("mcp_smoke: serverInfo name mismatch")
    if server_info.get("version") != expected_version:
        raise RuntimeError("mcp_smoke: serverInfo version mismatch")


def validate_tool_list(tools: list[dict[str, Any]]) -> None:
    """Require exactly ask_noul, ask_choice, ask_score without duplicates.

    Args:
        tools: List from tools/list response.

    Raises:
        RuntimeError: Tools missing, duplicate, or extra names.
    """
    names = [t.get("name") for t in tools]
    expected = {"ask_noul", "ask_choice", "ask_score"}
    if set(names) != expected:
        raise RuntimeError("mcp_smoke: missing or extra tools")
    if len(names) != len(expected):
        raise RuntimeError("mcp_smoke: duplicate tool names")


def validate_usage(usage: dict[str, Any]) -> None:
    """Require input_tokens and output_tokens are positive ints, not bools.

    Args:
        usage: Usage dict from structuredContent.

    Raises:
        RuntimeError: Usage fields are malformed.
    """
    for key in ("input_tokens", "output_tokens"):
        val = usage.get(key)
        if not isinstance(val, int) or isinstance(val, bool) or val <= 0:
            raise RuntimeError("mcp_smoke: usage field malformed")


def _validate_probability(value: object) -> None:
    """Require a finite probability in the unit interval.

    Args:
        value: Untrusted probability value.

    Raises:
        ValueError: The value is not a finite probability.
    """
    if not is_finite_number(value) or not 0 <= value <= 1:
        raise ValueError("mcp_smoke: invalid probability")


def validate_distribution(
    probabilities: dict[str, Any], expected_keys: list[str]
) -> None:
    """Require probabilities match expected keys and sum to 1 within tolerance.

    Args:
        probabilities: Probabilities dict from structuredContent.
        expected_keys: List of expected key strings.

    Raises:
        RuntimeError: Keys or sum do not match.
        ValueError: A probability is not finite or outside the unit interval.
    """
    keys = set(probabilities.keys())
    expected = set(expected_keys)
    if keys != expected:
        raise RuntimeError("mcp_smoke: probability keys mismatch")

    # Validate each probability value
    for val in probabilities.values():
        _validate_probability(val)

    total = sum(probabilities.values())
    if abs(total - 1.0) > _TOLERANCE:
        raise RuntimeError("mcp_smoke: probability distribution invalid")


def validate_structured_content(content: object, tool_name: str) -> dict[str, Any]:
    """Validate structuredContent and return it.

    Args:
        content: structuredContent from tool result.
        tool_name: Name of the tool being called.

    Returns:
        The validated structuredContent.

    Raises:
        TypeError: Content fields have invalid types.
        ValueError: A probability is invalid.
        RuntimeError: Content values violate the tool contract.
    """
    if not isinstance(content, dict):
        raise TypeError("mcp_smoke: structuredContent not object")

    _validate_model(content.get("model"))
    usage = content.get("usage")
    if not isinstance(usage, dict):
        raise TypeError("mcp_smoke: usage must be object")
    validate_usage(usage)

    if tool_name == "ask_noul":
        _validate_noul(content.get("noul"))
    elif tool_name == "ask_choice":
        _validate_choice(content)
    elif tool_name == "ask_score":
        _validate_score(content)

    return content


def _validate_model(value: Any) -> None:
    """Require a nonempty model name.

    Args:
        value: Untrusted answer data.

    Raises:
        RuntimeError: The name is absent or invalid.
    """
    if not isinstance(value, str) or not value:
        raise RuntimeError("mcp_smoke: model must be non-empty string")


def _validate_noul(value: Any) -> None:
    """Require a finite Noul probability.

    Args:
        value: Untrusted answer data.

    Raises:
        RuntimeError: The probability is invalid.
    """
    if not is_finite_number(value) or value < 0 or value > 1:
        raise RuntimeError("mcp_smoke: noul must be finite in [0,1]")


def _validate_choice(content: dict[str, Any]) -> None:
    """Require a valid choice and probability distribution.

    Args:
        content: Untrusted answer data.

    Raises:
        TypeError: Choice or distribution has an invalid type.
        ValueError: A probability is invalid.
        RuntimeError: Choice, confidence or distribution is invalid.
    """
    choice = content.get("choice")
    if not isinstance(choice, str):
        raise TypeError("mcp_smoke: choice must be string")
    if choice not in ("yes", "no"):
        raise RuntimeError("mcp_smoke: choice must be yes or no")
    confidence = content.get("confidence")
    if not is_finite_number(confidence) or confidence < 0 or confidence > 1:
        raise RuntimeError("mcp_smoke: confidence must be finite in [0,1]")
    probabilities = content.get("probabilities")
    if not isinstance(probabilities, dict):
        raise TypeError("mcp_smoke: probabilities must be object")
    validate_distribution(probabilities, ["yes", "no"])


def _validate_score(content: dict[str, Any]) -> None:
    """Require a valid score, legend and distribution.

    Args:
        content: Untrusted answer data.

    Raises:
        TypeError: The distribution is not an object.
        ValueError: A probability is invalid.
        RuntimeError: Score, confidence, legend or distribution is invalid.
    """
    score = content.get("score")
    if not is_finite_number(score) or score < _SCORE_MIN or score > _SCORE_MAX:
        raise RuntimeError("mcp_smoke: score must be finite in [0,3]")
    confidence = content.get("confidence")
    if not is_finite_number(confidence) or confidence < 0 or confidence > 1:
        raise RuntimeError("mcp_smoke: confidence must be finite in [0,1]")
    legend = content.get("legend")
    expected_legend = {"0": "Poor", "1": "Fair", "2": "Good", "3": "Excellent"}
    if legend != expected_legend:
        raise RuntimeError("mcp_smoke: score legend mismatch")
    probabilities = content.get("probabilities")
    if not isinstance(probabilities, dict):
        raise TypeError("mcp_smoke: probabilities must be object")
    validate_distribution(probabilities, ["0", "1", "2", "3"])


def validate_tool_call(result: dict[str, Any], tool_name: str) -> None:
    """Validate a tools/call response for expected structure.

    Args:
        result: Full result from tool response.
        tool_name: Name of the tool being called.

    Raises:
        TypeError: Answer fields have invalid types.
        ValueError: A probability is invalid.
        RuntimeError: The answer reports failure or violates the tool contract.
    """
    is_error = result.get("isError", False)
    if is_error is not False:
        raise RuntimeError("mcp_smoke: tool returned isError")

    structured = result.get("structuredContent")
    validate_structured_content(structured, tool_name)
