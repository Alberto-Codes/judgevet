---
status: draft
---

# Call Jev from a synchronous Python program

Status: **draft**.

Use this recipe when a Python caller can wait for a judgment before continuing.
Install judgevet in that interpreter's environment. Configure an environment key, mounted file or
[credential command](../reference/configuration.md#credential-sources); the [first tutorial](../tutorials/first-judgment.md)
shows setup. The call needs service access and sends the supplied content.
Read [data disclosure](../../SECURITY.md#data-sent-to-the-service) first.

Save this complete program as `judge_ticket.py` and run it with your installed
Python interpreter:

```python
from judgevet import HTTPSystemOneAdapter, Noul, bind_request_id
from judgevet.adapters.inbound.logs import configure
from judgevet.adapters.inbound.settings import Settings

settings = Settings()
configure(settings.log)
key = settings.api.resolve_key()
if key is None:
    raise SystemExit("Configure a credential source before calling Jev")

with (
    HTTPSystemOneAdapter(
        api_key=key.get_secret_value(),
        base_url=settings.api.base_url,
        network=settings.api.network_config,
        retry=settings.api.retry_policy,
    ) as adapter,
    bind_request_id("request-123"),
):
    response = adapter.system_one(
        state="I was charged twice.",
        questions={"billing": Noul(instructions="Is this about billing?")},
        model="jev-1.13.0",
    )

print(response.nouls["billing"].noul)
```

Expected outcome: one probability between zero and one on stdout.
With `JEV_LOG__LEVEL=debug`, stderr also carries one terminal diagnostic with
request identifier `request-123`; supply your own non-sensitive identifier.
See the [event contract](../reference/events.md) for fields and scope lifetime. Its value
can vary. `nouls` selects typed Noul answers; use the name supplied in
`questions`. Noul semantics follow the [vendor definition](https://docs.typesafe.ai/primitives/noul).
A valid answer does not prove the classification is correct.

The context manager owns cleanup, including when a call raises. For several
calls, keep the adapter open around those calls and close it after the last
one. The returned values remain usable after closing. Direct constructors do
not read judgevet environment settings: this example explicitly reads Settings
and resolves one wrapped key before constructing the adapter. Leave `JEV_API__CA_BUNDLE` unset for normal HTTPX
trust roots. In a private-CA deployment, set it to your approved PEM bundle.
Certificate and hostname verification stay enabled. See
[network configuration](../reference/configuration.md#proxy-and-tls-configuration)
for proxy precedence and TLS limits.

For missing credentials, check the variable's presence without printing it.
For service failures, use [error handling](handle-errors.md). To produce a
local acceptance decision, follow the [policy workflow](use-policy-library.md).
Use the [async recipe](use-async-library.md) when your caller already uses async
I/O; see [supported imports](../reference/compatibility.md) for the contract.
