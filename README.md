# judgevet

Typed client, CLI and MCP server for TypeSafe's **Jev** (System One) judgment
model.

## Status: sketch

**No call has been made against the live API.** Every field name, endpoint and
response shape here is inferred from published documentation, not observed.
Treat the domain model as a hypothesis until a `live`-marked test passes with a
real `TYPESAFE_API_KEY`.

## What Jev is

Jev is not a chat model and not a coding model. You send it a piece of state
and a set of *typed questions*, and it returns one answer per question with a
calibrated probability:

| question | answer |
|---|---|
| `Noul` | yes/no, with a probability |
| `Choice` | one option from a set you defined, with per-option probabilities |
| `Score` | a position on a scale you defined, with a legend |

Every answer carries a confidence. That makes it a decision primitive your code
can branch on, sort by, and route with — a smart `if` rather than a paragraph.

## Why this client exists

Several MCP servers for Jev appeared within days of its launch, all
MCP-only. An MCP server cannot be called from a script, a pre-commit hook, or
CI without standing up a client first.

Here the **library is the artifact**. The CLI and the MCP server are two
inbound adapters over one contract-tested core:

```
domain/              question and answer types, calibrated probabilities  — pure
ports/               protocols the domain calls out through
adapters/outbound/   HTTP to the Jev API
adapters/inbound/    cli.py   — scripts, hooks, CI
                     mcp.py   — agents
```

`import-linter` enforces that map, and keeps the optional MCP runtime out of
everything but its own adapter.

## Use

```bash
uv sync
uv run jev --help
```

The MCP server is an optional extra, so the library and CLI install without an
MCP runtime:

```bash
uv sync --extra mcp
```

## Gates

```bash
uv run ruff check . && uv run ruff format --check .
uv run ty check
uv run lint-imports
uv run docvet check
uv run pytest -q --cov
```

Coverage floor is 90%. `live`-marked tests touch the real API and are excluded
by default.

## Sister projects

Shares the toolchain and hex layout used by
[automarket](https://github.com/Alberto-Codes/automarket),
[vramfit](https://github.com/Alberto-Codes/vramfit) and
[docvet](https://github.com/Alberto-Codes/docvet).
