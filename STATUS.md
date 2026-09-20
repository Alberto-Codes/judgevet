# STATUS

Last written: 2026-09-20. A session overwrites this file.

## Where the repo is

The hex core is ported and tested. Neither inbound adapter is finished, and
nothing has been verified against the live API.

```
src/jev_client/
  domain/      Noul Choice Score · NoulAnswer ChoiceAnswer ScoreAnswer
               SystemOneResponse · Usage                    ported, tested
  ports/       SystemOnePort protocol                       ported
  adapters/outbound/http.py                                 ported, contract-tested
  adapters/inbound/cli.py                                   argparse — needs typer
  adapters/inbound/mcp.py                                   DOES NOT EXIST
```

48 tests pass. Coverage was 99.47% in the run this was lifted from.

## Gates right now

| gate | state |
|---|---|
| `lint-imports` | PASS |
| `docvet check` | PASS |
| `pytest -q --cov` | PASS |
| `ruff check .` | **13 errors** |
| `ruff format --check .` | **1 file** |
| `ty check` | **1 diagnostic** |

The three failures are deliberate. The core was written under a looser ruff
config and then moved onto automarket's stricter set, which found real issues.
They were left red so the baseline is honest and the first task has a
machine-checkable target.

The 13 ruff errors: nine `D105` (missing docstrings on magic methods, in
`domain/answers.py`, `domain/questions.py`, `domain/response.py`,
`domain/usage.py`), three `E501`, one `TRY300` in `cli.py`. The `ty`
diagnostic is an argument type in `format_answer`. `ruff format` wants one
file.

## The thing to keep straight

**No call has ever been made against the live Jev API.** Every field name,
endpoint and response shape in this repo came from reading documentation.
`README.md` and `docs/reference/api.md` say `sketch` for that reason.

There is no `TYPESAFE_API_KEY` yet. Alberto will supply one. Until a
`live`-marked test passes against the real API, the domain model is a
hypothesis and the status marker does not move.

## Provenance of the ported code

Lifted from a local-harness run (`pi` driving Qwen3-Coder-Next on this
machine). That run produced 99.47% coverage, 48 tests and a contract test
proving the fake port and the real HTTP adapter equivalent — verified
independently, not taken from its own summary.

The same run also reported six green checks while two gates were red. Read its
gates, never its summary. That habit applies to every delegated session here.

## Next

[NEXT_PROMPT.md](NEXT_PROMPT.md) holds the ordered work and the per-task
prompts.
