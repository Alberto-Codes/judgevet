# CLAUDE.md

Guidance for coding agents in this repository. `AGENTS.md` is the same file.

## What this repo is

**judgevet** is a typed client for TypeSafe's Jev (System One) judgment
model, plus two inbound adapters over it: a CLI and an MCP server.

The **library is the artifact**. Jev answers typed questions with calibrated
probabilities, which makes it useful to scripts, pre-commit hooks and CI — not
only to agents. Every published Jev integration so far is MCP-only, and an MCP
server cannot be called from a shell script. Here MCP is one inbound adapter
beside the CLI, over one contract-tested core.

Conventions are inherited from the sister projects
[automarket](https://github.com/Alberto-Codes/automarket),
[vramfit](https://github.com/Alberto-Codes/vramfit) and
[docvet](https://github.com/Alberto-Codes/docvet).

## Trust levels

Docs pages carry `status: sketch | draft | stable`. Do not write code against a
`sketch` page without flagging it. Promote a page in the change that lands the
code proving it.

## Non-negotiables

- **The domain model is unverified.** No call has been made against the live
  Jev API. Every field name, endpoint and response shape is inferred from
  published documentation. `README.md` and `docs/reference/api.md` stay
  `sketch` until a `live`-marked test passes against the real API with a
  `TYPESAFE_API_KEY`. Promoting them before that is the one change this repo
  will not accept.
- **No API detail without a citation.** A field name, an endpoint or a status
  code carries the URL it came from, in the docstring or the docs page. An
  uncited detail is an invention.
- **Sources disagree, and that is reportable.** When two pages describe the
  response differently, record both and mark it an open question. Do not pick
  one silently.
- **The domain is pure.** No IO, no serialization, no HTTP, no CLI or server
  framework. `import-linter` enforces it.
- **MCP stays in its adapter.** `mcp` is an optional extra so the library and
  CLI install without an MCP runtime. An `import-linter` contract forbids it
  everywhere else. If that contract fails, the import is in the wrong layer —
  move the code, never weaken the contract.
- **Modules cap at 300 code lines, functions at 50.** Over the limit means
  decompose.
- **Never silence a gate.** Fix the cause. Do not add `per-file-ignores`,
  `# noqa`, `# type: ignore`, `--no-verify`, or a narrowed scope. If a type
  checker rejects a test double, the fix is a better double — a small class
  that satisfies the protocol — not a cast to `Any`.
- **Fixing one gate must not break another.** Run the whole table before you
  report. Adding a docstring to satisfy ruff `D` earns a docvet `enrichment`
  finding unless it carries the `Args:`, `Returns:`, `Raises:` and
  `Attributes:` sections the case needs.
- **Every new module needs its docstring sections on the first pass.** docvet
  fails on `enrichment`, so a module docstring needs an `Examples:` block with
  runnable code and a `See Also:` list of `[judgevet.module.path][]`
  cross-references. A class needs `Attributes:`, a function that returns needs
  `Returns:`, one that raises needs `Raises:`. Writing them afterwards has cost
  three extra sessions already.

## Architecture

Hexagonal, enforced by `import-linter`:

```
adapters/inbound/    cli.py (typer) · mcp.py (stdio server)
adapters/outbound/   http.py — the Jev API
ports/               SystemOnePort protocol
domain/              Noul · Choice · Score · their answers · Usage — pure
```

Both inbound adapters take a `SystemOnePort`. Neither constructs an HTTP client
itself. That is what makes the contract test meaningful and the MCP server
testable without a network.

## Build and gates

```bash
uv sync                    # library and CLI
uv sync --extra mcp        # adds the MCP runtime
uv run pre-commit install
uv run jev --help
```

| gate | command |
|---|---|
| lint | `uv run ruff check .` |
| format | `uv run ruff format --check .` |
| types | `uv run ty check` |
| layers | `uv run lint-imports` |
| docs | `uv run docvet check` |
| tests | `uv run pytest -q --cov` |

Coverage floor is 90. Test markers are `unit`, `contract` and `live`; `live`
touches the real API and is excluded from the default run.

A `contract` test proves a fake port and the real adapter agree on the same
fixtures. When the outbound adapter changes, that test is the one that must
still pass.

### Gates run themselves

A turn-end hook runs these gates after any turn that edits Python and reports
only failures. Silence means green. Do not spend tool calls re-running them by
hand; read what the hook reports. A gate slower than two seconds runs every
fifth turn rather than every turn.

A tool that fails to spawn is a failure, not an environment detail — it means
a tool is configured but not installed, and installing it is part of the work.

## Vocabulary

One term per concept, in docs, identifiers and commit messages.

| use | not |
|---|---|
| question | prompt, query |
| answer | response, result |
| confidence | certainty, score |
| `Noul` / `Choice` / `Score` | boolean / enum / rating |
| port | interface |
| adapter | implementation, driver |

`Score` is a Jev question type. The number inside an answer is a **score**; how
sure Jev is of it is **confidence**. Do not swap them.

## Writing system

Short declarative sentences. Active voice, name the actor. One instruction per
sentence. No hedging stacks, no marketing adjectives (seamless, robust,
powerful, blazing). State a fact or write an explicit **Open question**.

Applies to docstrings, docs pages, error messages, CLI help and commit
messages.

## Working rounds

- **One deliverable per round.** Land one thing, run the gates, stop.
- **`STATUS.md` is rewritten in the commit that changes what it says.** It names
  the test count, the coverage figure, the gate state and what is verified
  against the live service. A commit that moves any of those and leaves STATUS
  alone publishes a claim the next session has to discover is false. automarket
  lost three sessions to exactly that and gated it; see #28.
- **Read a file once.** Use `git diff` between reads rather than re-reading.
- **Never poll.** Wait on a watcher, not a loop of empty checks.
- **Do not write summary documents.** `docs/` holds `reference/api.md` and the
  Diátaxis tree. The README is the only summary. No `PROJECT_SUMMARY.md`, no
  `FINAL_REPORT.md`.

## Commits

Conventional Commits 1.0.0. The type comes from the closed vocabulary
(`feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `build`, `ci`).
Reference an issue in the description or a footer.

Default branch is `main`. The repo is private. **No pull requests** — commit a
finished piece of work directly to `main` and push. The pre-commit and pre-push
hooks are the only gate between a change and the branch, so
`uv run pre-commit install --install-hooks -t pre-commit -t pre-push` is the
first thing a clone does. Never pass `--no-verify`.

Do not describe work as complete while any gate is red. If a requirement was
not met, name it.
