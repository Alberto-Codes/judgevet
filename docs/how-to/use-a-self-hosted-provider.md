---
status: draft
---

# Use a self-hosted judgment provider

Status: **draft**.

Use this recipe when an application runs judgevet on a judgment model that it
hosts itself. judgevet needs no code change for this. The provider seam
shipped in 0.14.0.
Source: https://github.com/Alberto-Codes/judgevet/issues/242.

A provider is an object whose `system_one` method satisfies `SystemOnePort`.
The application builds the provider, owns its dependencies and closes it.
judgevet has no default provider, no discovery and no fallback.
Source: https://github.com/Alberto-Codes/judgevet/issues/201#issuecomment-5850529268.

Ollama is a second server behind the hosted adapter, not a provider. See
[Use Ollama as a local server](use-ollama.md).

## Choose a backend

typevet on Gemma 4 is the worked example. typevet documents two backends.
This page links them and does not repeat them.

- Serve Gemma 4 31B with vLLM on a rented H100.
  Source: https://alberto-codes.github.io/typevet/how-to/serve-gemma-4-31b-on-a-rented-h100/.
- Run Gemma 4 with llama.cpp on a local 24 GiB GPU. Use the
  `gemma-4-31b-24gib-kv11-decoder` preset.
  Source: https://alberto-codes.github.io/typevet/how-to/run-gemma4-llamacpp/.

typevet describes its own relationship to judgevet.
Source: https://alberto-codes.github.io/typevet/explanation/typellm-and-judgevet/.

typevet 0.2.0 ships the bridge that exposes typevet as a judgevet provider.
Install it with `pip install 'typevet[judgevet]'`. The provider class is
`typevet.adapters.inbound.judgevet.TypevetSystemOnePort`. typevet documents
its setup.
Source: https://pypi.org/project/typevet/0.2.0/.
Source: https://alberto-codes.github.io/typevet/how-to/use-typevet-as-a-judgevet-provider/.

The examples below keep `FakeSystemOnePort` as a stand-in provider. typevet is
not a judgevet dependency, and the documentation check runs these examples
offline. Replace `FakeSystemOnePort` with `TypevetSystemOnePort` or your own
provider.

## Compatible in shape, not equivalent in judgment

**A provider that satisfies `SystemOnePort` is compatible in shape, not equivalent in judgment.**
The port fixes the question and answer types. It does not fix what the model
answers. Calibration does not transfer between judge models. A threshold or
policy tuned against Jev needs new evidence on another provider.

Huang and coauthors found that fine-tuned judge models score high on in-domain
test sets. The same models underperform GPT-4 on generalizability, fairness
and adaptability.
Source: https://arxiv.org/abs/2403.02839.

Fiedler shows that a calibration shared across compared models can bias the
comparison severely. In a real-data case, the comparison reversed direction.
Source: https://arxiv.org/abs/2605.06939.

typevet plans a study of agreement between Jev and its Gemma 4 judge. That
study has no results yet.
Source: https://github.com/Alberto-Codes/typevet/issues/252.

## Select the provider in Python

`provider_scope` from `judgevet.providers` takes exactly one of `port` or
`factory`. A factory returns a context manager that yields the provider. The
scope enters that context, validates the provider and runs cleanup exactly
once. A borrowed `port` stays open after the scope ends.

Save this program as `self_hosted_judgment.py` and run it with your Python
interpreter. It runs offline:

```python
from contextlib import AbstractContextManager, nullcontext

from judgevet import JudgmentRecord, Noul, NoulAnswer
from judgevet.ports import SystemOnePort
from judgevet.providers import provider_scope
from judgevet.testing import FakeSystemOnePort


class ListSink:
    def __init__(self) -> None:
        self.records: list[JudgmentRecord] = []

    def record(self, record: JudgmentRecord) -> None:
        self.records.append(record)


sink = ListSink()


def self_hosted_factory() -> AbstractContextManager[SystemOnePort]:
    provider = FakeSystemOnePort(answers={"billing": NoulAnswer(noul=0.9)}, audit=sink)
    return nullcontext(provider)


with provider_scope(factory=self_hosted_factory) as port:
    response = port.system_one(
        state="I was charged twice.",
        questions={"billing": Noul(instructions="Is this about billing?")},
        model="application-model",
    )

print(response.model, response.nouls["billing"].noul)
record = sink.records[0]
print(record.requested_model, record.resolved_model)
```

Expected outcome: two lines on stdout. The first line carries the model and
the probability. The second line carries the requested and resolved models.

## Read the model identity

The model identity appears in two places:

- `SystemOneResponse.model` holds the model that the provider reports for
  one call.
- A `JudgmentRecord` holds `requested_model` and `resolved_model`.
  `resolved_model` is `None` unless the call succeeded.

