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

- **The domain model is verified in part, and only in part.** This rule used
  to read "no call has been made". Calls have now been made: a `live`-marked
  test passes against the real API, and three probe calls on 2026-09-21
  settled the success shape and the 401 and 422 error bodies. `README.md` and
  `docs/reference/api.md` moved from `sketch` to `draft` on that evidence, for
  those parts only.

  What the rule becomes, rather than disappears: **promote a claim only when a
  call has exercised it.** The 429 and 529 bodies are unseen — one needs
  abusing the service, the other cannot be provoked — every model other than
  `jev-1.13.0` is untested, and any field no call touched is still inference.
  `STATUS.md` carries the line-by-line table, and moving a line from inferred
  to verified without a call that did it is the one change this repo will not
  accept.

  Nothing reaches `stable` while a documented status code has never been
  seen.
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
uv run judgevet --help
```

| gate | command |
|---|---|
| lint | `uv run ruff check .` |
| format | `uv run ruff format --check .` |
| types | `uv run ty check` |
| layers | `uv run lint-imports` |
| docs | `uv run docvet check` |
| tests | `uv run pytest -q --cov` |

docvet runs in two modes: the pre-commit hook vets only the files a commit
touches (`uv run docvet check`, diff mode), and the pre-push hook vets the
whole repo (`uv run docvet check --all`), so commits never fail on doc debt
they did not introduce and no stale docstring can leave the branch.

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

### A summary is not evidence

**Never report work complete while a gate is red.** Report what is red and say
why you think it should be accepted. That is a conversation you can win; a
false "complete" is one you cannot.

This has happened. A session reported "Implementation complete" with five
properties ticked while `check_suppressions.py` exited 1, having added four
`per-file-ignores` codes and edited that gate's own test to assert the
inflated number. The work underneath was correct. The claim was not.

**A green gate table is not an audit either.** Gates catch the mechanical
class. They cannot see:

- a test that passes whether or not the behaviour under test happens — a bare
  `try`/`except` around a call that must raise, where nothing raised means the
  handler never runs;
- a helper that raises where the specification said return, which makes its
  own return annotation false and the call site unreachable;
- an unwrapped secret bound to a local, which `--showlocals` prints on any
  failure.

All three shipped with every gate green. #94 and #95 exist to convert the
mechanically decidable half into gates; the rest is read by eye.

**Prove a property with a command, not a sentence.** "Confirm that X" is
answered by a claim. A command whose output either exhibits the property or
does not is answered by the world. For a test, the command is: break the
precondition and show it go red. A test that cannot be made to fail is not
evidence.

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

- **Behavioral changes start red.** Write the acceptance test first and record
  its failing command and output on the issue. Verify it fails for the missing
  behavior, not a broken fixture. Give the coder that exact test contract,
  then require green gates and an independent failure proof. Do not split a
  production-only change from tests promised in a later round.
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

**A commit that finishes an issue closes it from the footer.** Write
`Closes #N` — spec rule 8's `<space>#` separator — and GitHub closes the issue
on push and leaves a permanent link from the issue to the commit. Do not close
issues by hand with `gh issue close`: a hand-written "landed in <sha>" comment
is prose that goes stale the moment history is rewritten, and it did. Use
`Refs #N` for an issue the commit touches but does not finish.

Footers follow the git trailer convention the spec is built on: the token
takes `-` in place of whitespace (`Generated-By`, `Co-Authored-By`), and a
value may wrap onto further lines because parsing only stops at the next
`token: ` or `token #` pair.

Attribution is per-commit and factual. A commit a local model wrote carries
`Generated-By: <model> (local, via pi)`, with a trailing clause naming any part
of it that someone else wrote. A commit written by hand carries no such
trailer — the trailer is evidence, and this repo is partly an evaluation of
those models, so decorating an unearned commit corrupts the record.

**Two models, two trailers.** When a reasoning model wrote the specification
and a coder implemented it, both are named and the roles are not merged:

    Specified-By: Qwen3.8-27B-UD-Q4_K_M (local, via pi, --thinking medium)
    Generated-By: Qwen3-Coder-Next-UD-IQ4_XS (local, via pi)

`Specified-By` means that model produced the definition of ready and done the
coder worked from — not that it wrote code. Collapsing the two into one
trailer would destroy the only comparison that makes the pipeline falsifiable:
whether a refined specification changes what the coder lands. The same
distinction is recorded as `spec_refined` in the delegation log, so the commit
history and the log agree.

A commit with no `Specified-By` went to the coder from an issue and a prompt.
That absence is data too, so do not add the trailer to make a commit look more
rigorous than it was.

**The specification lives on the issue, not on disk.** A reasoning pass posts
its definition of ready and done as an issue comment, bylined with the model
that wrote it, before any coder sees it. The coder then reads it with
`gh issue view <N> --comments`. This is not bookkeeping: a local scratch file
is invisible to review, dies with the machine, and has already been deleted
twice — once by a crashing session and once by the coder itself. Keeping the
original issue body intact beside the comment also shows what the reasoning
pass added, which is the comparison being measured.

## Never destroy work you did not create

A delegated session does not run `git checkout`, `git restore`, `git reset`,
`git stash`, `git clean`, or `rm -rf` against any path, and does not modify a
file its task did not name. Unrelated modifications in the tree belong to
someone else; leave them and mention them in the summary.

This is not hypothetical. A session working one issue ran
`git checkout CLAUDE.md && rm -rf scratchpad/` after inspecting the diff and
the git log of a file that was not its concern, destroying an uncommitted
change and a specification. Every gate here examines files that were
*changed*; nothing notices a file that was *reverted*, because a revert leaves
no diff and a clean-looking tree. See #82.

Default branch is `main`. The repo is private. **No pull requests** — commit a
finished piece of work directly to `main` and push. The pre-commit and pre-push
hooks are the only gate between a change and the branch, so
`uv run pre-commit install --install-hooks -t pre-commit -t pre-push -t commit-msg`
is the
first thing a clone does. Never pass `--no-verify`.

Do not describe work as complete while any gate is red. If a requirement was
not met, name it.
