#!/usr/bin/env python3
"""Fail when a change silences a gate instead of fixing it.

CLAUDE.md forbids `# noqa`, `# type: ignore` and `per-file-ignores` added to
make a gate pass. That rule needs teeth: the first three delegated sessions in
this repo each reached for a suppression when a gate resisted, once replacing a
working test double with `object()` and a `# type: ignore[assignment]`.

Reading the diff afterwards catches it. A hook prevents it.

The two `per-file-ignores` entries already in `pyproject.toml` are allowed and
counted: tests relax docstring and assert rules, and the typer CLI takes one
argument per option by design. Adding a third is a decision, so this script
fails until the budget here is raised deliberately.

Usage:
    check_suppressions.py [paths...]     # defaults to src/ and tests/

Exit status is 1 when a suppression is found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# A suppression comment anywhere in a line of Python.
SUPPRESSION = re.compile(r"#\s*(noqa|type:\s*ignore|ruff:\s*noqa|pyright:\s*ignore)")

# Deliberate `per-file-ignores` blocks in pyproject.toml. Raise this only with
# a reason in the commit message.
ALLOWED_PER_FILE_IGNORES = 2


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


def count_per_file_ignores(pyproject: Path) -> int:
    """Count entries under ruff's `per-file-ignores` table.

    Args:
        pyproject: The `pyproject.toml` to read.

    Returns:
        The number of file patterns given their own ignore list.
    """
    if not pyproject.is_file():
        return 0
    text = pyproject.read_text(errors="replace")
    start = text.find("[tool.ruff.lint.per-file-ignores]")
    if start == -1:
        return 0
    rest = text[start + 1 :]
    end = rest.find("\n[")
    block = rest if end == -1 else rest[:end]
    return len(re.findall(r'^\s*"[^"]+"\s*=\s*\[', block, re.MULTILINE))


def main(argv: list[str]) -> int:
    """Run the check.

    Args:
        argv: Paths to scan; defaults to `src` and `tests`.

    Returns:
        1 when a suppression is found or the ignore budget is exceeded.
    """
    roots = [Path(a) for a in argv] or [Path("src"), Path("tests")]
    findings = scan([r for r in roots if r.exists()])

    ignores = count_per_file_ignores(Path("pyproject.toml"))
    over_budget = ignores > ALLOWED_PER_FILE_IGNORES

    if not findings and not over_budget:
        return 0

    if findings:
        print("Gate suppressions are not allowed. Fix the cause instead:")
        for finding in findings:
            print(f"  {finding}")
    if over_budget:
        print(
            f"pyproject.toml has {ignores} per-file-ignores entries, "
            f"budget is {ALLOWED_PER_FILE_IGNORES}. "
            "Raise ALLOWED_PER_FILE_IGNORES deliberately, with a reason."
        )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
