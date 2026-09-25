---
status: draft
---

# Test code that calls Jev without a network

Status: **draft**.

Use this recipe when your code takes a `SystemOnePort` or an
`AsyncSystemOnePort` and your tests must run without a key or a network.
`judgevet.testing` ships two fakes in the installed package. No extra is
needed. `FakeSystemOnePort` satisfies the synchronous port.
`AsyncFakeSystemOnePort` satisfies the asynchronous port; its `system_one`
must be awaited.

Each fake takes `seed` (default `0`) and `answers`, a mapping from question
name to a scripted answer. A scripted name returns its answer unchanged. Every
other typed question receives a seeded answer that passes the
[answer validators](../reference/api.md#answer-and-container-types):

- `Noul` receives a probability in `[0, 1]`.
- `Choice` receives probabilities over its criteria labels and selects the
  most probable label.
- `Score` receives a legend equal to its criteria, keyed from level zero.

The same seed, state and question give the same answer. A raw mapping
question without a scripted answer raises `TypeError`. The response `model`
echoes the `model` argument. Each call appends `(state, questions, model)` to
`calls`.

Each fake also takes two keyword-only arguments. `usage` sets the `Usage` that
every response carries; the default is `Usage()`, which has no token counts.
`error` sets an exception that every call raises. The error covers the whole
call: the fake appends the call to `calls` first, then raises the instance you
passed. No option fails one question of a call, because the real adapter never
does.

Each fake takes `spend_cap` and `audit` too. They behave as the
[HTTP adapter options](../reference/configuration.md#spend-cap) of the same
name. The fake claims one attempt from the `SpendCap` before each call. A
refused claim raises `JevBudgetExceededError` and the call is not recorded in
`calls`. A successful call settles its `usage.input_tokens`; a failed call
settles nothing. The `audit` sink receives one `JudgmentRecord` per call,
whether the call returned, raised or was refused. A successful record carries
`status_code=None`, because no HTTP response arrived. A sink failure never
changes the result.

Seeded answers are synthetic. They exercise your code paths. They do not
predict what the service would answer.

## Synchronous code

Save this program as `test_route_ticket.py`. Run it with `pytest` or with
your Python interpreter:

```python
from judgevet import Noul, NoulAnswer
from judgevet.ports import SystemOnePort
from judgevet.testing import FakeSystemOnePort


def route(port: SystemOnePort, ticket: str) -> str:
    response = port.system_one(
        state=ticket,
        questions={"billing": Noul(instructions="Is this about billing?")},
        model="jev-1.13.0",
    )
    return "billing" if response.nouls["billing"].noul >= 0.5 else "general"


def test_route_sends_billing_tickets_to_billing() -> None:
    fake = FakeSystemOnePort(answers={"billing": NoulAnswer(noul=0.9)})
    assert route(fake, "I was charged twice.") == "billing"
    assert fake.calls[0][0] == "I was charged twice."


if __name__ == "__main__":
    test_route_sends_billing_tickets_to_billing()
```

## Asynchronous code

Save this program as `test_route_ticket_async.py`. It runs the coroutine with
`asyncio.run`, so it needs no async test plugin:

```python
import asyncio

from judgevet import Choice
from judgevet.ports import AsyncSystemOnePort
from judgevet.testing import AsyncFakeSystemOnePort


async def queue_for(port: AsyncSystemOnePort, ticket: str) -> str:
    response = await port.system_one(
        state=ticket,
        questions={"queue": Choice(criteria={"billing": "Money", "bugs": "Defects"})},
        model="jev-1.13.0",
    )
    return response.choices["queue"].choice


def test_queue_is_stable_for_a_seed() -> None:
    first = asyncio.run(queue_for(AsyncFakeSystemOnePort(seed=4), "Card declined"))
    again = asyncio.run(queue_for(AsyncFakeSystemOnePort(seed=4), "Card declined"))
    assert first == again
    assert first in {"billing", "bugs"}


if __name__ == "__main__":
    test_queue_is_stable_for_a_seed()
```

## Scripted errors

Save this program as `test_route_ticket_errors.py`. It scripts a rate limit
and checks that the caller falls back:

```python
from judgevet import JevRateLimitError, Noul
from judgevet.ports import SystemOnePort
from judgevet.testing import FakeSystemOnePort


def route(port: SystemOnePort, ticket: str) -> str:
    try:
        response = port.system_one(
            state=ticket,
            questions={"billing": Noul(instructions="Is this about billing?")},
            model="jev-1.13.0",
        )
    except JevRateLimitError:
        return "retry-later"
    return "billing" if response.nouls["billing"].noul >= 0.5 else "general"


def test_route_defers_when_rate_limited() -> None:
    fake = FakeSystemOnePort(error=JevRateLimitError("rate limit", 429))
    assert route(fake, "I was charged twice.") == "retry-later"
    assert len(fake.calls) == 1


if __name__ == "__main__":
    test_route_defers_when_rate_limited()
```

## Spend cap and audit

Save this program as `test_route_ticket_budget.py`. It caps the fake at one
attempt and collects each audit record in a list:

```python
from judgevet import JevBudgetExceededError, JudgmentRecord, Noul, SpendCap
from judgevet.testing import FakeSystemOnePort


class ListSink:
    def __init__(self) -> None:
        self.records: list[JudgmentRecord] = []

    def record(self, record: JudgmentRecord) -> None:
        self.records.append(record)


def test_second_call_is_refused_by_the_cap() -> None:
    sink = ListSink()
    fake = FakeSystemOnePort(spend_cap=SpendCap(max_attempts=1), audit=sink)
    questions = {"billing": Noul(instructions="Is this about billing?")}
    fake.system_one("I was charged twice.", questions, "jev-1.13.0")
    try:
        fake.system_one("I was charged twice.", questions, "jev-1.13.0")
    except JevBudgetExceededError as error:
        assert error.limit == "attempts"
    else:
        raise AssertionError("the cap did not refuse the second call")
    assert len(fake.calls) == 1
    assert [record.outcome for record in sink.records] == ["success", "error"]


if __name__ == "__main__":
    test_second_call_is_refused_by_the_cap()
```

The refused call writes the second record. The first call wrote one record.

Both fakes import only the domain, the ports and `judgevet.diagnostics`. An import-linter contract
forbids them from importing an adapter. Use the
[HTTP adapters](use-library.md) when a test must reach the service.
