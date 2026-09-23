"""Check source links and adapt repository-relative links for the built site.

Examples:
    Run ``uv run mkdocs build --strict`` from the checkout root.

See Also:
    - [judgevet][]: Documented package.
"""

import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page

ROOT = Path(__file__).resolve().parents[1]


def on_page_markdown(
    markdown: str, page: Page, config: MkDocsConfig, files: Files
) -> str:
    """Map repository links to site pages or source browsing URLs.

    Args:
        markdown: Page Markdown before rendering.
        page: Current page.
        config: Site configuration.
        files: Site inventory.

    Returns:
        Markdown with repository-relative links adapted for the site.
    """
    uri = Path(page.file.src_uri)
    source = ROOT / (uri.name if uri.parts[0] == "project" else Path("docs") / uri)

    def replace(match: re.Match[str]) -> str:
        url = urlsplit(match[1])
        if url.scheme or url.netloc or not url.path:
            return match[0]
        target = (source.parent / url.path).resolve()
        suffix = f"#{url.fragment}" if url.fragment else ""
        if target.is_relative_to(ROOT / "docs"):
            site_target = target.relative_to(ROOT / "docs")
        elif target.parent == ROOT and target.suffix == ".md":
            site_target = Path("project") / target.name
        elif target.is_relative_to(ROOT):
            return f"](https://github.com/Alberto-Codes/judgevet/blob/main/{target.relative_to(ROOT)}{suffix})"
        else:
            return match[0]
        return f"]({os.path.relpath(site_target, uri.parent)}{suffix})"

    return re.sub(r"\]\(([^)]+)\)", replace, markdown)
