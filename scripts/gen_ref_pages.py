"""Generate source reference and repository pages for the local MkDocs build.

Examples:
    Run ``uv run mkdocs build --strict`` from the checkout root.

See Also:
    - [judgevet][]: Public root exports.
"""

from pathlib import Path

import mkdocs_gen_files

ROOT = Path.cwd()

for name in ("README.md", "SECURITY.md", "STATUS.md", "CLAUDE.md", "AGENTS.md"):
    with mkdocs_gen_files.open(f"project/{name}", "w") as page:
        page.write((ROOT / name).read_text())

entries = []
for source in sorted((ROOT / "src/judgevet").rglob("*.py")):
    parts = list(source.relative_to(ROOT / "src").with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    module = ".".join(parts)
    destination = f"reference/python/{module}.md"
    with mkdocs_gen_files.open(destination, "w") as page:
        page.write(
            f"---\nstatus: draft\n---\n\n# {module}\n\nStatus: **draft**.\n\n::: {module}\n"
        )
    entries.append(f"- [{module}]({module}.md)\n")

with mkdocs_gen_files.open("reference/python/index.md", "w") as page:
    page.write(
        "---\nstatus: draft\n---\n\n# Python source reference\n\nStatus: **draft**.\n\n"
    )
    page.write(
        "Use the [supported imports](../compatibility.md) for public contracts.\n"
    )
    page.write("Internal modules are included to resolve source cross-references.\n\n")
    page.writelines(entries)
