---
status: draft
---

# Error reference

Status: **draft**. Local error mapping is separate from live-service evidence.
Only the recorded calls establish what the service returned; see the
[evidence ledger](../../STATUS.md#what-is-verified-and-what-is-not).

## Service and transport errors

The supported names are exported from `judgevet`. Each concrete error below
inherits directly from `JevError`, which inherits from `Exception`.
`JevRateLimitError` is not a subclass of `JevRequestError` or `JevServiceError`.

| Type | Constructor | HTTP adapter mapping | `retryable` |
|---|---|---|---|
| `JevError` | `JevError(message, status_code=None)` | Base type; not a catch-all for every failure | `False` |
| `JevAuthError` | `JevAuthError(message, status_code)` | 401 or 403 | `False` |
| `JevRequestError` | `JevRequestError(message, status_code)` | Other 400–499 statuses, excluding 429 | `False` |
| `JevRateLimitError` | `JevRateLimitError(message, status_code)` | 429 | `True` |
| `JevServiceError` | `JevServiceError(message, status_code=None)` | 500–599, or HTTPX `RequestError` such as a timeout | `True` |
| `JevResponseError` | `JevResponseError(message, status_code)` | Successful 200–299 answer that cannot be parsed | `False` |

This table describes the [adapter mapping](../../src/judgevet/adapters/outbound/http.py)
and [error classes](../../src/judgevet/domain/errors.py). It does not assert that
every status has been observed. The [vendor API reference](https://docs.typesafe.ai/api.md)
is the source for documented service errors. Live 401 and 422 bodies have been
observed; 429 and 529 bodies remain unseen. Other mapped statuses are local
compatibility behavior, not additional verified service outcomes.

Concrete constructors validate the status range and raise `ValueError` for an
invalid code. `JevRequestError` permits 400–499 except 401/403 when constructed
directly, including 429; the HTTP adapter nevertheless maps 429 to
`JevRateLimitError`. `JevServiceError` permits `None` for transport failures.
`JevError` itself does not validate the status or infer retryability from it.

All errors expose `status_code` and the `retryable` property. The message is in
standard exception `args`, not a `.message` attribute. `str(error)` appends
`(status N)` when a status is present. Messages can include remote content;
do not assume they are safe to publish.

The following complete example runs offline and prints nothing when its
assertions pass. It demonstrates metadata only; it makes no service call.

```python
from judgevet import JevError, JevRateLimitError, JevServiceError

base = JevError("Synthetic base error", 500)
assert base.retryable is False
rate_limit = JevRateLimitError("Synthetic rate limit", 429)
assert rate_limit.retryable is True
transport = JevServiceError("Synthetic transport failure")
assert transport.status_code is None
assert transport.retryable is True
```

### Retry and exception boundaries

`retryable` is advisory metadata. Callers can enable the adapter's
[bounded retry policy](configuration.md#retry-limits). The default is one attempt.
The adapter does not honor `Retry-After` headers. A read timeout does not prove the service stopped processing.

`except JevError` does not catch every HTTPX or Python exception. Redirects are
disabled and can propagate raw `httpx.HTTPStatusError`. Missing constructor keys,
invalid arguments, serialization failures and application errors can raise other
types. Keep those visible without publishing an arbitrary traceback. See the
[handling recipe](../how-to/handle-errors.md).

### Error content

The adapter extracts selected information from service `detail` values. For
validation lists it omits the `input` field. That omission is not universal
redaction of remote text, URLs or credentials. The observed 401 body contains an
object and the observed 422 body contains a list; neither shape establishes the
unseen 429/529 bodies. See [diagnostic limits](../../SECURITY.md#diagnostics-and-error-content).

## Local policy errors

Import these from `judgevet.policy`, not the package root:

| Type | Parent | Meaning |
|---|---|---|
| `PolicyError` | `ValueError` | Base for local policy failures. |
| `PolicyDefinitionError` | `PolicyError` | Invalid rule, policy JSON or question binding. |
| `PolicyAnswerError` | `PolicyError` | A selected answer is missing, has the wrong type or violates required answer constraints. |

These errors have ordinary exception arguments and no `status_code` or
`retryable` contract. They do not inherit from `JevError`. A valid evaluation
with `passed=False` is an unmet policy, not a `PolicyAnswerError`.
The [Python policy guide](../how-to/use-policy-library.md#handle-errors-and-immutable-values)
explains handling and the [compatibility reference](compatibility.md) distinguishes
strict public evaluation from the legacy CLI checks.

## Adapter presentation

The CLI renders handled input/service failures on stderr and exits 1. With
`--json`, those handled errors use an `error` string member; framework usage
errors retain their own presentation and exit 2. Startup and unexpected failures
are outside that envelope. A valid unmet policy exits 3 with answers on stdout.
See the [CLI policy guide](../how-to/use-cli-policy.md#distinguish-policy-rejection-in-automation).

MCP call failures are distinct from a negative judgment. Tool handlers can raise
for bad arguments, missing/wrong-type answers or service failures; the MCP
runtime handles their protocol presentation. The entry point reports missing
runtime, invalid settings or missing credentials with status 2. It returns 130
on keyboard interruption and reports handled startup/runtime exceptions with a
fixed diagnostic. See [MCP connection checks](../how-to/troubleshoot.md#when-mcp-does-not-connect).