The fake echoes the requested model, so both values match here. A
self-hosted provider reports its own identifier. judgevet does not add audit
records to an arbitrary provider. The HTTP adapters and the fakes write them
through an `AuditSink`. Record both model identifiers with each judgment. A
later reader can then tell which model answered.
Source: https://github.com/Alberto-Codes/judgevet/issues/202#issuecomment-5850672112.

## Run the CLI on the provider

`create_cli_app` from `judgevet.adapters.inbound.cli` returns a Typer
application. Pass `provider_factory` for an owned provider or `port` for a
borrowed one. The installed `judgevet` command keeps its hosted behavior.
Save this module as `self_hosted_cli.py`:

```python
from contextlib import AbstractContextManager, nullcontext

from judgevet.adapters.inbound.cli import create_cli_app
from judgevet.ports import SystemOnePort
from judgevet.testing import FakeSystemOnePort


def self_hosted_factory() -> AbstractContextManager[SystemOnePort]:
    return nullcontext(FakeSystemOnePort())


app = create_cli_app(provider_factory=self_hosted_factory)
```

The factory runs once per command, and its cleanup runs after each command.
See [CLI provider selection](use-cli-policy.md#select-an-application-provider).

## Serve MCP on the provider

The `judgevet-mcp` command keeps its hosted defaults and takes no provider.
An agent-facing self-hosted judge is a small launcher that calls `main` from
`judgevet.adapters.inbound.mcp_entrypoint`. It needs no new server. Install
`judgevet[mcp]` in the launcher environment. Save this module as
`self_hosted_mcp.py`:

```python
from contextlib import AbstractContextManager, nullcontext

from judgevet.adapters.inbound.mcp_entrypoint import main
from judgevet.ports import SystemOnePort
from judgevet.testing import FakeSystemOnePort


def self_hosted_factory() -> AbstractContextManager[SystemOnePort]:
    return nullcontext(FakeSystemOnePort())


def serve() -> int:
    return main(provider_factory=self_hosted_factory, model="application-model")
```

`serve` returns the exit code of `main`. The `model` argument is the model
that the server requests from your provider.

Declare both modules as console scripts in the `[project.scripts]` table of
your application's `pyproject.toml`. Map `self-hosted-judge` to
`self_hosted_cli:app`. Map `self-hosted-judge-mcp` to `self_hosted_mcp:serve`.

Configure the MCP host to run `self-hosted-judge-mcp` in place of
`judgevet-mcp`. The host setup is otherwise the same as in
[Connect MCP](connect-mcp.md#vs-code). See
[Run an application provider](connect-mcp.md#run-an-application-provider) for
provider lifetime.

## Check the provider with the conformance kit

The `conformance` extra adds pytest, anyio and `judgevet.testing.conformance`.
Install `judgevet[conformance]` in the provider's test environment. Subclass
`BaseProviderConformance` in the provider's test suite. Override two fixtures:

- `provider_factory` returns the provider's factory.
- `failing_port` returns a port whose call raises a `ProviderError` subclass.

Override `media_port` when the provider supports images. The kit then sends
one kit-owned image of a declared type through `judge_with_images`. The media
port must return answers that the kit policy accepts. Override
`provider_model` to test a model label other than the kit default. The
`provider_port` fixture enters one scope of your factory; override it only for
a special case. The kit needs no credentials and no inference dependency.

Subclass `BaseAsyncProviderConformance` for an `AsyncSystemOnePort` provider.
It checks the port shape, that awaited answers pass the kit policy, and that
an awaited failure raises a `ProviderError` subclass. Override two fixtures:
`provider_factory` returns a callable whose async context manager yields the
port, and `failing_port` returns a port whose awaited call fails. Each rule
runs its coroutine with `anyio.run`, so the kit needs no async pytest plugin.
Source: https://github.com/Alberto-Codes/judgevet/issues/246.
The async kit also runs the three scope rules through `async_provider_scope`.
Each scope must get its own context, exit once and let a body exception
propagate.
Source: https://github.com/Alberto-Codes/judgevet/issues/251.
The media rules are synchronous only for now.
Annotate the synchronous fixture with `ProviderFactory` from
`judgevet.providers`. Annotate the async fixture with `AsyncProviderFactory`
from `judgevet.testing.conformance` or `judgevet.providers`.
Source: https://github.com/Alberto-Codes/judgevet/issues/277.

The kit source contains a minimal subclass in its module example. See the
[conformance kit reference](../reference/api.md#offline-fakes) and the
[kit source](../../src/judgevet/testing/conformance.py). A passing kit shows
compatible shape. It does not show equivalent judgment.
Source: https://github.com/Alberto-Codes/judgevet/issues/241#issuecomment-5902293909.
