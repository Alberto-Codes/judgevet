"""MCP discovery schemas with explicit supported fields for keyed policy questions.

SDK fields follow the tagged
[SDK definitions](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/src/mcp-types/mcp_types/_types.py).
Each tool also declares an `output_schema` for its structured content.
The factory supplies SDK types so importing this module needs no MCP runtime.
The evaluate_policy `policy` argument carries a closed JSON Schema 2020-12 for
the policy grammar, from [policy_schema][judgevet.adapters.inbound.mcp_schemas.policy_schema].

Examples:
    ```python
    from judgevet.adapters.inbound import mcp_schemas

    assert callable(mcp_schemas.create_noul_tool)
    ```

See Also:
    - [judgevet.adapters.inbound.mcp][]: Server factory.
    - [judgevet.ports][]: Judgment port.
    - [judgevet.adapters.inbound.mcp_output_schemas][]: Output schemas.
"""

from __future__ import annotations

from typing import Any

from judgevet.adapters.inbound.mcp_output_schemas import (
    choice_output_schema,
    noul_output_schema,
    policy_output_schema,
    score_output_schema,
)


def create_noul_tool(mcp_types: Any) -> Any:
    """Create the ask_noul tool definition.

    Args:
        mcp_types: SDK type constructors.

    Returns:
        Tool definition for ask_noul; `state` accepts a string or an object.
        The output schema describes the structured content.
    """
    return mcp_types.Tool(
        name="ask_noul",
        description=(
            "Ask a yes/no question with a probability of true. "
            "Takes a state (text or JSON) and an instruction, "
            "returns the NoulAnswer."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "state": {
                    "type": ["string", "object"],
                    "description": (
                        "The content to evaluate. Can be plain text or a JSON object."
                    ),
                },
                "instruction": {
                    "type": "string",
                    "description": (
                        "The yes/no question or statement to evaluate about the state."
                    ),
                },
            },
            "required": ["state", "instruction"],
        },
        output_schema=noul_output_schema(),
    )


def create_choice_tool(mcp_types: Any) -> Any:
    """Create the ask_choice tool definition.

    Args:
        mcp_types: SDK type constructors.

    Returns:
        Tool definition for ask_choice; `state` accepts a string or an object.
        The output schema describes the structured content.
    """
    return mcp_types.Tool(
        name="ask_choice",
        description=(
            "Ask a multiple-choice question. Takes a state (text or "
            "JSON) and an instruction, returns the ChoiceAnswer with "
            "choice name, confidence, and probabilities."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "state": {
                    "type": ["string", "object"],
                    "description": (
                        "The content to evaluate. Can be plain text or a JSON object."
                    ),
                },
                "instruction": {
                    "type": "string",
                    "description": (
                        "The multiple-choice question or statement "
                        "to evaluate about the state."
                    ),
                },
                "criteria": {
                    "type": "object",
                    "description": (
                        "Mapping of choice names to descriptions. "
                        'If omitted, defaults to {"yes": "Yes", "no": "No"}.'
                    ),
                },
            },
            "required": ["state", "instruction"],
        },
        output_schema=choice_output_schema(),
    )


def create_score_tool(mcp_types: Any) -> Any:
    """Create the ask_score tool definition.

    Args:
        mcp_types: SDK type constructors.

    Returns:
        Tool definition for ask_score; `state` accepts a string or an object.
        The descriptions ask for criteria that fit the question and call the
        default a generic quality rubric. The output schema describes the
        structured content.
    """
    return mcp_types.Tool(
        name="ask_score",
        description=(
            "Ask a scored question. Takes a state (text or JSON) "
            "and an instruction, returns the ScoreAnswer with score, "
            "confidence, legend, and probabilities. Pass criteria that "
            "match the question, for example urgency levels ending in "
            '"Critical". The default ["Poor", "Fair", "Good", '
            '"Excellent"] is a generic quality rubric.'
        ),
        input_schema={
            "type": "object",
            "properties": {
                "state": {
                    "type": ["string", "object"],
                    "description": (
                        "The content to evaluate. Can be plain text or a JSON object."
                    ),
                },
                "instruction": {
                    "type": "string",
                    "description": (
                        "The scored question or statement to evaluate about the state."
                    ),
                },
                "criteria": {
                    "type": "array",
                    "description": (
                        "Ordered levels, lowest first, of the property "
                        "the question asks about. For urgency: "
                        '["Not urgent", "Low", "Medium", "High", '
                        '"Critical"]. If omitted, defaults to the generic '
                        'quality rubric ["Poor", "Fair", "Good", '
                        '"Excellent"].'
                    ),
                },
            },
            "required": ["state", "instruction"],
        },
        output_schema=score_output_schema(),
    )


