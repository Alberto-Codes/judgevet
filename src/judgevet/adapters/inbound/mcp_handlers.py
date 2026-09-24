"""MCP tool handlers and result formatting.

SDK fields follow the tagged
[SDK definitions](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/src/mcp-types/mcp_types/_types.py).
The factory supplies SDK types so importing this module needs no MCP runtime.

Examples:
    ```python
    from judgevet.adapters.inbound import mcp_handlers

    assert callable(mcp_handlers.handle_ask_noul)
    ```

See Also:
    - [judgevet.adapters.inbound.mcp][]: Server factory.
    - [judgevet.ports][]: Judgment port.
"""

from __future__ import annotations

from typing import Any

from judgevet.domain.answers import ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.response import SystemOneResponse
from judgevet.ports import SystemOnePort


async def handle_ask_noul(port: SystemOnePort, mcp_types: Any, params: Any) -> Any:
    """Handle the ask_noul tool.

    Args:
        port: Judgment port.
        mcp_types: SDK type constructors.
        params: Tool call parameters.

    Returns:
        CallToolResult with structured content containing noul, model, usage.

    Raises:
        ValueError: If arguments are missing or answer is invalid.
        TypeError: If the answer has the wrong type.
    """
    arguments = params.arguments or {}
    state = arguments.get("state")
    instruction = arguments.get("instruction")

    if state is None:
        raise ValueError("Missing required argument: state")
    if instruction is None:
        raise ValueError("Missing required argument: instruction")

    # Build the questions payload for the Jev API
    questions = {
        "noul_question": {
            "type": "noul",
            "instructions": instruction,
        }
    }

    # Call the port
    response = port.system_one(
        state=state,
        questions=questions,
        model="jev-latest",
    )

    # Extract the NoulAnswer
    noul_answer = response.answers.get("noul_question")
    if noul_answer is None:
        raise ValueError("No answer returned for noul_question")

    if not isinstance(noul_answer, NoulAnswer):
        raise TypeError(f"Expected NoulAnswer, got {type(noul_answer).__name__}")

    return _noul_result(mcp_types, noul_answer, response)


def _noul_result(
    mcp_types: Any, noul_answer: NoulAnswer, response: SystemOneResponse
) -> Any:
    """Format the existing noul answer as text and structured content.

    Args:
        mcp_types: SDK type constructors.
        noul_answer: Typed answer.
        response: Port response with model and usage.

    Returns:
        SDK tool result preserving both representations.
    """
    structured_content = {
        "noul": noul_answer.noul,
        "model": response.model,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }

    return mcp_types.CallToolResult(
        content=[
            mcp_types.TextContent(
                type="text",
                text=(
                    f"Probability of true: {noul_answer.noul:.4f}\n"
                    f"Model: {response.model}\n"
                    f"Usage: {response.usage.input_tokens} input tokens, "
                    f"{response.usage.output_tokens} output tokens"
                ),
            )
        ],
        structured_content=structured_content,
    )


async def handle_ask_choice(port: SystemOnePort, mcp_types: Any, params: Any) -> Any:
    """Handle the ask_choice tool.

    Args:
        port: Judgment port.
        mcp_types: SDK type constructors.
        params: Tool call parameters.

    Returns:
        CallToolResult with structured content containing choice, probabilities,
        confidence, model, usage.

    Raises:
        ValueError: If arguments are missing or answer is invalid.
        TypeError: If the answer has the wrong type.
    """
    arguments = params.arguments or {}
    state = arguments.get("state")
    instruction = arguments.get("instruction")
    criteria = arguments.get("criteria")

    if state is None:
        raise ValueError("Missing required argument: state")
    if instruction is None:
        raise ValueError("Missing required argument: instruction")

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

    # Call the port
    response = port.system_one(
        state=state,
        questions=questions,
        model="jev-latest",
    )

    # Extract the ChoiceAnswer
    choice_answer = response.answers.get("choice_question")
    if choice_answer is None:
        raise ValueError("No answer returned for choice_question")

    if not isinstance(choice_answer, ChoiceAnswer):
        raise TypeError(f"Expected ChoiceAnswer, got {type(choice_answer).__name__}")

    return _choice_result(mcp_types, choice_answer, response)


def _choice_result(
    mcp_types: Any, choice_answer: ChoiceAnswer, response: SystemOneResponse
) -> Any:
    """Format the existing choice answer as text and structured content.

    Args:
        mcp_types: SDK type constructors.
        choice_answer: Typed answer.
        response: Port response with model and usage.

    Returns:
        SDK tool result preserving both representations.
    """
    structured_content = {
        "choice": choice_answer.choice,
        "confidence": choice_answer.confidence,
        "probabilities": choice_answer.probabilities,
        "model": response.model,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }

    return mcp_types.CallToolResult(
        content=[
            mcp_types.TextContent(
                type="text",
                text=(
                    f"Choice: {choice_answer.choice}\n"
                    f"Confidence: {choice_answer.confidence:.4f}\n"
                    f"Model: {response.model}\n"
                    f"Usage: {response.usage.input_tokens} input tokens, "
                    f"{response.usage.output_tokens} output tokens"
                ),
            )
        ],
        structured_content=structured_content,
    )


async def handle_ask_score(port: SystemOnePort, mcp_types: Any, params: Any) -> Any:
    """Handle the ask_score tool.

    Args:
        port: Judgment port.
        mcp_types: SDK type constructors.
        params: Tool call parameters.

    Returns:
        CallToolResult with structured content containing score, legend,
        probabilities, confidence, model, usage.

    Raises:
        ValueError: If arguments are missing or answer is invalid.
        TypeError: If the answer has the wrong type.
    """
    arguments = params.arguments or {}
    state = arguments.get("state")
    instruction = arguments.get("instruction")
    criteria = arguments.get("criteria")

    if state is None:
        raise ValueError("Missing required argument: state")
    if instruction is None:
        raise ValueError("Missing required argument: instruction")

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

    # Call the port
    response = port.system_one(
        state=state,
        questions=questions,
        model="jev-latest",
    )

    # Extract the ScoreAnswer
    score_answer = response.answers.get("score_question")
    if score_answer is None:
        raise ValueError("No answer returned for score_question")

    if not isinstance(score_answer, ScoreAnswer):
        raise TypeError(f"Expected ScoreAnswer, got {type(score_answer).__name__}")

    return _score_result(mcp_types, score_answer, response)


def _score_result(
    mcp_types: Any, score_answer: ScoreAnswer, response: SystemOneResponse
) -> Any:
    """Format the existing score answer as text and structured content.

    Args:
        mcp_types: SDK type constructors.
        score_answer: Typed answer.
        response: Port response with model and usage.

    Returns:
        SDK tool result preserving both representations.
    """
    structured_content = {
        "score": score_answer.score,
        "legend": score_answer.legend,
        "probabilities": score_answer.probabilities,
        "confidence": score_answer.confidence,
        "model": response.model,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }

    return mcp_types.CallToolResult(
        content=[
            mcp_types.TextContent(
                type="text",
                text=(
                    f"Score: {score_answer.score:.4f}\n"
                    f"Confidence: {score_answer.confidence:.4f}\n"
                    f"Model: {response.model}\n"
                    f"Usage: {response.usage.input_tokens} input tokens, "
                    f"{response.usage.output_tokens} output tokens"
                ),
            )
        ],
        structured_content=structured_content,
    )
