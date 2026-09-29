"""MCP tool handlers and result formatting.

SDK fields follow the tagged
[SDK definitions](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/src/mcp-types/mcp_types/_types.py).
The factory supplies SDK types so importing this module needs no MCP runtime.
Handlers pass the host-selected model to the asynchronous dispatcher and await
the synchronous provider outside the event loop. Invalid arguments return a
tool error result before any provider call. A declared service error, a
spend cap trip included, also returns a tool error result, as the MCP tools
specification classifies it. Source:
https://modelcontextprotocol.io/specification/2025-11-25/server/tools#error-handling.
The cap spans the server's lifetime, so its message says a restart is
required. A success result carries structured content and one text block
whose text is that structured content serialized as JSON, as the MCP tools
specification recommends. Source:
https://modelcontextprotocol.io/specification/2025-11-25/server/tools#structured-content.

Examples:
    ```python
    from judgevet.adapters.inbound import mcp_handlers

    assert callable(mcp_handlers.handle_ask_noul)
    ```

See Also:
    - [judgevet.adapters.inbound.mcp][]: Server factory.
    - [judgevet.ports][]: Judgment port.
    - [judgevet.adapters.inbound.mcp_arguments][]: Argument validation.
"""

from __future__ import annotations

import json
from typing import Any

from judgevet.adapters.inbound.mcp_arguments import ask_arguments, tool_error
from judgevet.adapters.inbound.mcp_dispatch import ProviderDispatch
from judgevet.domain.answers import ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.errors import JevBudgetExceededError, JudgevetError
from judgevet.domain.response import SystemOneResponse

RESTART = "restart the server to continue."


def service_error(mcp_types: Any, error: JudgevetError, *, media: bool = False) -> Any:
    """Return a declared service error as a tool error result.

    A tripped spend cap names the limit and says a restart is required,
    because the cap never resets. Other media errors keep only the type name.

    Args:
        mcp_types: SDK type constructors.
        error: Declared library error raised by the provider call.
        media: Whether the call carried embedded evidence.

    Returns:
        SDK tool result with `is_error` true.
    """
    if isinstance(error, JevBudgetExceededError):
        return tool_error(mcp_types, f"{error}; {RESTART}")
    if media:
        return tool_error(mcp_types, f"{type(error).__name__}: media evaluation failed")
    return tool_error(mcp_types, str(error))


def answer_result(
    mcp_types: Any, fields: dict[str, Any], response: SystemOneResponse
) -> Any:
    """Return answer fields with model and usage as JSON text and structured content.

    The text is `json.dumps` with default settings, the same serialization
    `evaluate_policy` uses. Its ASCII escapes keep the text transport-safe, and
    `json.loads` of the text equals the structured content.

    Args:
        mcp_types: SDK type constructors.
        fields: Answer fields that lead the structured content.
        response: Port response with model and usage.

    Returns:
        SDK tool result whose one text block is the serialized structured content.
    """
    structured_content = {
        **fields,
        "model": response.model,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }
    return mcp_types.CallToolResult(
        content=[
            mcp_types.TextContent(type="text", text=json.dumps(structured_content))
        ],
        structured_content=structured_content,
    )


async def handle_ask_noul(
    port: ProviderDispatch, mcp_types: Any, params: Any, *, model: str = "jev-latest"
) -> Any:
    """Handle the ask_noul tool.

    Args:
        port: Judgment port.
        mcp_types: SDK type constructors.
        params: Tool call parameters.
        model: Host-selected model.

    Returns:
        CallToolResult with structured content containing noul, model and
        usage, and the same content as JSON text. Invalid arguments and service
        errors return a tool error result.

    Raises:
        ValueError: If the answer is missing.
        TypeError: If the answer has the wrong type.
    """
    try:
        state, instruction, _ = ask_arguments(params.arguments, "noul")
    except ValueError as exc:
        return tool_error(mcp_types, str(exc))

    # Build the questions payload for the Jev API
    questions = {
        "noul_question": {
            "type": "noul",
            "instructions": instruction,
        }
    }

    try:
        response = await port.system_one(
            state=state,
            questions=questions,
            model=model,
        )
    except JudgevetError as exc:
        return service_error(mcp_types, exc)

    # Extract the NoulAnswer
    noul_answer = response.answers.get("noul_question")
    if noul_answer is None:
        raise ValueError("No answer returned for noul_question")

    if not isinstance(noul_answer, NoulAnswer):
        raise TypeError(f"Expected NoulAnswer, got {type(noul_answer).__name__}")

    return answer_result(mcp_types, {"noul": noul_answer.noul}, response)