def _bounds(names: tuple[str, ...], *, at_least_one: bool) -> dict[str, Any]:
    """Return a closed object schema of numeric bounds.

    Args:
        names: Allowed bound names.
        at_least_one: Whether at least one bound is required.

    Returns:
        JSON Schema for the bound object; order and ranges stay in code.
    """
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {name: {"type": "number"} for name in names},
        "additionalProperties": False,
    }
    if at_least_one:
        schema["minProperties"] = 1
    else:
        schema["required"] = list(names)
    return schema


def _predicate(kind: str, value: dict[str, Any], *, confidence: bool) -> dict[str, Any]:
    """Return one closed `pass` branch for a predicate kind.

    Args:
        kind: Predicate key: noul, choice or score.
        value: Schema for the predicate value.
        confidence: Whether the optional confidence floor is allowed.

    Returns:
        JSON Schema for a `pass` object of that kind.
    """
    properties = {kind: value}
    if confidence:
        properties["confidence"] = _bounds(("min",), at_least_one=False)
    return {
        "type": "object",
        "required": [kind],
        "properties": properties,
        "additionalProperties": False,
    }


def policy_schema() -> dict[str, Any]:
    """Return the JSON Schema 2020-12 for the evaluate_policy `policy` argument.

    The grammar is in docs/reference/policy.md "JSON grammar". Bound order,
    question-relative ranges, boolean bounds, unique question
    names and duplicate keys stay enforced in `judgevet.policy_json`. The
    `pass` branches use a nested `anyOf`, never a root combinator; see
    https://github.com/anthropics/claude-code/issues/95504.

    Returns:
        Closed object schema with a nonempty `rules` array.
    """
    range_bounds = _bounds(("min", "max"), at_least_one=True)
    rule = {
        "type": "object",
        "required": ["question", "pass"],
        "properties": {
            "question": {"type": "string", "minLength": 1},
            "pass": {
                "anyOf": [
                    _predicate("noul", range_bounds, confidence=False),
                    _predicate("choice", {"type": "string"}, confidence=True),
                    _predicate("score", range_bounds, confidence=True),
                ]
            },
        },
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "description": (
            "Acceptance rules over the keyed questions. Every rule must pass. "
            "Each rule names one question and one predicate that matches its "
            "type: noul takes min and max probability bounds, choice takes "
            "an exact label and an optional confidence min, score takes min "
            "and max level bounds and an optional confidence min. Example: "
            '{"rules":[{"question":"clear","pass":{"noul":{"min":0.8}}}]}'
        ),
        "required": ["rules"],
        "properties": {"rules": {"type": "array", "minItems": 1, "items": rule}},
        "additionalProperties": False,
    }


def create_policy_tool(mcp_types: Any) -> Any:
    """Create the keyed policy tool with optional embedded evidence JSON text.

    Args:
        mcp_types: SDK type constructors.

    Returns:
        Tool definition accepting state, questions and policy. The policy
        schema comes from `policy_schema`. The output schema describes the
        structured content.
    """
    return mcp_types.Tool(
        name="evaluate_policy",
        description=(
            "Evaluate keyed judgment questions against an acceptance policy. "
            "Questions map caller keys to noul, choice or score questions. "
            "A policy is a list of rules; each rule names a question and the "
            "answer it needs to pass. The result holds the answers, the "
            "policy result (pass or fail, with each rule's outcome and "
            "detail), the model and the usage. An unmet policy is not an "
            "error."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "state": {"type": ["string", "object", "array"]},
                "questions": {
                    "type": "object",
                    "minProperties": 1,
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "type": {"enum": ["noul", "choice", "score"]},
                            "instructions": {},
                            "criteria": {},
                        },
                        "required": ["type"],
                        "additionalProperties": False,
                    },
                },
                "policy": policy_schema(),
                "evidence": {
                    "type": "string",
                    "description": "Strict JSON image evidence with base64 attachments.",
                },
            },
            "required": ["state", "questions", "policy"],
            "additionalProperties": False,
        },
        output_schema=policy_output_schema(),
    )
