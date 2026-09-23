# judgevet

A typed Python client, CLI and optional MCP server for TypeSafe's **Jev**
(System One) judgment model. Send content and typed questions; use the answers
to classify, route or evaluate that content without parsing generated prose.

**Unofficial and not affiliated with TypeSafe.** The
[official TypeSafe Python SDK](https://docs.typesafe.ai/sdk/python) also offers
typed questions and synchronous and asynchronous clients. Choose judgevet when
you want an importable library, shell/CI workflows with explicit acceptance
policies, and agent tools over one contract-tested core. The library and CLI
install without the MCP runtime; the wheel includes `py.typed` for type checkers.

## Install

Use Python 3.12 or newer. In a virtual environment:

```bash
python -m pip install 'judgevet==0.7.0'
judgevet --help
```

For an existing uv project, use `uv add 'judgevet==0.7.0'`.
See [installation and MCP client setup](docs/how-to/install.md) and
[security, credential handling and cryptographic posture](SECURITY.md).

Supply a TypeSafe API key through your process environment or secret provider.
The CLI and MCP accept `JEV_API__KEY` or `TYPESAFE_API_KEY`; `JEV_API__KEY` takes
precedence. Library adapters take an explicit key. The example below reads
`JEV_API__KEY`. Do not put real keys in source or command arguments.

## Use the typed library

```python
import os

from judgevet import Choice, HTTPSystemOneAdapter, Noul, Score

with HTTPSystemOneAdapter(api_key=os.environ["JEV_API__KEY"]) as client:
    answer = client.system_one(
        state="I was charged twice. Please help today.",
        questions={
            "billing": Noul(instructions="Is this about billing?"),
            "team": Choice(
                instructions="Which team should handle this?",
                criteria={"billing": "Payments", "support": "Technical help"},
            ),
            "urgency": Score(
                instructions="How urgent is this?",
                criteria=["Can wait", "This week", "Today"],
            ),
        },
    )

print(answer.nouls["billing"].noul)
print(answer.choices["team"].choice)
print(answer.scores["urgency"].score)
```

The [API reference](https://docs.typesafe.ai/api) defines the three question
types and their answer fields:

| Question | Typed answer |
|---|---|
| `Noul` | Probability of yes; no separate confidence field |
| `Choice` | Selected option, per-option probabilities and confidence |
| `Score` | Continuous score, scale legend, per-level probabilities and confidence |

The answer also contains the resolved model and token usage. Use
`AsyncHTTPSystemOneAdapter` with `async with` and await `system_one` for async
applications. Both adapters close their HTTP client when the context exits.

## Evaluate policies from Python

Version 0.7.0 adds `judgevet.policy` for immutable typed rules, validated
question snapshots and ordered pass/fail reports. `judgevet.policy_json` decodes
the existing CLI policy grammar. Both APIs are published in 0.7.0.
See the [runnable typed and JSON policy guide](docs/how-to/use-policy-library.md)
and [supported imports and compatibility](docs/reference/compatibility.md).

The CLI retains its grammar, diagnostics, output and exit meanings. MCP retains
its three tools. The base installation still omits MCP; one distribution and
version cover all surfaces.

## Use the CLI

With a key in the environment, ask a question and emit JSON:

```bash
judgevet 'I was charged twice.' \
  '{"billing":{"type":"noul","instructions":"Is this about billing?"}}' --json
```

For reusable questions and an explicit pass/fail policy, create the files using
[the file input guide](docs/how-to/use-cli-files.md) and
[the policy guide](docs/how-to/use-cli-policy.md), then run:

```bash
judgevet --state-file document.txt --questions-file questions.json --policy policy.json --json
```

A valid judgment exits 0 when the policy passes and 3 when it does not.
Input/service failures exit 1; usage conflicts exit 2. Without a policy, a low
probability remains a successful judgment. State can also come from stdin with
`--state-file -`. The [staged-diff example](docs/how-to/review-staged-diff.md)
shows an opt-in Git workflow.

## Use the optional MCP server

Install the extra and launch the stdio server with a key in its environment:

```bash
python -m pip install 'judgevet[mcp]==0.7.0'
judgevet-mcp
```

Configure your MCP host to run `judgevet-mcp`. It waits for protocol input on
stdin; stdout carries protocol frames and stderr carries diagnostics. It is
not an interactive shell. See [client setup and the pinned uvx launcher](docs/how-to/install.md).

The tools are `ask_noul`, `ask_choice` and `ask_score`. For example, call
`ask_noul` with these arguments from your MCP client:

```json
{"state":"I was charged twice.","instruction":"Is this about billing?"}
```

Choice accepts a criteria map; Score accepts an ordered criteria list. See the
[connection checks](docs/how-to/install.md#verify-the-connection) for all three.
If initialization or discovery fails, follow the
[connection troubleshooting steps](docs/how-to/install.md#when-mcp-does-not-connect).
Intermittent initialization failures have no established cause or remedy.
A successful separate check does not prove an existing session loaded the tools.

## Diagnostics and security

Routine diagnostics are quiet by default. `JEV_LOG__LEVEL=debug` emits HTTP
call metadata to stderr; `JEV_LOG__FORMAT` selects `json` or `console`.
These events exclude state, question text, headers and exception text.
MCP runtime diagnostics retain severity only. This does not promise redaction
of MCP protocol errors, CLI error envelopes or arbitrary tracebacks. Library
imports do not configure logging. Read the [security policy](SECURITY.md)
before handling sensitive content or sharing diagnostics.

## What is verified

Documentation status: **draft**. The published package has passed isolated
library, CLI and MCP checks. The library and policy-guide examples have been
executed against it. Synthetic answers do not prove model quality.

Live calls exercised the success shapes, resolved `jev-1.13.0` model, Noul
criteria and Score legend, plus authentication and validation errors. The
observed error detail is polymorphic: an object for authentication and an
array for validation. The [API notes](docs/reference/api.md) and
[verification table](STATUS.md#what-is-verified-and-what-is-not) separate these
observations from documentation-derived expectations.

Live 429/529 bodies remain unseen. Other resolved models and fields not touched
by a call remain unverified. Contract tests exercise synthetic fixtures; they
do not turn those cases into live evidence. The [evidence ledger](STATUS.md) links the release verification records.

## Development

The domain is pure. Ports separate it from HTTP and the CLI/MCP adapters;
`import-linter` enforces those boundaries and isolates the optional MCP runtime.
From a source checkout:

```bash
uv sync --extra mcp
uv run pre-commit install --install-hooks -t pre-commit -t pre-push -t commit-msg
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run lint-imports
uv run docvet check --all
uv run pytest -q --cov
```

Coverage floor is 90%. `live` tests contact the real service and are excluded
from the default run. Contributions follow [AGENTS.md](AGENTS.md).

Release operators: see the [maintainer procedures](docs/maintainers/index.md).
