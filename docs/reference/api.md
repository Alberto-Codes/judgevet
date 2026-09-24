---
status: draft
---

# Python API reference

Status: **draft**. Success and 401/422 bodies have live evidence. The 429/529
bodies, resolved models other than `jev-1.13.0`, and untouched fields remain
inferred. See the [evidence ledger](../../STATUS.md#what-is-verified-and-what-is-not).

The [supported imports](compatibility.md) enumerate the root exports and policy
facades. Generated Python reference in the site provides source signatures;
this page records their semantics. [Configuration](configuration.md),
[errors](errors.md) and [policies](policy.md) describe the related contracts.
The [glossary](glossary.md) distinguishes probability, confidence and score.

## Question types

`Question` is `Noul | Choice | Score`. These are mutable local objects, not
service-side validation results. Their constructors do not validate every
vendor constraint. Typed objects and raw question mappings are accepted by the
HTTP adapters, including mixed mappings.

| Type | Constructor arguments | Meaning and source |
|---|---|---|
| `Noul` | `instructions=None`, `criteria=None` | Yes/no question; optional criteria use `true` and `false` descriptions. [Noul](https://docs.typesafe.ai/primitives/noul) |
| `Choice` | required `criteria`, `instructions=None` | Named alternatives mapped to descriptions. [Choice](https://docs.typesafe.ai/primitives/choice) |
| `Score` | required `criteria`, `instructions=None` | Ordered rubric descriptions; positions start at zero. [Score](https://docs.typesafe.ai/primitives/score) |

`instructions` accepts a string, dictionary, sequence or `None` in the Python
annotations. Choice descriptions accept those same forms; Score descriptions
accept strings, dictionaries or sequences. Noul criteria accepts a dictionary.
These annotations are not evidence that every possible value has been exercised
against the service. Prefer the simple text examples in the task guides.

Choice copies its criteria into a dictionary; Score copies its criteria into a
list. These are shallow copies. Noul keeps its supplied criteria reference.
The [question source](../../src/judgevet/domain/questions.py) defines the exact
Python types. The outbound adapter adds the wire `type` and omits optional
`None` instructions/criteria when converting typed questions.

## Adapters and ports

`HTTPSystemOneAdapter` and `AsyncHTTPSystemOneAdapter` implement the synchronous
and asynchronous calls respectively. Their constructors accept `api_key`,
`base_url`, `default_model`, `transport`, `timeout_seconds`, `retry`, `network`
`gateway` and `redactor`; see the
[defaults and validation table](configuration.md#direct-python-adapters).
Both send the [documented request](https://api.typesafe.ai/docs) to
`POST /v1/systemone` with bearer authentication by default. Explicit
[gateway configuration](configuration.md#gateway-authentication-and-metadata)
selects alternate authentication, path prefixes and metadata. Optional
[state redaction](configuration.md#caller-owned-state-redaction) transforms a
private copy before serialization and reuses the resulting bytes across retries.

| Call argument | Python contract |
|---|---|
| `state` | Required string, dictionary or list containing the content to judge. |
| `questions` | Required mapping from caller-chosen names to typed questions or raw mappings. |
| `model` | Optional string on the concrete adapters; omitted/empty uses the constructor default. |
| `metadata` | Keyword-only `RequestMetadata` on concrete HTTP adapters; overrides gateway default headers. |

`system_one` returns `SystemOneResponse`; the async call must be awaited. By default, one
call produces one HTTP request. Optional [retry limits](configuration.md#retry-limits)
permit bounded additional attempts. The adapters parse
wire answers into domain types. Successful parsing does not validate the
judgment's quality or guarantee an answer for every supplied name. See
[error boundaries](errors.md#retry-and-exception-boundaries).

Use `with` or `close()` for sync ownership and `async with` or awaited `aclose()`
for async ownership. The async adapter has no synchronous close/context-manager
API. The caller owns construction and cleanup, including after a failed call.
See the [sync](../how-to/use-library.md) and [async](../how-to/use-async-library.md)
recipes.

`SystemOnePort` and `AsyncSystemOnePort` are structural protocols, not client
factories. They declare the same state and question inputs and typed return,
but require the `model` argument. Only the concrete adapters offer a default
for that call argument. Transport-specific metadata is also limited to the
concrete HTTP adapters. The async port declares an async method. Neither port
requires lifecycle methods; ownership belongs to the code that creates the
concrete adapter. See [port signatures](../../src/judgevet/ports/__init__.py).

## Answer and container types

`Answer` is `NoulAnswer | ChoiceAnswer | ScoreAnswer`.

| Type | Required fields | Semantics |
|---|---|---|
| `NoulAnswer` | `noul: float` | Probability of true; no confidence field. [Noul source](https://docs.typesafe.ai/primitives/noul) |
| `ChoiceAnswer` | `choice: str`, `confidence: float`, `probabilities: dict[str, float]` | Selected label, confidence and distribution over labels. [Choice source](https://docs.typesafe.ai/primitives/choice) |
| `ScoreAnswer` | `score: float`, `confidence: float`, `legend: dict[int, str]`, `probabilities: dict[int, float]` | Continuous expected score, confidence and rubric/distribution indexed by level. [Score source](https://docs.typesafe.ai/primitives/score) |
| `Usage` | None required; `input_tokens=None`, `output_tokens=None` | Optional nonnegative integer token counts; booleans are rejected. [Wire fields](https://docs.typesafe.ai/api.md) |
| `SystemOneResponse` | `model: str`, `usage: Usage`; `answers` defaults to a new empty dictionary | Answer mapping keyed by question name. The observed service model is the resolved version, not necessarily the requested alias. [Wire envelope](https://docs.typesafe.ai/api.md) |

Token counts are usage metadata, not a price quote. This client reference makes
no current pricing or retention claim.

Answer constructors require finite integer or float values for Noul, Score,
confidence and each probability. Booleans and nonnumeric values raise `TypeError`.
NaN, either infinity and out-of-range values raise `ValueError`. Constructors
retain inclusive probability/confidence bounds of `[0,1]`, choice membership,
matching Score legend/distribution keys, inclusive score range and the
probability-sum tolerance of `1e-6`. They do not enforce argmax selection or
expected-score equality. Public policy evaluation also checks values when it
consumes an answer; see [policy validation](policy.md#evaluation-and-reports).
The [answer source](../../src/judgevet/domain/answers.py) is authoritative for
constructor behavior. Do not infer service guarantees from local checks.

Answer, Usage and response instances are frozen dataclasses. Frozen prevents
attribute reassignment, not mutation of nested dictionaries. `answers`,
`probabilities` and `legend` can remain mutable. The container properties
`nouls`, `choices` and `scores` each return a fresh shallow dictionary filtered
by answer type. Their values are the same answer objects. Missing names or
wrong-type names raise normal `KeyError` when indexed in a filtered mapping.

## Examples

### Basic Usage

These examples require `TYPESAFE_API_KEY` in the process environment. The
application reads it and passes it explicitly. Do not put the key in source
code. Both examples send the supplied state and questions to the service;
read the [security policy](../../SECURITY.md#data-sent-to-the-service) first.
The answer values vary. The assertions check types and valid ranges, not
whether the model made a correct judgment.

```python
import os

from judgevet import Choice, ChoiceAnswer, HTTPSystemOneAdapter, Noul, NoulAnswer

adapter = HTTPSystemOneAdapter(api_key=os.environ["TYPESAFE_API_KEY"])
try:
    response = adapter.system_one(
        state="I was charged twice for my plan",
        questions={
            "is_refund": Noul(instructions="Is this about a refund?"),
            "queue": Choice(
                criteria={
                    "billing": "Payments and refunds",
                    "technical": "Product faults",
                },
                instructions="Which queue should handle this message?",
            ),
        },
    )
finally:
    adapter.close()

refund = response.answers["is_refund"]
queue = response.answers["queue"]
assert isinstance(refund, NoulAnswer)
assert isinstance(queue, ChoiceAnswer)
assert 0 <= refund.noul <= 1
assert queue.choice in {"billing", "technical"}
```

### Context Manager

The context manager closes the adapter even when a call raises.

```python
import os

from judgevet import HTTPSystemOneAdapter, Noul, NoulAnswer

with HTTPSystemOneAdapter(api_key=os.environ["TYPESAFE_API_KEY"]) as adapter:
    response = adapter.system_one(
        state="I was charged twice for my plan",
        questions={"is_refund": Noul(instructions="Is this about a refund?")},
        model="jev-1.13.0",
    )

answer = response.answers["is_refund"]
assert isinstance(answer, NoulAnswer)
assert 0 <= answer.noul <= 1
```

The vendor documents the [request and answer format](https://docs.typesafe.ai/api.md)
and the [Noul](https://docs.typesafe.ai/primitives/noul) and
[Choice](https://docs.typesafe.ai/primitives/choice) primitives.
Adapter ownership and explicit key injection are judgevet behavior; see the
[adapter source](../../src/judgevet/adapters/outbound/http.py).
