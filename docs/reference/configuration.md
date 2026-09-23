---
status: draft
---

# Configuration reference

Status: **draft**. This page describes judgevet 0.7.0 configuration, not the
configuration contract of the official TypeSafe SDK.

## Direct Python adapters

Both `HTTPSystemOneAdapter` and `AsyncHTTPSystemOneAdapter` take these constructor
arguments. Neither reads judgevet environment settings or installs logging.

| Argument | Default | Behavior |
|---|---|---|
| `api_key` | `None` | Supply a key explicitly. `None` raises `ValueError`; this is not an authentication check. |
| `base_url` | `None` | Uses `https://api.typesafe.ai` when omitted or empty. |
| `default_model` | `"jev-latest"` | Used when `system_one` receives no model or an empty model string. |
| `transport` | `None` | Optional HTTPX transport; use the sync or async transport type appropriate to the adapter. |
| `timeout_seconds` | `30.0` | HTTPX read, write and pool timeout in seconds; connect timeout is fixed at 5 seconds. Values at or below zero raise `ValueError`. |

These are judgevet defaults from the [HTTP adapter](../../src/judgevet/adapters/outbound/http.py).
The service host and endpoint are documented by [TypeSafe](https://api.typesafe.ai/docs).
Timeouts apply to HTTPX operations, not a guaranteed total wall-clock deadline.
The adapters do not retry automatically. A timed-out request may still be running
at the service; another call is another attempt.

Direct constructors do not apply the CLI/MCP settings URL validator. Callers own
URL selection and credential disclosure. HTTPX environment proxy and certificate
settings can still affect transport; see [transport limits](../../SECURITY.md#transport-and-certificates).
Use [sync](../how-to/use-library.md) or [async](../how-to/use-async-library.md)
context managers to release the client. Changing the process environment does
not reconfigure an existing adapter.

## CLI and MCP settings

The composition roots read [Settings](../../src/judgevet/adapters/inbound/settings.py)
when they start. No judgevet configuration file or automatic `.env` loading is
configured. An external tool such as direnv can populate the process environment.
The nested settings use the `JEV_` prefix and `__` separator.

| Environment name | Compatibility alias | Default | Effect |
|---|---|---|---|
| `JEV_API__KEY` | `TYPESAFE_API_KEY` | No key | Credential supplied to the adapter. |
| `JEV_API__BASE_URL` | `TYPESAFE_BASE_URL` | `https://api.typesafe.ai` | Service base URL. |
| `JEV_API__DEFAULT_MODEL` | None | `jev-latest` | Stored adapter default; entry-point call overrides are described below. |
| `JEV_API__TIMEOUT_SECONDS` | None | `30.0` | Adapter timeout; must be greater than zero. |
| `JEV_LOG__FORMAT` | None | `auto` | `auto`, `json` or `console` logging format. |
| `JEV_LOG__LEVEL` | None | `info` | `debug`, `info`, `warning`, `error` or `critical`, in lowercase. |

When both documented names for a key or base URL are set, the `JEV_API__...`
value wins. These values are not merged. Python callers can also construct
`Settings` with explicit values; those override environment values. Ordinary
library callers can bypass `Settings` entirely and pass constructor arguments.

Settings accepts HTTPS URLs and HTTP URLs whose hostname is `localhost` or
`127.0.0.1`. It rejects other schemes and remote plaintext HTTP. This validation
does not prove that a destination is trusted or reachable.

### Entry-point overrides

The CLI's explicit `--api-key` overrides the settings key. Prefer an approved
environment or secret provider because command arguments may be visible to
other processes or stored in shell history. Invalid settings can still prevent
startup even when an option supplies another value.

The CLI always passes its `--model` value, whose default is `jev-latest`.
Consequently, `JEV_API__DEFAULT_MODEL` does not select the CLI's requested model.
The MCP tools also explicitly request `jev-latest`; they have no model argument.
Although MCP constructs an adapter with the settings default, that default does
not override the model passed by its tools. For a pinned model, use the CLI
`--model` option or a direct library call.

This behavior comes from the [CLI](../../src/judgevet/adapters/inbound/cli.py),
[policy invocation](../../src/judgevet/adapters/inbound/cli_policy_run.py),
[MCP entry point](../../src/judgevet/adapters/inbound/mcp_entrypoint.py) and
[MCP tools](../../src/judgevet/adapters/inbound/mcp.py).

### Logging and diagnostics

Logs use stderr. `auto` selects console output when stderr is a terminal and
JSON otherwise. The log format is separate from CLI `--json`, which selects
answer and handled-error rendering. Use the documented lowercase settings;
unknown log levels are not accepted by the logging configuration.

`SecretStr` masks the settings key's normal representation. The HTTP adapter
retains an unwrapped key. Redaction has limits: CLI error text, protocol errors
and arbitrary tracebacks are not universally scrubbed. Consult
[credentials](../../SECURITY.md#credentials) and
[diagnostic disclosure](../../SECURITY.md#diagnostics-and-error-content)
before logging or sharing output. For recovery steps, use
[troubleshooting](../how-to/troubleshoot.md).
