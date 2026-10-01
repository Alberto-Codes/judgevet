"""Check that the documentation index links every page the site nav lists.

The `mkdocs.yml` nav and `docs/index.md` are two maps of the same pages.
This test fails when a nav page that exists under `docs/` has no link from
the index. Generated pages, such as `project/*` and `reference/python/*`,
have no file under `docs/` and are skipped.

Examples:
    Run the check on its own:

    ```bash
    uv run pytest -q tests/unit/test_doc_nav_coverage.py
    ```

See Also:
    [scripts.check_doc_links][]: The link checker for documentation pages.
"""

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
LINK_TARGET = re.compile(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)")


def _walk_nav(node: object) -> Iterator[str]:
    """Yield every page path in a nested mkdocs nav structure.

    Args:
        node: A nav list, a mapping of titles to entries, or a page path.

    Yields:
        Each page path string, in nav order.
    """
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for item in node:
            yield from _walk_nav(item)
    elif isinstance(node, dict):
        for value in node.values():
            yield from _walk_nav(value)


def nav_pages(config: Path) -> list[str]:
    """Return nav page paths that exist as files under `docs/`.

    Args:
        config: The path to `mkdocs.yml`.

    Returns:
        The nav paths with a file under `docs/`, excluding `index.md`.

    Raises:
        KeyError: If the config has no `nav` key.
    """
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    pages = _walk_nav(data["nav"])
    return [p for p in pages if p != "index.md" and (DOCS / p).is_file()]


def linked_pages(index: Path) -> set[str]:
    """Return the page paths an index page links, relative to its directory.

    Args:
        index: The Markdown page to scan.

    Returns:
        Normalised link targets ending in `.md`, without fragments.
    """
    text = index.read_text(encoding="utf-8")
    return {Path(target).as_posix() for target in LINK_TARGET.findall(text)}


@pytest.mark.unit
def test_index_links_every_nav_page() -> None:
    """Fail with the list of nav pages that `docs/index.md` does not link."""
    pages = nav_pages(ROOT / "mkdocs.yml")
    assert pages, "the nav yielded no pages under docs/"
    links = linked_pages(DOCS / "index.md")
    missing = [page for page in pages if page not in links]
    assert missing == [], f"docs/index.md omits nav pages: {missing}"
