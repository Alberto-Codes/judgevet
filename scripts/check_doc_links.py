"""Validate repository Markdown destinations and anchors without network access.

Examples:
    Run ``uv run python scripts/check_doc_links.py`` from the checkout root.

See Also:
    - [judgevet][]: Library documented by these pages.
"""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import markdown
from mkdocs.config.defaults import MkDocsConfig

REPOSITORY_URL = "https://github.com/Alberto-Codes/judgevet/blob/main/"


class Links(HTMLParser):
    """Collect rendered destinations and explicit or generated anchors.

    Attributes:
        targets: Link and image destinations in document order.
        anchors: Element identifiers and legacy named anchors.
    """

    def __init__(self) -> None:
        """Initialize empty collections."""
        super().__init__()
        self.targets: list[str] = []
        self.anchors: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect relevant attributes from one rendered element.

        Args:
            tag: HTML element name.
            attrs: Parsed attributes.
        """
        values = dict(attrs)
        identifier = values.get("id") or (values.get("name") if tag == "a" else None)
        if identifier:
            self.anchors.add(identifier)
        target = values.get("href") if tag == "a" else values.get("src")
        if target:
            self.targets.append(target)


def parse_page(path: Path) -> Links:
    """Render Markdown with the site's heading and block extensions.

    Args:
        path: Markdown file to read.

    Returns:
        Parsed links and anchors, excluding code literals.
    """
    parser = Links()
    parser.feed(
        markdown.markdown(
            path.read_text(), extensions=["meta", "fenced_code", "tables", "toc"]
        )
    )
    return parser


def check_links(pages: list[Path], repository_root: Path | None = None) -> list[str]:
    """Check local destinations and Markdown fragments for every supplied page.

    Args:
        pages: Source Markdown pages.
        repository_root: Checkout for absolute repository URLs; defaults to this script's root.

    Returns:
        Actionable source/target findings. External URLs are not fetched.
    """
    findings = []
    root = repository_root or Path(__file__).resolve().parents[1]
    parsed = {page.resolve(): parse_page(page) for page in pages}
    for page in pages:
        for target in parsed[page.resolve()].targets:
            base = page.parent
            if target.startswith(REPOSITORY_URL):
                url = urlsplit(target[len(REPOSITORY_URL) :])
                base = root
            else:
                url = urlsplit(target)
                if url.scheme or url.netloc:
                    continue
            destination = (
                (base / unquote(url.path)).resolve() if url.path else page.resolve()
            )
            if not destination.is_file():
                findings.append(f"{page}: missing target {target}")
            elif url.fragment and destination.suffix == ".md":
                if destination not in parsed:
                    parsed[destination] = parse_page(destination)
                if unquote(url.fragment) not in parsed[destination].anchors:
                    findings.append(f"{page}: missing anchor {target}")
    return findings


def documentation_pages(root: Path) -> list[Path]:
    """List authored documentation and repository entry pages.

    Args:
        root: Checkout root.

    Returns:
        Complete documentation integrity scope.
    """
    names = ("README.md", "SECURITY.md", "STATUS.md", "CLAUDE.md", "AGENTS.md")
    return [*(root / name for name in names), *sorted((root / "docs").rglob("*.md"))]


def main() -> int:
    """Check the checkout documentation.

    Returns:
        One on any broken local destination or anchor, otherwise zero.
    """
    findings = check_links(documentation_pages(Path.cwd()))
    for finding in findings:
        print(finding)
    if not findings:
        print("Documentation links and anchors passed")
    return int(bool(findings))


def check_site(root: Path, site_path: str = "/") -> list[str]:
    """Check final HTML URLs, including root-relative navigation.

    Args:
        root: Built site directory.
        site_path: URL path beneath which the site is published.

    Returns:
        Missing file or fragment findings from rendered HTML.
    """
    root = root.resolve()
    pages = {}
    for path in root.rglob("*.html"):
        parser = Links()
        parser.feed(path.read_text())
        pages[path] = parser
    findings = []
    for path, page in pages.items():
        for target in page.targets:
            url = urlsplit(target)
            if url.scheme or url.netloc:
                continue
            base = root if url.path.startswith("/") else path.parent
            local_path = unquote(url.path)
            prefix = "/" + site_path.strip("/")
            if prefix != "/" and local_path.startswith(prefix + "/"):
                local_path = local_path[len(prefix) :]
            destination = (
                (base / local_path.lstrip("/")).resolve() if url.path else path
            )
            if destination.is_dir():
                destination /= "index.html"
            if not destination.is_file():
                findings.append(f"{path}: missing rendered target {target}")
            elif (
                url.fragment
                and destination in pages
                and unquote(url.fragment) not in pages[destination].anchors
            ):
                findings.append(f"{path}: missing rendered anchor {target}")
    return findings


def on_post_build(config: MkDocsConfig) -> None:
    """Reject broken final HTML links after source-reference rendering.

    Args:
        config: Configuration with the output directory.

    Raises:
        ValueError: If any rendered local link is broken.
    """
    findings = check_site(Path(config.site_dir), urlsplit(config.site_url or "").path)
    if findings:
        raise ValueError("\n".join(findings))


def on_pre_build(config: object) -> None:
    """Reject invalid source links when MkDocs starts a build.

    Args:
        config: MkDocs configuration, unused by the source check.

    Raises:
        ValueError: If any authored local link is broken.
    """
    root = Path(__file__).resolve().parents[1]
    findings = check_links(documentation_pages(root))
    if findings:
        raise ValueError("\n".join(findings))


if __name__ == "__main__":
    sys.exit(main())
