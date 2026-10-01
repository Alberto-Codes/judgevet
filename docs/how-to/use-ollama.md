---
status: draft
---

# Use Ollama as a local server

Status: **draft**. This page follows Ollama's documentation and one
recorded call. On 2026-09-30, release 0.15.0 called Ollama 0.35.0 with
`nimble:latest` (9.0B, Q8_0). The adapter parsed the choice, noul and score
answers unchanged. That is one call, one model and one machine.
It shows a compatible response shape, not equivalent judgment.
Source: https://github.com/Alberto-Codes/judgevet/issues/268#issuecomment-5917968541.

Use this recipe to run judgevet against a decision model on your own machine.
Ollama is a second server behind the hosted adapter, `HTTPSystemOneAdapter`.
It is not a provider. judgevet needs no code change and no extra install.
Source: https://github.com/Alberto-Codes/judgevet/issues/268.

For a judgment model that your application hosts behind its own port, see
[Use a self-hosted judgment provider](use-a-self-hosted-provider.md).

## What Ollama serves

Ollama 0.35 serves `POST /v1/systemone` on `http://localhost:11434`. The
endpoint has the same wire shape as the Jev API.
Source: https://docs.ollama.com/api/systemone.
Source: https://ollama.com/blog/ollama-now-supports-jev-style-decision-models.

Ollama calls a System One model a **decision model**. Three models run locally:

- `nimble`: 9B parameters, from Bespoke Labs.
  Source: https://ollama.com/library/nimble.
- `tev1`: 4B parameters, from Together AI.
  Source: https://ollama.com/blog/ollama-now-supports-jev-style-decision-models.
- `tev1:0.8b`: a smaller `tev1` variant.
  Source: https://ollama.com/blog/ollama-now-supports-jev-style-decision-models.

The endpoint accepts three question types. Choice takes 2 to 26 options.
Noul takes one yes/no question. Score takes 2 to 26 levels.
Source: https://docs.ollama.com/capabilities/decision.

## Pull a model

Pull `nimble` with the Ollama CLI:

```bash
ollama pull nimble
```

Source: https://ollama.com/blog/ollama-now-supports-jev-style-decision-models.

## Point judgevet at Ollama

Set the base URL and a placeholder key in the shell that runs judgevet:

```bash
export TYPESAFE_BASE_URL=http://localhost:11434
export TYPESAFE_API_KEY=ollama
```

`JEV_API__BASE_URL` and `JEV_API__KEY` are the equivalent names. See
[configuration](../reference/configuration.md). judgevet accepts plaintext
`http://` only for `localhost` and `127.0.0.1`. Any other host needs
`https://`. Source: [settings](../../src/judgevet/adapters/inbound/settings.py).

A local Ollama request needs no API key.
Source: https://docs.ollama.com/capabilities/decision.
judgevet still requires a key before it builds the adapter, so the
placeholder `ollama` fills that slot. judgevet sends it in the
`Authorization` header.

## Allow time for the first load

judgevet waits 30 seconds for a reply by default. The first call after a
pull or an idle period loads the model onto the GPU. That load is the slow
part, and it can exceed 30 seconds. One maintainer call to a freshly pulled
`nimble` timed out, and the CLI exited 1 with `{"error": "timed out"}`.
Source: https://github.com/Alberto-Codes/judgevet/issues/268#issuecomment-5917968541.

Raise the timeout to 120 seconds, the value in Ollama's own SDK example:

```bash
export JEV_API__TIMEOUT_SECONDS=120
```

Source: https://ollama.com/blog/ollama-now-supports-jev-style-decision-models.
Source: [settings](../../src/judgevet/adapters/inbound/settings.py).
In Python, pass `timeout_seconds=120` to the adapter. You can also send one
warm-up call before the calls that matter.

The endpoint accepts a `keep_alive` request field. It controls how long the
model stays loaded after a call.
Source: https://docs.ollama.com/api/systemone.
judgevet does not send that field, so the server's setting applies. Raise it
in Ollama when your calls are far apart.

## Run the CLI

The CLI sends `--model` on every call, and its default is `jev-latest`.
Ollama does not serve `jev-latest`. Pass the local tag:

