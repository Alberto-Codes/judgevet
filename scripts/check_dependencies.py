"""Fail when the runtime dependency set is not the pinned set.

The `[project.dependencies]` table declares what this package publishes to
PyPI. Only runtime dependencies belong there; test and tooling packages must
live in `[dependency-groups].dev`. A package appearing in the wrong list
becomes a transitive dependency of every consumer — see issue #100 for the
incident.

This gate reads `pyproject.toml` and compares the runtime dependency set to a
pin. The pin is names only, not specifiers — version ranges are already
declared and visible; this gate's job is to catch misplacement, not version
drift. A removal fails as well as an addition: "the set changes" is the issue's
wording.

Usage:
    check_dependencies.py [path]  # path to pyproject.toml; defaults to pyproject.toml

Exit status is 1 when the dependency set is not the pinned set.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

# PEP 503 normalization: lowercase, runs of -/_/., collapsed to -
# Used to compare package names consistently.
PEP_503_NORMALIZE = re.compile(r"[-_.]+")


def _normalize(name: str) -> str:
    """Normalize a package name per PEP 503.

    Args:
        name: The package name to normalize.

    Returns:
        The normalized name, lowercase with runs of -/_/. replaced by -.
    """
    return PEP_503_NORMALIZE.sub("-", name.lower())


def _extract_name(dependency: str) -> str:
    """Extract the bare package name from a dependency string.

    Strips extras (e.g. `pkg[extra]`), specifiers (e.g. `>=1.0`), and markers
    (e.g. `; python_version < "3.12"`) to the bare name.

    Args:
        dependency: A dependency string like `pkg[extra]>=1.0; python_version < "3.12"`.

    Returns:
        The normalized package name.
    """
    # Remove extras: pkg[extra] -> pkg
    name = dependency.split("[", maxsplit=1)[0].strip()
    # Remove specifiers and markers: pkg>=1.0; ... -> pkg
    # Find the FIRST occurrence of any separator (not the first type)
    # The version specifier comes before the marker, so we need the first char overall
    first_idx = len(name)
    for sep in (";", ">", "<", "=", "!", "~"):
        idx = name.find(sep)
        if idx != -1 and idx < first_idx:
            first_idx = idx
    name = name[:first_idx] if first_idx < len(name) else name
    # Clean up any remaining whitespace
    name = name.strip()
    return _normalize(name)


def parse_runtime_names(pyproject: Path) -> set[str]:
    """Parse `[project.dependencies]` from a pyproject.toml file.

    Args:
        pyproject: The path to pyproject.toml.

    Returns:
        A set of normalized package names, or the empty set if the table
        does not exist.
    """
    if not pyproject.is_file():
        return set()
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return set()

    dependencies = data.get("project", {}).get("dependencies", [])
    if not dependencies:
        return set()

    return {_extract_name(dep) for dep in dependencies}


# The pinned runtime dependency set.
# Raise this only with a reason in the commit message.
# Current set: 4 packages
# - httpx: async HTTP client for Jev API calls
# - pydantic-settings: Settings class for API key and other config
# - structlog: structured logging for CLI and MCP adapter
# - typer: CLI framework for the judgevet command
ALLOWED_RUNTIME_DEPENDENCIES = {
    "httpx",
    "pydantic-settings",
    "structlog",
    "typer",
}


def check_dependencies(
    pyproject: Path, allowed: set[str]
) -> tuple[list[str], list[str]]:
    """Compare the runtime dependency set to the pinned set.

    Args:
        pyproject: The path to pyproject.toml.
        allowed: The pinned set of allowed runtime dependencies.

    Returns:
        A tuple of (unpinned, missing), each a sorted list of normalized names.
        unpinned: packages in pyproject.dependencies but not in allowed.
        missing: packages in allowed but not in pyproject.dependencies.
    """
    current = parse_runtime_names(pyproject)
    unpinned = sorted(current - allowed)
    missing = sorted(allowed - current)
    return unpinned, missing


def main(argv: list[str]) -> int:
    """Run the check.

    Args:
        argv: Path to pyproject.toml; defaults to "pyproject.toml".

    Returns:
        0 if the dependency set matches the pin, 1 otherwise.
    """
    path = Path(argv[0]) if argv else Path("pyproject.toml")
    unpinned, missing = check_dependencies(path, ALLOWED_RUNTIME_DEPENDENCIES)

    if not unpinned and not missing:
        print(
            f"check_dependencies: clean, {len(ALLOWED_RUNTIME_DEPENDENCIES)} runtime "
            f"dependencies match the pin ({', '.join(sorted(ALLOWED_RUNTIME_DEPENDENCIES))})"
        )
        return 0

    print("check_dependencies: the runtime dependency set is not the pinned set.")
    if unpinned:
        print(f"  unpinned: {', '.join(unpinned)}")
    else:
        print("  unpinned: (none)")
    if missing:
        print(f"  pinned but absent: {', '.join(missing)}")
    else:
        print("  pinned but absent: (none)")
    # The advice follows the finding. A removal has nothing to do with the dev
    # group, and printing that sentence anyway trains the reader to skip it.
    if unpinned:
        print(
            "To fix an unpinned name: test and tooling packages belong in "
            "[dependency-groups].dev, not [project.dependencies]. A deliberate "
            "runtime dependency is added to ALLOWED_RUNTIME_DEPENDENCIES in "
            "scripts/check_dependencies.py, with a reason, in the same commit."
        )
    if missing:
        print(
            "To fix an absent name: a deliberate removal drops it from "
            "ALLOWED_RUNTIME_DEPENDENCIES in scripts/check_dependencies.py in the "
            "same commit. If you did not mean to remove it, restore it to "
            "[project.dependencies]."
        )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
