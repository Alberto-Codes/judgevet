"""The evaluate_policy `policy` schema accepts documented policies and rejects bad shapes.

Source: https://github.com/Alberto-Codes/judgevet/issues/214#issuecomment-5860663681
and https://json-schema.org/draft/2020-12/json-schema-core.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.testing import FakeSystemOnePort

pytestmark = pytest.mark.unit
ROOT = Path(__file__).parents[2]
COMBINATORS = ("anyOf", "oneOf", "allOf", "not", "if")


def _policy_tool() -> dict[str, Any]:
    """Return the serialized evaluate_policy definition from tools/list.

    Returns:
        The evaluate_policy tool definition.
    """
    server = create_mcp_server(FakeSystemOnePort(seed=1))

    async def exercise() -> Any:
        """Call the registered tools/list handler.

        Returns:
            The SDK list tools result.
        """
        return await server._request_handlers["tools/list"].handler(None, None)

    listed = asyncio.run(exercise()).model_dump(mode="json", by_alias=True)
    return next(tool for tool in listed["tools"] if tool["name"] == "evaluate_policy")


def _errors(policy: object) -> list[str]:
    """Validate a policy against the declared schema under JSON Schema 2020-12.

    Args:
        policy: Candidate `policy` argument.

    Returns:
        Validation error messages; empty when the policy is valid.
    """
    schema = _policy_tool()["inputSchema"]["properties"]["policy"]
    Draft202012Validator.check_schema(schema)
    return [error.message for error in Draft202012Validator(schema).iter_errors(policy)]


def _documented_policies() -> list[dict[str, Any]]:
    """Extract every JSON object that starts with `{"rules"` from docs and README.

    Returns:
        Each decoded policy example, in file order.
    """
    decoder = json.JSONDecoder()
    found: list[dict[str, Any]] = []
    paths = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        start = text.find('{"rules"')
        while start != -1:
            found.append(decoder.raw_decode(text, start)[0])
            start = text.find('{"rules"', start + 1)
    return found


def test_docs_contain_policy_examples() -> None:
    """The extraction finds the documented examples, so the next test is not vacuous."""
    assert len(_documented_policies()) >= 3


@pytest.mark.parametrize("policy", _documented_policies())
def test_documented_policies_validate(policy: dict[str, Any]) -> None:
    """Every documented policy example satisfies the declared schema."""
    assert _errors(policy) == []


@pytest.mark.parametrize(
    "policy",
    [
        {"rules": [{"question": "n", "pass": {"noul": {"max": 0.2}}}]},
        {"rules": [{"question": "n", "pass": {"noul": {"min": 0, "max": 1}}}]},
        {"rules": [{"question": "c", "pass": {"choice": "yes"}}]},
        {
            "rules": [
                {"question": "c", "pass": {"choice": "yes", "confidence": {"min": 0.5}}}
            ]
        },
        {"rules": [{"question": "s", "pass": {"score": {"min": 1}}}]},
        {
            "rules": [
                {
                    "question": "s",
                    "pass": {"score": {"max": 2}, "confidence": {"min": 0.9}},
                }
            ]
        },
    ],
)
def test_grammar_forms_validate(policy: dict[str, Any]) -> None:
    """Each predicate form in the policy grammar satisfies the schema."""
    assert _errors(policy) == []


@pytest.mark.parametrize(
    "policy",
    [
        {"rules": [{"question": "q1", "min": 0.5}]},
        {"rules": [{"question": "q1", "pass": {"noul": {"min": 0.5}}, "min": 0.5}]},
        {"rules": [{"question": "", "pass": {"noul": {"min": 0.5}}}]},
        {"rules": []},
        {},
        {"rules": [], "extra": 1},
        {"rules": [{"question": "q1"}]},
        {"rules": [{"question": 1, "pass": {"noul": {"min": 0.5}}}]},
        {
            "rules": [
                {
                    "question": "q1",
                    "pass": {"noul": {"min": 0.5}, "score": {"min": 1}},
                }
            ]
        },
        {"rules": [{"question": "q1", "pass": {"noul": {"min": 0.5, "unknown": 1}}}]},
        {"rules": [{"question": "q1", "pass": {"noul": {}}}]},
        {"rules": [{"question": "q1", "pass": {}}]},
        {
            "rules": [
                {
                    "question": "q1",
                    "pass": {"noul": {"min": 0.5}, "confidence": {"min": 0.1}},
                }
            ]
        },
        {"rules": [{"question": "q1", "pass": {"choice": 1}}]},
        {
            "rules": [
                {"question": "q1", "pass": {"choice": "y", "confidence": {"max": 1}}}
            ]
        },
        {"rules": [{"question": "q1", "pass": {"score": {"min": "1"}}}]},
    ],
)
def test_invalid_shapes_rejected(policy: dict[str, Any]) -> None:
    """The schema rejects shapes the policy grammar forbids."""
    assert _errors(policy) != []


def test_no_root_combinator_and_policy_described() -> None:
    """The input schema root stays a plain object; `policy` carries an example."""
    tool = _policy_tool()
    schema = tool["inputSchema"]
    assert schema["type"] == "object"
    assert not set(COMBINATORS) & set(schema)
    description = schema["properties"]["policy"]["description"]
    example = description[description.index('{"rules"') :]
    assert _errors(json.JSONDecoder().raw_decode(example)[0]) == []
    assert "policy" in tool["description"]
    assert "usage" in tool["description"]
