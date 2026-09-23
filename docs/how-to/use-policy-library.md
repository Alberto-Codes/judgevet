---
status: draft
---

# Evaluate policies from Python

Status: **draft**.

Version 0.7.0 adds `judgevet.policy` and `judgevet.policy_json`. These
modules are absent from 0.6.0. Install the verified 0.7.0 release with
`python -m pip install 'judgevet==0.7.0'`.

## Construct a typed policy

This example runs without a key or network. The answers are synthetic.
Thresholds demonstrate inclusive comparisons, not a model-quality guarantee.

```python
from judgevet import (
    Answer,
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Question,
    Score,
    ScoreAnswer,
)
from judgevet.policy import (
    ChoiceRule,
    NoulRule,
    Policy,
    ScoreRule,
    evaluate_policy,
    validate_policy,
)

questions: dict[str, Question] = {
    "clear": Noul(instructions="Is this clear?"),
    "risk": Choice(criteria={"low": "Low risk", "high": "High risk"}),
    "quality": Score(criteria=["Poor", "Fair", "Good"]),
}
policy = Policy(
    (
        NoulRule("clear", minimum=0.8),
        ChoiceRule("risk", "low", min_confidence=0.7),
        ScoreRule("quality", minimum=1.5, maximum=2, min_confidence=0.6),
    )
)
validated = validate_policy(policy, questions)
answers: dict[str, Answer] = {
    "clear": NoulAnswer(0.8),
    "risk": ChoiceAnswer("low", 0.7, {"low": 0.7, "high": 0.3}),
    "quality": ScoreAnswer(
        1.5,
        0.6,
        {0: "Poor", 1: "Fair", 2: "Good"},
        {0: 0, 1: 0.5, 2: 0.5},
    ),
}
report = evaluate_policy(validated, answers)
assert report.passed
assert tuple(item.question for item in report.rules) == ("clear", "risk", "quality")
print(report.rules[0].detail)
```

Every rule must pass. Reports retain policy order, including rules after an
unmet predicate. Noul and Score require at least one bound; all bounds are
inclusive. Noul bounds and confidence floors lie in [0, 1]. Score bounds use
zero through `len(question.criteria) - 1`. Choice uses an exact criteria label.
Names must be nonempty and unique. A policy may select a subset of questions.

These are local acceptance predicates over the [typed API fields](../reference/api.md).
They do not add fields to the vendor request.

## Decode the same grammar as the CLI

File reading belongs to the caller. `parse_policy` takes text, checks duplicate
keys and the [CLI grammar](use-cli-policy.md), and returns a `ValidatedPolicy`.
This example also needs no key or network.

```python
from judgevet import Noul, NoulAnswer
from judgevet.policy import NoulRule, Policy, evaluate_policy, validate_policy
from judgevet.policy_json import parse_policy

questions = {"clear": Noul(instructions="Is this clear?")}
text = '{"rules":[{"question":"clear","pass":{"noul":{"min":0.8}}}]}'
decoded = parse_policy(text, questions)
constructed = validate_policy(Policy((NoulRule("clear", minimum=0.8),)), questions)
assert decoded == constructed
report = evaluate_policy(decoded, {"clear": NoulAnswer(0.7)})
assert not report.passed
assert not report.rules[0].passed
```

For a file, pass `Path("policy.json").read_text(encoding="utf-8")` as text.
The caller handles file errors. JSON errors raise `PolicyDefinitionError`
without an exit code or `--policy` prefix.

## Own the adapter lifecycle

For actual judgments, construct and close the adapter explicitly. This example
makes one live request and requires `TYPESAFE_API_KEY` in the environment.
The zero floor demonstrates wiring; choose acceptance thresholds for your task.

```python
import os

from judgevet import HTTPSystemOneAdapter, Noul, SystemOnePort, SystemOneResponse
from judgevet.policy import NoulRule, Policy, evaluate_policy, validate_policy

questions = {"clear": Noul(instructions="Is this text clear?")}
validated = validate_policy(Policy((NoulRule("clear", minimum=0),)), questions)


def judge(port: SystemOnePort) -> SystemOneResponse:
    return port.system_one("The meeting starts at noon.", questions, "jev-latest")


with HTTPSystemOneAdapter(api_key=os.environ["TYPESAFE_API_KEY"]) as adapter:
    answer = judge(adapter)

report = evaluate_policy(validated, answer.answers)
assert report.passed
print(report.rules[0].detail)
```

The port does not own cleanup. The caller that creates an adapter closes it.
A synchronous adapter supports `with` and `close()`. Its separate asynchronous
counterpart supports `async with` and `aclose()`, without synchronous lifecycle
methods. There is no environment-reading convenience client.

Async callers use the same synchronous pure evaluator. This example makes one
live request with the same key environment.

```python
import asyncio
import os

from judgevet import AsyncHTTPSystemOneAdapter, AsyncSystemOnePort, Noul
from judgevet.policy import NoulRule, Policy, evaluate_policy, validate_policy


async def main() -> None:
    questions = {"clear": Noul(instructions="Is this text clear?")}
    validated = validate_policy(Policy((NoulRule("clear", minimum=0),)), questions)
    async with AsyncHTTPSystemOneAdapter(
        api_key=os.environ["TYPESAFE_API_KEY"]
    ) as adapter:
        port: AsyncSystemOnePort = adapter
        answer = await port.system_one(
            "The meeting starts at noon.", questions, "jev-latest"
        )
    report = evaluate_policy(validated, answer.answers)
    assert report.passed


asyncio.run(main())
```

## Handle errors and immutable values

`PolicyError(ValueError)` has two subclasses: `PolicyDefinitionError` for
malformed definitions and `PolicyAnswerError` for missing or invalid required
answers. They are separate from `JevError`, which represents Jev service and
transport failures. An unmet predicate returns `passed=False`; it does not raise.

Rules validate names and local bounds on construction. `Policy` copies its rule
sequence to a tuple and rejects empty or duplicate rules. Both
`ValidatedPolicy(policy, questions)` and `validate_policy` validate against
questions and snapshot only choice labels and score bounds. Later edits to the
questions, their criteria, or the original mapping cannot change that snapshot.
Validate again when the questions change. Do not reuse a policy with a different
question set merely because the names match.

Rules, policies and reports are frozen slotted dataclasses. `PolicyReport.passed`
is derived from all rule outcomes. `dataclasses.replace` reruns constructor
validation; replacing a `ValidatedPolicy` requires supplying `questions` again.
These guarantees cover normal construction and assignment. Python reflection
such as `object.__setattr__` can bypass frozen objects and is unsupported.
Existing answer/response objects retain their earlier shallow immutability:
their nested dictionaries remain mutable.

Public evaluation checks the selected value and Choice/Score confidence even
without a confidence predicate. It rejects nonnumeric, boolean, nonfinite or
out-of-range scalars, Choice labels outside the snapshot, and Score values
outside the snapshotted scale. It does not revalidate unused probability or
legend metadata; those remain the answer types' responsibility.

The legacy CLI bridge checks confidence only when requested. It does not
compare returned Choice/Score values to the original question criteria. Its
private `Rule`, parser and evaluator return shapes remain
available. Both paths share actual predicate comparisons and detail rendering.
See the [supported imports and compatibility contract](../reference/compatibility.md).

For the full contract, see the [policy reference](../reference/policy.md).

Look up local policy exceptions in the [error reference](../reference/errors.md).
