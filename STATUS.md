# STATUS

Last written: 2026-09-21. A session overwrites this file.

## The headline

**judgevet 0.1.0 is on PyPI.** `pip install judgevet` installs it, the CLI and
the MCP server; the wheel was verified from the index before this line was
written. It went up over OIDC trusted publishing with no stored token in the
path, from a draft release a human published by hand — `publish.yml` triggers
on `release: types: [published]` and nothing else.

`0.0.1` is yanked, with the reason "Name reservation only; contained no
working code. Use 0.1.0 or later." It still resolves for anyone who pins it
exactly, which is what yanking means; it is gone from resolution. #88 closed.

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
  adapters/outbound/http.py    four module-level helpers — build payload,
                               parse body, translate status error, translate
                               request error — and a thin adapter over them.
                               The translators return the exception rather
                               than raising, so #92's async adapter shares
                               them and keeps `raise ... from exc` at one
                               site per adapter (#91)
  adapters/inbound/cli.py      typer app; takes a port, one construction site
  adapters/inbound/settings.py one Settings, key as SecretStr
  adapters/inbound/logs.py     structlog to stderr, secrets redacted
  adapters/inbound/mcp.py      stdio server: ask_noul · ask_choice · ask_score
scripts/
  check_suppressions.py        gate: no noqa / type: ignore
  probe_live.py                prints one real response; asserts nothing
```

Tests and coverage: see the gate table below. 242 tests, 94.52% overall.

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
| models other than `jev-latest` | never called |
| `model` in a response is the **resolved** version, not the alias sent | verified — the live test caught `jev-1.13.0` where `jev-latest` was sent |
| fake and real adapter produce identical outcomes | verified — contract tests on 12 hand-authored fixtures, inferred from docs/reference/api.md |
| 401 and 422 error responses become JevAuthError and JevRequestError with retryable=False | **verified** — live tests, 2026-09-21 |
| the adapter drops the `input` field from 422 bodies to avoid echoing caller data | **verified** — live test asserts test state does not leak |
| API keys do not leak in error str/repr | **verified** — live tests assert key not in str or repr |
| secret guard redacts API key from test output | **verified** — `test_secret_guard.py` proves guard scrubs key from pytest report with `--showlocals` |

#17 and #29 have landed, so the error rows above are observations now, not
inferences. `README.md` and `docs/reference/api.md` stay `sketch` until #6
promotes only the verified rows.

The 3xx fallthrough in `system_one` is the one branch no test pins — it was
checked by hand for #91 and holds, and #96 exists to make that permanent.

## Working with pi

Issues carry two extra labels beyond priority: `pi-fit` or `judgment`, and
`size-S|M|L`. Across 37 delegated sessions, `size-S` lands clean roughly three
times in four and `size-M` one time in four, so split before assigning. Some
tasks do land clean first time; the ones that do not fail in two recurring
ways.

**A green gate table is not an audit.** Two consecutive sessions returned with
all eight gates green and a real defect: a test that passed whether or not the
behaviour under test happened, and a helper that raised where the spec said
return, making its own return annotation false and the call site unreachable.
Neither is visible to any linter — #94 and #95 exist to convert the
mechanically decidable half into gates.

`judgment` means the task asks for a shape to be decided. The one such task
that was delegated (#2) came back with a parallel structure beside the intended
one and had to be reverted. Decide the shape, then hand over the wiring.

Outcomes are logged to
`~/Projects/bazzite-dotfiles/agents/data/delegation-log.jsonl`.

## Next

[NEXT_PROMPT.md](NEXT_PROMPT.md) holds the ordered work. The open queue is in
GitHub issues; `gh issue list --label ready --label pi-fit` is the assignable
set.
