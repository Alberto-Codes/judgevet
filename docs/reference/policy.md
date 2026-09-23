---
status: draft
---

# Policy reference

Status: **draft**. Policies compare answers locally. They make no service call
and do not establish model accuracy or calibration.

## Supported Python surface

Import the following from `judgevet.policy`. Signatures and docstrings are
provided by the [public facade](../../src/judgevet/policy.py) and generated
Python reference. Bounds are inclusive.

| Name | Arguments or meaning |
|---|---|
| `NoulRule` | `name`, `minimum=None`, `maximum=None` |
| `ChoiceRule` | `name`, `choice`, `min_confidence=None` |
| `ScoreRule` | `name`, `minimum=None`, `maximum=None`, `min_confidence=None` |
| `Rule` | Union of the three rule types. |
| `Policy` | `rules`: nonempty ordered tuple of uniquely named typed rules. |
| `ValidatedPolicy` | `policy`, `questions`: validates and snapshots constraints. |
| `validate_policy` | `(policy, questions) -> ValidatedPolicy`; equivalent validation path. |
| `evaluate_policy` | `(policy, answers) -> PolicyReport`; requires a validated policy. |
| `RuleReport` | `question`, `passed`, `detail` |
| `PolicyReport` | `rules`: ordered rule reports; derived `passed` is their conjunction. |
| `PolicyError` | Base local error, a `ValueError`. |
| `PolicyDefinitionError` | Invalid construction, JSON or question binding. |
| `PolicyAnswerError` | Missing or malformed selected answer. |

`judgevet.policy_json` exports `parse_policy(text, questions) -> ValidatedPolicy`.
It decodes JSON text and validates against typed questions. It does not read
files or stdin. Both facades are available from 0.7.0; these names are not root
exports. See [compatibility](compatibility.md).

## Construction and question validation

Names must be nonempty strings. Bounds must be finite nonnegative numbers;
booleans are rejected. Noul and confidence bounds are at most 1. Noul and Score
rules require at least one bound and require `minimum <= maximum` when both
exist. Confidence can add a minimum only to Choice or Score.

`Policy` rejects empty rules, untyped entries and duplicate names. It copies
its sequence to a tuple. Rules, policies and reports are frozen. Report
constructors require unique nonempty question names, boolean outcomes and
string details; aggregate reports cannot be empty.

Validation accepts a mapping of typed questions. Each selected question must
exist and match the rule type. Choice labels must be strings and the required
label must be present. Score criteria must be a nonempty list/tuple; each bound
must fit zero through `len(criteria) - 1`. Rules may select a subset of questions.

`ValidatedPolicy` snapshots Choice labels and Score scale limits without
retaining mutable question objects. Later edits to questions do not change an
existing policy's constraints. Construct a new validated policy to adopt new
constraints. See [validation source](../../src/judgevet/domain/policy_validation.py).

## Evaluation and reports

Evaluation checks every selected answer in rule order. Missing/wrong-type
answers raise `PolicyAnswerError`. Noul probability must be finite and within
0–1. Choice confidence must be finite and within 0–1, and the selected label
must belong to the snapshot. Score confidence must be finite and within 0–1;
score must be finite and within the snapshotted scale. Confidence is checked
even when the rule has no confidence predicate.

Extra answers are ignored. Evaluation checks selected scalars, not all
probability distributions or legend metadata. Those remain the answer types'
responsibility. Passing malformed values past an answer constructor does not
make them valid public policy input.

For valid answers, evaluation returns every `RuleReport`, including after an
unmet rule. `detail` describes comparisons. `PolicyReport.passed` is true only
when every rule passed. A malformed later answer raises instead of returning a
partial report. An unmet rule is a valid decision, not an exception.
See [evaluation source](../../src/judgevet/domain/policy_evaluation.py).

The CLI shares comparisons but retains its legacy malformed-answer checks.
Public evaluation checks confidence without a confidence predicate and checks
Choice/Score against the question snapshot; do not assume the legacy CLI
wrapper enforces those additional conditions. This distinction concerns
malformed answers, not different threshold operators.

## JSON grammar

The root object has exactly one member, `rules`, containing a nonempty array.
Each rule has exactly `question` and `pass`. `question` names an existing typed
question and may occur only once. `pass` uses exactly one matching predicate:

| Question | Required predicate | Optional addition |
|---|---|---|
| Noul | `"noul": {"min": number, "max": number}` with either or both bounds | None |
| Choice | `"choice": "exact label"` | `"confidence": {"min": number}` |
| Score | `"score": {"min": number, "max": number}` with either or both bounds | `"confidence": {"min": number}` |

The objects in the table are grammar fragments. Unknown fields, duplicate JSON
keys, nonfinite values, boolean bounds, wrong types, empty ranges and reversed
bounds are rejected. JSON `null` does not mean an omitted bound. The same
question-relative ranges apply as for typed construction.

This complete offline example decodes one policy and compares synthetic answers.
It prints nothing when the assertions pass.

```python
from judgevet import Noul, NoulAnswer
from judgevet.policy import evaluate_policy
from judgevet.policy_json import parse_policy

policy = parse_policy(
    '{"rules":[{"question":"clear","pass":{"noul":{"min":0.8}}}]}',
    {"clear": Noul(instructions="Is the text clear?")},
)
assert evaluate_policy(policy, {"clear": NoulAnswer(0.8)}).passed
assert not evaluate_policy(policy, {"clear": NoulAnswer(0.79)}).passed
```

For construction and file workflows, use the [Python policy guide](../how-to/use-policy-library.md)
or [CLI guide](../how-to/use-cli-policy.md). Error types are detailed in the
[error reference](errors.md#local-policy-errors).
