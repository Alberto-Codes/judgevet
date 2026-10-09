---
status: draft
---

# MCP reference

Status: **draft**. `judgevet-mcp` requires the optional `mcp` extra. It serves
MCP over stdio: stdout is protocol traffic and stderr is diagnostics. For
installation, host configuration and discovery, use [Connect MCP](../how-to/connect-mcp.md).

## Tool arguments

The three `ask_*` tools take these arguments. All require `state` and
`instruction` (singular). `instruction` is a string. The published schema
allows a string or object for `state`.

| Tool | Additional argument | Default when omitted |
|---|---|---|
| `ask_noul` | None | No criteria argument is exposed. |
| `ask_choice` | `criteria`: object mapping labels to descriptions | `{"yes":"Yes","no":"No"}` |
| `ask_score` | `criteria`: ordered levels, lowest first, of the property the question asks about, such as `["Not urgent","Low","Medium","High","Critical"]` for urgency | `["Poor","Fair","Good","Excellent"]`, a generic quality rubric |

The [tool definitions](../../src/judgevet/adapters/inbound/mcp.py) are the source
for these local schemas. `ask_noul`, `ask_choice` and `ask_score` accept a
string or an object for `state`. They do not accept an array. `evaluate_policy`
accepts a string, an object or an array for `state`. Each ask tool schema sets
`additionalProperties: false`. The ask tool schemas do not specify item/value
schemas for criteria. Handlers are not a substitute for full schema validation.

