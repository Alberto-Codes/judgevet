---
status: draft
---

# Diagnostic events and caller correlation

Status: **draft**.

This is the local event contract for judgevet 0.8.0. It does not describe a
vendor API or promote live-service evidence. Built-in event names form a closed
set: `http.call` and `mcp.runtime`. Application-defined events are separate.

## Rendering and ownership

Library imports and unconfigured calls stay silent. Applications own logging
configuration. CLI and MCP configure stderr; their default info level omits
routine HTTP events. Set `JEV_LOG__LEVEL=debug` to include those events.
`JEV_LOG__FORMAT=json` selects one JSON object per stderr line. Console output
uses the same event fields with human-readable formatting. JSON key order is
not part of the contract.

The configured chain filters built-in fields after merging logging context.
Application-bound state, tenant data, credentials, `command` and `run_id` are
excluded from built-in events. Generic application events retain context merging
and existing redaction. Applications supplying their own structlog processors
own any additional data those processors inject.

See [configuration](configuration.md#logging-and-diagnostics) and
[diagnostic disclosure](../../SECURITY.md#diagnostics-and-error-content).

## HTTP terminal event

`http.call` emits once per logical sync or async judgment call, at debug level.
Retries do not add events. The event records the final attempt's status.
A recovered rate limit followed by success records status 200 and success.
A final transport failure records null status and error. Parsing failure
records the received status and error. Cancellation propagates and records error.

With judgevet's configured JSON renderer, every event has exactly these keys:

| Key | Type | Meaning |
|---|---|---|
| `event` | string | Always `http.call`. |
| `level` | string | Always `debug`. |
| `timestamp` | string | UTC ISO timestamp added by the renderer. |
| `model` | string or null | Filtered requested model, including the adapter default. |
| `question_count` | integer | Number of supplied questions. |
| `status_code` | integer or null | Final attempt's HTTP status; null when no response arrived. |
| `outcome` | string | `success` after typed parsing; otherwise `error`. |
| `resolved_model` | string or null | Filtered model from the successful typed response; null on failure. |
| `input_tokens` | integer or null | Typed input token count; null when unavailable. |
| `output_tokens` | integer or null | Typed output token count; null when unavailable. |
| `request_id` | string or null | Dedicated caller correlation binding; null outside a scope. |

Token counts come only from a successful typed response. The current HTTP parser
requires both counts; missing usage is a parsing failure, not estimated usage.
The logger never computes a total or reads counts from a failed response.

The model filter retains `jev-latest` and `jev-<digits>.<digits>.<digits>` values
of at most 64 characters. Other model strings become null in diagnostics only.
Actual request and response model values remain unchanged. This filter does not
validate upstream model availability. Version-shaped identifiers must still
contain no sensitive data.

Question identifiers, instructions, criteria, state, answers, headers and
exception text are excluded. Question identifiers can contain customer data;
this contract deliberately provides only the question count.

## MCP runtime event

`mcp.runtime` forwards SDK diagnostics at warning, error or critical severity.
Its exact keys are `event`, `level`, `timestamp` and `request_id`. The event name
is fixed. Correlation comes from the dedicated binding in the emitting context.
SDK messages, arguments and tracebacks are excluded.

MCP JSON-RPC errors on stdout are separate from diagnostic stderr. This event
contract does not scrub protocol error content or arbitrary library exceptions.

## Caller correlation

Import `bind_request_id` from `judgevet`. Use its context manager around a call,
including inside an async function. The [complete synchronous example](../how-to/use-library.md)
binds a caller identifier and configures logging explicitly.

A non-sensitive opaque identifier must match ASCII
`[A-Za-z0-9][A-Za-z0-9._:-]{0,127}`. Invalid types, characters or lengths raise
`ValueError` on scope entry without changing the outer binding. Syntax validation
cannot determine whether an identifier contains a secret; the caller owns that
choice. The error message does not echo the supplied value.

Nested scopes restore the previous identifier. Passing `None` temporarily clears
it. Normal exit, exceptions and task cancellation all restore the previous value.
Concurrent asyncio tasks have separate bindings. A child inherits its creation
context; a later parent change does not rewrite the child's context.
Unrelated threads do not receive automatic propagation. These semantics follow
[Python context variables](https://docs.python.org/3/library/contextvars.html).

Correlation does not configure logging, generate an identifier, alter port
signatures or add HTTP headers. The CLI has no request-ID flag, and MCP tool
schemas have no request-ID field. Gateway header propagation remains separate.
Do not use arbitrary structlog context fields to supply this dedicated binding.
See [structlog context behavior](https://www.structlog.org/en/stable/contextvars.html)
for application-owned logging context.