async def handle_ask_choice(
    port: ProviderDispatch, mcp_types: Any, params: Any, *, model: str = "jev-latest"
) -> Any:
    """Handle the ask_choice tool.

    Args:
        port: Judgment port.
        mcp_types: SDK type constructors.
        params: Tool call parameters.
        model: Host-selected model.

    Returns:
        CallToolResult with structured content containing choice, probabilities,
        confidence, model and usage, and the same content as JSON text. Invalid
        arguments and service errors return a tool error result.

    Raises:
        ValueError: If the answer is missing.
        TypeError: If the answer has the wrong type.
    """
    try:
        state, instruction, criteria = ask_arguments(params.arguments, "choice")
    except ValueError as exc:
        return tool_error(mcp_types, str(exc))

    # Build the questions payload for the Jev API
    question_data: dict[str, Any] = {
        "type": "choice",
        "instructions": instruction,
    }
    if criteria is not None:
        question_data["criteria"] = criteria
    else:
        # Default to yes/no choices if criteria not provided
        question_data["criteria"] = {"yes": "Yes", "no": "No"}

    questions = {
        "choice_question": question_data,
    }

    try:
        response = await port.system_one(
            state=state,
            questions=questions,
            model=model,
        )
    except JudgevetError as exc:
        return service_error(mcp_types, exc)

    # Extract the ChoiceAnswer
    choice_answer = response.answers.get("choice_question")
    if choice_answer is None:
        raise ValueError("No answer returned for choice_question")

    if not isinstance(choice_answer, ChoiceAnswer):
        raise TypeError(f"Expected ChoiceAnswer, got {type(choice_answer).__name__}")

    fields = {
        "choice": choice_answer.choice,
        "confidence": choice_answer.confidence,
        "probabilities": choice_answer.probabilities,
    }
    return answer_result(mcp_types, fields, response)


async def handle_ask_score(
    port: ProviderDispatch, mcp_types: Any, params: Any, *, model: str = "jev-latest"
) -> Any:
    """Handle the ask_score tool.

    Args:
        port: Judgment port.
        mcp_types: SDK type constructors.
        params: Tool call parameters.
        model: Host-selected model.

    Returns:
        CallToolResult with structured content containing score, legend,
        probabilities, confidence, default_criteria, model and usage, and the
        same content as JSON text. `default_criteria` is true only when the
        call omitted `criteria` and the server applied the default rubric.
        Invalid arguments and service errors return a tool error result.

    Raises:
        ValueError: If the answer is missing.
        TypeError: If the answer has the wrong type.
    """
    try:
        state, instruction, criteria = ask_arguments(params.arguments, "score")
    except ValueError as exc:
        return tool_error(mcp_types, str(exc))

    # Build the questions payload for the Jev API
    question_data: dict[str, Any] = {
        "type": "score",
        "instructions": instruction,
    }
    if criteria is not None:
        question_data["criteria"] = criteria
    else:
        # Default to 4-level rubric if criteria not provided
        question_data["criteria"] = ["Poor", "Fair", "Good", "Excellent"]

    questions = {
        "score_question": question_data,
    }

    try:
        response = await port.system_one(
            state=state,
            questions=questions,
            model=model,
        )
    except JudgevetError as exc:
        return service_error(mcp_types, exc)

    # Extract the ScoreAnswer
    score_answer = response.answers.get("score_question")
    if score_answer is None:
        raise ValueError("No answer returned for score_question")

    if not isinstance(score_answer, ScoreAnswer):
        raise TypeError(f"Expected ScoreAnswer, got {type(score_answer).__name__}")

    fields = {
        "score": score_answer.score,
        "legend": score_answer.legend,
        "probabilities": score_answer.probabilities,
        "confidence": score_answer.confidence,
        "default_criteria": criteria is None,
    }
    return answer_result(mcp_types, fields, response)
