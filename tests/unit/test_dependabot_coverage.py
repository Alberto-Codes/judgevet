"""Require Dependabot's github-actions entry to scan every remote action pin.

GitHub's options reference states the scan rules this test models:
https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference

- "For GitHub Actions, use the value `/`. Dependabot will search the
  `/.github/workflows` directory, as well as the `action.yml/action.yaml`
  file from the root directory."
- "The `directories` key supports globbing and the wildcard character `*`.
  These features are not supported by the `directory` key."
"""

import re
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".github/dependabot.yml"
USES_LINE = re.compile(r"^\s*(?:-\s+)?uses:\s*([^\s#]+)")


def configured_directories() -> list[str]:
    """Return the github-actions entry's `directories`, or its `directory`.

    Returns:
        The configured directory patterns, each rooted at `/`.
    """
    config = yaml.safe_load(CONFIG.read_text())
    (entry,) = [
        update
        for update in config["updates"]
        if update["package-ecosystem"] == "github-actions"
    ]
    if "directories" in entry:
        return list(entry["directories"])
    return [entry["directory"]]


def scanned_by(pattern: str, directory: str) -> bool:
    """Decide whether one configured pattern makes Dependabot scan a directory.

    `/` scans `/.github/workflows` and the root. Any other pattern matches
    one path segment per segment, since `*` is a single-segment wildcard.

    Args:
        pattern: A configured `directory` value or `directories` item.
        directory: A repository directory, rooted at `/`.

    Returns:
        True when Dependabot scans `directory` for that pattern.
    """
    if pattern == "/" and directory in ("/", "/.github/workflows"):
        return True
    want = PurePosixPath(pattern).parts
    have = PurePosixPath(directory).parts
    return len(want) == len(have) and all(
        fnmatchcase(part, glob) for part, glob in zip(have, want, strict=True)
    )


def has_remote_uses(path: Path) -> bool:
    """Report whether a YAML file holds a `uses:` line naming a remote action.

    Args:
        path: The workflow or action file to read.

    Returns:
        True when some `uses:` value is neither local (`./`) nor `docker://`.
    """
    return any(
        not match.group(1).startswith(("./", "docker://"))
        for line in path.read_text().splitlines()
        if (match := USES_LINE.match(line))
    )


def pinned_directories() -> list[str]:
    """List every directory under .github that holds a remote `uses:` line.

    Returns:
        The sorted directories, rooted at `/`.
    """
    github = ROOT / ".github"
    return sorted(
        {
            "/" + path.parent.relative_to(ROOT).as_posix()
            for pattern in ("*.yml", "*.yaml")
            for path in github.rglob(pattern)
            if has_remote_uses(path)
        }
    )


@pytest.mark.unit
def test_pinned_directories_found() -> None:
    """Fail loudly if the scan finds nothing, which would pass vacuously."""
    found = pinned_directories()
    assert "/.github/workflows" in found
    assert "/.github/actions/supply-chain" in found


@pytest.mark.unit
@pytest.mark.parametrize(
    ("pattern", "directory", "expected"),
    [
        ("/", "/.github/workflows", True),
        ("/", "/", True),
        ("/", "/.github/actions/supply-chain", False),
        ("/.github/actions/*", "/.github/actions/supply-chain", True),
        ("/.github/actions/*", "/.github/actions/a/b", False),
        ("/.github/actions/*", "/.github/workflows", False),
        ("/.github/actions/supply-chain", "/.github/actions/supply-chain", True),
    ],
)
def test_scanned_by_models_the_documented_rules(
    pattern: str, directory: str, expected: bool
) -> None:
    """Match `/` specially and every other pattern one segment at a time.

    Args:
        pattern: A configured directory pattern.
        directory: The candidate directory.
        expected: Whether Dependabot scans it.
    """
    assert scanned_by(pattern, directory) is expected


@pytest.mark.unit
def test_github_actions_entry_scans_every_pin() -> None:
    """Cover each directory that holds a remote action pin."""
    patterns = configured_directories()
    uncovered = [
        directory
        for directory in pinned_directories()
        if not any(scanned_by(pattern, directory) for pattern in patterns)
    ]
    assert uncovered == []