Each tool constructs one named question and calls the sync port with
the host-selected model, which defaults to `"jev-latest"`.
The installed `judgevet-mcp` command takes the host-selected model from
`JEV_API__DEFAULT_MODEL`.
Tool arguments cannot select a model or acceptance policy.
The internal question names are `noul_question`, `choice_question` and
`score_question`. Host argument `instruction` becomes wire `instructions`.
See [configuration overrides](configuration.md#entry-point-overrides).

## Tool titles and annotations

Each tool publishes a display `title` and two annotations in `tools/list`.

| Tool | `title` |
|---|---|
| `ask_noul` | Ask a yes/no judgment |
| `ask_choice` | Ask a multiple-choice judgment |
| `ask_score` | Ask a scored judgment |
| `evaluate_policy` | Evaluate a judgment policy |

Every tool sets `readOnlyHint: true`, because a judgment changes no
environment state. Every tool sets `openWorldHint: true`, because the call
reaches an outside judgment model through the configured provider. judgevet
omits `destructiveHint` and `idempotentHint`. The specification gives them
meaning only when `readOnlyHint` is false. All annotations are hints. A client
must not trust them from an untrusted server.
Source: https://modelcontextprotocol.io/specification/2026-07-28/schema.
Source: https://modelcontextprotocol.io/specification/2026-07-28/server/tools.

## Successful answers

A successful call returns structured content and one text content item. The
text is that structured content serialized as JSON, so parsing the text gives
the same object. Source:
[structured content](https://modelcontextprotocol.io/specification/2025-11-25/server/tools#structured-content).
Python SDK attributes use `structured_content` and `is_error`; wire JSON fields
use `structuredContent` and `isError`. This distinction is recorded in the
[adapter's SDK citations](../../src/judgevet/adapters/inbound/mcp.py).

| Tool | Structured fields |
|---|---|
| `ask_noul` | `noul`, `model`, `usage` |
| `ask_choice` | `choice`, `confidence`, `probabilities`, `model`, `usage` |
| `ask_score` | `score`, `confidence`, `probabilities`, `legend`, `default_criteria`, `model`, `usage` |

`usage` contains `input_tokens` and `output_tokens`. `default_criteria` is a
boolean. It is `true` when the call omitted `criteria` and the server applied
the default `["Poor", "Fair", "Good", "Excellent"]`. It is `false` when the
caller supplied `criteria`, including a list equal to the default. Sources:
[issue #228 decision](https://github.com/Alberto-Codes/judgevet/issues/228#issuecomment-5882662573)
and [AIP-129](https://google.aip.dev/129). Structured content contains
the single answer's fields directly, not the CLI's `answers` envelope. JSON
object keys for Score levels are strings on the wire. Field semantics and vendor
citations are in the [Python API reference](api.md#answer-and-container-types).
A host that shows only text shows this JSON. A successful call is a judgment,
not evidence of its correctness.

Release 0.14.0 and later declare an `outputSchema` for each of the four tools. Each
schema is a closed JSON Schema 2020-12 object that matches the fields in the
table above and, for `evaluate_policy`, the result described below. Every
field carries a description. A token count in `usage` is an integer or null.
Error results carry no structured content, and the schemas do not cover them.
The [output schemas](../../src/judgevet/adapters/inbound/mcp_output_schemas.py)
are the source. Releases before 0.14.0 declare no output schemas.
Source: [output schema rules](https://modelcontextprotocol.io/specification/2025-11-25/server/tools#output-schema).

## Keyed policy tool

Release 0.14.0 adds `evaluate_policy` to discovery.

Pass required `state`, `questions` and `policy`, with optional `evidence`.
State accepts a string, object
or array. Questions use the CLI JSON grammar, keyed by caller IDs. Each question
accepts only `type`, `instructions` and `criteria`; unknown fields produce an
error before dispatch. Optional Noul criteria pass through unchanged. Choice
and score questions need `criteria`. A choice question takes a non-empty object
of labels. A score question takes a non-empty array of levels, lowest first.
The defaults of `ask_choice` and `ask_score` do not apply here. The question
schema declares this rule with nested `if` and `then` conditionals. The handler
also rejects a question without valid criteria, because not every client
validates the input schema.
Source: https://github.com/Alberto-Codes/judgevet/issues/305. Policy uses
the public [policy JSON grammar](policy.md#json-grammar). The `policy` schema
declares that grammar as closed JSON Schema 2020-12 objects, with a nested
`anyOf` for `pass` and one example in its description. The handler still checks
bound order, question-relative ranges, boolean bounds and duplicate keys. An
unknown-field error names the first unknown key in sorted order, shortened to 64
characters, and the allowed keys. The application selects the model;
a `model` argument is rejected before dispatch. Invalid definitions also fail
before dispatch.

Success returns matching JSON text and structured content with `model`, `usage`,
`answers` and `policy`. The policy object contains `result` (`pass` or `fail`)
and ordered `rules` with `question`, `pass` and `detail`. An unmet policy has
`isError: false`. Invalid input, invalid policy answers and declared provider
failures have `isError: true`, without fabricated answers or a verdict. Unexpected
implementation errors retain SDK handling. Provider error messages must be safe
for the application to disclose. Unknown usage stays null.

The tool uses strict public policy evaluation. Existing CLI semantics remain
unchanged. Provider selection does not install audit or spend controls. Providers
that opt into those controls retain their own accounting and records.
Source: [keyed policy contract](https://github.com/Alberto-Codes/judgevet/issues/202#issuecomment-5851056470).

## Failure and lifecycle behavior

The ask tools check their arguments before any provider call. A missing
`state` or `instruction` returns a tool result with `isError` true and the text
`Missing required argument: <name>`. `ask_choice` criteria must be a non-empty
object, and `ask_score` criteria must be a non-empty array, when given. Wrong
criteria return the same kind of tool result. An argument the tool schema does
not declare returns `Unknown arguments: <names>`, with every unknown name in
sorted order. `ask_noul` declares no `criteria`, so `criteria` is unknown
there. The handlers check this because not every client validates the input
schema. Source: https://github.com/Alberto-Codes/judgevet/issues/303. The MCP tools specification
classifies input validation errors as tool execution errors; see
[error handling](https://modelcontextprotocol.io/specification/2025-11-25/server/tools#error-handling).

An unknown tool and a missing expected answer raise `ValueError` in the
handlers. A wrong answer variant raises `TypeError`. A declared service error
from any tool returns a tool result with `isError` true and the error text.
With `evidence`, `evaluate_policy` reports only the error type, as
`<Type>: media evaluation failed`. A tool failure is not a negative Noul answer
or an unmet policy.

A tripped [spend cap](configuration.md#spend-cap) returns a tool result with
`isError` true on every tool, the media path included. Its text names the limit
and says a restart is required. An example is
`Spend cap reached: attempts spent 2 of 2; restart the server to continue.`.
The cap lasts for the server's lifetime and never resets, so a retry cannot
succeed until the host restarts the server. Do not assume error text has been
scrubbed; see [diagnostic limits](../../SECURITY.md#diagnostics-and-error-content).

The entry point constructs and closes the adapter around serving. It returns 2
for missing runtime, invalid settings or missing key, and 130 for keyboard
interruption. With `JEV_API__AUDIT_PATH` set, it opens the
[audit file](configuration.md#entry-point-audit-file) first and closes it after
the adapter. A fatal failure exits 1 and names its stage: `audit sink`,
`credential resolution`, `provider acquisition`, `serving` or `shutdown`.
A sink that cannot open reports `judgevet-mcp: audit sink failed (<TypeName>)`.
See [fatal diagnostics](../how-to/troubleshoot.md).
EOF ends the stdio session. The tested SDK baseline and legacy
initialization path are recorded in the adapter source; an unexercised protocol
path is not promoted by those tests. Intermittent host initialization failures
have no established remedy; use [connection checks](../how-to/troubleshoot.md#when-mcp-does-not-connect).

For embedding, `create_mcp_server(port)` accepts a `SystemOnePort`. The factory
does not construct or close the caller's port. This entry point stays in the
optional inbound adapter; importing the base library does not require MCP.


## Application-selected providers

`create_mcp_server(port, *, model="jev-latest")` borrows a provider and accepts
an explicit host-selected model. `run_stdio` accepts the same arguments.
`mcp_entrypoint.main` accepts keyword-only `port`, `provider_factory` and `model`.
Supply either a borrowed port or an owning factory. Supplying both raises
`ValueError` before acquisition. Explicit selection skips hosted settings and
credentials. Omission retains the hosted command and its configuration.

The server serializes synchronous calls on a worker thread. The event loop
remains available while a provider runs. Cancellation removes queued calls
before dispatch. A running call finishes before cancellation propagates, even
when cancellation repeats. Factory acquisition, calls and cleanup share one
worker thread. Session exit shuts down that worker. Borrowed ports remain open.
Direct registered-handler calls outside a server lifespan use temporary workers.
Applications own provider deadlines; cancellation cannot kill synchronous work.

Declared provider failures cross the entrypoint's existing safe diagnostic
boundary. Provider selection adds no audit sink, spend cap or redaction.
Applications configure those controls on their providers.
Source: [MCP provider contract](https://github.com/Alberto-Codes/judgevet/issues/202#issuecomment-5850906357).

## Image evidence

`evaluate_policy` accepts optional `evidence` as a JSON text string. The embedded
object contains `images`, `by_question` and optional `required`. Each image
contains exactly `id`, `data_base64` and `media_type`. `data_base64` carries
standard ASCII base64 of the original encoded image bytes. `by_question` maps
question IDs to ordered image IDs. `required` lists questions that must have
images. The provider receives original byte order and per-question associations.

The adapter rejects duplicate embedded keys, non-finite constants, unknown
fields, invalid base64 and invalid associations. Already-decoded objects are
invalid. The JSON text ceiling is 48 MiB UTF-8. Limits are 16 images, 8 MiB per
image and 32 MiB decoded bytes in total. Provider capabilities can reduce these
limits. The adapter reads no paths or URLs and does not decode image formats.
Omitting evidence or supplying valid empty optional evidence retains text routing.
The hosted provider does not implement image evidence.

Decoding, validation and inference share the existing serialized worker.
Canceled queued calls submit no work. Canceled running calls drain before owned
cleanup. Acquisition can precede request validation because it belongs to the
serving session. Media failures return `isError: true` with a neutral error class
and safe category, without answers, policy verdicts or payload diagnostics.
An explicitly declared insufficient-evidence Choice remains an ordinary answer
and can produce an unmet policy. Success preserves model and usage metadata.

Source: [MCP media contract](https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851508259).
