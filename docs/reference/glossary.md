---
status: draft
---

# Glossary

Status: **draft**. Definitions follow the shipped typed contract. Service
observations cover only the cases listed in the [evidence ledger](../../STATUS.md#what-is-verified-and-what-is-not).
The numeric examples below are illustrative, not recorded service answers.

## Canonical vocabulary

Use this table for authored prose about judgevet. Its preferred and avoided
columns are the source for terminology enforcement. Apply each row only in its
stated context; ordinary technical uses outside that context remain valid.

| Preferred | Avoid | Context | Check |
|---|---|---|---|
| question | `prompt`; `query` | An evaluation instruction supplied to Jev. | question |
| answer | `response`; `result` | A judgment for one named question. HTTP responses and function results are different concepts. | answer |
| confidence | `certainty` | The reported Choice or Score confidence value. | confidence |
| score | `confidence` | The value on a Score rubric. This is a semantic distinction, not a global word replacement. | human |
| port | `interface` | The typed boundary used by judgevet callers and adapters. Other interfaces retain their own names. | boundary |
| adapter | `implementation`; `driver` | A judgevet component connecting that boundary to HTTP, CLI or MCP. | adapter |
| verified | `documented` | A claim described as observed against the live service. Vendor documentation alone is insufficient. | human |
| model judgment | `calibrated judgment` | A model answer whose statistical calibration has not been established here. | always |
| typed client | `—` | judgevet as a Python library. This description is accurate and permitted. | human |

The Check column selects a bounded lexical context. `human` rows require
semantic review; they do not trigger a global word replacement. The
[writing guide](../maintainers/writing-guide.md#check-terminology) defines the
selectors and the safe source-identifier scope.

These preferences do not rename public APIs. Preserve exact Python identifiers,
JSON fields, third-party API names and quoted diagnostics. Use code formatting
for literals such as `SystemOneResponse`, `result`, `instructions`, and
`HTTPSystemOneAdapter`. A statement about an HTTP response may use that term;
it does not mean the answer to an individual question.

A lexical check cannot decide whether a number is a score or confidence, or
whether evidence justifies a claim. Human review must check those meanings.
The examples and definitions below supply that context.

## Inputs and answers

### State

The content to evaluate: text, a JSON object or a JSON array. For example,
`"I was charged twice"` is state. It is distinct from the question asked about
that content. See the vendor's [API request definition](https://docs.typesafe.ai/api)
and judgevet's [port types](../../src/judgevet/ports/__init__.py).

### Question

A named evaluation instruction expressed as `Noul`, `Choice` or `Score`.
For the state above, `"Is this about billing?"` can be the instructions for a
Noul question named `billing`. The name lets the caller find its answer.
See [question types](../../src/judgevet/domain/questions.py) and the
[vendor request format](https://docs.typesafe.ai/api).

### Answer

The typed judgment for one question: `NoulAnswer`, `ChoiceAnswer` or
`ScoreAnswer`. For example, a Noul answer can contain `noul=0.8`.
`SystemOneResponse` is the container for named answers, resolved model and
usage; it is not another question type. See [answer types](../../src/judgevet/domain/answers.py)
and the [vendor answer format](https://docs.typesafe.ai/api).

### Noul

A yes/no question answered with the model's probability of yes. A value of
`0.8` is not a Python boolean and does not measure how much billing occurred.
Noul has no separate confidence field. See [TypeSafe's Noul definition](https://docs.typesafe.ai/primitives/noul).

### Choice

A question that selects a named alternative. A routing question might offer
`billing` and `technical`. Its answer contains the selected label,
probabilities for the alternatives, and confidence. See
[TypeSafe's Choice definition](https://docs.typesafe.ai/primitives/choice).

### Score

A question that evaluates an ordered rubric. Criteria such as
`["Can wait", "This week", "Today"]` define levels starting at zero.
Its answer contains a numeric score, probabilities for levels, a legend and
confidence. Capitalized `Score` names the question type; lowercase **score**
names the numeric value. See [TypeSafe's Score definition](https://docs.typesafe.ai/primitives/score).

### Criteria

Descriptions that define outcomes or rubric levels. Noul uses optional
`true` and `false` descriptions. Choice maps labels to descriptions.
Score uses an ordered list of descriptions. For example, a Choice criterion
`"billing": "Payments and refunds"` explains that label's meaning.
See the [Noul](https://docs.typesafe.ai/primitives/noul),
[Choice](https://docs.typesafe.ai/primitives/choice) and
[Score](https://docs.typesafe.ai/primitives/score) request definitions.

## Numbers and decisions

### Probability

A model-reported value from zero to one for an outcome. Noul supplies the
probability of yes; Choice and Score supply per-option or per-level values.
For example, `noul=0.8` reports probability, not a local acceptance decision.
See the primitive definitions above. These values do not establish measured
accuracy on your data.

### Confidence

The model-reported confidence associated with a Choice selection or a Score
value, from zero to one. It is separate from the selected label or score.
For example, a score of `1.6` and confidence of `0.7` describe different things.
See the [Choice](https://docs.typesafe.ai/primitives/choice) and
[Score](https://docs.typesafe.ai/primitives/score) answer definitions.
The vendor Choice page defines Choice confidence as "A number from 0 to 1
computed from how `probabilities` is spread. A flat shape, with probability
spread across several options, means low confidence. A single peak on one
option means high confidence." Source: https://docs.typesafe.ai/primitives/choice.
The page publishes no formula. Choice confidence is not `probabilities[choice]`.
Source: https://docs.typesafe.ai/confidence.
The [Choice confidence reference](api.md#choice-confidence) records the
observed values and the open question.
judgevet has not established statistical calibration: confidence `0.7` is not
proof that 70% of comparable judgments are correct.

### Score value

The numeric value on the question's rubric. It can fall between levels.
On a zero-to-two rubric, `1.6` is a score, not a probability or confidence.
The vendor describes it as the probability-weighted average of the levels.
For illustrative probabilities `0.1`, `0.2`, `0.7`, that average is
`0 × 0.1 + 1 × 0.2 + 2 × 0.7 = 1.6`.
See [TypeSafe's Score answer definition](https://docs.typesafe.ai/primitives/score).

### Policy

Application-defined rules evaluated locally against typed answers. A policy
produces a binary acceptance decision: pass or fail. It does not ask the model
another question and does not prove that an accepted judgment is correct.
For example, a Noul minimum of `0.8` accepts `0.8` and rejects `0.79`; the bound
is inclusive. Missing or invalid required answers raise an error instead of
returning an unmet-policy decision. See the [typed policy guide](../how-to/use-policy-library.md)
and [policy evaluation source](../../src/judgevet/domain/policy_evaluation.py).
Thresholds in examples are teaching values, not universal recommendations.

## Architecture

### Port

The typed contract through which callers request judgments. `SystemOnePort`
and `AsyncSystemOnePort` describe synchronous and asynchronous calls.
For example, a caller can receive a compatible fake port in a test.
See the [port protocols](../../src/judgevet/ports/__init__.py).

### Adapter

A component connecting a port to a particular entry point or external service.
The HTTP adapter calls Jev. CLI and MCP are inbound adapters that accept user
or host input. For example, changing how CLI input is read does not require
adding file operations to the pure domain. See the
[HTTP adapter](../../src/judgevet/adapters/outbound/http.py) and
[architecture contracts](../../pyproject.toml).

## Evidence and documentation status

### Verified

A claim supported by an identified check within a stated scope. **Live verified**
means a call exercised the behavior against the service. For example, a recorded
401 call verifies that observed error shape. A synthetic test can verify a
local comparison or parser, but cannot establish an unseen service body.
See the [evidence ledger](../../STATUS.md#what-is-verified-and-what-is-not).

### Documented and inferred

**Documented** means a source states the behavior. **Inferred** means the
expectation has not been established by the relevant observation. Vendor
statements can support a documented expectation while it remains unverified
against the live service here. The 429 and 529 bodies remain unseen.
A fixture copied from documentation does not promote them to live verified.
If sources disagree, retain both citations and state the open question.

### Sketch, draft and stable

These are page trust statuses, not judgments about writing polish.

- **Sketch:** a proposal or an unproven description. Flag it before writing code
  against it. For example, a proposed capability is not a shipped feature.
- **Draft:** usable guidance with explicit evidence limits. The current API
  reference is draft because some service behavior remains unseen.
- **Stable:** a claim that the required evidence is established. Under this
  repository's rules, no page reaches stable while a documented status code
  remains unseen. Editing prose or passing offline tests does not qualify.

See the [repository trust rules](../../AGENTS.md#trust-levels). Keep each
claim's scope explicit even when a page has a single status marker.
