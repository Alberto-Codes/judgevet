# NEXT_PROMPT

The ordered work, and the prompt for each piece. Read
[STATUS.md](STATUS.md) first.

## How this repo is built

Work is handed to `pi`, a local coding harness running Qwen3-Coder-Next on
this machine at no token cost. The orchestrating agent scopes each task,
hands it over, and then **verifies against the gates rather than pi's
summary**.

Why the verification is not optional: across four measured runs the local
model produced genuinely good work — 99.47% coverage, a working contract test
— and then reported six green checks while two gates were red, hedged a type
failure as "passes on source", and configured a linter it never installed.
It executes well and judges badly. That is the whole reason the split works.

### Handing off

```bash
cd ~/Projects/jev
pi --model 'llama.cpp/Qwen3-Coder-Next-UD-IQ4_XS'
```

Do **not** pass `--no-context-files`. The conventions live in `CLAUDE.md` and
pi must read them. That is why the prompts below are short.

A turn-end hook runs this project's gates after any turn that edits Python and
reports only failures, so a delegated session self-corrects between turns.

### Verifying

```bash
python3 ~/Projects/bazzite-dotfiles/agents/scripts/pi-forensics.py --project ~/Projects/jev
```

Reports what the session did and runs every gate. Flags a claim mismatch when
the run reports success while gates fail. Exit 1 on a failing gate. Then read
the diff.

## Task 1 — bring the ported code to green

Smallest piece, and it proves the loop works before anything harder.

> The gates listed in STATUS.md are red on ported code: 13 ruff errors, one
> file needing `ruff format`, one `ty` diagnostic in `format_answer`. Fix the
> cause of each. Do not add per-file-ignores, `# noqa`, or narrow any gate.
> Stop when `ruff check`, `ruff format --check` and `ty check` all pass and
> the existing tests still pass.

## Task 2 — port the CLI to typer

> `src/judgevet/adapters/inbound/cli.py` uses argparse. Port it to typer,
> keeping behaviour identical. `pyproject.toml` already declares
> `jev = "judgevet.adapters.inbound.cli:app"`, so the module must expose a
> typer `app`. The CLI takes a `SystemOnePort`; it must not construct an HTTP
> client itself. Keep its contract test passing and `uv run jev --help`
> working.

## Task 3 — the MCP inbound adapter

The real test of the architecture.

> Add `src/judgevet/adapters/inbound/mcp.py`: an MCP stdio server exposing
> the three question types as typed tools, over the same `SystemOnePort` the
> CLI uses. Return MCP structured content, not a JSON string for the client to
> re-parse. The `mcp` package is an optional extra (`uv sync --extra mcp`) and
> an import-linter contract forbids importing it anywhere else — if that
> contract fails, the import is in the wrong layer. Cover it with unit tests
> against a fake port; no network.

## Task 4 — the live test that promotes the sketch

> Add a `@pytest.mark.live` test that calls the real Jev API using
> `TYPESAFE_API_KEY` from the environment and asserts the response parses into
> the domain types. It must skip cleanly when the key is absent. `addopts`
> already excludes `live` from the default run. There is no key yet; the test
> exists so the sketch can be promoted the moment there is one.

## Task 5 — promote, once a key exists

Not delegated. Run the live test, read what the API actually returned, and
reconcile it against the domain model. Every mismatch is a real finding:
the model was built from documentation alone.

Only after that passes do `README.md` and `docs/reference/api.md` move off
`sketch`, and only for the parts the call actually verified.

## Later, not now

- CLI and MCP usage pages under `docs/how-to/`.
- An ADR recording why the library is the artifact and MCP is one adapter.
- Consuming this client from `pi-forensics.py` to replace its regex claim
  audit with a typed judgment. The seam exists; the client has to be real
  first.
