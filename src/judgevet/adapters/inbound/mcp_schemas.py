"""Unchanged MCP discovery schemas.

SDK fields follow the tagged
[SDK definitions](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/src/mcp-types/mcp_types/_types.py).
The factory supplies SDK types so importing this module needs no MCP runtime.

Examples:
    ```python
    from judgevet.adapters.inbound import mcp_schemas

    assert callable(mcp_schemas.create_noul_tool)
    ```

See Also:
    - [judgevet.adapters.inbound.mcp][]: Server factory.
    - [judgevet.ports][]: Judgment port.
"""

from __future__ import annotations

from typing import Any


def create_noul_tool(mcp_types: Any) -> Any:
    """Create the ask_noul tool definition.

    Args:
        mcp_types: SDK type constructors.

    Returns:
        Tool definition for ask_noul.
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
                        "The content to evaluate. Can be plain text "
                        "or a JSON object/array."
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
    )


def create_choice_tool(mcp_types: Any) -> Any:
    """Create the ask_choice tool definition.

    Args:
        mcp_types: SDK type constructors.

    Returns:
        Tool definition for ask_choice.
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
                        "The content to evaluate. Can be plain text "
                        "or a JSON object/array."
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
    )


def create_score_tool(mcp_types: Any) -> Any:
    """Create the ask_score tool definition.

    Args:
        mcp_types: SDK type constructors.

    Returns:
        Tool definition for ask_score.
    """
    return mcp_types.Tool(
        name="ask_score",
        description=(
            "Ask a scored question. Takes a state (text or JSON) "
            "and an instruction, returns the ScoreAnswer with score, "
            "confidence, legend, and probabilities."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "state": {
                    "type": ["string", "object"],
                    "description": (
                        "The content to evaluate. Can be plain text "
                        "or a JSON object/array."
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
                        "Ordered list of rubric level descriptions. "
                        'If omitted, defaults to ["Poor", "Fair", '
                        '"Good", "Excellent"].'
                    ),
                },
            },
            "required": ["state", "instruction"],
        },
    )
