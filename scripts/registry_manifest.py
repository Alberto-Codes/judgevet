"""Validate registry metadata and render the tested uvx launch convention.

Fields follow https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json.
Argument ordering follows VS Code's AbstractCommonMcpManagementService at
https://github.com/microsoft/vscode/blob/ad77169b64ccc8c9b2401b67f29d99efd487e3c0/src/vs/platform/mcp/common/mcpManagementService.ts.

Examples:
    Run ``uv run python -m scripts.registry_manifest`` from the repository root.

See Also:
    - [scripts.smoke_registry_release][]: Isolated manifest launcher checks.
    - [judgevet.adapters.inbound.mcp_entrypoint][]: Installed executable.
"""

import ast
import json
import tomllib
from pathlib import Path
from typing import Any

from jsonschema.validators import validator_for


def launch_command(manifest: dict[str, Any]) -> list[str]:
    """Render fixed arguments using the tested registry consumer's ordering.

    Args:
        manifest: Schema-validated judgevet manifest with fixed runtime arguments.

    Returns:
        Uvx argv, including the consumer-appended package identity token.

    Raises:
        ValueError: The package selects an unsupported registry, runtime or argument.
    """
    package = manifest["packages"][0]
    if package["registryType"] != "pypi" or package["runtimeHint"] != "uvx":
        raise ValueError("registry launcher requires PyPI and uvx")
    command = [package["runtimeHint"]]
    for argument in package["runtimeArguments"]:
        if argument["type"] == "named":
            command.append(argument["name"])
        elif argument["type"] != "positional":
            raise ValueError("unsupported registry argument")
        value = argument["value"]
        for name, variable in argument.get("variables", {}).items():
            value = value.replace("{" + name + "}", variable["value"])
        command.append(value)
    if package.get("registryBaseUrl") or package.get("packageArguments"):
        raise ValueError("unexpected index or package arguments")
    command.append(f"{package['identifier']}@{package['version']}")
    return command


def check_versions(root: Path, manifest: dict[str, Any]) -> str:
    """Require agreement of all release-controlled version fields.

    Args:
        root: Repository directory.
        manifest: Parsed registry manifest.

    Returns:
        The common version.

    Raises:
        ValueError: Version values disagree or a root package version is absent.
    """
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    locked = tomllib.loads((root / "uv.lock").read_text())["package"]
    release = json.loads((root / ".release-please-manifest.json").read_text())["."]
    module = ast.parse((root / "src/judgevet/__init__.py").read_text())
    exported = [
        ast.literal_eval(node.value)
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets)
    ]
    package = manifest["packages"][0]
    pins = [p["version"] for p in locked if p["name"] == project["name"]]
    values = [release, manifest["version"], package["version"], *exported, *pins]
    values.append(package["runtimeArguments"][0]["variables"]["version"]["value"])
    if len(exported) != 1 or len(pins) != 1 or set(values) != {project["version"]}:
        raise ValueError("release-controlled versions disagree")
    return project["version"]


def validate(root: Path) -> dict[str, Any]:
    """Validate the manifest schema, synchronized versions and owned launch contract.

    Args:
        root: Repository directory with manifest and official schema fixture.

    Returns:
        Validated registry manifest.

    Raises:
        ValueError: Package identity, credential input or launcher differs from the contract.
        jsonschema.exceptions.ValidationError: The official schema rejects the manifest.
    """
    manifest = json.loads((root / "server.json").read_text())
    schema = json.loads((root / "tests/fixtures/mcp_registry_schema.json").read_text())
    validator_for(schema)(schema).validate(manifest)
    version = check_versions(root, manifest)
    (package,) = manifest["packages"]
    (key,) = package["environmentVariables"]
    expected = [
        "uvx",
        "--from",
        f"judgevet[mcp]=={version}",
        "judgevet-mcp",
        f"judgevet@{version}",
    ]
    if (
        manifest["$schema"] != schema["$id"]
        or manifest["name"] != "io.github.Alberto-Codes/judgevet"
        or package["identifier"] != "judgevet"
        or package["transport"] != {"type": "stdio"}
        or key["name"] != "JEV_API__KEY"
        or key.get("isSecret") is not True
        or key.get("isRequired") is not True
        or "value" in key
        or "default" in key
        or launch_command(manifest) != expected
    ):
        raise ValueError("registry identity, secret input or launcher contract changed")
    return manifest


if __name__ == "__main__":
    validate(Path.cwd())
    print("Registry schema, launcher and release versions pass")
