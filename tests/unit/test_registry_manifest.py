"""Validate the owned registry manifest contract against the official schema."""

import copy
import json
import shutil
import tomllib
from pathlib import Path

import pytest
from jsonschema.validators import validator_for

from scripts.registry_manifest import check_versions, launch_command, validate

ROOT = Path(__file__).resolve().parents[2]


def test_manifest_matches_official_schema() -> None:
    """Require a manifest accepted by the downloaded official dated schema."""
    schema = json.loads((ROOT / "tests/fixtures/mcp_registry_schema.json").read_text())
    manifest = json.loads((ROOT / "server.json").read_text())
    validator = validator_for(schema)
    validator.check_schema(schema)
    validator(schema).validate(manifest)
    assert manifest["$schema"] == schema["$id"]


def test_manifest_package_and_secret_contract() -> None:
    """Require the real package, explicit MCP extra, executable and private input."""
    manifest = json.loads((ROOT / "server.json").read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert manifest["name"] == "io.github.Alberto-Codes/judgevet"
    assert len(manifest["packages"]) == 1
    package = manifest["packages"][0]
    assert package["registryType"] == "pypi"
    assert package["identifier"] == project["name"]
    assert package["version"] == manifest["version"] == project["version"]
    assert package["transport"] == {"type": "stdio"}
    assert package["runtimeHint"] == "uvx"
    source, command = package["runtimeArguments"]
    assert source["name"] == "--from"
    assert source["value"] == "judgevet[mcp]=={version}"
    assert source["variables"]["version"]["value"] == project["version"]
    assert command["value"] == "judgevet-mcp"
    assert package.get("packageArguments", []) == []
    (key,) = package["environmentVariables"]
    assert key["name"] == "JEV_API__KEY"
    assert key["isRequired"] is True
    assert key["isSecret"] is True
    assert "value" not in key and "default" not in key


def test_owned_manifest_validator() -> None:
    """Execute the release check over current package and launcher configuration."""
    assert validate(ROOT)["name"] == "io.github.Alberto-Codes/judgevet"


@pytest.mark.parametrize("field", ["server", "package", "launcher"])
def test_registry_version_drift_rejected(field: str) -> None:
    """Reject each independently stale manifest version."""
    manifest = json.loads((ROOT / "server.json").read_text())
    package = manifest["packages"][0]
    if field == "server":
        manifest["version"] = "0.0.1"
    elif field == "package":
        package["version"] = "0.0.1"
    else:
        package["runtimeArguments"][0]["variables"]["version"]["value"] = "0.0.1"
    with pytest.raises(ValueError, match="versions disagree"):
        check_versions(ROOT, manifest)


@pytest.fixture
def registry_root(tmp_path: Path) -> Path:
    """Copy only release metadata for independent mutation checks."""
    for name in (
        "server.json",
        "pyproject.toml",
        "uv.lock",
        ".release-please-manifest.json",
        "src/judgevet/__init__.py",
        "tests/fixtures/mcp_registry_schema.json",
    ):
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    return tmp_path


@pytest.mark.parametrize(
    "field,value", [("isSecret", False), ("value", "canary"), ("default", "canary")]
)
def test_secret_contract_rejected(
    registry_root: Path, field: str, value: object
) -> None:
    """Reject unsafe credential configuration even when schema-valid."""
    path = registry_root / "server.json"
    manifest = json.loads(path.read_text())
    manifest["packages"][0]["environmentVariables"][0][field] = value
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="secret input"):
        validate(registry_root)


def test_launcher_is_manifest_derived() -> None:
    """Require the command renderer to consume the manifest's executable value."""
    manifest = json.loads((ROOT / "server.json").read_text())
    changed = copy.deepcopy(manifest)
    changed["packages"][0]["runtimeArguments"][1]["value"] = "canary-executable"
    assert launch_command(changed)[3] == "canary-executable"
    assert launch_command(manifest)[3] == "judgevet-mcp"
