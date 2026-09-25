---
status: draft
---

# Handle a failed library call

Status: **draft**.

Use this pattern after [installing judgevet](install.md) and supplying
`JEV_API__KEY`. It calls the service with synthetic text and permits at most three attempts. The handler
prints error category and retry metadata, not service-supplied message text.
It retries eligible HTTP failures and keeps an unavailable answer separate from
a policy rejection. Transport retries remain disabled.

```python
import os

from judgevet import HTTPSystemOneAdapter, JevError, Noul, RetryPolicy

try:
    with HTTPSystemOneAdapter(
        api_key=os.environ["JEV_API__KEY"], retry=RetryPolicy(max_attempts=3)
    ) as adapter:
        response = adapter.system_one(
            state="I was charged twice.",
            questions={"billing": Noul(instructions="Is this about billing?")},
        )
except JevError as error:
    print(f"Service call failed: {type(error).__name__}")
    print(f"Retry candidate: {error.retryable}")
else:
    print(response.nouls["billing"].noul)
```

Expected outcome: a probability on success, or a failure category and a boolean
retry hint for a handled Jev error. The script demonstrates handling; it does
not set a failing process exit code. Add your application's exit or recovery
policy where appropriate.

`JevError` covers the supported service-error hierarchy. It does not catch a
missing environment variable, invalid constructor arguments, every HTTPX
exception or every programming error. In particular, redirects can propagate
raw `httpx.HTTPStatusError`. Keep unexpected failures visible to your application
without publishing arbitrary traceback contents. See
[error reference](../reference/errors.md).

## Choose a next action by category

| Category | Next action |
|---|---|
| `JevAuthError` | Check credential selection and service authorization without printing the key. |
| `JevRequestError` | Correct the supplied questions/state or configuration before repeating the call. |
| `JevMaxTokensExceededError` | Shrink the state or the longest question. This subclass of `JevRequestError` is not retryable. |
| `JevResponseError` | Preserve a minimal synthetic reproduction of the unusable answer and report it. |
| `JevRateLimitError` | Defer work under your application's retry and spending policy. |
| `JevServiceError` | Check transport/service availability; decide whether another attempt is appropriate. |

`retryable` is a classification, not a promise of success. The example enables
bounded retries; the default adapter makes one attempt. Each retry sends another
service request. Choose [retry limits](../reference/configuration.md#retry-limits)
under your spending policy. Error mappings are defined
by the [adapter](../../src/judgevet/adapters/outbound/http.py) and
[error types](../../src/judgevet/domain/errors.py).

Handle local `PolicyDefinitionError` and `PolicyAnswerError` separately using
the [policy guide](use-policy-library.md#handle-errors-and-immutable-values).
A policy returning `passed=False` is a valid decision and is not an exception.
Review [diagnostic disclosure limits](../../SECURITY.md#diagnostics-and-error-content)
before logging error strings or sharing tracebacks. For safe checks by symptom,
use [troubleshooting](troubleshoot.md).
