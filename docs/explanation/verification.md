---
status: draft
---

# What the evidence can establish

Status: **draft**. Service evidence is partial. This page explains its scope;
the [evidence ledger](../../STATUS.md#what-is-verified-and-what-is-not) records
individual claims and their supporting observations.

A support-ticket workflow has several independent failure points. The local
policy may compare a threshold incorrectly. The HTTP adapter may parse an
answer incorrectly. The service may reject a request. Even when all those
steps work, the model may classify the ticket incorrectly. One kind of test
cannot establish all four properties.

## Synthetic checks establish local behavior

A synthetic answer is one the test author constructs. Giving the policy an
answer of `0.85` proves whether the code compares that value with a threshold
as specified. It does not show what the service would return for a ticket.
It is useful precisely because the input is controlled and the test needs
neither a credential nor a network.

An adapter contract test sends the same fixtures through a fake port and the
HTTP adapter. Agreement establishes compatibility for those fixtures. When the
HTTP transport is synthetic, it does not establish that the fixtures match
an unseen service case. See the [contract fixtures](../../tests/contract/fixtures.py).
A wheel installation check establishes another property: whether the packaged
code and entry points work outside the checkout.

## Live observations establish only exercised cases

Live checks have exercised successful answer shapes, authentication and
validation errors, and the resolved `jev-1.13.0` model. The observed
Noul has no separate confidence, and a Score legend maps levels to descriptions.
These observations support those fields and cases, not every possible request.
The vendor describes the contract in its [API reference](https://docs.typesafe.ai/api)
and [primitive definitions](judgments.md).

The 429 and 529 error bodies remain unseen. Other resolved models and fields
not exercised by a call remain unverified here. A documented status code does
not turn its proposed body into an observed one. Do not provoke service abuse
to fill an evidence table.

Error shapes can also differ by case. The observed authentication `detail`
is an object; validation `detail` is an array. A single universal shape would
misrepresent that evidence. The adapter discards validation `input` fields,
but this is not universal sanitization of all service-supplied text. Consult
[diagnostic disclosure limits](../../SECURITY.md#diagnostics-and-error-content)
before sharing errors.

If two sources disagree, record both and the unresolved question. Do not
silently choose whichever shape is easier to implement. A live observation
settles the exercised case; it does not automatically settle every model or
error path. The current observations above are recorded separately from
expectations derived from vendor documentation.

## Working transport does not establish model quality

A successful request proves that one request completed and its answer could
be parsed. It does not establish whether billing was the right team. A policy
pass proves that local comparisons passed; it does not make the model correct.
Use [labeled task evaluations](policies.md#choose-thresholds-with-task-evidence)
to assess decisions on your own content. Synthetic passing tests do not
establish statistical calibration of probability or confidence.

Recording the requested model, resolved model, question definitions and
policy helps compare runs. It does not guarantee identical future answers.
Keep enough context to investigate differences, subject to your data-handling
requirements. judgevet does not supply a persistent audit store or a guarantee
of deterministic service behavior.

## Startup and operational evidence has its own scope

Intermittent MCP initialization failures remain unexplained. Successful later
runs do not establish a cache or timeout remedy. A successful standalone
launcher also does not prove that an already-running host loaded its tools.
Use the [connection checks](../how-to/install.md#when-mcp-does-not-connect)
in the host session you intend to use.

For exact facts, such as whether a required file exists, prefer a deterministic
check. For consequential decisions with unresolved context, involve a person
or obtain better evidence. These are application choices; judgevet does not
provide an automatic escalation mechanism.

The [glossary's trust statuses](../reference/glossary.md#sketch-draft-and-stable)
keep these limits visible. Documentation remains draft while documented error
bodies are unseen. Passing the documentation build proves links and references
resolve, not that the prose teaches well or that a judgment is reliable.

Practice with the [offline policy tutorial](../tutorials/first-policy.md).
