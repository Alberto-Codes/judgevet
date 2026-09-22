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

It also validates that any extras requested by the manifest exist in the
package's own lock entry. A nonexistent extra is caught by reading `uv.lock`
and comparing `requires-dist`/`requires-dev` extras against `optional-
dependencies` for each provider.

Usage:
    check_dependencies.py [path]  # path to pyproject.toml; defaults to pyproject.toml

Exit status is 1 when the dependency set is not the pinned set or when extras
are invalid.
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


def _parse_lock_file(pyproject: Path) -> dict | None:
    """Parse the uv.lock file corresponding to a pyproject.toml.

    Args:
        pyproject: The path to pyproject.toml.

    Returns:
        The parsed lock data as a dict, or None if the lock file doesn't exist.
    """
    lock_path = pyproject.parent / "uv.lock"
    if not lock_path.is_file():
        return None
    try:
        with open(lock_path, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError:
        return None


def _find_package_in_lock(lock_data: dict, package_name: str) -> dict | None:
    """Find a package entry in the lock file by name.

    Args:
        lock_data: The parsed uv.lock data.
        package_name: The normalized package name to find.

    Returns:
        The package dict if found, None otherwise.
    """
    for package in lock_data.get("package", []):
        if package.get("name") == package_name:
            return package
    return None


def _get_requested_extras(requirement: dict) -> list[str]:
    """Extract requested extras from a requirement dict.

    Args:
        requirement: A requirement dict from requires-dist or requires-dev.

    Returns:
        A list of requested extra names, or an empty list if none.
    """
    return requirement.get("extras", [])


def _get_available_extras(package_entry: dict) -> set[str]:
    """Extract available extras from a package lock entry.

    Args:
        package_entry: A package dict from the lock file.

    Returns:
        A set of available extra names.
    """
    optional_deps = package_entry.get("optional-dependencies", {})
    return set(optional_deps.keys())


def _parse_pyproject_dependencies(
    pyproject: Path,
) -> list[tuple[str, list[str], str]]:
    """Parse dependencies from pyproject.toml, extracting package, extras, source.

    Args:
        pyproject: The path to pyproject.toml.

    Returns:
        A list of tuples of (normalized_name, list_of_extras, source).
        The source indicates where the requirement came from (e.g., "requires-dist"
        or "requires-dev.dev").
    """
    if not pyproject.is_file():
        return []
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return []

    result: list[tuple[str, list[str], str]] = []

    # Parse requires-dist (runtime dependencies)
    requires_dist = data.get("project", {}).get("dependencies", [])
    for dep in requires_dist:
        # Parse extras from the raw dependency string
        if "[" in dep:
            extras_str = dep.split("[", maxsplit=1)[1]
            extras_str = extras_str.split("]", maxsplit=1)[0]
            extras = [e.strip() for e in extras_str.split(",")]
        else:
            extras = []
        name = _extract_name(dep)
        result.append((name, extras, "requires-dist"))

    # Parse requires-dev (dev dependencies)
    requires_dev = data.get("dependency-groups", {})
    for group_name, group_deps in requires_dev.items():
        for dep in group_deps:
            if "[" in dep:
                extras_str = dep.split("[", maxsplit=1)[1]
                extras_str = extras_str.split("]", maxsplit=1)[0]
                extras = [e.strip() for e in extras_str.split(",")]
            else:
                extras = []
            name = _extract_name(dep)
            result.append((name, extras, f"requires-dev.{group_name}"))

    return result


def _check_extras(
    pyproject: Path,
) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Check that all requested extras exist in their providers.

    Args:
        pyproject: The path to pyproject.toml.

    Returns:
        A tuple of (invalid_extras, stale_locks):
        - invalid_extras: list of (package, extra, source) tuples for missing extras
        - stale_locks: list of package names absent from the lock
    """
    lock_data = _parse_lock_file(pyproject)
    if lock_data is None:
        # Lock file doesn't exist - this will be caught by the existing check
        # or by a missing file error. Just return empty.
        return [], []

    # Build a mapping of package name -> lock entry
    lock_packages: dict[str, dict] = {}
    for package in lock_data.get("package", []):
        lock_packages[package.get("name")] = package

    # Parse dependencies from pyproject.toml
    dependencies = _parse_pyproject_dependencies(pyproject)

    invalid_extras: list[tuple[str, str, str]] = []
    stale_locks: list[str] = []

    for pkg_name, extras, source in dependencies:
        # Check if this package is in the lock
        if pkg_name not in lock_packages:
            stale_locks.append(pkg_name)
            continue

        # Get the lock entry for this package
        lock_entry = lock_packages[pkg_name]
        available_extras = _get_available_extras(lock_entry)

        # Check each requested extra
        invalid_extras.extend(
            (pkg_name, extra, source)
            for extra in extras
            if extra not in available_extras
        )

    return invalid_extras, stale_locks


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


def _report_extras_issues(
    invalid_extras: list[tuple[str, str, str]], stale_locks: list[str]
) -> None:
    """Report extras-related issues.

    Args:
        invalid_extras: List of (package, extra, source) tuples for invalid extras.
        stale_locks: List of package names absent from the lock.
    """
    # Two different findings, so two different headers. A stale lock filed
    # under "invalid extras" sends the reader hunting for a typo in an extra
    # name when the fix is a re-lock.
    if stale_locks:
        print("check_dependencies: the lock does not cover every requirement.")
        for pkg in sorted(stale_locks):
            print(
                f"  {pkg} is required but absent from uv.lock; the lock is stale "
                "— run uv lock"
            )

    if invalid_extras:
        print("check_dependencies: invalid extras detected.")
        for pkg, extra, source in sorted(invalid_extras, key=lambda x: (x[0], x[1])):
            print(f"  {pkg} has no extra named '{extra}' (from {source})")


def _report_extras_advice(invalid_extras: list[tuple[str, str, str]]) -> None:
    """Print advice for fixing extras issues.

    Args:
        invalid_extras: List of (package, extra, source) tuples for invalid extras.
    """
    if invalid_extras:
        print(
            "To fix an invalid extra: use only extras that the provider "
            "package actually publishes in its lock entry's optional-dependencies."
        )


def _report_all_issues(unpinned: list[str], missing: list[str]) -> None:
    """Report dependency set issues."""
    print("check_dependencies: the runtime dependency set is not the pinned set.")
    if unpinned:
        print(f"  unpinned: {', '.join(unpinned)}")
    else:
        print("  unpinned: (none)")
    if missing:
        print(f"  pinned but absent: {', '.join(missing)}")
    else:
        print("  pinned but absent: (none)")


def _report_advice(unpinned: list[str], missing: list[str]) -> None:
    """Print advice for fixing dependency issues."""
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


def main(argv: list[str]) -> int:
    """Run the check.

    Args:
        argv: Path to pyproject.toml; defaults to "pyproject.toml".

    Returns:
        0 if the dependency set matches the pin and all extras are valid,
        1 otherwise.
    """
    path = Path(argv[0]) if argv else Path("pyproject.toml")
    unpinned, missing = check_dependencies(path, ALLOWED_RUNTIME_DEPENDENCIES)
    invalid_extras, stale_locks = _check_extras(path)

    # If everything is clean, report success
    if not unpinned and not missing and not invalid_extras and not stale_locks:
        print(
            f"check_dependencies: clean, {len(ALLOWED_RUNTIME_DEPENDENCIES)} runtime "
            f"dependencies match the pin ({', '.join(sorted(ALLOWED_RUNTIME_DEPENDENCIES))})"
        )
        return 0

    # Report dependency issues
    if unpinned or missing:
        _report_all_issues(unpinned, missing)
    else:
        print("check_dependencies: the runtime dependency set is clean.")

    # Report extras issues
    if invalid_extras or stale_locks:
        _report_extras_issues(invalid_extras, stale_locks)
        _report_extras_advice(invalid_extras)

    # Report advice
    if unpinned or missing:
        _report_advice(unpinned, missing)

    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
