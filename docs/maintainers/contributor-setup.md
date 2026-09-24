---
status: draft
---

# Set up a contributor checkout

Status: **draft**.

This route prepares the full test and gate environment without a TypeSafe key.
It does not call the live service. Read the [repository rules](../../AGENTS.md)
before changing files. Package consumers should use [installation](../how-to/install.md).

## Prerequisites

Install Git, Bash, [uv](https://docs.astral.sh/uv/getting-started/installation/),
and Node.js with npm. The release-configuration gate runs Node's test runner
and installs its locked npm dependencies. It is part of ordinary verification.
Python must be 3.12 or newer; uv can provision a suitable interpreter.
CI currently uses uv 0.11.20. Use that version to reproduce its audit command.

Initial setup needs network access to download dependencies and hook tools.
The dependency audit also contacts public advisory services. None of these
steps needs a TypeSafe account, API key, direnv or a configured MCP host.
The [pre-commit Go hook support](https://pre-commit.com/#golang) bootstraps a
Go toolchain when needed for actionlint. A missing tool or failed download
is a setup failure to fix, not a reason to skip its gate.

The commands below use Bash. Windows users can use a suitable Bash environment;
Windows and ChromeOS Linux walkthroughs remain [unverified](https://github.com/Alberto-Codes/judgevet/issues/167).
Do not interpret a Linux walkthrough as evidence for those platforms.

## Clone and install hooks first

From a directory where you want the checkout:

```bash
git clone https://github.com/Alberto-Codes/judgevet.git
cd judgevet
uv run --locked --extra mcp pre-commit install --install-hooks -t pre-commit -t pre-push -t commit-msg
```

The first project command installs all three hooks and their environments.
`uv run` first resolves the locked development environment, so no separate
pre-commit installation is needed. Authorized maintainers land finished work
directly on `main`; these hooks guard that path. Never bypass them.
The commit-message gate also checks the configured author allowlist. Successful
setup does not grant permission to commit or publish as someone else.

Confirm synchronization and command availability:

```bash
uv sync --locked --extra mcp
uv run judgevet --help
```

The default development group supplies test, lint, type and documentation tools.
The MCP extra enables the complete contributor test suite. It remains optional
for library and CLI consumers. Omitting it can skip MCP tests; a smaller test
count does not prove the full suite passed. No key is needed for CLI help.

## Run the gates

Run both stages over the complete checkout before declaring it ready:

```bash
uv run pre-commit run --all-files
uv run pre-commit run --all-files --hook-stage pre-push
```

Both commands must exit zero. The push stage checks coverage, all-file docstrings,
isolated examples and the dependency audit. These commands do not commit or
push. Hook definitions in [.pre-commit-config.yaml](../../.pre-commit-config.yaml)
are authoritative for the complete gate set.

For focused diagnosis, the core commands are:

| Gate | Command |
|---|---|
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format --check .` |
| Types | `uv run ty check` |
| Architecture | `uv run lint-imports` |
| Changed docstrings | `uv run docvet check` |
| All docstrings | `uv run docvet check --all` |
| Tests and coverage | `uv run pytest -q --cov` |
| Suppressions | `uv run python scripts/check_suppressions.py` |
| Documentation | `uv run mkdocs build --strict` |

`[tool.ty.src] include` in `pyproject.toml` pins ty's checked roots to `src`,
`tests` and `scripts`.

The stage commands also check lock consistency, YAML, workflows, dependency
constraints, test hygiene, registry metadata, release configuration, example
inventory, prose and terminology. Focused checks do not replace full stages.
The coverage floor is 90%. [STATUS](../../STATUS.md#gates) records measured
counts and coverage rather than a permanent expected count.

## Select tests deliberately

`uv run pytest -q` selects the default suite. Project `addopts` excludes `live`.
It includes unmarked tests as well as the marked unit and contract tests.

- `uv run pytest -q -m unit` selects isolated unit tests.
- `uv run pytest -q -m contract` selects shared adapter contract tests.
- `uv run pytest -q -m live` explicitly selects service calls and can incur cost.

A contract test exercises a fake port and the real adapter against the same
fixtures. It checks that their outcomes agree. Synthetic HTTP fixtures are
not live service evidence. Neither focused selection replaces the default suite.

Live tests require an explicitly supplied `TYPESAFE_API_KEY` and service access.
Keep them out of ordinary setup. The separate
[probe script](../../scripts/probe_live.py) makes a paid call and prints the
response for manual comparison; it asserts nothing. It is not a gate.
Read the [evidence limits](../explanation/verification.md) before promoting claims.

## Recover without weakening checks

Read the first failing command and its diagnostic. Install a missing prerequisite
or repair the reported source, configuration or documentation. Then rerun that
check and both complete stages. Do not add suppressions, skip hooks, lower
coverage or narrow checks to obtain a green result.

A stale lockfile needs investigation. Do not regenerate it merely to conceal
an unintended dependency change. A missing API key during the default suite
is a regression or an accidentally selected live command, not a setup prerequisite.
Keep credentials out of logs and issue reports.

Each separate checkout or worktree needs its own environment. Run hook installation
and locked synchronization there too. Preserve unrelated files and local changes.
For deeper tasks, use [documentation building](build-docs.md),
[package verification](verify-package.md), or the [release procedure](cut-a-release.md).
Release publication has separate authorization and live verification requirements.
