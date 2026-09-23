"""Validate documented data against an isolated installation's contracts.

Examples:
    The schema parent supplies an exact JSON/TOML block manifest to this child.

See Also:
    - [judgevet.policy_json][]: Policy JSON decoder.
    - [judgevet.adapters.inbound.mcp][]: Discovered MCP schemas.
"""

import asyncio
import json
import tomllib
from pathlib import Path
from typing import Any

import jsonschema

from judgevet import Choice, HTTPSystemOneAdapter, Noul, Score
from judgevet.adapters.inbound.cli import parse_questions
from judgevet.adapters.inbound.cli_inputs import _validate_question_file_content
from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.policy import PolicyReport, RuleReport
from judgevet.policy_json import parse_policy
from scripts.smoke_release_child import assert_in_site_packages


async def noul_schema() -> dict[str, Any]:
    """Read the actual installed server's ask_noul discovery schema.

    Returns:
        The input schema from tool discovery, without a service call.

    Raises:
        ValueError: If the expected tool is absent.
    """
    with HTTPSystemOneAdapter(api_key="synthetic-doc-key") as adapter:
        server = create_mcp_server(adapter)
        listing = await server._request_handlers["tools/list"].handler(None, None)
        for tool in listing.tools:
            if tool.name == "ask_noul":
                return tool.input_schema
    raise ValueError("ask_noul missing from discovery")


def validate_mcp(text: str) -> None:
    """Validate an exact documented argument object against discovery.

    Args:
        text: Complete JSON argument object for ask_noul.

    Raises:
        ValueError: If JSON is invalid or the tool is absent.
        jsonschema.ValidationError: If arguments violate the discovered schema.
    """
    jsonschema.validate(json.loads(text), asyncio.run(noul_schema()))


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
        "risk": Choice({"low": "Low risk", "high": "High risk"}),
        "quality": Score(["Poor", "Fair", "Good", "Excellent"]),
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


def validate_host(text: str) -> None:
    """Parse the host template without launching or modifying a host.

    Args:
        text: Exact TOML template with its documented placeholder path.

    Raises:
        ValueError: If the launcher shape is incomplete.
    """
    server = tomllib.loads(text)["mcp_servers"]["judgevet"]
    if server["command"] != "direnv" or server["args"][:2] != [
        "exec",
        "/absolute/path/to/project",
    ]:
        raise ValueError("unexpected host launcher template")
    if server["args"][-1] != "judgevet-mcp":
        raise ValueError("host template does not launch judgevet-mcp")


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
        "host": validate_host,
    }
    if kind == "policy":
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
