"""Keyed policy evaluation with strict question fields before provider dispatch.

Source: https://github.com/Alberto-Codes/judgevet/issues/202#issuecomment-5851056470.
Service errors return tool error results through the shared ask handler
helper. A tripped spend cap says a restart is required on every path.

Examples:
    ```python
    from judgevet.adapters.inbound.mcp_policy import handle_evaluate_policy

    assert callable(handle_evaluate_policy)
    ```

See Also:
    - [judgevet.policy][]: Strict typed policy evaluation.
    - [judgevet.policy_json][]: Policy JSON grammar.
    - [judgevet.adapters.inbound.mcp_dispatch][]: Serialized provider calls.
    - [judgevet.adapters.inbound.mcp_arguments][]: Shared tool error results.
    - [judgevet.adapters.inbound.mcp_handlers][]: Shared service error results.
"""

from __future__ import annotations

import json
from typing import Any

from judgevet import JudgevetError
from judgevet.adapters.inbound.cli import build_response_data, parse_questions
from judgevet.adapters.inbound.mcp_arguments import tool_error
from judgevet.adapters.inbound.mcp_dispatch import ProviderDispatch
from judgevet.adapters.inbound.mcp_handlers import service_error
from judgevet.domain.questions import Question
from judgevet.policy import ValidatedPolicy, evaluate_policy
from judgevet.policy_json import parse_policy


def _parse(arguments: Any) -> tuple[Any, dict[str, Question], ValidatedPolicy]:
    """Validate required fields and optional evidence before provider dispatch.

    Args:
        arguments: Decoded MCP argument object.

    Returns:
        Original state, typed questions and validated policy.

    Raises:
        ValueError: If tool or question structure is invalid.
        TypeError: If state has an unsupported type.
        PolicyDefinitionError: If policy definitions are invalid.
    """
    if (
        not isinstance(arguments, dict)
        or not {"state", "questions", "policy"} <= set(arguments)
        or set(arguments) - {"state", "questions", "policy", "evidence"}
    ):
        raise ValueError("Expected exactly state, questions and policy")
    state = arguments["state"]
    if not isinstance(state, (str, dict, list)):
        raise TypeError("state must be a string, object or array")
    raw = arguments["questions"]
    if not isinstance(raw, dict) or not raw:
        raise ValueError("questions must be a non-empty object")
    for name, question in raw.items():
        if not isinstance(name, str) or not name or not isinstance(question, dict):
            raise ValueError("questions require non-empty names and object definitions")
        if set(question) - {"type", "instructions", "criteria"}:
            raise ValueError("Unsupported question field")
        kind = question.get("type")
        if kind not in ("noul", "choice", "score"):
            raise ValueError("Unknown question type")
        criteria = question.get("criteria")
        if kind == "choice" and (not isinstance(criteria, dict) or not criteria):
            raise ValueError("choice criteria must be a non-empty object")
        if kind == "score" and (not isinstance(criteria, list) or not criteria):
            raise ValueError("score criteria must be a non-empty array")
    questions = parse_questions(json.dumps(raw))
    return state, questions, parse_policy(json.dumps(arguments["policy"]), questions)


async def handle_evaluate_policy(
    port: ProviderDispatch, mcp_types: Any, params: Any, *, model: str
) -> Any:
    """Evaluate text or media with host-selected model and strict policy rules.

    Args:
        port: Existing serialized dispatcher.
        mcp_types: SDK type constructors.
        params: SDK tool parameters.
        model: Host-selected model.

    Returns:
        Matching text and structured envelopes, or a declared tool error
        from the shared tool error helper. A tripped spend cap says a restart
        is required, on the media path too.

    Raises:
        Exception: Unexpected implementation failures retain SDK handling.
    """
    try:
        state, questions, policy = _parse(params.arguments)
    except (ValueError, TypeError, JudgevetError) as exc:
        return tool_error(mcp_types, str(exc))
    try:
        if "evidence" in params.arguments:
            response = await port.system_one_media(
                state, questions, model, params.arguments["evidence"]
            )
        else:
            response = await port.system_one(state, questions, model)
        report = evaluate_policy(policy, response.answers)
    except JudgevetError as exc:
        return service_error(mcp_types, exc, media="evidence" in params.arguments)
    data = build_response_data(response)
    data["policy"] = {
        "result": "pass" if report.passed else "fail",
        "rules": [
            {"question": rule.question, "pass": rule.passed, "detail": rule.detail}
            for rule in report.rules
        ],
    }
    text = json.dumps(data)
    return mcp_types.CallToolResult(
        content=[mcp_types.TextContent(type="text", text=text)],
        structured_content=json.loads(text),
        is_error=False,
    )
