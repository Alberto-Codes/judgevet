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
Absolute GitHub `blob/main` URLs for this repository resolve against the checkout,
including their fragments. Published URLs beneath the judgevet Pages site map
to authored pages and section indexes in `docs/`, including their fragments.
This keeps README links usable on PyPI and checked offline. Other external URLs are not fetched, so checks need no API key or service.
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
execution; it does not substitute a simpler example. Behavioral checks are separate from this classification check.

## Execute Python and CLI examples

```bash
uv run python -m scripts.check_doc_python
```

This builds into a fresh temporary directory and installs that exact wheel into
a new environment. It proves import isolation and executes all 15 current
Python blocks from README/user docs without rewriting them. It reuses the release
helpers and Python extractor, and verifies extraction matches the inventory's
exact text. The base install has no optional MCP dependency. A final typing pass
checks each extracted file against that interpreter.

Execution supplies synthetic credentials and HTTP answers, blocks socket
connections/name resolution, and checks HTTP client cleanup. It does not inherit
caller environment secrets. Programs retain their assertions; failures identify
the source page and opening-fence line. Output is captured to keep example
prints and arbitrary exception text out of gate diagnostics. This is a test
harness for trusted repository examples, not a sandbox for untrusted code.
Dependency installation may use package indexes; example execution is offline.

The command runs on push and in CI. It verifies Python wiring, not live-service
behavior or judgment quality. Existing opt-in release smoke checks retain their
separate live purpose. The same isolated gate also executes five exact shell blocks from the
CLI files and CLI policy guides. It supplies the documented JSON files and
validates them through the installed decoders. Bash commands use a loopback
HTTP fixture and synthetic credentials; no inherited key, proxy or user
configuration is passed. It checks JSON answers, separate streams, file creation,
policy pass/unmet/service-failure outcomes, and redirected automation output.
An invalid documented option fails the check. The shared subprocess helper
retains release-runner behavior; CLI examples have a 60-second deadline.

The explicit workflow selection is in `scripts/doc_cli_prepare.py`. The same
check runs both tutorial shell continuations against their exact saved Python
programs. It compares policy tutorial output literally and judgment output with
synthetic fixture values. A temporary startup helper routes tutorial HTTPX
clients to loopback. The staged-review continuation uses the three checkout
example files in a temporary Git repository and checks clean, met and unmet
outcomes. A wrong tutorial filename fails with its source page and fence line.

Installation commands require separate disposable-environment verification.
They may access package indexes and do not belong in the offline executor.
Use temporary virtual environments and uv cache/tool directories. Verify each
command's exit and output; a shell block without `set -e` can hide an earlier
failure. Follow the [repository rules](../../AGENTS.md) for development gates;
those checks do not need API credentials. Separate MCP startup checks may use
a dummy key and closed stdin. That verifies startup and shutdown, not host
connectivity. Credential acquisition and configured-host shell templates
remain unexecuted, with explicit inventory reasons.

The current 49-block scope is accounted for as follows:

| Blocks | Verification |
|---|---|
| 15 Python programs | Isolated execution and typing |
| 5 CLI shell workflows | Exact local inputs, output and exit checks |
| 3 shell continuations | Saved tutorial programs and staged Git cases |
| 8 JSON/TOML blocks | Decoder, discovery schema or contextual validation |
| 8 installation blocks | Separate disposable setup audit |
| 4 credential/host shell templates | Explicit substitution requirements; not executed |
| 4 container blocks | Separate source-wheel image build and synthetic runtime checks; published-wheel preparation remains a release check |
| 2 text outputs | Exact policy output; synthetic judgment output with live placeholders retained |

Repeat the setup audit when installation instructions or packaging changes.
Record commands and outcomes on the tracking issue. Routine gates do not prove
package-index availability, a user's credential setup or a configured host's
connection.


## Validate documented data and MCP arguments

```bash
uv run python -m scripts.check_doc_schemas
```

This separate check builds a fresh wheel and installs its MCP extra in another
isolated environment. It uses the installed server's discovered `ask_noul`
schema to validate the exact connection-guide arguments. It makes
no service call and does not launch or modify a user host.

All current JSON/TOML fences have explicit contracts. These cover question-file
validation, policy decoding, contextual rule fragments, illustrative report
consistency, MCP arguments and host-template structure.
The checker rejects new data blocks without a contract and stale selections.
Rule fragments remain fragments; wrapping them for validation does not turn
them into complete policy-file examples. The host template is parsed, not used
as proof of a live connection. JSON Schema validation comes from the optional
MCP runtime's dependency; the base Python/CLI gate remains independent of it.

Push hooks and the MCP-enabled CI job run this command. Schema failures report
the source page and fence line. Live behavior and judgment values remain outside
these offline checks.


The shared wheel builder requires a new or empty output directory before it
starts. It still requires exactly one resulting wheel. Reusing a directory with
an old wheel, source distribution or any other file fails before the builder
runs; existing files are preserved. This prevents a successful build command
that emits no artifact from silently selecting an old wheel. The documentation
commands allocate fresh temporary directories automatically.


## Deploy through GitHub Pages

The [documentation workflow](../../.github/workflows/docs.yml) builds main with
locked development dependencies and `mkdocs build --strict`. Its deployment job
requires the successful build artifact and uses the `github-pages` environment.
An explicit workflow dispatch also builds; only main may deploy.

Pages uses the Actions publishing source. Repository visibility is public and
this workflow does not change it. Deployment permission is limited to Pages and
an OIDC token; the build reads repository contents and Pages configuration.
Concurrent deployments are serialized without cancelling an active deployment.
The project-path site URL is set in `mkdocs.yml`.

After a deployment, inspect the live site in a browser. Check navigation,
project-path assets, diagrams and generated Python reference pages. A successful
artifact upload alone does not prove that those pages are live.
The workflow follows [GitHub's custom-workflow guidance](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
