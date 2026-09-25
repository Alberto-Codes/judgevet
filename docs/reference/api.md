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

### Choice criteria values

Each value in a Choice `criteria` map takes one of four forms.

| Form | Meaning | Source | Evidence |
|---|---|---|---|
| string | A plain-text description of the option. | [Choice](https://docs.typesafe.ai/primitives/choice) | Verified. The live tests send only string values. |
| object | Structured guidance, such as what the option covers, what it does not cover and example inputs. | [Structured instructions and criteria](https://docs.typesafe.ai/primitives/choice#structured-instructions-and-criteria) | Inferred from the page. No call has sent it. |
| array | An accepted form. The page gives no array example. | [Choice](https://docs.typesafe.ai/primitives/choice) | Inferred from the page. No call has sent it. |
| `None` (`null`) | The option needs no extra detail. | [API reference](https://docs.typesafe.ai/api) | Inferred from the page. No call has sent it. |

The Choice page states that "each entry in `criteria` can be a string, an
object, or an array". The API reference types `criteria` as
`map<string, string | object | array | null>` and states "use null when an
option needs no extra detail".

**Open question:** the two pages disagree on `null`. The Choice page lists
three forms and omits `null` from that list, although one of its later request
examples sends `null` descriptions. The API reference lists `null` as a fourth
form. No call from this repository has sent `null`, so the service behaviour is
unknown.

Choice copies its criteria into a dictionary; Score copies its criteria into a
list. These are shallow copies. Noul keeps its supplied criteria reference.
The [question source](../../src/judgevet/domain/questions.py) defines the exact
Python types. The outbound adapter adds the wire `type` and omits optional
`None` instructions/criteria when converting typed questions.

## Adapters and ports

`HTTPSystemOneAdapter` and `AsyncHTTPSystemOneAdapter` implement the synchronous
and asynchronous calls respectively. Their constructors accept `api_key`,
`base_url`, `default_model`, `transport`, `timeout_seconds`, `retry`, `network`,
`gateway`, `redactor`, `spend_cap` and `audit`; see the
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

## Offline fakes

`judgevet.testing` provides `FakeSystemOnePort` for `SystemOnePort` and
`AsyncFakeSystemOnePort` for `AsyncSystemOnePort`. They ship in the installed
package without an extra and import only the domain, the ports and the
request-id binding in `judgevet.diagnostics`. Each takes `seed: int = 0` and
`answers: Mapping[str, Answer] | None`, and records each call's
`(state, questions, model)` in `calls`. A scripted name returns its answer.
Other typed questions receive seeded answers that pass the answer
constructors; an unscripted raw mapping raises `TypeError`. The response echoes
the `model` argument and carries the scripted `usage`, default `Usage()`. A
scripted `error` is raised after the call is recorded. The fakes accept the
same `spend_cap` and `audit` options as the HTTP adapters and honour them the
same way. Seeded answers are local test data, not service behaviour. See the
[offline testing recipe](../how-to/test-offline.md) and the
[fake source](../../src/judgevet/testing.py).

## Answer and container types

`Answer` is `NoulAnswer | ChoiceAnswer | ScoreAnswer`.

| Type | Required fields | Semantics |
|---|---|---|
| `NoulAnswer` | `noul: float` | Probability of true; no confidence field. [Noul source](https://docs.typesafe.ai/primitives/noul) |
| `ChoiceAnswer` | `choice: str`, `confidence: float`, `probabilities: dict[str, float]` | Selected label, confidence and distribution over labels. The vendor defines `confidence` as a number from 0 to 1 computed from how `probabilities` is spread. It is not `probabilities[choice]`. See [Choice confidence](#choice-confidence). Source: https://docs.typesafe.ai/primitives/choice. Source: https://docs.typesafe.ai/confidence. |
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
probability-sum tolerance of `0.005` per probability. They do not enforce argmax selection or
expected-score equality. Public policy evaluation also checks values when it
consumes an answer; see [policy validation](policy.md#evaluation-and-reports).
The [answer source](../../src/judgevet/domain/answers.py) is authoritative for
constructor behavior. Do not infer service guarantees from local checks.

Both HTTP adapters and both offline fakes check each Choice answer against the
question the caller sent. The answer's `choice` and every `probabilities` key
must be a key of that question's `criteria`. Otherwise the call raises
`JevResponseError` with status 200, and the message names the question and the
option. `probabilities` may cover a subset of the criteria. The adapters run
the check when they parse the body, before the spend cap settles the attempt.
A raw question mapping is checked when its `type` is `"choice"` and its
`criteria` is a mapping. Other questions and unasked answer names are not
checked. The criteria keys are the Choice options. Source:
https://docs.typesafe.ai/primitives/choice. No live call has returned an
off-list option, so the check guards an inferred failure.

Wire precision: one consumer call on 2026-09-24 against `jev-1.13.0` returned a
four-level Score whose probabilities summed to 0.99
([issue #175](https://github.com/Alberto-Codes/judgevet/issues/175)). Two-decimal
rounding can move each probability by up to 0.005, so constructors accept a sum
within `0.005 × k` of 1.0 for `k` probabilities. That call is the only
observation. This repository's live suite has not reproduced it, and it does not
establish a general rounding rule for the service.

Answer, Usage and response instances are frozen dataclasses. Frozen prevents
attribute reassignment, not mutation of nested dictionaries. `answers`,
`probabilities` and `legend` can remain mutable. The container properties
`nouls`, `choices` and `scores` each return a fresh shallow dictionary filtered
by answer type. Their values are the same answer objects. Missing names or
wrong-type names raise normal `KeyError` when indexed in a filtered mapping.

## Choice confidence

The vendor Choice page defines the field: "A number from 0 to 1 computed from
how `probabilities` is spread. A flat shape, with probability spread across
several options, means low confidence. A single peak on one option means high
confidence." The same page defines `choice` as "The option with the highest
probability." Source: https://docs.typesafe.ai/primitives/choice.

The page publishes no formula. The vendor Confidence page calls the field "a
statistic computed from the probability distribution the answer already gives
you" and publishes no service formula either. Source:
https://docs.typesafe.ai/confidence. `confidence` is a spread measure. It is not
`probabilities[choice]`, and callers must not read it as that probability.
The client checks only that `confidence` lies in `[0, 1]`. It checks no
relation between `confidence` and `probabilities`.

Two live runs recorded a Choice `confidence`. The 0.11.0 production smoke on
2026-09-25 returned `confidence=0.89` for `choice='a'`. Source:
https://github.com/Alberto-Codes/judgevet/issues/186#issuecomment-5825514560.
That comment elides the probabilities. The issue that reports the run records
the full answer as
`ChoiceAnswer(choice='a', confidence=0.89, probabilities={'b': 0.05, 'a': 0.95})`.
Source: https://github.com/Alberto-Codes/judgevet/issues/187. The 0.10.2
production smoke on 2026-09-25 returned `confidence=0.9` for `choice='a'` and
elides the probabilities. Source:
https://github.com/Alberto-Codes/judgevet/issues/183#issuecomment-5824552631.
The 0.89 value is consistent with the vendor definition. The 0.9 run recorded
no probabilities, so it cannot be compared.

**Open question:** the formula that maps `probabilities` to `confidence`.
No source publishes it, and no differential live test has measured it.

## Service limits

The [TypeSafe models page](https://docs.typesafe.ai/models.md) states these
limits. This section records that page as fetched on 2026-09-24. The values
are vendor statements. Two judgevet calls on 2026-09-25 tested the context
budget. Neither call established where the threshold lies.

The service enforces these limits. judgevet does not check them before a call.
It counts no tokens, because the vendor documents no tokenizer. It does not
throttle requests.

| Limit | Value the page states for `jev-1.13.0` |
|---|---|
| Context length | "64k tokens per request; 32k tokens for `state` plus the longest question" |
| Rate limits | "250,000 tokens per second / 1,200 requests per minute" |
| Input | "Text only. String, JSON object, or array of text values. No image, audio, or video input." |

The page explains the two context budgets. The 64k budget "covers the `state`
plus all questions combined". The 32k budget "applies to the `state` plus the
single longest question".
Source: https://docs.typesafe.ai/models.md.

Size a request against both budgets. The `state` and the longest single
question share the 32k-token budget. The whole request shares the 64k-token
budget. Size the `state` against 32k tokens minus the longest question. The page
does not state how the other questions count toward the 64k budget beyond
"all questions combined".

A request over the budget fails. One call sent a 400,000-character state with
one `noul` question to `jev-1.13.0`. The service returned status 400 with the
body `{"detail": {"error_type": "max_tokens_exceeded"}}`.
Source: https://github.com/Alberto-Codes/judgevet/issues/39#issuecomment-5825759575.
The client raises `JevMaxTokensExceededError`, a subclass of `JevRequestError`
with `retryable=False`. The adapter matches the `max_tokens_exceeded` marker,
not the status. The body does not say which budget the request exceeded. That
request exceeded both budgets, so the call proves the marker, not the
threshold. See the [error reference](errors.md).

A second call sent a 2,959-byte JSON state and seven `choice` questions with up
to 16 options. The service returned 200 and reported 3,110 input tokens.
Source: https://github.com/Alberto-Codes/judgevet/issues/39#issuecomment-5825777868.

The page says a request over either rate limit "returns `429 Too Many
Requests`". judgevet has never observed a 429 body. See the
[evidence ledger](../../STATUS.md#what-is-verified-and-what-is-not).

The page warns that the rate limits change. Its warning reads "Rate limits are
adjusting dynamically." It also says "the limits above can change without
notice". Check the cited page before you size a workload.

The page names two aliases. Both point to `jev-1.13.0` on the fetch date.

| Alias | Points to |
|---|---|
| `jev-latest` | `jev-1.13.0` |
| `jev-preview` | `jev-1.13.0` |

The page states that "an alias moves when a new release ships, so the
answers behind it can change without a change on your side". Pin a
versioned ID to keep one model.

On language, the page states that "English is the primary training language".
It also states that other languages "are handled but not equally well".

**Open question:** the page does not say which status code a request over the
context length returns. It also does not name the error body for that case.

**Open question:** the page does not say how the service counts tokens. A
caller cannot compute the context budget locally before a call.

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
