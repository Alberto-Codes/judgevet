"""Materialize synthetic credentials for mechanical recipe launch checks.

This fixture implements only the recipe substitutions stated in the docs. It
cannot prove a native host performs those substitutions. No user environment,
credential or configuration is inspected.

Examples:
    Run ``uv run pytest -q tests/unit/test_doc_host_launchers.py``.

See Also:
    - [scripts.doc_host_contracts][]: Bounded template parser.
    - [scripts.mcp_smoke_transport][]: Standalone transport oracle.
"""

import importlib
import json
import os
import shutil
import sys
from pathlib import Path

from dotenv import dotenv_values
from packaging.requirements import Requirement
from packaging.utils import parse_wheel_filename

from scripts.doc_host_contracts import HostRecipe, parse_recipe

ROOT = Path(__file__).resolve().parents[2]
PAGE = "docs/how-to/connect-mcp.md"
HOSTS = ("vscode", "cursor", "claude-code", "desktop", "codex")


def exact_recipe(host: str, root: Path = ROOT) -> str:
    """Select an exact fenced template through the gate's schema inventory.

    Args:
        host: Host whose contract is required.
        root: Documentation root, including a deliberate mutation copy.

    Returns:
        The original fenced configuration text.
    """
    contracts = importlib.import_module("scripts.check_doc_schemas").CONTRACTS
    (number,) = [
        number
        for (page, number), kind in contracts.items()
        if page == PAGE and kind == f"host-{host}"
    ]
    language = "toml" if host == "codex" else "json"
    return exact_block(number, language, root)


def exact_block(number: int, language: str, root: Path = ROOT) -> str:
    """Read an exact fence without preloading another checker's executable module.

    Args:
        number: One-based fence number owned by the acceptance contract.
        language: Required fence language.
        root: Source root, including independent mutation copies.

    Returns:
        Unchanged fenced text selected by the existing inventory consumer.
    """
    inventory = importlib.import_module("scripts.doc_example_inventory")
    prepare = importlib.import_module("scripts.doc_cli_prepare")
    return prepare.source_block(inventory.discover(root), PAGE, number, language).text


def environment(workdir: Path, wheel: Path, requirement: str) -> dict[str, str]:
    """Create a fresh uvx cache and map only the requested extra to the candidate.

    Args:
        workdir: Test-owned directory outside the checkout.
        wheel: Exact candidate artifact.
        requirement: Exact documented package requirement.

    Returns:
        Explicit environment with no inherited credentials or Python paths.
    """
    requested = Requirement(requirement)
    _, wheel_version, _, _ = parse_wheel_filename(wheel.name)
    assert requested.name == "judgevet"
    assert str(requested.specifier) == f"=={wheel_version}", (
        "recipe pin differs from artifact"
    )
    extras = "[" + ",".join(sorted(requested.extras)) + "]" if requested.extras else ""
    override = workdir / "override.txt"
    override.write_text(f"judgevet{extras} @ {wheel.resolve().as_uri()}\n")
    return {
        "PATH": os.defpath,
        "HOME": str(workdir),
        "UV_PYTHON": sys.executable,
        "UV_ISOLATED": "1",
        "UV_CACHE_DIR": str(workdir / "cache"),
        "UV_OVERRIDE": str(override),
    }


def materialize(recipe: HostRecipe, workdir: Path) -> dict[str, str]:
    """Model only the chosen host credential fixture without reading real files.

    Args:
        recipe: Parsed template naming the credential mechanism.
        workdir: Test-owned directory for synthetic files.

    Returns:
        Synthetic server environment using the recipe's selected mechanism.
    """
    if recipe.credential == "key-file":
        key = workdir / "judgevet.key"
        key.write_text("host-canary\n")
        return {"JEV_API__KEY_FILE": str(key)}
    if recipe.credential == "env-file":
        env_file = workdir / "judgevet.env"
        env_file.write_text("JEV_API__KEY=host-canary\n")
        return {k: v for k, v in dotenv_values(env_file).items() if v is not None}
    return {recipe.location: "host-canary"}


def launcher(
    host: str, text: str, workdir: Path, wheel: Path, base_url: str
) -> tuple[list[str], dict[str, str]]:
    """Prepare the exact recipe argv with a synthetic service and fresh artifact.

    Args:
        host: Selected template contract.
        text: Exact source template, or deliberately broken variant.
        workdir: Isolated execution directory.
        wheel: Candidate wheel.
        base_url: Loopback fixture endpoint.

    Returns:
        Actual command and explicitly constructed child environment.
    """
    recipe = parse_recipe(host, text)
    command = list(recipe.command)
    executable = shutil.which(command[0])
    assert executable is not None, "documented launcher executable is required"
    command[0] = executable
    env = environment(workdir, wheel, command[2])
    env.update(materialize(recipe, workdir))
    env["JEV_API__BASE_URL"] = base_url
    return command, env


def verify_cli(stdout: str, kind: str) -> None:
    """Require a typed CLI answer, model and usage in the actual output.

    Args:
        stdout: Captured JSON from the exact CLI command.
        kind: Expected question type.
    """
    data = json.loads(stdout)
    assert data["model"] == "jev-1.13.0"
    assert data["usage"] == {"input_tokens": 3, "output_tokens": 2}
    assert set(data["answers"]) == {f"{kind}_question"}
    assert data["answers"][f"{kind}_question"]["type"] == kind
