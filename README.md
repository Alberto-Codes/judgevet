# judgevet

Typed client, CLI and MCP server for TypeSafe's **Jev** (System One) judgment
model.

## What is verified

This library is on PyPI and usable: `pip install judgevet`. This section says
how much of it has been checked against the real service, because the answer
is "most, not all" and you should know which parts before you rely on them.

**The response shape is verified. The error surface is partly verified.
Everything else is still inferred from documentation.**

A `live`-marked test passes against the real API, and three probe calls on
2026-09-21 settled what had been guesswork:

- The success shape parses field for field — including the parts easiest to
  get wrong. A noul answer carries no `confidence` while choice and score do;
  `score` is continuous, not an index; `legend` is a map keyed by stringified
  position. The real probabilities summed to exactly 1.0, the choice appeared
  in its own map, and the score sat inside its legend, so the domain's
  invariants do not reject real data.
- `model` in a response is the **resolved** version. Sending `jev-latest`
  returned `jev-1.13.0`.
- `detail` on an error is **polymorphic**: an object for authentication
  errors, an array for validation errors. Documentation did not say so, and
  code that assumes either shape breaks on the other.

Still inferred, and marked as such in `STATUS.md`: the 429 and 529 bodies —
one needs abusing the service, the other cannot be provoked — every model
other than `jev-1.13.0`, and any field no call has exercised.

The repository marks `README.md` and `docs/reference/api.md` as `draft`
rather than `stable` under its own documentation trust levels — one model and
two error statuses is not the whole surface. That is a statement about
documentation coverage, not about whether the package works.

## What Jev is

Jev is not a chat model and not a coding model. You send it a piece of state
and a set of *typed questions*, and it returns one answer per question with a
calibrated probability:

| question | answer |
|---|---|
| `Noul` | yes/no, with a probability |
| `Choice` | one option from a set you defined, with per-option probabilities |
| `Score` | a position on a scale you defined, with a legend |

Typed answers let code branch, sort and route without parsing prose.

## Why this client exists

The [official TypeSafe Python SDK](https://docs.typesafe.ai/sdk/python)
provides synchronous and asynchronous clients.

judgevet combines a typed library with two inbound adapters, CLI and MCP,
over one contract-tested core. The **library is the artifact**: scripts, hooks
and CI can call it directly. [STATUS.md](STATUS.md) separates verified claims
from inferences.

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
uv run judgevet --help
```

The MCP server is an optional extra, so the library and CLI install without an
MCP runtime:

```bash
uv sync --extra mcp
```

## Developer workflows

Version 0.5.0 supports reusable question files, file/stdin state and explicit
acceptance policies:

```bash
judgevet --state-file document.txt --questions-file questions.json --policy policy.json --json
```

A successful judgment exits 0 when its policy passes and 3 when it does not.
Input/service failures exit 1; invalid usage exits 2. Without a policy, a low
probability remains a successful judgment.

See [file inputs](docs/how-to/use-cli-files.md),
[policy rules](docs/how-to/use-cli-policy.md), and the
[opt-in staged-diff example](docs/how-to/review-staged-diff.md).
[Installation](docs/how-to/install.md) covers the library, CLI and MCP command.

CLI and MCP diagnostics stay quiet at the default log level. Set
`JEV_LOG__LEVEL=debug` to emit one `http.call` event per HTTP call to stderr.
Events contain the requested model, question count, HTTP status (or null before
an answer arrives), and success/error outcome. They exclude caller payloads,
headers and exception text. Non-TTY diagnostics use JSON lines; `JEV_LOG__FORMAT`
can force `json` or `console`. MCP SDK warnings/errors use a safe `mcp.runtime`
event with severity only. Debug CLI failures have a diagnostic line followed by
the existing error envelope on stderr; stdout retains its existing JSON shape.
Library imports do not configure logging, and unconfigured library calls stay
silent. Applications may configure structlog themselves to receive events.

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
