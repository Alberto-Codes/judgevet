"""Acceptance contracts for exact host recipes, separate from host observations."""

import json

import pytest
from jsonschema.exceptions import ValidationError

from scripts.doc_schema_child import validate_block

ARGV = ["--from", "judgevet[mcp]==0.10.0", "judgevet-mcp"]


def recipe(host: str) -> str:
    """Build a synthetic template with the selected host's credential route."""
    if host == "codex":
        return (
            '[mcp_servers.judgevet]\ncommand = "uvx"\n'
            f"args = {json.dumps(ARGV)}\n"
            'env_vars = ["JEV_API__KEY"]\n'
        )
    server: dict[str, object] = {"command": "uvx", "args": ARGV}
    if host in {"vscode", "cursor"}:
        server.update(type="stdio", envFile="/absolute/path/to/judgevet.env")
    elif host == "claude-code":
        server["env"] = {"JEV_API__KEY": "${JEV_API__KEY}"}
    else:
        server["env"] = {"JEV_API__KEY_FILE": "/absolute/path/to/judgevet.key"}
    root = "servers" if host == "vscode" else "mcpServers"
    return json.dumps({root: {"judgevet": server}})


@pytest.mark.parametrize(
    "host", ["vscode", "cursor", "claude-code", "desktop", "codex"]
)
def test_native_recipe_schema(host: str) -> None:
    assert validate_block(f"host-{host}", recipe(host)) is None


@pytest.mark.parametrize(
    "host", ["vscode", "cursor", "claude-code", "desktop", "codex"]
)
def test_missing_credential_is_rejected(host: str) -> None:
    text = recipe(host)
    if host == "codex":
        text = text.replace('env_vars = ["JEV_API__KEY"]', "env_vars = []")
    else:
        data = json.loads(text)
        root = "servers" if host == "vscode" else "mcpServers"
        server = data[root]["judgevet"]
        server.pop("envFile" if host in {"vscode", "cursor"} else "env")
        text = json.dumps(data)
    with pytest.raises(ValueError, match="credential mechanism"):
        validate_block(f"host-{host}", text)


@pytest.mark.parametrize("host", ["vscode", "cursor", "claude-code", "desktop"])
def test_another_hosts_root_is_rejected(host: str) -> None:
    data = json.loads(recipe(host))
    servers = next(iter(data.values()))
    wrong_root = "mcpServers" if host == "vscode" else "servers"
    with pytest.raises(ValueError, match="invalid root"):
        validate_block(f"host-{host}", json.dumps({wrong_root: servers}))


@pytest.mark.parametrize("value", ["${env:JEV_API__KEY}", "literal-canary", ""])
def test_claude_credential_reference_is_not_cursor_syntax(value: str) -> None:
    data = json.loads(recipe("claude-code"))
    data["mcpServers"]["judgevet"]["env"]["JEV_API__KEY"] = value
    with pytest.raises(ValueError, match="credential mechanism"):
        validate_block("host-claude-code", json.dumps(data))


@pytest.mark.parametrize("kind", ["mcp-choice", "mcp-score"])
def test_criteria_are_checked_against_real_tool_schema(kind: str) -> None:
    text = '{"state":"Synthetic state","instruction":"Question?","criteria":42}'
    with pytest.raises(ValidationError):
        validate_block(kind, text)
