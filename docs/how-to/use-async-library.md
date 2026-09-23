---
status: draft
---

# Call Jev from asynchronous Python

Status: **draft**.

Use this recipe in an asynchronous application. Install judgevet and provide
`JEV_API__KEY` in the process environment. The [first tutorial](../tutorials/first-judgment.md)
provides setup. Only send content you can disclose to the service.

Save this complete program as `judge_ticket_async.py`:

```python
import asyncio
import os

from judgevet import AsyncHTTPSystemOneAdapter, Noul


async def main() -> None:
    """Ask one billing question and print its probability."""
    async with AsyncHTTPSystemOneAdapter(api_key=os.environ["JEV_API__KEY"]) as adapter:
        response = await adapter.system_one(
            state="I was charged twice.",
            questions={"billing": Noul(instructions="Is this about billing?")},
            model="jev-1.13.0",
        )
    print(response.nouls["billing"].noul)


asyncio.run(main())
```

Run it with the interpreter where judgevet is installed. Expected outcome:
one probability between zero and one. The value is a model judgment, not a
fixed test output. See the [Noul definition](https://docs.typesafe.ai/primitives/noul).

In an application that already runs an event loop, await the operation from
that loop instead of calling `asyncio.run` inside it. Keep the adapter within
its intended lifetime. `async with` awaits cleanup; manual ownership requires
`await adapter.aclose()` even when the operation fails.

The async adapter uses the same typed answers and explicit configuration as
the [sync adapter](use-library.md). Async does not add automatic retries or a
policy tool. After awaiting the answer, evaluate a local policy using the
[async policy workflow](use-policy-library.md#own-the-adapter-lifecycle).
For failures, follow [error handling](handle-errors.md) and
[troubleshooting](troubleshoot.md).
