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
| JSONL audit sink | `JsonlAuditSink` |
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

`judgevet.providers` supports `ProviderFactory`, `provider_scope`,
`AsyncProviderFactory`, `async_provider_scope`, `ProviderError`,
`ProviderUnavailableError`, `ProviderRequestError`, `ProviderCapabilityError`,
`ProviderTransportError` and `ProviderResponseError`. These are module exports;
they add no root imports. The error classes retain identity with the classes
`judgevet.domain.provider_errors` exports. `ProviderError` is defined in
`judgevet.domain.errors`, and `judgevet.domain.provider_errors` re-exports it.

`ProviderError` derives from `JudgevetError`. `JevError` derives from
`ProviderError`, so the hierarchy is
`JudgevetError` → `ProviderError` → `JevError` → each `Jev*` error.
Hosted Jev failures now satisfy `ProviderError`, and the conformance kit accepts
them. The change is additive: existing `except JevError` and
`except JudgevetError` catches behave as before, and a `ProviderError` is still
not a `JevError`. Code that catches `ProviderError` now also catches Jev errors.
Source: https://github.com/Alberto-Codes/judgevet/issues/259#issuecomment-5910551186.

The five specific provider errors
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

## Image evidence library extension

`judgevet.media` supports `ImageAttachment`, `ImageEvidence`, `MediaCapabilities`,
`MediaSystemOnePort`, `MissingEvidenceError` and `judge_with_images`.
`judgevet.media` also exports `AsyncMediaSystemOnePort` and
`async_judge_with_images`.
Source: https://github.com/Alberto-Codes/judgevet/issues/252.
These are
module exports; existing root exports, `SystemOnePort` and `SystemOneResponse`
remain unchanged. The pure values live in `judgevet.domain.media`; the protocol
lives in `judgevet.ports.media`. Re-exports retain object identity.

