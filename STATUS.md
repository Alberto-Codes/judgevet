# STATUS

Last written: 2026-09-25. A session overwrites this file.

## The headline

**judgevet 0.1.0 is on PyPI.** `pip install judgevet` installs it, the CLI and
the MCP server; the wheel was verified from the index before this line was
written. It went up over OIDC trusted publishing with no stored token in the
path, from a draft release a human published by hand — `publish.yml` triggers
on `release: types: [published]` and nothing else.

`0.0.1` remains on the index unyanked. It is the name reservation and installs
nothing useful; see #88.

## What the release contains

**The domain model matches the live service.** It was written entirely from
documentation and never exercised. One probe call settled it: every field
parses, including the parts easiest to get wrong — a noul answer carries no
`confidence` while choice and score do, `score` is a continuous `1.05` rather
than an integer index, and `legend` is a map keyed by stringified position
rather than a list. The official HTTP reference then confirmed all three
independently.

Error bodies are now verified too, for the two statuses that can be provoked
without abusing the service. The response shape held a second time against a
domain that has since grown invariants: the real probabilities summed to
exactly 1.0 in both maps, the choice appeared in its own map, and the score sat
inside its legend — so the constraints added in #77 do not reject real data.

What is still inferred: 429 and 529 bodies, every model but `jev-1.13.0`, and
the field names no call has exercised.

## Where the repo is

```
src/judgevet/
  domain/      questions · answers · response · usage · errors     tested
               frozen dataclasses; __post_init__ raises ValueError on a
               bad range, a non-distribution, or a choice off its own map
               errors carry `retryable`: true on rate-limit and service
  ports/       SystemOnePort — a typing.Protocol, satisfied by shape
  adapters/outbound/http.py    parses the body, translates httpx into domain errors
  adapters/inbound/cli.py      typer app; takes a port, one construction site
  adapters/inbound/settings.py one Settings, key as SecretStr
  adapters/inbound/logs.py     structlog to stderr, secrets redacted
  adapters/inbound/mcp.py      stdio server: ask_noul · ask_choice · ask_score
scripts/
  check_suppressions.py        gate: no noqa / type: ignore
  probe_live.py                prints one real response; asserts nothing
```

Tests and coverage: see the gate table below. 240 tests, 95% overall.

## Gates

`ruff check` · `ruff format --check` · `ty check` · `lint-imports` ·
`docvet check` · `docvet check --all` · `pytest --cov` · `check_suppressions`

All green. pre-commit runs the fast ones, pre-push adds the coverage floor
and the whole-repo docvet check.
There are no pull requests here: those hooks are the only gate before `main`. 

## What is verified, and what is not

| claim | status |
|---|---|
| endpoint, auth header, three answer shapes, usage | verified — probe + official reference |
| noul has no confidence; score is continuous; legend is a map | verified — both sources |
| 401 returns `{"detail": {"error_type", "message"}}` | **verified** — live call with an invalid key, 2026-09-21 |
| 422 returns `{"detail": [ {type, loc, msg, input} ]}` | **verified** — live call omitting `questions`, 2026-09-21 |
| `detail` is polymorphic: an object for auth, an array for validation | **verified** — the two calls above disagree in shape |
| a 422 body echoes the request payload back under `input` | **verified**, and the adapter discards it (#85) |
| 429 and 529 | still unseen. 429 needs abusing the service and 529 cannot be forced |
| every other field name | inferred from documentation |
| error response bodies | never seen |
| models other than `jev-latest` | never called |
| `model` in a response is the **resolved** version, not the alias sent | verified — the live test caught `jev-1.13.0` where `jev-latest` was sent |
| fake and real adapter produce identical outcomes | verified — contract tests on 12 hand-authored fixtures, inferred from docs/reference/api.md |

#17 has landed. `README.md` and `docs/reference/api.md` stay `sketch` until #29
observes the real error bodies and #6 promotes only the verified rows.

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
