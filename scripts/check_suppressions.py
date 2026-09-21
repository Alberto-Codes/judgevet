#!/usr/bin/env python3
"""Fail when a change silences a gate instead of fixing it.

CLAUDE.md forbids `# noqa`, `# type: ignore` and `per-file-ignores` added to
make a gate pass. That rule needs teeth: the first three delegated sessions in
this repo each reached for a suppression when a gate resisted, once replacing a
working test double with `object()` and a `# type: ignore[assignment]`.

Reading the diff afterwards catches it. A hook prevents it.

The `per-file-ignores` entries already in `pyproject.toml` are allowed and
counted by total codes, not patterns. Adding a new code to an existing entry
is a decision, so this script fails until the budget is raised deliberately.

Usage:
    check_suppressions.py [paths...]     # defaults to src/ and tests/

Exit status is 1 when a suppression is found.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

# A suppression comment anywhere in a line of Python.
SUPPRESSION = re.compile(r"#\s*(noqa|type:\s*ignore|ruff:\s*noqa|pyright:\s*ignore)")

# Deliberate `per-file-ignores` codes in pyproject.toml. Raise this only with
# a reason in the commit message.
# Current budget: 12 codes
# - 7 in tests/**/*.py (S101, D100, D101, D102, D103, D104, PLR2004)
# - 1 in conftest.py (PLC0415 - import inside function; E402 would fire at module level)
# - 3 in mcp.py (PLC0415, C901, PLR0915)
# - 1 in test_secret_guard.py (S603 - subprocess call required for end-to-end proof)
ALLOWED_PER_FILE_IGNORE_CODES = 12


def scan(paths: list[Path]) -> list[str]:
    """Report every suppression comment found under the given paths.

    Args:
        paths: Files or directories to scan.

    Returns:
        One line per finding, empty when the tree is clean.
    """
    findings: list[str] = []
    for root in paths:
        files = root.rglob("*.py") if root.is_dir() else [root]
        for file in files:
            if "__pycache__" in file.parts or ".venv" in file.parts:
                continue
            try:
                lines = file.read_text(errors="replace").splitlines()
            except OSError:
                continue
            for number, line in enumerate(lines, start=1):
                if SUPPRESSION.search(line):
                    findings.append(f"{file}:{number}: {line.strip()}")
    return findings


def count_per_file_ignores(pyproject: Path) -> tuple[int, dict[str, list[str]]]:
    """Count codes under ruff's `per-file-ignores` table.

    Args:
        pyproject: The `pyproject.toml` to read.

    Returns:
        A tuple of (total code count, dict mapping file pattern to its codes).
    """
    if not pyproject.is_file():
        return 0, {}
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return 0, {}
    ignores_table = (
        data.get("tool", {}).get("ruff", {}).get("lint", {}).get("per-file-ignores", {})
    )
    if not ignores_table:
        return 0, {}
    total = 0
    per_pattern: dict[str, list[str]] = {}
    for pattern, codes in ignores_table.items():
        if isinstance(codes, list):
            per_pattern[pattern] = codes
            total += len(codes)
    return total, per_pattern


def main(argv: list[str]) -> int:
    """Run the check.

    Args:
        argv: Paths to scan; defaults to `src` and `tests`.

    Returns:
        1 when a suppression is found or the ignore budget is exceeded.
    """
    roots = [Path(a) for a in argv] or [Path("src"), Path("tests")]
    findings = scan([r for r in roots if r.exists()])

    total, per_pattern = count_per_file_ignores(Path("pyproject.toml"))
    over_budget = total > ALLOWED_PER_FILE_IGNORE_CODES

    if not findings and not over_budget:
        return 0

    if findings:
        print("Gate suppressions are not allowed. Fix the cause instead:")
        for finding in findings:
            print(f"  {finding}")
    if over_budget:
        print(
            f"pyproject.toml has {total} per-file-ignores codes, "
            f"budget is {ALLOWED_PER_FILE_IGNORE_CODES}. "
            "Raise ALLOWED_PER_FILE_IGNORE_CODES deliberately, with a reason."
        )
        print("Breakdown by pattern:")
        for pattern, codes in sorted(per_pattern.items()):
            print(f"  {pattern!r}: {len(codes)} code(s) — {', '.join(codes)}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
