"""Validate documented data against an isolated installation's contracts.

Examples:
    The schema parent supplies an exact JSON/TOML block manifest to this child.

See Also:
    - [judgevet.policy_json][]: Policy JSON decoder.
    - [judgevet.adapters.inbound.mcp][]: Discovered MCP schemas.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

import jsonschema

from judgevet import Choice, HTTPSystemOneAdapter, Noul, Score
from judgevet.adapters.inbound.cli import parse_questions
from judgevet.adapters.inbound.cli_inputs import _validate_question_file_content
from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.policy import PolicyReport, RuleReport
from judgevet.policy_json import parse_policy
from scripts.doc_host_contracts import parse_recipe
from scripts.smoke_release_child import assert_in_site_packages


async def tool_schema(name: str) -> dict[str, Any]:
    """Read the actual installed server's selected tool discovery schema.

    Args:
        name: Exact public tool name.

    Returns:
        The input schema from tool discovery, without a service call.

    Raises:
        ValueError: If the expected tool is absent.
    """
    with HTTPSystemOneAdapter(api_key="synthetic-doc-key") as adapter:
        server = create_mcp_server(adapter)
        listing = await server._request_handlers["tools/list"].handler(None, None)
        for tool in listing.tools:
            if tool.name == name:
                return tool.input_schema
    raise ValueError("tool missing from discovery")


def validate_mcp(text: str, name: str = "ask_noul") -> None:
    """Validate an exact documented argument object against discovery.

    Args:
        text: Complete JSON argument object.
        name: Exact public tool name.

    Raises:
        ValueError: If JSON is invalid or the tool is absent.
        jsonschema.ValidationError: If arguments violate the discovered schema.
    """
    jsonschema.validate(json.loads(text), asyncio.run(tool_schema(name)))


def validate_questions(text: str) -> None:
    """Apply installed file-input validation and question decoding.

    Args:
        text: Exact question file contents.

    Raises:
        ValueError: If input violates the file or question contract.
    """
    _validate_question_file_content(text)
    parse_questions(text)


def validate_fragment(text: str) -> None:
    """Validate a documented rule fragment with its stated question context.

    Args:
        text: Single rule object, not a complete policy file.

    Raises:
        ValueError: If the rule or question binding is invalid.
    """
    questions = {
        "risk": Choice(criteria={"low": "Low risk", "high": "High risk"}),
        "quality": Score(criteria=["Poor", "Fair", "Good", "Excellent"]),
    }
    parse_policy(json.dumps({"rules": [json.loads(text)]}), questions)


def validate_output(text: str) -> None:
    """Check the illustrative CLI policy member against report fields.

    Args:
        text: JSON policy member, with illustrative textual details.

    Raises:
        ValueError: If report fields or aggregate verdict are inconsistent.
    """
    data = json.loads(text)
    report = PolicyReport(
        tuple(
            RuleReport(item["question"], item["pass"], item["detail"])
            for item in data["rules"]
        )
    )
    if data["result"] != ("pass" if report.passed else "fail"):
        raise ValueError("illustrative policy result disagrees with rule reports")


def validate_block(kind: str, text: str) -> None:
    """Dispatch an explicitly classified schema check.

    Args:
        kind: Selected input/template/output contract.
        text: Exact fenced body.

    Raises:
        ValueError: If data is invalid or the contract is unknown.
        jsonschema.ValidationError: If MCP arguments violate discovery.
    """
    validators = {
        "mcp": validate_mcp,
        "questions": validate_questions,
        "fragment": validate_fragment,
        "output": validate_output,
    }
    if kind.startswith("host-"):
        parse_recipe(kind.removeprefix("host-"), text)
    elif kind in {"mcp-choice", "mcp-score"}:
        validate_mcp(text, "ask_" + kind.removeprefix("mcp-"))
    elif kind == "policy":
        parse_policy(text, {"clear": Noul()})
    elif kind in validators:
        validators[kind](text)
    else:
        raise ValueError("unknown documentation schema check")


def main() -> int:
    """Validate every selected exact block and report its source location.

    Returns:
        One on a failed contract or empty selection, otherwise zero.
    """
    assert_in_site_packages()
    jobs = json.loads(Path("schema_examples.json").read_text())
    if not jobs:
        print("Documentation schemas: empty inventory")
        return 1
    for job in jobs:
        try:
            validate_block(job["kind"], job["text"])
        except (ValueError, TypeError, KeyError, jsonschema.ValidationError) as error:
            print(f"{job['label']}: {type(error).__name__} validating {job['kind']}")
            return 1
    print(f"Documentation schemas: {len(jobs)} exact JSON/TOML blocks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
