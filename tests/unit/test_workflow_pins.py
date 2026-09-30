"""Require every remote GitHub Action to be pinned by full commit SHA.

GitHub's hardening guide calls a full-length commit SHA the only immutable
action reference:
https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
"""

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PINNED = re.compile(r"^[\w.-]+/[\w.-]+(/[\w./-]+)?@[0-9a-f]{40}$")
USES_LINE = re.compile(r"^\s*(?:-\s+)?uses:\s*(\S+)\s*(#.*)?$")
VERSION_COMMENT = re.compile(r"^#\s*v\d+(\.\d+)*$")


def action_files() -> list[Path]:
    """List every workflow and composite action definition under .github.

    Returns:
        The sorted YAML paths under .github/workflows and .github/actions.
    """
    github = ROOT / ".github"
    return sorted(
        path
        for folder in ("workflows", "actions")
        for pattern in ("*.yml", "*.yaml")
        for path in (github / folder).rglob(pattern)
    )


def parsed_uses(node: object) -> Iterator[str]:
    """Yield every `uses:` value in a parsed workflow, at any depth.

    Args:
        node: A parsed YAML mapping, sequence or scalar.

    Yields:
        Each `uses:` string, from steps and job-level reusable workflows.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "uses" and isinstance(value, str):
                yield value
            else:
                yield from parsed_uses(value)
    elif isinstance(node, list):
        for item in node:
            yield from parsed_uses(item)


def raw_uses(path: Path) -> list[tuple[str, str]]:
    """Return each raw `uses:` line's value and trailing comment.

    Args:
        path: The workflow or action file to read.

    Returns:
        One (value, comment) pair per `uses:` line, comment empty if absent.
    """
    found = []
    for line in path.read_text().splitlines():
        match = USES_LINE.match(line)
        if match:
            found.append((match.group(1), (match.group(2) or "").strip()))
    return found


@pytest.mark.unit
def test_action_files_exist() -> None:
    """Fail loudly if the scan finds nothing, which would pass vacuously."""
    files = action_files()
    assert ROOT / ".github/workflows/ci.yml" in files
    assert ROOT / ".github/actions/supply-chain/action.yml" in files


@pytest.mark.unit
@pytest.mark.parametrize("path", action_files(), ids=lambda path: path.name)
def test_remote_actions_pin_commit_sha(path: Path) -> None:
    """Pin each remote action by a 40-hex SHA and name its tag in a comment.

    Args:
        path: The workflow or action file under test.
    """
    lines = raw_uses(path)
    parsed = sorted(parsed_uses(yaml.safe_load(path.read_text())))
    assert sorted(value for value, _ in lines) == parsed
    unpinned = [
        f"{value} {comment}".strip()
        for value, comment in lines
        if not value.startswith("./")
        and not (PINNED.match(value) and VERSION_COMMENT.match(comment))
    ]
    assert unpinned == []
