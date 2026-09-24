# judgevet

A typed Python client for TypeSafe's **Jev** (System One) judgment model, with
CLI and optional MCP entry points. Use it to ask structured questions about
content—for example, whether a support ticket concerns billing.

The **state** is your content. A **question** describes what to evaluate.
A typed **answer** contains the model's values, which your application can
inspect or compare with a local acceptance policy.

**Unofficial and not affiliated with TypeSafe.** The
[official TypeSafe Python SDK](https://docs.typesafe.ai/sdk/python) also provides
typed questions and synchronous and asynchronous clients. judgevet adds a
shared library, CLI and MCP contract with local policy evaluation.
The library and CLI install without the MCP runtime.

Documentation status: **draft**. Start below or follow the
[first-judgment tutorial](https://alberto-codes.github.io/judgevet/tutorials/first-judgment/)
for environment setup, checkpoints and recovery steps.

## Install and ask one question

Use Python 3.12 or newer. In a virtual environment:

```bash
python -m pip install 'judgevet==0.7.0'
judgevet --help
```

Supply a TypeSafe API key through your process environment or secret provider.
This example reads `JEV_API__KEY` and passes it explicitly to the library.
Do not put real keys in source or command arguments. The
[installation guide](https://alberto-codes.github.io/judgevet/how-to/install/)
covers other installation methods.

**This call sends the state, questions and selected model to the configured
service.** Send only content you are authorized to disclose. Read the
[data and credential guidance](https://github.com/Alberto-Codes/judgevet/blob/main/SECURITY.md)
before using sensitive content. The example uses a synthetic ticket:

```python
import os

from judgevet import HTTPSystemOneAdapter, Noul

with HTTPSystemOneAdapter(api_key=os.environ["JEV_API__KEY"]) as client:
    response = client.system_one(
        state="I was charged twice. Please help today.",
        questions={"billing": Noul(instructions="Is this about billing?")},
    )

answer = response.nouls["billing"]
print(f"Probability of billing: {answer.noul}")
print(f"Resolved model: {response.model}")
print(f"Input tokens: {response.usage.input_tokens}")
```

The context manager closes the HTTP client after the call. The answer remains
available. If the import or call fails, use the tutorial's
[recovery steps](https://alberto-codes.github.io/judgevet/tutorials/first-judgment/#recover-from-a-failed-checkpoint)
or the [troubleshooting guide](https://alberto-codes.github.io/judgevet/how-to/troubleshoot/).

## Read the answer and make a decision

A Noul value such as `0.85` reports the model's probability of yes. The actual
value varies. It is not a boolean, a measured accuracy rate or an instruction
to route the ticket. Noul has no separate confidence field.
See the [vendor's Noul definition](https://docs.typesafe.ai/primitives/noul).

The returned container also records the resolved model and token usage.
Other question types let you select a label or evaluate an ordered rubric:

| Question | What its answer contains |
|---|---|
| `Noul` | Probability of yes |
| `Choice` | Selected label, per-label probabilities and confidence |
| `Score` | Continuous score, rubric legend, per-level probabilities and confidence |

The [vendor API reference](https://docs.typesafe.ai/api) defines those fields.
The [question-type explanation](https://alberto-codes.github.io/judgevet/explanation/judgments/)
shows how to choose a type and distinguish score, confidence and probability.

A local policy can require a minimum value before your application accepts an
answer. For example, `0.85` meets a minimum of `0.8` and fails one of `0.9`.
These are teaching thresholds, not production recommendations. A passing policy
does not prove the model is correct or perform the application's next action.
Try the [first-policy tutorial](https://alberto-codes.github.io/judgevet/tutorials/first-policy/)
with synthetic answers; it requires no key or network.

## Choose your next task

| Need | Start here |
|---|---|
| Learn one complete service call | [First judgment](https://alberto-codes.github.io/judgevet/tutorials/first-judgment/) |
| Call from an async application | [Async Python guide](https://alberto-codes.github.io/judgevet/how-to/use-async-library/) |
| Use a mounted key or secret provider | [Credential sources](https://alberto-codes.github.io/judgevet/reference/configuration/#credential-sources) |
| Deploy in containers or serverless | [Deployment guide](https://alberto-codes.github.io/judgevet/how-to/deploy/) |
| Correlate diagnostic events | [Event contract and caller binding](https://alberto-codes.github.io/judgevet/reference/events/) |
| Configure a proxy or private CA | [Network configuration](https://alberto-codes.github.io/judgevet/reference/configuration/#proxy-and-tls-configuration) |
| Configure bounded retries | [Retry limits](https://alberto-codes.github.io/judgevet/reference/configuration/#retry-limits) |
| Handle service and transport failures | [Library error handling](https://alberto-codes.github.io/judgevet/how-to/handle-errors/) |
| Evaluate typed or JSON policies in Python | [Policy guide](https://alberto-codes.github.io/judgevet/how-to/use-policy-library/) |
| Use shell commands, files or stdin | [CLI inputs](https://alberto-codes.github.io/judgevet/how-to/use-cli-files/) and [CLI policies](https://alberto-codes.github.io/judgevet/how-to/use-cli-policy/) |
| Give an agent judgment tools | [Optional MCP installation, connection and discovery](https://alberto-codes.github.io/judgevet/how-to/connect-mcp/) |
| Look up types, options or schemas | [Reference map](https://alberto-codes.github.io/judgevet/#reference-look-up-a-contract) |
| Understand thresholds and tradeoffs | [Local policy explanation](https://alberto-codes.github.io/judgevet/explanation/policies/) |
| Choose an entry point and own its lifecycle | [Library-first architecture](https://alberto-codes.github.io/judgevet/explanation/architecture/) |

The CLI uses the same library and can return JSON or a policy exit status.
The optional MCP server exposes `ask_noul`, `ask_choice` and `ask_score` over
stdio. Follow the connection guide to install the extra and configure a host.
These are alternative entry points; you do not need MCP to use Python or the CLI.

## Know the limits

Exact documentation examples run against isolated installations with synthetic
answers. Those checks establish local wiring, not model quality or calibration.
Live evidence covers only the observed cases and resolved `jev-1.13.0` model.
The 429/529 error bodies remain unseen; other models and untouched fields remain
unverified. The [verification explanation](https://alberto-codes.github.io/judgevet/explanation/verification/)
separates local tests, vendor statements and live observations.

Diagnostics are quiet by default. Debug metadata excludes state and question
text, but protocol errors, CLI error envelopes and arbitrary tracebacks can
contain sensitive content. Review them before sharing. The
[security policy](https://github.com/Alberto-Codes/judgevet/blob/main/SECURITY.md)
describes credential, disclosure and diagnostic limits.

## Maintainers

Use the [maintainer procedures](https://alberto-codes.github.io/judgevet/maintainers/)
for documentation checks, package verification and releases.
[Repository contribution rules](https://github.com/Alberto-Codes/judgevet/blob/main/AGENTS.md)
define gates and commits. The
[evidence ledger](https://github.com/Alberto-Codes/judgevet/blob/main/STATUS.md)
retains release records and the detailed live-verification table.

<!-- mcp-name: io.github.Alberto-Codes/judgevet -->
