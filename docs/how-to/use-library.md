---
status: draft
---

# Call Jev from a synchronous Python program

Status: **draft**.

Use this recipe when a Python caller can wait for a judgment before continuing.
Install judgevet in that interpreter's environment. Supply `JEV_API__KEY` through
your process environment or secret provider; the [first tutorial](../tutorials/first-judgment.md)
shows setup. The call needs service access and sends the supplied content.
Read [data disclosure](../../SECURITY.md#data-sent-to-the-service) first.

Save this complete program as `judge_ticket.py` and run it with your installed
Python interpreter:

```python
import os

from judgevet import HTTPSystemOneAdapter, NetworkConfig, Noul

with HTTPSystemOneAdapter(
    api_key=os.environ["JEV_API__KEY"],
    network=NetworkConfig(ca_bundle=os.environ.get("JEV_API__CA_BUNDLE")),
) as adapter:
    response = adapter.system_one(
        state="I was charged twice.",
        questions={"billing": Noul(instructions="Is this about billing?")},
        model="jev-1.13.0",
    )

print(response.nouls["billing"].noul)
```

Expected outcome: one probability between zero and one on stdout. Its value
can vary. `nouls` selects typed Noul answers; use the name supplied in
`questions`. Noul semantics follow the [vendor definition](https://docs.typesafe.ai/primitives/noul).
A valid answer does not prove the classification is correct.

The context manager owns cleanup, including when a call raises. For several
calls, keep the adapter open around those calls and close it after the last
one. The returned values remain usable after closing. Direct constructors do
not read judgevet environment settings: this example reads the key and optional
CA bundle path explicitly. Leave `JEV_API__CA_BUNDLE` unset for normal HTTPX
trust roots. In a private-CA deployment, set it to your approved PEM bundle.
Certificate and hostname verification stay enabled. See
[network configuration](../reference/configuration.md#proxy-and-tls-configuration)
for proxy precedence and TLS limits.

For missing credentials, check the variable's presence without printing it.
For service failures, use [error handling](handle-errors.md). To produce a
local acceptance decision, follow the [policy workflow](use-policy-library.md).
Use the [async recipe](use-async-library.md) when your caller already uses async
I/O; see [supported imports](../reference/compatibility.md) for the contract.
