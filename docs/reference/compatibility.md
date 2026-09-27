---
status: draft
---

# Supported imports and compatibility

Status: **draft**.

judgevet ships one distribution and one version. The library, CLI, MCP server
and optional dependencies have separate compatibility assessments within that
release. One wheel does not have independently released library/CLI/MCP versions.

## Library imports

The root `__all__` declares these supported names:

| Purpose | Imports from `judgevet` |
|---|---|
| Explicit adapters | `HTTPSystemOneAdapter`, `AsyncHTTPSystemOneAdapter` |
| Network configuration | `NetworkConfig` |
| State transformation | `StateRedactor` |
| Gateway configuration | `GatewayConfig`, `RequestMetadata` |
| Retry configuration | `RetryPolicy` |
| Spend cap | `SpendCap` |
| Audit records | `AuditSink`, `JudgmentRecord` |
| Scoped diagnostic correlation | `bind_request_id` |
| Structural ports | `SystemOnePort`, `AsyncSystemOnePort` |
| Questions | `Question`, `Noul`, `Choice`, `Score` |
| Answers and metadata | `Answer`, `NoulAnswer`, `ChoiceAnswer`, `ScoreAnswer`, `SystemOneResponse`, `Usage` |
| Common error base | `JudgevetError` |
| Service errors | `JevError`, `JevAuthError`, `JevRequestError`, `JevMaxTokensExceededError`, `JevResponseError`, `JevServiceError`, `JevRateLimitError`, `JevBudgetExceededError` |
| Version | `__version__` |
| Verified model | `VERIFIED_MODEL` |

Re-exports retain the original objects. Existing domain, port and adapter deep
imports remain valid. There are no wrapper classes or implicit adapter owners.
The [API reference](api.md) documents service fields and observed versus inferred
errors. Not every possible Python or HTTP exception is a `JevError`; existing
raw redirect errors, for example, retain their prior behavior.

`judgevet.policy` supports `NoulRule`, `ChoiceRule`, `ScoreRule`, `Rule`, `Policy`,
`ValidatedPolicy`, `RuleReport`, `PolicyReport`, `validate_policy`,
`evaluate_policy`, `PolicyError`, `PolicyDefinitionError`, and `PolicyAnswerError`.
`judgevet.policy_json` supports `parse_policy`. These modules are new in the
0.7.0 release and absent from 0.6.0. The implementation helpers are internal;
use the facades for new policy callers.

The [policy reference](policy.md) defines the complete local contract.
The [typed policy guide](../how-to/use-policy-library.md) gives runnable examples,
constructor invariants, strict answer checks, immutable snapshots, error handling
and explicit sync/async lifecycle ownership. Public policy errors are local
`ValueError` subclasses, separate from the Jev service-error hierarchy.

## Neutral error base

`JudgevetError` adds a common catch for declared library errors. The root,
`judgevet.domain` and `judgevet.domain.errors` exports share one class.
`JevError` now inherits from it. `PolicyError` inherits from it and `ValueError`.
Existing Jev and policy imports retain identity, constructors and catch behavior.
Jev status and retry metadata remain unchanged. Policy errors remain separate
from `JevError` and retain ordinary exception arguments.

The neutral base adds no status or retry metadata. Existing Python validation
errors and arbitrary provider exceptions keep their original types.
No caller migration is required for existing exception catches.
Source: https://github.com/Alberto-Codes/judgevet/issues/78#issuecomment-5850346340.

## Provider imports and errors

`judgevet.providers` supports `ProviderFactory`, `provider_scope`, `ProviderError`,
`ProviderUnavailableError`, `ProviderRequestError`, `ProviderCapabilityError`,
`ProviderTransportError` and `ProviderResponseError`. These are module exports;
they add no root imports. The error classes retain identity with their definitions
in `judgevet.domain.provider_errors`.

`ProviderError` derives from `JudgevetError`. The five specific provider errors
derive from `ProviderError`: unavailable support or setup, rejected requests,
unsupported capabilities, transport failures and invalid typed responses.
They accept ordinary exception arguments and add no HTTP status or retry
metadata. Applications supply safe messages and map known backend failures at
their provider boundary. Unexpected exceptions keep their original types.
Existing `JevError` imports, constructors and catch behavior remain unchanged.

