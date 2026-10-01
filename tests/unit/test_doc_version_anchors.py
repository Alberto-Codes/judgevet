"""Prove no unmarked documentation line anchors judgevet to a stale version.

release-please rewrites versions only between its start and end markers.
Every ``judgevet==X.Y.Z`` pin or ``judgevet X.Y.Z`` anchor outside such a
block must therefore name the current ``judgevet.__version__``, or it goes
stale on the next release.

Examples:
    ```python
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    assert (repo_root / "docs").is_dir()
    ```

See Also:
    - [judgevet][]: Package whose version unmarked anchors must equal.
"""

import re
from pathlib import Path

import pytest

import judgevet

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
START_MARKER = "x-release-please-start-version"
END_MARKER = "x-release-please-end"
ANCHOR = re.compile(
    r"\bjudgevet(?:\[mcp\])?(?:==| )(\d+\.\d+\.\d+(?:-[\w.]+)?)",
)


def _scanned_pages(root: Path) -> list[Path]:
    """List the Markdown pages the guard covers.

    Args:
        root: Repository root containing ``docs/``, ``README.md`` and
            ``SECURITY.md``.

    Returns:
        Every Markdown page under ``docs/`` except ``docs/project/``, followed
        by ``README.md`` and ``SECURITY.md``.
    """
    project = root / "docs" / "project"
    pages = [
        page
        for page in sorted((root / "docs").rglob("*.md"))
        if project not in page.parents
    ]
    return [*pages, root / "README.md", root / "SECURITY.md"]


def _unmarked_lines(text: str, label: str) -> list[tuple[int, str]]:
    """Return the numbered lines outside release-please marked blocks.

    Args:
        text: Page content.
        label: Page name used in failure messages.

    Returns:
        Pairs of one-based line number and line text, excluding marker lines
        and every line between a start marker and its end marker.

    Raises:
        AssertionError: If markers nest, an end marker has no start, or a
            start marker never closes.
    """
    kept: list[tuple[int, str]] = []
    inside = False
    for number, line in enumerate(text.splitlines(), start=1):
        if START_MARKER in line:
            assert not inside, f"{label}:{number}: nested start marker"
            inside = True
        elif END_MARKER in line:
            assert inside, f"{label}:{number}: end marker without start"
            inside = False
        elif not inside:
            kept.append((number, line))
    assert not inside, f"{label}: start marker never closes"
    return kept


def _stale_anchors(root: Path, current: str) -> list[str]:
    """Find unmarked version anchors that differ from the current version.

    Args:
        root: Repository root to scan.
        current: Version every unmarked anchor must equal.

    Returns:
        One ``path:line: text`` entry per offending line.
    """
    offenders: list[str] = []
    for page in _scanned_pages(root):
        label = page.relative_to(root).as_posix()
        text = page.read_text(encoding="utf-8")
        for number, line in _unmarked_lines(text, label):
            versions = ANCHOR.findall(line)
            if any(version != current for version in versions):
                offenders.append(f"{label}:{number}: {line.strip()}")
    return offenders


def test_unmarked_version_anchors_match_package_version() -> None:
    """Require every unmarked judgevet pin or anchor to equal __version__."""
    offenders = _stale_anchors(REPO_ROOT, judgevet.__version__)

    assert offenders == [], (
        f"Unmarked judgevet version anchors differ from "
        f"{judgevet.__version__}:\n" + "\n".join(offenders)
    )


def test_guard_skips_marked_blocks_and_flags_unmarked_pins() -> None:
    """Prove the scanner ignores marked blocks and reports unmarked pins."""
    text = (
        "Install judgevet 0.1.0 here.\n"
        f"<!-- {START_MARKER} -->\n"
        "pip install 'judgevet==0.2.0'\n"
        f"<!-- {END_MARKER} -->\n"
        "pip install 'judgevet[mcp]==0.3.0'\n"
    )
    lines = _unmarked_lines(text, "sample.md")
    flagged = [number for number, line in lines if ANCHOR.search(line)]

    assert flagged == [1, 5]
