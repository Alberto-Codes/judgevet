"""Tool error results and ask argument validation for the MCP tools.

The MCP tools specification classifies input validation errors as tool
execution errors: a `CallToolResult` with `isError` true, not a protocol
error. Source: https://modelcontextprotocol.io/specification/2025-11-25/server/tools#error-handling.
SDK field names follow the tagged
[SDK definitions](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/src/mcp-types/mcp_types/_types.py).
The caller supplies SDK types, so importing this module needs no MCP runtime.
`AskKind` names the three ask question types, so a misspelt kind fails the
type check.

Examples:
    ```python
    from judgevet.adapters.inbound.mcp_arguments import ask_arguments

    state, instruction, criteria = ask_arguments(
        {"state": "text", "instruction": "Is it true?"}, "noul"
    )
    assert (state, instruction, criteria) == ("text", "Is it true?", None)
    ```

See Also:
    - [judgevet.adapters.inbound.mcp_handlers][]: Ask tool handlers.
    - [judgevet.adapters.inbound.mcp_policy][]: Policy tool handler.
"""

from __future__ import annotations

from typing import Any, Literal

AskKind = Literal["noul", "choice", "score"]


def tool_error(mcp_types: Any, message: str) -> Any:
    """Return a tool error result without answers or a policy verdict.

    Args:
        mcp_types: SDK type constructors.
        message: Declared diagnostic.

    Returns:
        SDK tool result with `is_error` true and the message as text.
    """
    return mcp_types.CallToolResult(
        content=[mcp_types.TextContent(type="text", text=message)], is_error=True
    )


def ask_arguments(arguments: Any, kind: AskKind) -> tuple[Any, Any, Any]:
    """Validate ask tool arguments before any provider call.

    Choice criteria must be a non-empty object and score criteria a
    non-empty array when given. Noul ignores criteria.

    Args:
        arguments: Decoded MCP argument object, or None.
        kind: Question type, one of the `AskKind` literals `noul`,
            `choice` or `score`.

    Returns:
        State, instruction and criteria; criteria is None when absent.

    Raises:
        ValueError: If a required argument is missing or criteria has the
            wrong shape.
    """
    arguments = arguments or {}
    for name in ("state", "instruction"):
        if arguments.get(name) is None:
            raise ValueError(f"Missing required argument: {name}")
    criteria = arguments.get("criteria")
    if criteria is not None:
        if kind == "choice" and (not isinstance(criteria, dict) or not criteria):
            raise ValueError("choice criteria must be a non-empty object")
        if kind == "score" and (not isinstance(criteria, list) or not criteria):
            raise ValueError("score criteria must be a non-empty array")
    return arguments["state"], arguments["instruction"], criteria