The [ownership helper](configuration.md#application-owned-providers) requires an
explicit borrowed port or factory. It does not change the `SystemOnePort`
contract or install an inference dependency. Existing callers can continue to
pass their ports directly. Unknown usage remains `None`; provider confidence
semantics and policy thresholds remain application-owned.
Source: [accepted provider contract](https://github.com/Alberto-Codes/judgevet/issues/200#issuecomment-5850335591).

## Application-selected CLI providers

`judgevet.adapters.inbound.cli.create_cli_app` accepts keyword-only `port` or
`provider_factory` and returns an independent Typer application. Selection is
explicit and applies to ordinary and policy commands. Borrowed ports remain
open; factory contexts own acquisition and cleanup for each invocation.
Omitting both arguments preserves hosted defaults. Both arguments raise `ValueError`.
No provider flag, discovery or provider environment setting is added.

The existing `app`, `main`, `cli_main` and helper imports remain supported.
The generated command preserves existing grammar, output and exit meanings.
Explicit selection bypasses hosted settings and credentials without fallback.
Declared `JudgevetError` subclasses, including provider and spend failures,
use the existing handled-error output. Provider-owned audit and spend mechanisms
remain opt-in; selecting a port adds neither mechanism.
Source: [CLI provider contract](https://github.com/Alberto-Codes/judgevet/issues/202#issuecomment-5850672112).

## 0.7.0 compatibility assessment

| Surface | Assessment | Migration |
|---|---|---|
| Library | Additive root exports, pure policy API and separate JSON facade | No existing import migration. Use typed rules and immutable reports for new policy callers. |
| CLI | Grammar, diagnostics, ordered output and exit meanings 0/1/2/3 retained | None. Private CLI policy wrappers keep their historical return shapes and answer checks. |
| MCP | Same three tools, schemas and structured content | None. No policy tool is added. |
| Dependencies | Same mandatory dependencies and optional `mcp` extra | None. Base installs still omit MCP and include `py.typed`. |

Strict public policy evaluation and the legacy CLI wrapper intentionally differ
for malformed answers. Public evaluation always checks selected confidence and
snapshotted choice/score constraints; the legacy checks remain as before. This
is a new API contract, not a migration of existing CLI semantics.

## Credential-source compatibility

Direct adapter `api_key` values remain literal. Settings keys starting with `!`
now opt into command resolution. File and command resolution is explicit in
Python and occurs once at CLI/MCP adapter construction. Commands require POSIX;
existing literal keys and file sources do not require process-group support.
The mandatory dependency set and optional MCP boundary are unchanged.

## Diagnostic compatibility

The 0.8.0 event contract adds nullable correlation, resolved-model and usage
fields. Existing event names and terminal retry semantics remain. Diagnostic
model values outside the documented filter now render null. Built-in events
exclude arbitrary application context; generic application logging retains it.
Strict event-key consumers must adopt the [documented field sets](events.md).
The library binding API is additive. CLI output and MCP tool schemas remain
unchanged; no gateway headers or runtime dependencies are added.

## Finite-answer validation correction

The correction in [#170](https://github.com/Alberto-Codes/judgevet/issues/170)
tightens invalid-input handling relative to published 0.10.1. Answer constructors
reject NaN and both infinities with `ValueError`. Boolean scores now raise
`TypeError`, matching the other numeric answer fields. Valid integer and float
inputs, inclusive bounds, distribution tolerance and public imports remain.
Callers that supplied those invalid values must handle the domain error or
supply a valid value.

Malformed service answer values now raise `JevResponseError` instead of leaking
constructor `TypeError` or `ValueError`. The error is not retryable. CLI and MCP
receive the same error through their port; successful outputs and tool schemas
remain unchanged. Runtime dependencies and the optional MCP extra remain.
Policy validation still rejects deliberately corrupted answers when it consumes
them. Nested dictionaries remain mutable. This correction does not publish a
release or change the live-service evidence.

## Keyword-only question constructors

The change in [#172](https://github.com/Alberto-Codes/judgevet/issues/172)
makes every `Noul`, `Choice` and `Score` constructor argument keyword-only.
Positional construction now raises `TypeError`. Parameter names and defaults
remain. Callers name `instructions` and `criteria`, for example
`Choice(criteria={"a": "A", "b": "B"})`. The
[TypeSafe Python SDK](https://docs.typesafe.ai/sdk/python) constructs these
types by keyword only, and the three types share no positional order.

## Retries on by default

The change in [#196](https://github.com/Alberto-Codes/judgevet/issues/196)
turns retries on by default. `RetryPolicy()` now makes three attempts, and an
adapter built without `retry` uses it. The CLI and MCP server follow through
the `JEV_API__MAX_ATTEMPTS` default, which moves from `1` to `3`. The variable
name is unchanged.

A caller who relied on one attempt now gets three on HTTP 429 or any 5xx
status. A persistent failure takes longer to surface and sends up to two more
requests. Other errors still make one attempt. Transport retries stay opt-in,
and `Retry-After` is not honoured. To keep one attempt, pass
`retry=RetryPolicy(max_attempts=1)` or set `JEV_API__MAX_ATTEMPTS=1`. A spend
cap counts every attempt. Audit records stay one per call. The default follows
the vendor SDK.
Source: https://docs.typesafe.ai/sdk/python/api/retries.md.

## Verification limits

Policy tests are synthetic local acceptance evidence. They do not establish model
quality or new service behavior. Live 429/529 bodies remain unseen; resolved
models other than `jev-1.13.0` remain untested. Intermittent MCP
initialization failures have no established cause or remedy. Follow the
[connection checks](../how-to/install.md#when-mcp-does-not-connect). A successful
fresh launcher does not prove that an existing agent session reloaded its tools.


## Application-selected MCP providers

The optional MCP adapter adds keyword-only `model` to `create_mcp_server` and
`run_stdio`. Its composition root adds keyword-only `port`, `provider_factory`
and `model`. Existing calls retain their defaults. Tool schemas, answer shapes
and the three existing tool names remain unchanged. The application selects
the model; tool arguments cannot override it.

Synchronous provider calls now run serially outside the event loop.
Cancellation waits for running work before owned cleanup. Queued canceled calls
do not start. Borrowed ports remain open. Applications retain responsibility
for provider deadlines, audit, spend accounting and state redaction.
Source: [MCP provider contract](https://github.com/Alberto-Codes/judgevet/issues/202#issuecomment-5850906357).


## Additive MCP policy tool

The source tree adds `evaluate_policy` to tool discovery. Consumers that assert
exactly three tools must allow the new name. The original three schemas and
results remain unchanged. The new tool accepts caller question IDs and public
policy JSON. It uses strict public evaluation without changing CLI behavior.
The application selects the model; the tool cannot override it. This is source
acceptance evidence, not a claim about the published 0.13.0 release.
Source: [keyed policy contract](https://github.com/Alberto-Codes/judgevet/issues/202#issuecomment-5851056470).
