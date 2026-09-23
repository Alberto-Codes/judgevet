---
status: draft
---

# A policy expresses your acceptance decision

Status: **draft**. This page uses synthetic answers and teaching thresholds.
They are not recommended production thresholds.

The [support-ticket example](judgments.md) asks the model about content.
A policy asks a different question: does this answer satisfy the application's
rules? The first operation uses the remote model. The second compares typed
values locally. Changing a threshold can change the decision without another
service call when you retain the same answer.

## One answer, two decisions

Suppose the billing Noul answer is `0.85`. An application that adds tickets
to a candidate review queue might require at least `0.8`. An application
that proposes an automatic route might require at least `0.9`. The same
answer passes the first rule and fails the second. The model did not change;
the application accepted a different tradeoff.

This complete example runs offline after installing judgevet:

```python
from judgevet import Noul, NoulAnswer
from judgevet.policy import NoulRule, Policy, evaluate_policy, validate_policy

questions = {"billing": Noul(instructions="Is this about billing?")}
answers = {"billing": NoulAnswer(noul=0.85)}
review = validate_policy(Policy((NoulRule("billing", minimum=0.8),)), questions)
route = validate_policy(Policy((NoulRule("billing", minimum=0.9),)), questions)

assert evaluate_policy(review, answers).passed
assert not evaluate_policy(route, answers).passed
```

A passing report does not route the ticket. It gives the application a decision
it can use. It also does not prove that billing is the correct classification.
The [policy evaluator](../../src/judgevet/domain/policy_evaluation.py) performs
comparisons; it does not verify the underlying content against an external truth.

## Combine conditions deliberately

Noul bounds are inclusive. A minimum of `0.8` accepts exactly `0.8`.
Choice rules match a label; Score rules compare the rubric value against
bounds. Choice and Score can also require minimum confidence. When a rule
contains both a value condition and a confidence condition, both must pass.
Every rule in a policy must pass for the aggregate decision to pass.
See the [typed policy guide](../how-to/use-policy-library.md) and
[comparison source](../../src/judgevet/domain/policy_comparisons.py).

This conjunction matters when you add a requirement. A correctly selected
billing label does not excuse an unmet confidence threshold. Likewise, high
confidence does not excuse the wrong label. Rules are explicit constraints,
not votes that compensate for each other.

An unmet rule returns a failed report with comparison details. Missing or
invalid required answers raise a local policy error instead. There is no usable
pass/fail decision in that case. The CLI also distinguishes unmet policies
from input/service failures through its [exit codes](../how-to/use-cli-policy.md).
Treating every nonzero exit as “the content failed” loses that distinction.

## Choose thresholds with task evidence

Start by defining the action and the cost of a wrong decision. For ticket
routing, identify both wrong routes and missed routes. Collect representative
tickets with expected labels agreed by reviewers. Include ambiguous tickets,
missing context and categories that overlap.

Compare candidate rules on those examples. Count accepted incorrect routes,
rejected correct routes and cases needing review. Use a separate set of labeled
examples to evaluate the rule you selected; tuning and evaluating on the same
examples gives weak evidence of performance on new tickets.

A higher minimum accepts a subset of the same fixed answers. It can reduce
some mistaken acceptances while rejecting more correct cases. That ordering
does not establish an accuracy guarantee. Review actual mistakes instead of
assuming the model's confidence equals the observed success rate.

Keep the question wording, criteria and policy version with your evaluation
records. Reassess after changing any of them or the selected model. Validated
policies snapshot question constraints; changing labels or rubric length needs
revalidation. A snapshot prevents accidental constraint drift during local
comparison, not changes in the remote service's behavior.

For implementation, follow [typed or JSON policy construction](../how-to/use-policy-library.md)
or [CLI policy files](../how-to/use-cli-policy.md). Read
[verification limits](verification.md) before using a passing decision to
justify automation.
