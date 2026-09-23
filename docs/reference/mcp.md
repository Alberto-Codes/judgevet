---
status: draft
---

# MCP reference

Status: **draft**. `judgevet-mcp` requires the optional `mcp` extra. It serves
MCP over stdio: stdout is protocol traffic and stderr is diagnostics. For
installation, host configuration and discovery, use [Connect MCP](../how-to/connect-mcp.md).

## Tool arguments

Discovery exposes exactly these three tools. All require `state` and
`instruction` (singular). `instruction` is a string. The published schema
allows a string or object for `state`.

| Tool | Additional argument | Default when omitted |
|---|---|---|
| `ask_noul` | None | No criteria argument is exposed. |
| `ask_choice` | `criteria`: object mapping labels to descriptions | `{"yes":"Yes","no":"No"}` |
| `ask_score` | `criteria`: array of ordered rubric descriptions | `["Poor","Fair","Good","Excellent"]` |

The [tool definitions](../../src/judgevet/adapters/inbound/mcp.py) are the source
for these local schemas. Their prose currently mentions arrays for state, but
the actual `state` schema excludes arrays. Use string/object state for host
calls; do not infer array support from that description. The schemas do not
specify item/value schemas for criteria or `additionalProperties: false`.
Handlers are not a substitute for full schema validation.

Each tool constructs one named question and calls the sync port with
`model="jev-latest"`. Tool arguments cannot select a model or acceptance policy.
The internal question names are `noul_question`, `choice_question` and
`score_question`. Host argument `instruction` becomes wire `instructions`.
See [configuration overrides](configuration.md#entry-point-overrides).

## Successful answers

A successful call returns a text content item and structured content. Python
SDK attributes use `structured_content` and `is_error`; wire JSON fields use
`structuredContent` and `isError`. This distinction is recorded in the
[adapter's SDK citations](../../src/judgevet/adapters/inbound/mcp.py).

| Tool | Structured fields |
|---|---|
| `ask_noul` | `noul`, `model`, `usage` |
| `ask_choice` | `choice`, `confidence`, `probabilities`, `model`, `usage` |
| `ask_score` | `score`, `confidence`, `probabilities`, `legend`, `model`, `usage` |

`usage` contains `input_tokens` and `output_tokens`. Structured content contains
the single answer's fields directly, not the CLI's `answers` envelope. JSON
object keys for Score levels are strings on the wire. Field semantics and vendor
citations are in the [Python API reference](api.md#answer-and-container-types).
Text content formats the answer for reading; use structured values for programmatic
access. A successful call is a judgment, not evidence of its correctness.

## Failure and lifecycle behavior

Missing state/instruction, unknown tools and missing expected answers raise
`ValueError` in the handlers. A wrong answer variant raises `TypeError`. Service
errors propagate to the MCP runtime, which presents protocol failures. A tool
failure is not a negative Noul answer or an unmet policy. Do not assume protocol
error text has been scrubbed; see [diagnostic limits](../../SECURITY.md#diagnostics-and-error-content).

The entry point constructs and closes the adapter around serving. It returns 2
for missing runtime, invalid settings or missing key, and 130 for keyboard
interruption. EOF ends the stdio session. The tested SDK baseline and legacy
initialization path are recorded in the adapter source; an unexercised protocol
path is not promoted by those tests. Intermittent host initialization failures
have no established remedy; use [connection checks](../how-to/troubleshoot.md#when-mcp-does-not-connect).

For embedding, `create_mcp_server(port)` accepts a `SystemOnePort`. The factory
does not construct or close the caller's port. This entry point stays in the
optional inbound adapter; importing the base library does not require MCP.