```bash
judgevet 'I was charged twice.' '{"billing":{"type":"noul","instructions":"Is this about billing?"}}' --model nimble --json
```

For the `judgevet-mcp` command, set `JEV_API__DEFAULT_MODEL=nimble` beside the
base URL. See [model selection](../reference/configuration.md) for how each
entry point picks its model.

## Call it from Python

Pass the base URL, a placeholder key and the model tag to the adapter. Save
this module as `ollama_judgment.py`:

```python
from judgevet import HTTPSystemOneAdapter, Noul, SystemOneResponse


def ask_ollama(state: str) -> SystemOneResponse:
    with HTTPSystemOneAdapter(
        api_key="ollama",
        base_url="http://localhost:11434",
        default_model="nimble",
    ) as adapter:
        return adapter.system_one(
            state=state,
            questions={"billing": Noul(instructions="Is this about billing?")},
            model="nimble",
        )
```

Importing the module sends no request. Call `ask_ollama` while Ollama runs.
The adapter passes `base_url` through without the settings check. Keep it
on a loopback host or `https://`.

## Handle errors

Errors still arrive as `Jev*` classes. The hosted adapter maps each HTTP status
the same way for any server. Every `JevError` is a `ProviderError`, so
`except ProviderError` catches them. See [errors](../reference/errors.md).

Ollama caps a request body at 64 KiB.
Source: https://docs.ollama.com/api/systemone.
An oversized request returns HTTP 413 with the body
`{"error": "request body must not exceed 64 KiB"}`. The API reference lists
the status codes 200, 400, 404, 413 and 500.
Source: https://docs.ollama.com/api/systemone.
judgevet maps that status to `JevRequestError`, as it maps every 4xx other
than 401, 403 and 429. When the body has no `detail` field, the adapter
appends the string `error` field to the exception message. The 413 text then
appears in the `JevRequestError`.
Source: https://github.com/Alberto-Codes/judgevet/commit/17f24f3.

## Read the answer

Ollama returns the answer fields that the Jev API returns. Two details
differ from Jev.

- `model` echoes the requested tag, such as `nimble`. Jev returns a resolved
  version. Record the tag as the model identity.
- Ollama does not support streaming, images, tools or generation controls.

Source: https://docs.ollama.com/api/systemone.

Probabilities arrive at full float precision, unlike the rounded examples in
Ollama's documentation. The Jev service has returned two decimals once
([STATUS](../../STATUS.md), #175).
Source: https://github.com/Alberto-Codes/judgevet/issues/268#issuecomment-5917968541.

The recorded call carried `usage` with `input_tokens` 826 and
`output_tokens` 4. That is observed once.
Source: https://github.com/Alberto-Codes/judgevet/issues/268#issuecomment-5917968541.

Ollama defines a Score value as the probability-weighted average of the
zero-based levels. That matches the Jev definition in the
[glossary](../reference/glossary.md#score-value).
Source: https://docs.ollama.com/capabilities/decision.

Ollama's confidence runs from 0 to 1. It measures how strongly the model
favors one answer. Ollama publishes no formula. Ollama states: "A higher
value does not guarantee the answer is correct."
Source: https://docs.ollama.com/capabilities/decision.

## Compatible in shape, not equivalent in judgment

A local model answers the same question types. It does not give the same
answers as Jev. A threshold tuned against Jev needs new evidence on `nimble`
or `tev1`. See
[Compatible in shape, not equivalent in judgment](use-a-self-hosted-provider.md#compatible-in-shape-not-equivalent-in-judgment).

On 2026-09-30, ten conformance kit tests passed against `nimble` on Ollama
0.35.0. The two media-port rules skipped because the hosted adapters supply
no media port.
Source: https://github.com/Alberto-Codes/judgevet/issues/267.

On 2026-10-01, 14 conformance kit tests passed and 4 skipped against
`nimble` on Ollama 0.35.0.
Source: https://github.com/Alberto-Codes/judgevet/issues/267.

Rerun the kit with
`pytest -m live -p no:randomly -rsx -v tests/live/test_ollama_kit_live.py`.
