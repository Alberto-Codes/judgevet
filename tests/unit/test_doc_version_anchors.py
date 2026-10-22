"""Prove no unmarked documentation line anchors judgevet to a stale version.

release-please rewrites versions only between its start and end markers.
Every judgevet version pin or prose anchor outside such a
block must therefore name the current ``judgevet.__version__``, or it goes
stale on the next release. Marked pages must appear in the release updater's
extra-files list. Only standalone marker comments delimit a version block.

Examples:
    ```python
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    assert (repo_root / "docs").is_dir()
    ```

See Also:
    - [judgevet][]: Package whose version unmarked anchors must equal.
"""

import json
import re
from pathlib import Path

import pytest

import judgevet

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
START_MARKER = "x-release-please-start-version"
END_MARKER = "x-release-please-end"
ANCHOR = re.compile(
    r"\bjudgevet(?:\[mcp\])?`?(?:==|>=|[ \t]+v?)(\d+\.\d+\.\d+(?:-[\w.]+)?)",
)


def _is_marker(line: str, marker: str) -> bool:
    """Check whether a whole line is a release marker comment.

    Args:
        line: Markdown line to inspect.
        marker: Release marker name.

    Returns:
        Whether the comment occupies the whole line, allowing whitespace.
    """
    return re.fullmatch(rf"\s*<!--\s*{re.escape(marker)}\s*-->\s*", line) is not None


def _scanned_pages(root: Path) -> list[Path]:
    """List the Markdown pages the guard covers.

    Args:
        root: Repository root containing ``docs/``, ``README.md`` and
            ``SECURITY.md``.

    Returns:
        Every Markdown page under ``docs/`` except ``docs/project/`` and
        ``docs/history/``, followed by ``README.md`` and ``SECURITY.md``.
        Both excluded trees hold historical records whose versions must not
        change: generated project copies and frozen snapshots.
    """
    excluded = (root / "docs" / "project", root / "docs" / "history")
    pages = [
        page
        for page in sorted((root / "docs").rglob("*.md"))
        if not any(tree in page.parents for tree in excluded)
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
        if _is_marker(line, START_MARKER):
            assert not inside, f"{label}:{number}: nested start marker"
            inside = True
        elif _is_marker(line, END_MARKER):
            assert inside, f"{label}:{number}: end marker without start"
            inside = False
        elif not inside:
            kept.append((number, line))
    assert not inside, f"{label}: start marker never closes"
    return kept


def _stale_anchors(root: Path, current: str) -> list[str]:
    """Find stale anchors and marked pages absent from release configuration.

    Args:
        root: Repository root to scan.
        current: Version every unmarked anchor must equal.

    Returns:
        Diagnostics for stale unmarked anchors and unregistered marked pages.
    """
    config = json.loads((root / "release-please-config.json").read_text())
    extra_files = {
        entry if isinstance(entry, str) else entry["path"]
        for entry in config["packages"]["."]["extra-files"]
    }
    offenders: list[str] = []
    for page in _scanned_pages(root):
        label = page.relative_to(root).as_posix()
        text = page.read_text(encoding="utf-8")
        if label not in extra_files and any(
            _is_marker(line, START_MARKER) for line in text.splitlines()
        ):
            offenders.append(
                f"{label}: marked page missing from release-please extra-files"
            )
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


def test_guard_skips_frozen_history_but_scans_current_pages(tmp_path: Path) -> None:
    """Prove a frozen snapshot keeps its old versions while live pages are checked."""
    (tmp_path / "docs" / "history").mkdir(parents=True)
    (tmp_path / "docs" / "how-to").mkdir(parents=True)
    (tmp_path / "docs" / "history" / "status.md").write_text(
        "judgevet 0.1.0 is published.\n", encoding="utf-8"
    )
    (tmp_path / "docs" / "how-to" / "install.md").write_text(
        "pip install 'judgevet==0.1.0'\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text("judgevet 9.9.9\n", encoding="utf-8")
    (tmp_path / "SECURITY.md").write_text("No anchor.\n", encoding="utf-8")
    (tmp_path / "release-please-config.json").write_text(
        json.dumps({"packages": {".": {"extra-files": []}}}), encoding="utf-8"
    )

    offenders = _stale_anchors(tmp_path, "9.9.9")

    assert offenders == ["docs/how-to/install.md:1: pip install 'judgevet==0.1.0'"]


@pytest.mark.parametrize(
    "anchor",
    ["judgevet  0.1.0", "`judgevet` 0.1.0", "judgevet v0.1.0", "judgevet>=0.1.0"],
)
def test_guard_recognizes_additional_version_spellings(anchor: str) -> None:
    assert ANCHOR.findall(anchor) == ["0.1.0"]


@pytest.mark.parametrize("registered", [False, True])
def test_marked_page_requires_release_registration(
    tmp_path: Path, registered: bool
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("No anchor.\n", encoding="utf-8")
    (tmp_path / "SECURITY.md").write_text("No anchor.\n", encoding="utf-8")
    page = tmp_path / "docs" / "example.md"
    page.write_text(
        f"<!-- {START_MARKER} -->\njudgevet==0.1.0\n<!-- {END_MARKER} -->\n",
        encoding="utf-8",
    )
    entries = ["docs/example.md"] if registered else []
    (tmp_path / "release-please-config.json").write_text(
        json.dumps({"packages": {".": {"extra-files": entries}}}), encoding="utf-8"
    )

    offenders = _stale_anchors(tmp_path, "9.9.9")

    assert offenders == (
        []
        if registered
        else ["docs/example.md: marked page missing from release-please extra-files"]
    )


def test_prose_marker_mentions_do_not_hide_unmarked_anchor() -> None:
    text = (
        f"The marker is `<!-- {START_MARKER} -->`.\n"
        "judgevet==0.1.0\n"
        f"The closing marker is `<!-- {END_MARKER} -->`.\n"
    )

    assert _unmarked_lines(text, "example.md") == list(
        enumerate(text.splitlines(), start=1)
    )


def test_prose_end_marker_does_not_terminate_marked_block() -> None:
    text = (
        f"<!-- {START_MARKER} -->\n"
        f"The closing marker is `<!-- {END_MARKER} -->`.\n"
        "judgevet==0.1.0\n"
        f"<!-- {END_MARKER} -->\n"
    )

    assert _unmarked_lines(text, "example.md") == []


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (f"<!-- {START_MARKER} -->\n", "start marker never closes"),
        (f"<!-- {END_MARKER} -->\n", "end marker without start"),
        (
            f"<!-- {START_MARKER} -->\n<!-- {START_MARKER} -->\n",
            "nested start marker",
        ),
    ],
)
def test_guard_rejects_malformed_marker_blocks(text: str, message: str) -> None:
    with pytest.raises(AssertionError, match=message):
        _unmarked_lines(text, "example.md")
