---
status: draft
---

# Build and check documentation

Status: **draft**.

From a clean checkout with Python 3.12 or newer and uv installed:

```bash
uv sync --locked --dev
uv run mkdocs build --strict
```

The build writes `site/`, which Git ignores. It does not deploy anything.
Preview it locally with `uv run mkdocs serve`. The lockfile fixes the tooling
versions. Documentation dependencies belong to the development group; normal
library installations do not install them.

The strict build checks authored local links and Markdown fragments before
rendering. It then resolves generated Python cross-references and checks every rendered
HTML destination and fragment, including root-relative navigation.
It covers README, SECURITY, STATUS, repository guidance and all docs pages.
External URLs are not fetched, so ordinary checks need no API key or service.
Installing dependencies can require the package index.

Run just the repository link check with:

```bash
uv run python scripts/check_doc_links.py
```

The link parser recognizes inline/reference links, images and HTML anchors.
It ignores fenced code literals. Fragment IDs follow the site's Markdown TOC
extension. Findings identify the source file and offending destination.

The site copies repository entry pages into a generated `project/` section.
Repository source links point to GitHub after their local targets are checked.
Python reference pages are generated from the current source; internal module
pages exist to resolve source links, not to promise public compatibility.
Use [supported imports](../reference/compatibility.md) for that contract.

Add reader-facing pages to `mkdocs.yml` and the [documentation map](../index.md).
Keep their draft metadata and visible evidence limits. Missing symbols, files
and anchors must be fixed; do not lower validation severity to pass a build.
The build runs in commit/push hooks and CI. Example execution is a separate
check; rendering a code block does not prove it works.

Implementation follows the [MkDocs configuration reference](https://www.mkdocs.org/user-guide/configuration/)
and [mkdocstrings source-reference recipe](https://mkdocstrings.github.io/recipes/).

## Classify documentation examples

Run the inventory check with:

```bash
uv run python -m scripts.doc_example_inventory
```

It scans every fenced block in README and authored user docs. Backtick and
tilde fences are supported. Maintainer procedures and generated source
reference are outside this user-example inventory; they remain covered by
link/build checks and their dedicated release checks.

[scripts/doc_examples.json](../../scripts/doc_examples.json) records each page's
blocks in source order. Every record states its language, classification and
reason. `runnable` means a complete program, command or input; `continuation`
needs a prior saved file or setup; `template` needs substitution or surrounding
structure; `output` illustrates what a program prints. Classification does not
mean execution has passed. Setup commands require separate disposable-environment
verification; credential and host-configuration commands must never be executed
by a generic shell runner.

Add or update records when fences change. New pages, added/removed blocks,
changed languages, missing reasons, unclosed fences and an empty inventory fail
with page/block diagnostics. The checker preserves exact body text for subsequent
execution; it does not substitute a simpler example. It does not yet detect
behavioral drift inside a same-language block. The isolated execution, schema
and artifact checks are the remaining work in #153.
