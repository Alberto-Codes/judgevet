"""MCP output schemas for the structured content of each successful tool result.

Each schema is a closed JSON Schema 2020-12 object without a `$schema` key,
per the [2025-11-25 output schema rules](https://modelcontextprotocol.io/specification/2025-11-25/server/tools#output-schema).
The shapes follow the structured content that
[judgevet.adapters.inbound.mcp_handlers][] and
[judgevet.adapters.inbound.mcp_policy][] build. Error results carry no
structured content and fall outside these schemas. Source:
https://github.com/Alberto-Codes/judgevet/issues/211#issuecomment-5860666386.

Examples:
    ```python
    from judgevet.adapters.inbound.mcp_output_schemas import noul_output_schema

    assert noul_output_schema()["required"] == ["noul", "model", "usage"]
    ```

See Also:
    - [judgevet.adapters.inbound.mcp_schemas][]: Tool definitions that carry these schemas.
    - [judgevet.adapters.inbound.mcp_handlers][]: Ask tool results.
    - [judgevet.adapters.inbound.mcp_policy][]: Keyed policy result.
"""

from __future__ import annotations

from typing import Any

_PROBABILITY = {"type": "number", "minimum": 0, "maximum": 1}
_TOKENS = {"type": ["integer", "null"], "minimum": 0}


def _usage() -> dict[str, Any]:
    """Return the closed usage object schema.

    Returns:
        Schema for input and output token counts; an unknown count is null.
    """
    return {
        "type": "object",
        "description": "Token counts the service reported. An unknown count is null.",
        "required": ["input_tokens", "output_tokens"],
        "properties": {
            "input_tokens": {**_TOKENS, "description": "Input tokens used."},
            "output_tokens": {**_TOKENS, "description": "Output tokens used."},
        },
        "additionalProperties": False,
    }


def _model() -> dict[str, Any]:
    """Return the model field schema.

    Returns:
        Schema for the model identifier the service resolved.
    """
    return {"type": "string", "description": "Model identifier the service resolved."}


def _root(properties: dict[str, Any]) -> dict[str, Any]:
    """Return a closed object schema that requires every property.

    Args:
        properties: Field schemas, each with a description.

    Returns:
        Object schema with `additionalProperties` false.
    """
    return {
        "type": "object",
        "required": list(properties),
        "properties": properties,
        "additionalProperties": False,
    }


def _noul_fields() -> dict[str, Any]:
    """Return the Noul answer field schemas.

    Returns:
        Schema for the probability of true.
    """
    return {
        "noul": {
            **_PROBABILITY,
            "description": "Probability that the statement is true, from 0 to 1.",
        }
    }


def _choice_fields() -> dict[str, Any]:
    """Return the Choice answer field schemas.

    Returns:
        Schemas for the selected label, its confidence and label probabilities.
    """
    return {
        "choice": {"type": "string", "description": "Selected choice label."},
        "confidence": {**_PROBABILITY, "description": "Confidence in the choice."},
        "probabilities": {
            "type": "object",
            "description": "Probability of each choice, keyed by choice label.",
            "additionalProperties": _PROBABILITY,
        },
    }


def _score_fields() -> dict[str, Any]:
    """Return the Score answer field schemas.

    Returns:
        Schemas for the expected level, confidence, legend and level probabilities.
    """
    return {
        "score": {
            "type": "number",
            "description": "Expected level index, weighted by probability, against legend.",
        },
        "confidence": {**_PROBABILITY, "description": "Confidence in the score."},
        "legend": {
            "type": "object",
            "description": "Level label keyed by level index, as a string key.",
            "additionalProperties": {"type": "string"},
        },
        "probabilities": {
            "type": "object",
            "description": "Probability of each level, keyed by level index.",
            "additionalProperties": _PROBABILITY,
        },
    }


def noul_output_schema() -> dict[str, Any]:
    """Return the ask_noul output schema.

    Returns:
        Closed object schema for `noul`, `model` and `usage`.
    """
    return _root({**_noul_fields(), "model": _model(), "usage": _usage()})


def choice_output_schema() -> dict[str, Any]:
    """Return the ask_choice output schema.

    Returns:
        Closed object schema for `choice`, `confidence`, `probabilities`,
        `model` and `usage`.
    """
    return _root({**_choice_fields(), "model": _model(), "usage": _usage()})


def score_output_schema() -> dict[str, Any]:
    """Return the ask_score output schema.

    Returns:
        Closed object schema for `score`, `confidence`, `legend`,
        `probabilities`, `model` and `usage`.
    """
    return _root({**_score_fields(), "model": _model(), "usage": _usage()})


def _answer(kind: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Return one closed keyed answer branch.

    Args:
        kind: Answer type: noul, choice or score.
        fields: Answer field schemas.

    Returns:
        Object schema with `name`, `type` and the answer fields.
    """
    return _root(
        {
            "name": {"type": "string", "description": "Question key."},
            "type": {"const": kind, "description": "Answer type."},
            **fields,
        }
    )


def _policy() -> dict[str, Any]:
    """Return the closed policy verdict schema.

    Returns:
        Schema for the verdict and each rule outcome in order.
    """
    rule = _root(
        {
            "question": {"type": "string", "description": "Question key."},
            "pass": {"type": "boolean", "description": "Whether the rule passed."},
            "detail": {"type": "string", "description": "Readable comparisons."},
        }
    )
    verdict = _root(
        {
            "result": {"enum": ["pass", "fail"], "description": "Policy verdict."},
            "rules": {
                "type": "array",
                "description": "Rule outcomes in policy order.",
                "items": rule,
            },
        }
    )
    return {**verdict, "description": "Policy verdict with each rule outcome."}


def policy_output_schema() -> dict[str, Any]:
    """Return the evaluate_policy output schema.

    Returns:
        Closed object schema for `model`, `usage`, `answers` and `policy`.
    """
    answer = {
        "anyOf": [
            _answer("noul", _noul_fields()),
            _answer("choice", _choice_fields()),
            _answer("score", _score_fields()),
        ]
    }
    return _root(
        {
            "model": _model(),
            "usage": _usage(),
            "answers": {
                "type": "object",
                "description": "Answer for each question, keyed by question key.",
                "additionalProperties": answer,
            },
            "policy": _policy(),
        }
    )