`MissingEvidenceError` derives from `ProviderRequestError`. Constructor shape
errors are `ValueError`. Media dispatch distinguishes missing required evidence,
unsupported capabilities, transport failure and an explicitly declared Choice
answer for insufficient evidence. Existing text requests retain their original
route and result. The [library guide](../how-to/use-library.md#supply-ordered-image-evidence)
documents immutable snapshots, local ceilings and response checks.

This extension adds no inference dependency, HTTP media implementation or live
verification claim. Applications own provider selection, model declarations,
number semantics and policy thresholds.
Source: [accepted media contract](https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851219798).

## Provider options and receipts

`SystemOneResponse` adds a `receipts` field. It maps each answer name to
provider measurements of type `float`, `bool` or `None`. It defaults to an
empty mapping, so existing constructors and equality checks keep working. The
HTTP adapters and the fakes leave it empty.

`judge_with_images` and `async_judge_with_images` add keyword-only
`provider_options`. They forward the mapping only when it is set. judgevet
never interprets its keys. The chosen provider method must take a
`provider_options` keyword. Otherwise the call raises `ProviderCapabilityError`
before dispatch.

`judgevet.ports.options` holds four structural ports that declare the keyword.
The existing ports, the HTTP adapters, the fakes and the conformance kit stay
unchanged. A three-argument provider still satisfies `SystemOnePort`. The CLI,
the MCP server and the policy entry points do not pass options.
Source: [provider options contract](https://github.com/Alberto-Codes/judgevet/issues/281#issuecomment-5933041037).

## CLI image manifests

The source tree adds optional `--evidence-file` through public Typer command and
option classes. Existing positional and file grammar, stdin state, policy
rendering and public `main` signature remain unchanged. Each invocation keeps
its own file option metadata and each application keeps its provider selection.

Image evidence requires an application-selected media provider. The hosted
adapter remains text-only. Valid empty optional evidence retains the previous
text route. Required missing evidence fails before acquisition. Local manifest
errors, unsupported capabilities and declared transport failures exit 1; explicit
insufficient-evidence Choice answers retain ordinary success and policy semantics.
This is offline source acceptance evidence, not a published release or a new live
service verification claim.
Source: [CLI media contract](https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851367000).

### MCP image evidence

The source `evaluate_policy` schema adds optional `evidence` JSON text.
The original three tool schemas remain unchanged. Embedded images use base64
bytes and explicit ordered question associations. Valid empty optional evidence
retains text routing. Nonempty evidence requires a selected media provider.
Success retains the existing answer and policy envelope. Media failures expose
a neutral error class and safe category without payload content. Work uses the
existing serialized worker and cancellation cleanup. This adds no transport or
inference dependency and makes no live provider compatibility claim.
Source: [MCP media contract](https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851508259).

### Optional media provenance

`judgevet.media_audit` exports `MediaProvenance` and `media_provenance`.
`JudgmentRecord` adds optional `media_provenance` as its last field, defaulting
to `None`; schema version 1 and root exports remain unchanged. The pure value
lives in `judgevet.domain.media_audit`. Hashing stays outside the domain.
Applications explicitly supply a key and attach provenance to existing records.
No new audit wrapper, retry accounting or usage estimation is introduced.
Typed and equivalent raw question definitions share a request fingerprint.
Image order, exact bytes and bindings remain distinct evidence inputs.
Source: [media provenance contract](https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851443210).

## Installed provider extension proof

The `provider-artifacts` pre-push hook runs `scripts/smoke_provider_release.py`.
It builds the wheel and source archive, then builds a second wheel from that
archive. Each wheel is installed into a fresh base environment and a fresh
`mcp` extra environment outside the checkout. The hook records the SHA-256 of
the archive and both wheels, the installed version, the dependency inventory and
the file of every loaded judgevet module. The identity process, the library
consumer and each CLI and MCP child report their module files, and every file
must come from that environment's site-packages. The runner evaluates each
installed distribution's PEP 508 markers for the tested interpreter. The base
inventory must equal the declared dependency closure without MCP, with no
missing applicable dependency. The extra inventory adds only the `mcp` closure.

A repository fixture translates application questions into public judgevet types
and translates typed responses back into application findings. It exercises direct library text, media and policy calls,
the CLI factory with borrowed and owned providers, and the MCP policy tool over
real stdio. MCP calls use both raw JSON-RPC lines and the SDK's `stdio_client`
with `ClientSession`. The checks compare exact state, question definitions,
requested and resolved models, known and unknown usage, image bytes, image
order and bindings. They also cover insufficient-evidence outcomes, unsupported media and
the absence of fallback. Entered provider contexts close once after success,
call failure or an invalid port. Factories roll back failed setup.
An offline mock transport checks the hosted request shape. Optional
media provenance is fingerprinted without raw content. Every runtime child
starts through a bootstrap that refuses network connections and name lookups
before the package is imported. Children receive no inherited import path,
credential or configuration variable. Package build and installation may still
download declared public dependencies.

This proof is offline. It makes no live service, model quality, server or
private integration claim.
Source: [installed provider proof contract](https://github.com/Alberto-Codes/judgevet/issues/205#issuecomment-5851596904)
and [repair](https://github.com/Alberto-Codes/judgevet/issues/205#issuecomment-5851983135).

## MCP output schemas

Release 0.14.0 adds an `outputSchema` to each of the four MCP tools (#211).
Each schema is a closed JSON Schema 2020-12 object without a `$schema` key.
It describes the structured content of a successful tool call. Error outcomes
carry no structured content and fall outside the schemas. Tool names and input
schemas stay unchanged. Clients that read structured content can now validate it.
See `src/judgevet/adapters/inbound/mcp_output_schemas.py`.
Source: https://github.com/Alberto-Codes/judgevet/issues/211#issuecomment-5860666386.

## MCP ask tool text as JSON

Release 0.14.0 changes the text block of each `ask_*` tool (#225). The single
text block now holds `json.dumps` of the structured content. `json.loads` of
that text equals the structured content. `evaluate_policy` already used the
same serialization. Clients that parsed the earlier text must parse JSON instead.
See `answer_result` in `src/judgevet/adapters/inbound/mcp_handlers.py`.
Source: https://github.com/Alberto-Codes/judgevet/issues/225.

## Default rubric flag for ask_score

Release 0.14.0 adds a boolean `default_criteria` to `ask_score` structured
content (#228). It is true when the call omitted `criteria`. The server then
applied the default rubric `Poor`, `Fair`, `Good`, `Excellent`. It is false
when the caller supplied criteria. `evaluate_policy` Score answers omit the flag.
See `src/judgevet/adapters/inbound/mcp_handlers.py`.
Source: https://github.com/Alberto-Codes/judgevet/issues/228#issuecomment-5882662573.

## MCP model from settings

Release 0.14.0 lets `JEV_API__DEFAULT_MODEL` select the `judgevet-mcp` model
(#216). When the launch model is `jev-latest`, the entry point uses the
configured default model instead. An explicit other launch model still wins.
The CLI `--model` default stays unchanged; see the [CLI reference](cli.md).
See `src/judgevet/adapters/inbound/mcp_entrypoint.py`.
Source: https://github.com/Alberto-Codes/judgevet/issues/216.

## Spend cap settings in the roots

Release 0.14.0 reads the spend cap in the CLI and MCP composition roots (#56).
`JEV_API__SPEND_MAX_ATTEMPTS` and `JEV_API__SPEND_MAX_INPUT_TOKENS` opt in.
Both default to unset, so existing launches build no cap. Each root reads the
cap once. One cap spans a CLI process or an MCP server lifetime and never resets.
See `src/judgevet/adapters/inbound/settings.py`.
Source: https://github.com/Alberto-Codes/judgevet/issues/56.

## Audit file from settings

Release 0.16.0 adds `JEV_API__AUDIT_PATH` (#54). When it is set, the CLI and
`judgevet-mcp` open one `JsonlAuditSink` before credential resolution. Unset,
both roots write no audit file, as before. A CLI open failure names the
variable, not the path. See [JSONL sink](configuration.md#jsonl-sink).
See `src/judgevet/adapters/inbound/cli_policy_run.py` and
`src/judgevet/adapters/inbound/mcp_entrypoint.py`.
Source: https://github.com/Alberto-Codes/judgevet/issues/54.

## Ollama error bodies

Release 0.16.0 reads a second error body shape (#268). Ollama documents its
errors as `{"error": "<string>"}`. When a body lacks `detail`, the adapter
appends a nonempty string `error` to the exception message. Status mapping
and `detail` parsing stay unchanged. This shape is documented, not observed
against a running server. See `_read_error_detail` in
`src/judgevet/adapters/outbound/response_translation.py`.
Source: https://docs.ollama.com/api/systemone.

## Conformance kit and extra

Release 0.15.0 publishes `judgevet.testing.conformance` (#241, #246, #247).
A provider package subclasses `BaseProviderConformance` or
`BaseAsyncProviderConformance` in its own test suite. Release 0.16.0 adds the
async scope rules (#251) and exports `AsyncProviderFactory` from the kit (#277).
The `conformance` extra installs pytest and anyio for the kit. The base
install stays unchanged. Importing the kit without pytest raises `ImportError`.
The [API reference](api.md) lists the fixtures. The
[provider guide](../how-to/use-a-self-hosted-provider.md#check-the-provider-with-the-conformance-kit)
shows a run. See `src/judgevet/testing/conformance.py` and `pyproject.toml`.
Source: https://github.com/Alberto-Codes/judgevet/issues/241#issuecomment-5902293909.
