---
status: draft
---

# Make your first local policy decision

Status: **draft**.

You will construct an inclusive threshold and see both a passing and failing
decision. The answers are synthetic, so this exercise needs no API key or
service access. It teaches local comparisons, not model quality.

Use the environment from [first judgment](first-judgment.md#prepare-an-isolated-environment).
If you start here, follow only that installation section. You do not need to
supply a key or run its service example. Package installation needs network
access; the program below runs offline.

## Define acceptance separately from the question

The question remains “Is this about billing?” A policy adds the application
rule: accept a Noul probability of at least `0.8`. This is a teaching threshold,
not a recommended threshold for your tickets.

Save this complete program as `first_policy.py` in your tutorial directory:

```python
from judgevet import Noul, NoulAnswer
from judgevet.policy import NoulRule, Policy, evaluate_policy, validate_policy

questions = {"billing": Noul(instructions="Is this about billing?")}
policy = validate_policy(
    Policy((NoulRule("billing", minimum=0.8),)),
    questions,
)

at_boundary = {"billing": NoulAnswer(noul=0.8)}
below_boundary = {"billing": NoulAnswer(noul=0.79)}

passing = evaluate_policy(policy, at_boundary)
failing = evaluate_policy(policy, below_boundary)

print(f"At 0.8: passed={passing.passed}")
print(f"At 0.79: passed={failing.passed}")
print(f"Rule checked: {failing.rules[0].question}")
assert passing.passed
assert not failing.passed
```

`validate_policy` checks the rule against the named question and records its
constraints. `evaluate_policy` compares the supplied typed answer with that
validated rule. Neither operation sends anything to the service. These are
[judgevet's local policy operations](../how-to/use-policy-library.md).

## Run the comparison

```bash
.venv/bin/python first_policy.py
```

Expected output for these fixed synthetic inputs:

```text
At 0.8: passed=True
At 0.79: passed=False
Rule checked: billing
```

Checkpoint: exactly `0.8` passes. The minimum is inclusive. The lower value
fails, and the report still identifies the rule. This is an ordinary return
value, not an exception. Both Noul answers are valid numeric answers.

The Python process itself exits successfully after printing both decisions.
Your application chooses what to do with `passed`. The CLI's
[policy exit codes](../how-to/use-cli-policy.md) are a separate adapter behavior.
A false report does not automatically set a Python program's exit status.

## Distinguish failure from an unavailable decision

An unmet threshold means the policy was evaluated and did not pass.
A missing required answer or a wrong answer type instead raises
`PolicyAnswerError`. An invalid policy definition raises
`PolicyDefinitionError`. See [policy error handling](../how-to/use-policy-library.md#handle-errors-and-immutable-values).

If your program reports a policy-definition error, check that the rule name
matches the question. Check that the threshold is a finite number from zero to
one. If judgevet cannot be imported, run the file with the tutorial environment's
interpreter. Do not add service credentials to fix this offline example.

A service failure happens before a usable answer reaches this comparison.
Do not convert every exception into a failed policy: that would hide the
difference between rejected content and a broken request.

## Connect the two exercises

The first tutorial obtains answers from Jev. This tutorial constructs them
locally so you can observe the comparison at an exact boundary. In a real
application, pass the service call's `response.answers` to `evaluate_policy`
using a policy validated against the same question definitions.

Follow the complete [synchronous and asynchronous workflows](../how-to/use-policy-library.md#own-the-adapter-lifecycle)
to combine the steps. Before choosing production thresholds, read
[policy tradeoffs and labeled evaluation](../explanation/policies.md) and
[what verification proves](../explanation/verification.md).
The [compatibility reference](../reference/compatibility.md) describes the
supported imports and public policy contract.
