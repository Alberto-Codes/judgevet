"""Validate exact user-doc JSON and TOML in a separate MCP-enabled wheel install.

Examples:
    Run ``uv run python -m scripts.check_doc_schemas`` from the checkout.

See Also:
    - [judgevet.adapters.inbound.mcp][]: Optional runtime input schemas.
"""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from scripts.doc_example_inventory import discover, validate
from scripts.smoke_release import (
    build_wheel,
    create_venv,
    install_wheel,
    probe_import,
    run_child,
)

CONTRACTS = {
    ("docs/how-to/connect-mcp.md", 4): "host",
    ("docs/how-to/connect-mcp.md", 6): "mcp",
    ("docs/how-to/use-cli-files.md", 2): "questions",
    ("docs/how-to/use-cli-policy.md", 1): "questions",
    ("docs/how-to/use-cli-policy.md", 2): "policy",
    ("docs/how-to/use-cli-policy.md", 4): "fragment",
    ("docs/how-to/use-cli-policy.md", 5): "fragment",
    ("docs/how-to/use-cli-policy.md", 6): "output",
}


def prepare(root: Path, workdir: Path) -> None:
    """Require a schema contract for every inventoried JSON or TOML block.

    Args:
        root: Authored documentation root.
        workdir: Isolated child directory.

    Raises:
        ValueError: If selected blocks lack contracts or existing contracts are stale.
    """
    validate(root, root / "scripts/doc_examples.json")
    jobs = []
    seen = set()
    for page, blocks in discover(root).items():
        for number, block in enumerate(blocks, 1):
            if block.language not in {"json", "toml"}:
                continue
            key = (page, number)
            if key not in CONTRACTS:
                raise ValueError(f"{page}:{block.line}: no JSON/TOML contract")
            seen.add(key)
            jobs.append(
                {
                    "label": f"{page}:{block.line}",
                    "text": block.text,
                    "kind": CONTRACTS[key],
                }
            )
    if seen != CONTRACTS.keys():
        raise ValueError("stale JSON/TOML documentation contracts")
    (workdir / "schema_examples.json").write_text(json.dumps(jobs))


def check(root: Path, workdir: Path) -> int:
    """Build and inspect the exact wheel with its optional MCP dependencies.

    Args:
        root: Documentation root, including optional mutation copies.
        workdir: Fresh isolated directory.

    Returns:
        The schema child's exit status.

    Raises:
        ValueError: If documentation selection is invalid.
        RuntimeError: If artifact build, installation or isolation fails.
    """
    prepare(root, workdir)
    wheel = build_wheel(workdir / "dist")
    python = create_venv(workdir)
    install_wheel(python, wheel, extras=("mcp",))
    environment = {"PATH": str(python.parent)}
    probe_import(python, environment, workdir)
    (workdir / "scripts").mkdir()
    shutil.copy(Path(__file__).with_name("smoke_release_child.py"), workdir / "scripts")
    shutil.copy(Path(__file__).with_name("doc_schema_child.py"), workdir)
    return run_child(python, workdir / "doc_schema_child.py", environment, workdir)


def main() -> int:
    """Run separate optional-runtime schema checks without any live service call.

    Returns:
        Zero on success, one on invalid examples or setup failure.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix="judgevet-doc-schemas-") as directory:
            return check(args.root.resolve(), Path(directory))
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Documentation schemas: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
