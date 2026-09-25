---
status: draft
---

# Configuration reference

Status: **draft**. This page describes the current judgevet configuration, not the
configuration contract of the official TypeSafe SDK.

## Direct Python adapters

Both `HTTPSystemOneAdapter` and `AsyncHTTPSystemOneAdapter` take these constructor
arguments. Neither reads judgevet environment settings or installs logging.

| Argument | Default | Behavior |
|---|---|---|
| `api_key` | `None` | Supply a key explicitly. `None` raises `ValueError`; this is not an authentication check. |
| `base_url` | `None` | Uses `https://api.typesafe.ai` when omitted or empty. |
| `default_model` | `"jev-latest"` | Used when `system_one` receives no model or an empty model string. |
| `gateway` | `None` | Optional `GatewayConfig`; omission retains direct authentication and no metadata. |
| `redactor` | `None` | Optional synchronous `StateRedactor`; transforms a private state copy before transmission. |
| `network` | `None` | Optional `NetworkConfig`; omission retains HTTPX proxy and TLS defaults. |
| `retry` | `None` | Optional `RetryPolicy`; omission preserves one attempt. |
| `spend_cap` | `None` | Optional `SpendCap`; omission sends every attempt the retry policy permits. See [spend cap](#spend-cap). |
| `transport` | `None` | Optional HTTPX transport; use the sync or async transport type appropriate to the adapter. |
| `timeout_seconds` | `30.0` | HTTPX read, write and pool timeout in seconds; connect timeout is fixed at 5 seconds. Values at or below zero raise `ValueError`. |

These are judgevet defaults from the [HTTP adapter](../../src/judgevet/adapters/outbound/http.py).
The service host and endpoint are documented by [TypeSafe](https://api.typesafe.ai/docs).
Timeouts apply to HTTPX operations, not a guaranteed total wall-clock deadline.
Retries are disabled by default. See [retry limits](#retry-limits) before enabling them.
A timed-out request may still be running at the service.

The `jev-latest` alias follows the model the service currently serves.
`VERIFIED_MODEL` names the one model version that this repository's live tests
have exercised; [STATUS](../../STATUS.md) records it. Pass either value as
`model`; the choice between the latest and the verified model belongs to the caller.

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
| `JEV_API__KEY` | `TYPESAFE_API_KEY` | No key | Literal credential or an explicit `!command` source. |
| `JEV_API__KEY_FILE` | None | Unset | Regular UTF-8 file containing one credential token. |
| `JEV_API__KEY_COMMAND_TIMEOUT` | None | `5.0` | Command deadline after process creation; finite and greater than zero. |
| `JEV_API__BASE_URL` | `TYPESAFE_BASE_URL` | `https://api.typesafe.ai` | Service base URL. |
| `JEV_API__DEFAULT_MODEL` | None | `jev-latest` | Stored adapter default; entry-point call overrides are described below. |
| `JEV_API__TIMEOUT_SECONDS` | None | `30.0` | Adapter timeout; must be greater than zero. |
| `JEV_API__AUTH_HEADER` | None | `Authorization` | Credential field name. |
| `JEV_API__AUTH_SCHEME` | None | `Bearer` | Prefix token; empty sends the bare credential. |
| `JEV_API__HEADERS` | None | `{}` | JSON map of explicit string metadata. Values are literal. |
| `JEV_API__REQUEST_ID_HEADER` | None | Unset | Opt into forwarding the scoped request ID under this field. |
| `JEV_API__PROXY` | None | Unset | Explicit HTTPX proxy URL; overrides standard proxy routing. |
| `JEV_API__CA_BUNDLE` | None | Unset | PEM file replacing default trust roots; must load successfully. |
| `JEV_API__VERIFY` | None | `true` | Verify certificate chains and hostnames. Disable only in controlled tests. |
| `JEV_API__MAX_ATTEMPTS` | None | `1` | Total requests per call; must be a positive integer. |
| `JEV_API__RETRY_BASE_DELAY` | None | `0.5` | Initial backoff ceiling in seconds. |
| `JEV_API__RETRY_MAX_DELAY` | None | `5.0` | Maximum backoff ceiling in seconds. |
| `JEV_API__RETRY_TRANSPORT` | None | `false` | Permit retries after transport failures. |
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

The CLI's explicit `--api-key` is literal and overrides every settings source. Prefer an approved
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
The [event reference](events.md) defines exact built-in fields and caller correlation.

`SecretStr` masks configured keys, command specifications and resolved keys. The HTTP adapter
retains an unwrapped key. Redaction has limits: CLI error text, protocol errors
and arbitrary tracebacks are not universally scrubbed. Consult
[credentials](../../SECURITY.md#credentials) and
[diagnostic disclosure](../../SECURITY.md#diagnostics-and-error-content)
before logging or sharing output. For recovery steps, use
[troubleshooting](../how-to/troubleshoot.md).


## Retry limits

Pass `retry=RetryPolicy(...)` to either adapter. Import `RetryPolicy` from
`judgevet`. Its defaults are `max_attempts=1`, `retry_base_delay=0.5`,
`retry_max_delay=5.0` and `retry_transport=False`.

`max_attempts=1` preserves the default single request. Set a larger value to
retry errors whose `retryable` property is true. This covers rate limits and
service failures. Transport failures also require `retry_transport=True`.
A read or write failure can occur after the service accepted the request;
replaying it can duplicate a billed judgment. The library does not provide
an idempotency guarantee.

The attempt count includes the initial request. After failed attempt number
`n`, the delay ceiling is `min(retry_max_delay, retry_base_delay * 2**(n-1))`.
The actual delay is uniformly distributed between 75% and 100% of that ceiling.
Zero base delay or zero maximum delay disables waiting. Each delay must be
finite and nonnegative. Exhaustion re-raises the final error with its cause;
there is no delay after the final attempt.

The sync and async adapters use the same policy. Async retry waits use
`asyncio.sleep` and are cancellable.
Cancellation during a request or wait propagates without another attempt.
Authentication errors, request errors, malformed successful answers and
redirects do not trigger retries. The existing HTTP 408 mapping remains a
non-retryable request error. One terminal diagnostic describes the final
attempt of the logical call.

These limits bound attempts and backoff, not total wall-clock duration. HTTPX
operation timeouts still apply to each attempt. Account for all attempts and
waits when choosing a platform request deadline.

The [official SDK retry reference](https://docs.typesafe.ai/sdk/python/api/retries.md)
documents two retries by default, 0.5-second initial delay, a 5-second cap and
25% subtractive jitter. judgevet uses those timing defaults but requires retry
opt-in and separate transport opt-in. It does not honor `Retry-After` or
`retry-after-ms` headers. These are local policy choices, not live-service
observations. The [error recipe](../how-to/handle-errors.md) shows a bounded call.


## Spend cap

Pass `spend_cap=SpendCap(...)` to either adapter. Import `SpendCap` and
`JevBudgetExceededError` from `judgevet`. The cap is off by default. Its limits
are `max_attempts` and `max_input_tokens`. Each is `None` or a positive integer.
A `None` limit does not bound that counter.

The cap counts physical attempts, not logical calls. Before each attempt,
including every retry, the adapter claims one slot from the cap. The claim
fails when attempts already equal `max_attempts`, or when settled input tokens
already reach `max_input_tokens`. A failed claim raises
`JevBudgetExceededError` and sends nothing. That error is not retryable, so the
retry loop stops. It carries `limit` (`"attempts"` or `"input_tokens"`), `cap`
and `spent`. Its `status_code` is `None`.

After a successful attempt, the cap adds the response `usage.input_tokens`.
A failed attempt still counts as an attempt but settles zero tokens. The AWS SDK
retry quota also charges failed attempts.
Source: https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html.
LiteLLM also raises a distinct budget error that carries the spend and the cap.
Source: https://docs.litellm.ai/docs/proxy/users.

**Open question:** a timed-out or 5xx attempt may still bill input tokens at
the service. No call has shown whether it does. Settling zero for a failed
attempt is a local choice, tracked on
[#56](https://github.com/Alberto-Codes/judgevet/issues/56).

The counters never reset. Every adapter that receives the same `SpendCap`
object, sync or async, draws from the same counters. A `threading.Lock` guards
them, because an `asyncio.Lock` guards one event loop only. The lock is held
for the counter update alone, never across an await.
Source: https://docs.python.org/3/library/asyncio-sync.html.

The attempt bound is hard: concurrent callers cannot exceed it. The token bound
is checked before sending, and tokens settle after the response. Attempts in
flight when the bound is reached can therefore settle past it. Set
`max_attempts` as well when a hard ceiling matters. The cap has no currency
and no preflight size estimate.

CLI and MCP entry points do not set a spend cap. An application can construct
a capped HTTP adapter and pass it to `run_cli` or `create_mcp_server` through
the existing judgment port.

## Proxy and TLS configuration

Import `NetworkConfig` from `judgevet` and pass it as `network=` to either
adapter. Its defaults are `proxy=None`, `ca_bundle=None`, and `verify=True`.
The [sync recipe](../how-to/use-library.md) shows explicit optional CA selection.

With no explicit proxy, HTTPX retains its standard `HTTP_PROXY`, `HTTPS_PROXY`,
`ALL_PROXY`, and `NO_PROXY` behavior. An explicit proxy selects routing even
when `NO_PROXY` would bypass an environment proxy. HTTPX often requires an
`http://` proxy URL for an HTTPS destination; the destination TLS connection
then runs through a CONNECT tunnel. See [HTTPX proxies](https://www.python-httpx.org/advanced/proxies/)
and [environment variables](https://www.python-httpx.org/environment_variables/).

By default, HTTPX verifies certificates and hostnames using certifi roots.
`SSL_CERT_FILE` or `SSL_CERT_DIR` can replace those roots. An explicit
`ca_bundle` takes precedence and creates a verifying Python SSL context.
It replaces the default roots; include every required root in that PEM file.
An empty path, unreadable file or malformed bundle fails adapter construction.
The adapter never disables verification after a CA loading error.

`verify=False` disables both chain and hostname checks. Use it only for
controlled tests with synthetic data. Supplying a CA bundle together with
`verify=False` raises `ValueError`. The default remains secure on the sync,
async, CLI, policy CLI and MCP paths. See [HTTPX TLS configuration](https://www.python-httpx.org/advanced/ssl/).

The current HTTPX client does not switch to the OS trust store automatically.
An MCP SDK transport change does not change this outbound client's trust roots.
Caller-supplied transports own their own network and TLS behavior. Prefer the
default transport when using these settings. Review
[transport and certificate limits](../../SECURITY.md#transport-and-certificates)
before deployment. Changing settings does not reconfigure an existing client.


## Credential sources

Settings construction reads configuration but does not open credential files or
run commands. `settings.api.resolve_key()` performs resolution when requested.
It returns a `SecretStr`, or `None` when no source is configured. The CLI,
policy CLI and MCP resolve once when constructing their adapter. Retries reuse
that credential. Reconstruct the adapter to pick up a rotated source.

The resolver selects the first available source in this order:

1. An explicit argument to `resolve_key`, including an explicit empty string.
   It is literal, even if it starts with `!`.
2. A nonempty configured key that does not start with `!`.
3. `JEV_API__KEY_FILE`, if configured.
4. A configured key starting with `!`, interpreted as a command.

An empty configured key is absent. A selected source failure stops resolution;
it does not try lower-priority sources. Unselected files and commands perform
no IO. Existing key aliases retain their precedence. Direct HTTP adapter
`api_key` arguments remain literal and never execute commands.

For a mounted secret, set `JEV_API__KEY_FILE` to its path and leave literal
key variables unset. Relative paths use the process working directory.
Regular-file symlinks are supported; directories, pipes and devices are rejected.
File reads and command stdout accept at most 4096 bytes, including line endings.
The resolver removes trailing CR/LF and requires one printable ASCII token
without whitespace. Empty, oversized, malformed or multiline output fails with
`ValueError`. These are client input constraints, not a vendor key-format claim.

For a command, a value such as `!op read 'op://vault/item/credential'` names an
installed provider executable and its arguments. Command syntax uses
[Python shlex tokenization](https://docs.python.org/3/library/shlex.html#shlex.split)
and [direct argv execution](https://docs.python.org/3/library/subprocess.html#security-considerations).
Quotes group arguments. Pipes, redirection, substitutions and shell builtins
are not evaluated unless you explicitly name a shell executable. Executables
use the inherited PATH, environment and working directory. Use trusted,
noninteractive providers; stdin and stderr are discarded.

The default command deadline is five seconds after process creation. The
resolver kills the command process group and reaps its direct child after
success, failure or timeout. Cleanup allows one additional second for reaping.
OS process creation itself has no portable deadline guarantee. Commands require
POSIX process groups; unsupported platforms reject command resolution while
literal and file sources remain available. Descendants that deliberately leave
the process group are outside cleanup control. This feature is not a sandbox.

A nonzero exit, timeout, spawn failure or invalid output raises a generic
`ValueError`. Diagnostics omit command text and output. CLI source failures
produce a handled error; MCP uses its existing generic startup-failure path.
Keep the returned key wrapped until the adapter call expression, as in the
[sync recipe](../how-to/use-library.md). Resolution is synchronous; perform it
during startup before serving async requests. See
[credential security](../../SECURITY.md#credentials) for disclosure limits.


## Gateway authentication and metadata

Both HTTP adapters accept `gateway=GatewayConfig(...)`. Its defaults preserve
`Authorization: Bearer <key>`, direct TypeSafe routing and no custom metadata.
The gateway receives the supplied credential instead of a second TypeSafe key.
Gateway operators own upstream credential injection. See [TypeSafe authentication](https://docs.typesafe.ai/api).

`auth_header` chooses the credential field. `auth_scheme` chooses its token
prefix; an empty string sends a bare key. [Apigee's example](https://docs.cloud.google.com/apigee/docs/api-platform/reference/policies/verify-api-key-policy)
uses `x-apikey`. [Kong Key Auth](https://developer.konghq.com/plugins/key-auth/)
supports configured key names. [Azure APIM](https://learn.microsoft.com/en-us/azure/api-management/api-management-subscriptions)
uses `Ocp-Apim-Subscription-Key` by default. These are vendor conventions,
not proof of compatibility with an untested deployment.

The following program uses a synthetic gateway URL and credential. Replace them
with your approved destination and credential before calling a real gateway.
Documentation checks run the exact program with a synthetic HTTP transport.

```python
from judgevet import GatewayConfig, HTTPSystemOneAdapter, Noul, RequestMetadata

gateway = GatewayConfig(
    auth_header="x-apikey",
    auth_scheme="",
    headers={"Example-Tenant": "synthetic", "Example-Route": "default"},
)
with HTTPSystemOneAdapter(
    api_key="dummy-gateway-key",
    base_url="https://gateway.example/organization/jev",
    gateway=gateway,
) as adapter:
    response = adapter.system_one(
        state="Synthetic support ticket",
        questions={"billing": Noul(instructions="Is this about billing?")},
        metadata=RequestMetadata(headers={"example-route": "review"}),
    )
    print(response.answers["billing"])
```

Both trailing-slash forms of this base URL send to
`/organization/jev/v1/systemone`. URL path prefixes are separate from header
names and header values. Supply complete field names and values; no prefix
expansion occurs. Names compare case-insensitively. Per-call metadata replaces
matching defaults. Duplicates within one mapping are rejected. Configuration
and per-call maps are copied; later changes to the caller's dictionaries do not
affect requests. Each logical call snapshots merged fields once for every retry.
Concurrent calls do not change client-wide headers.

Names follow [HTTP token syntax](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.6.2).
Values accept printable ASCII, including empty strings, without leading or
trailing spaces. Controls, tabs, DEL and non-ASCII fail with `ValueError` before
transmission. Local metadata limits are 32 fields, 128 bytes per name, 2048 bytes
per value and 8192 total name/value bytes after merging. These limits are
judgevet policy, not published vendor limits.

Metadata cannot set the selected authentication header, `Authorization`,
`Proxy-Authorization`, `Host`, `Content-Type`, `Content-Length`,
`Content-Encoding`, `Transfer-Encoding`, `Connection`, `Keep-Alive`, `TE`,
`Trailer`, `Upgrade`, `Expect`, `Cookie` or `Set-Cookie`. Authentication can use
`Authorization` or a custom token name, but cannot reuse another protected name
or `traceparent`, `tracestate` or `baggage`.

`request_id_header` forwards only the dedicated [scoped request ID](events.md#caller-correlation).
Without a binding it sends no field. It cannot use a protected or trace field,
and collision with explicit metadata raises `ValueError`. Arbitrary logging
context remains local. Explicit `traceparent`, `tracestate` and `baggage` values
are opaque caller text. Callers own their format and disclosure choices under
[W3C Trace Context](https://www.w3.org/TR/trace-context/) and
[W3C Baggage](https://www.w3.org/TR/baggage/). The client does not create spans,
extract context or claim tracing conformance.

CLI, policy CLI and MCP consume the gateway environment settings listed above.
For example, set `JEV_API__AUTH_HEADER=x-apikey` and `JEV_API__AUTH_SCHEME` to an
empty string. Supply `JEV_API__HEADERS` as a JSON string map. `$NAME` and
`!command` metadata values remain literal. Only existing credential sources
resolve files or commands. MCP configuration belongs to the host environment;
its tool schemas do not accept headers or authentication overrides.

Credentials and metadata reach the configured base URL on each attempt. Choosing
another base URL changes their recipient. Redirects remain disabled, including
same-origin redirects. A plain HTTP proxy can inspect fields. HTTPS CONNECT
exposes the destination, and a TLS-terminating intermediary can inspect content.
TLS verification defaults remain unchanged. Header values are omitted from
configuration repr, validation messages and built-in events; arbitrary caller
tracebacks remain outside that guarantee. Metadata is not a secret vault.

Gateway-owned errors use the existing [status-based error mapping](errors.md).
A gateway 429 remains retryable without TypeSafe JSON. Unknown JSON, HTML and
text error bodies are omitted from messages; recognized TypeSafe detail parsing
remains unchanged. Local loopback tests prove these client properties. They do
not verify a deployed gateway or unseen TypeSafe error bodies.


## Caller-owned state redaction

Pass `redactor=` to either HTTP adapter to transform state before transmission.
Import the structural `StateRedactor` protocol from `judgevet` or
`judgevet.ports`. It defines one synchronous method,
`redact(state: str | dict[str, Any] | list[Any]) -> str | dict[str, Any] | list[Any]`.
The client supplies no detection rules. The caller owns what to remove or retain.
See the [protocol](../../src/judgevet/ports/__init__.py) and
[outbound preparation](../../src/judgevet/adapters/outbound/request_body.py).

The following synthetic example replaces all state. It demonstrates the seam,
not a useful judgment policy or a sensitive-data detector. Replace the callback,
URL and credential with approved application choices for a real call.
Documentation checks execute the exact program against an isolated wheel with
synthetic HTTP responses.

```python
from typing import Any

from judgevet import GatewayConfig, HTTPSystemOneAdapter, Noul, StateRedactor


class ReplaceState:
    def redact(self, state: str | dict[str, Any] | list[Any]) -> str:
        return "Caller-approved synthetic summary"


redactor: StateRedactor = ReplaceState()
with HTTPSystemOneAdapter(
    api_key="dummy-gateway-key",
    base_url="https://gateway.example/organization/jev",
    gateway=GatewayConfig(auth_header="x-apikey", auth_scheme=""),
    redactor=redactor,
) as adapter:
    response = adapter.system_one(
        state={"private_note": "Synthetic original content"},
        questions={"billing": Noul(instructions="Is this about billing?")},
    )
    print(response.answers["billing"])
```

The adapter deep-copies ordinary JSON state before invoking the callback.
Mutating that copy does not change caller-owned nested lists or dictionaries,
including when the callback raises. The callback receives no questions, model,
credentials or headers. Its return value must be a string, dictionary or list
that can be serialized as finite JSON. Invalid output fails before transmission.

A configured redactor runs once per logical call, immediately before the shared
outbound serializer. The adapter reuses the same immutable UTF-8 body on every
retry. Changes to input or retained callback output after preparation cannot
rewrite later attempts. Separate calls invoke the callback again. Copy failures,
callback exceptions and serialization failures propagate before retry handling,
with no request and no fallback to original state. Callback exceptions may carry
sensitive content; arbitrary application tracebacks are not scrubbed.

The same synchronous method runs in async adapters. Keep it fast and nonblocking;
async callbacks are not supported. Applications own synchronization for stateful
callbacks shared across concurrent calls. Do not mutate inputs concurrently
with preparation. A callback that changes external references or performs IO
remains caller-owned code; copying is not a sandbox.

Omitting `redactor`, or passing `None`, preserves the existing state and HTTPX
serialization path without copying. Gateway authentication, metadata and
correlation remain independent. State redaction does not redact question text
or header values. The [egress contract](../../SECURITY.md#data-sent-to-the-service)
lists each transmitted channel and its limits.

CLI and MCP command entry points retain the default. There is no environment
setting, command option or MCP tool argument that loads Python redactor code.
An application can construct a redaction-enabled HTTP adapter and pass it to
`run_cli` or `create_mcp_server` through the existing judgment port.
