# STATUS

Last written: 2026-09-21. A session overwrites this file.

## The headline

**The domain model matches the live service.** It was written entirely from
documentation and never exercised. One probe call settled it: every field
parses, including the parts easiest to get wrong — a noul answer carries no
`confidence` while choice and score do, `score` is a continuous `1.05` rather
than an integer index, and `legend` is a map keyed by stringified position
rather than a list. The official HTTP reference then confirmed all three
independently.

That does **not** promote the sketch. One call, three question types, one
model. Error bodies, other models and edge shapes remain unverified, and the
typed boundary is still in the wrong layer (#17).

## Where the repo is

```
src/jev_client/
  domain/      questions · answers · response · usage · errors     tested
  ports/       SystemOnePort — returns dict[str, Any], see #17
  adapters/outbound/http.py    translates httpx into domain errors
  adapters/inbound/cli.py      typer app, and the only parser (#17)
  adapters/inbound/settings.py one Settings, key as SecretStr
  adapters/inbound/mcp.py      DOES NOT EXIST (#4)
scripts/
  check_suppressions.py        gate: no noqa / type: ignore
  probe_live.py                prints one real response; asserts nothing
```

91 tests, 98.5% coverage, all seven gates green, eleven commits on `main`.

## Gates

`ruff check` · `ruff format --check` · `ty check` · `lint-imports` ·
`docvet check` · `pytest --cov` · `check_suppressions`

All green. pre-commit runs the fast ones, pre-push adds the coverage floor.
There are no pull requests here: those hooks are the only gate before `main`.

## What is verified, and what is not

| claim | status |
|---|---|
| endpoint, auth header, three answer shapes, usage | verified — probe + official reference |
| noul has no confidence; score is continuous; legend is a map | verified — both sources |
| 401 / 422 / 429 / 529 are the documented errors | documented, not exercised (#18) |
| every other field name | inferred from documentation |
| error response bodies | never seen |
| models other than `jev-latest` | never called |

`README.md` and `docs/reference/api.md` stay `sketch` until #17 lands and #6
promotes only the verified rows.

## Working with pi

Issues carry two extra labels beyond priority: `pi-fit` or `judgment`, and
`size-S|M|L`. Measured across ten delegated sessions, `size-S` lands clean far
more often than `size-M`, and no new task has landed clean on a first attempt.
Split before assigning.

`judgment` means the task asks for a shape to be decided. The one such task
that was delegated (#2) came back with a parallel structure beside the intended
one and had to be reverted. Decide the shape, then hand over the wiring.

Outcomes are logged to
`~/Projects/bazzite-dotfiles/agents/data/delegation-log.jsonl`.

## Next

[NEXT_PROMPT.md](NEXT_PROMPT.md) holds the ordered work. The open queue is in
GitHub issues; `gh issue list --label ready --label pi-fit` is the assignable
set.
