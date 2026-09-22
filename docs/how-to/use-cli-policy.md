---
status: draft
---

# Apply an explicit acceptance policy

Keep the questions and their acceptance policy in separate version-controlled
JSON files. First create `questions.json`:

```json
{"clear":{"type":"noul","instructions":"Is this text clear?"}}
```

Create `policy.json` with an inclusive probability floor:

```json
{"rules":[{"question":"clear","pass":{"noul":{"min":0.8}}}]}
```

Evaluate a file using the same approved key environment as other CLI calls:

```bash
judgevet --state-file document.txt --questions-file questions.json --policy policy.json --json
```

The command makes one judgment request after validating its inputs. Every rule
must pass. Rules may select a subset of the supplied questions, but each selected
question must exist and may appear only once.

| Status | Meaning |
|---|---|
| 0 | Judgment succeeded and the explicit policy passed. |
| 1 | Input, policy or service failure. No usable policy verdict. |
| 2 | Invalid command usage or competing input sources. |
| 3 | Judgment succeeded but the explicit policy was not met. |

Without `--policy`, a valid judgment still exits 0 even when its probability is
low. Use the explicit status to distinguish an unmet policy from a broken tool.
The policy does not make the model deterministic or guarantee the quality of its
judgment. Choose thresholds for your task and inspect the returned answers.

## Match predicates to question types

A Noul rule accepts `min`, `max`, or both inside `noul`. Bounds are inclusive
and lie between 0 and 1. Noul has no confidence predicate.

A Choice rule uses the exact label from the question's criteria:

```json
{"question":"risk","pass":{"choice":"low","confidence":{"min":0.7}}}
```

A Score rule uses the original rubric scale, from zero through the last criterion
index. It does not normalize that scale to a probability:

```json
{"question":"quality","pass":{"score":{"min":2,"max":3},"confidence":{"min":0.6}}}
```

Confidence is optional for Choice and Score and accepts only `min`, between
0 and 1. Bounds must be finite numbers; strings, booleans, NaN and infinity are
invalid. Unknown fields, duplicate JSON keys, duplicate question rules and
mismatched predicate types fail before a service request.

These predicates use the typed answer fields documented in the
[API reference](../reference/api.md). They are local acceptance rules, not extra
fields sent to the vendor.

## Read the report

With `--json`, stdout retains model, usage and answers and adds `policy`:

```json
{"result":"fail","rules":[{"question":"clear","pass":false,"detail":"..."}]}
```

The example above shows the policy member only. Rule reports retain file order;
the detail explains the actual comparison. Unmet policies retain the successful
answers on stdout and leave stderr empty. Human output prints answers to stdout
and the policy summary and comparisons to stderr.

A missing or wrong-type answer required by the policy is a response failure,
not an unmet policy or a vacuous pass. Error diagnostics identify the source
without printing the policy path or its contents.
