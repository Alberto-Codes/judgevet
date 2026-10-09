---
status: draft
---

# Verification ledger

Status: **draft**. This page records which claims about the Jev service a
call has exercised and which remain inferred. It replaces the retired root
`STATUS.md`; the [frozen snapshot](../history/status-2026-10-09.md) keeps its
history.

A row moves from inferred to verified only with a cited call. The citation
names the run, the date and the issue comment that records it. A test name
alone is not a citation. Nothing reaches `stable` while a documented status
code is unseen. Edit this page only when a call changes a claim.

Test counts, coverage and gate state come from the gate run, not from this
page. The gate table in [repository rules](../../CLAUDE.md#build-and-gates)
names those gates.

## What is verified, and what is not

| claim | status |
|---|---|
| installed CLI sends a mixed live request and renders typed answers with success status and clean stderr | verified — #30 live test on development install and actual TestPyPI/PyPI wheels |
| endpoint, auth header, three answer shapes, usage | verified — probe + official reference |
| noul has no confidence; score is continuous; legend is a map | verified — both sources |
| noul criteria keys `true`/`false` are read by the service — inverted criteria moved the measured answer by ≥ 0.13, while `yes`/`no` (normal and inverted) did not move it | **verified** — live differential test, issue #105 |
| score `legend` echoes the sent criteria list exactly | **verified** — live test asserts legend equals `{0: "Poor", 1: "Fair", 2: "Good", 3: "Excellent"}` |
| choice criteria string values | **verified** — every live call has sent string values only. `tests/live/test_cli_live.py::test_installed_cli_mixed_live` (`{"yes": "Clear", "no": "Unclear"}`) passed on the 0.10.2 index wheel. The release smoke's live run of the package-docstring Choice example (`{"a": "Option A", "b": "Option B"}`) returned a `ChoiceAnswer`. Both are recorded on #183, 2026-09-25. `tests/live/test_system_one_live.py::test_system_one_live_with_all_question_types` sends `{"cat": "Feline", ...}` and its legend assertion is the row above. Object, array and null forms are inferred from the vendor docs; no call has sent them (#174) |
| 401 returns `{"detail": {"error_type", "message"}}` | **verified** — live call with an invalid key, 2026-09-21 |
| 422 returns `{"detail": [ {type, loc, msg, input} ]}` | **verified** — live call omitting `questions`, 2026-09-21 |
| `detail` is polymorphic: an object for auth, an array for validation | **verified** — the two calls above disagree in shape |
| an oversized request returns 400 with `{"detail": {"error_type": "max_tokens_exceeded"}}` | **verified, observed once** — live call on 2026-09-25 with a 400,000-character state against `jev-1.13.0`. Recorded at https://github.com/Alberto-Codes/judgevet/issues/39#issuecomment-5825759575. The body does not say which budget fired. The request exceeded both the 32k and the 64k budget. A second 400,000-character call on 2026-09-30 through `tests/live/test_max_tokens_live.py` returned the same status. Recorded at https://github.com/Alberto-Codes/judgevet/issues/192#issuecomment-5924025204. A 180,000-character state of repeated English words was answered in the same run. Probe 2 on 2026-09-30 measured 10,798 input tokens for 60,000 characters of that text. It then sent 222,263 characters, about 40,000 tokens, with one `noul` question. The service refused it with status 400 and the same body. Recorded at https://github.com/Alberto-Codes/judgevet/issues/192#issuecomment-5924550998. **Verified, observed once:** the 32k state-plus-question budget fires on its own, below the 64k request budget. The boundary lies above about 32,394 tokens (the answered 180,000-character state by the measured rate) and below 40,000 tokens |
| a 2,959-byte JSON state with seven `choice` questions of up to 16 options fits the context budgets | **verified** — live call on 2026-09-25 against `jev-1.13.0` returned 200 with `input_tokens=3110`, recorded at https://github.com/Alberto-Codes/judgevet/issues/39#issuecomment-5825777868 |
| 400 with `detail.error_type` = `max_tokens_exceeded` becomes JevMaxTokensExceededError, retryable=False | **verified, observed once** — `tests/live/test_max_tokens_live.py` sent a 400,000-character state through the real adapter on 2026-09-30. It caught `JevMaxTokensExceededError` with `retryable is False` and `status_code == 400`, recorded at https://github.com/Alberto-Codes/judgevet/issues/192#issuecomment-5924025204. The body is the one the 2026-09-25 call returned, recorded at https://github.com/Alberto-Codes/judgevet/issues/39#issuecomment-5825759575 |
| an opt-in `SpendCap` refuses an attempt before sending once a limit is reached, and a failed attempt settles zero input tokens | **inferred** — offline tests against `httpx.MockTransport` only (#56 slice A); no live call has run the cap. Whether the service bills a failed attempt is an open question on #56 |
| an opt-in `AuditSink` receives one `JudgmentRecord` per logical call, never per attempt, with no state, and a sink failure never changes the result | **inferred** — offline tests against `httpx.MockTransport` only (#54 slice 1); no live call has written a record |
| a 422 body echoes the request payload back under `input` | **verified**, and the adapter discards it (#85) |
| 429 and 529 | still unseen. 429 needs abusing the service and 529 cannot be forced |
| every other field name | inferred from documentation |
| resolved models other than `jev-1.13.0` | untested; both `jev-latest` and explicit `jev-1.13.0` have been called |
| probabilities on the wire are rounded to two decimals | observed once — a consumer call on 2026-09-24 against `jev-1.13.0` returned a four-level Score summing to 0.99 (#175); the tolerance is 0.005 per probability since that fix. This repository's live suite asked a four-level Score once on 2026-09-24 (#184). The resolved `jev-1.13.0` returned probabilities summing to exactly 1.0, which neither confirms nor refutes the rounding |
| Choice `confidence` sits below `probabilities[choice]` | **observed five times for soft distributions; equal at 1.0 three times**. The 0.12.0 production smoke on 2026-09-25 returned `ChoiceAnswer(choice='a', confidence=0.9, probabilities={'b': 0.05, 'a': 0.95})` with both values in one run record. Recorded at https://github.com/Alberto-Codes/judgevet/issues/194#issuecomment-5826847175. The 0.11.0 production smoke on 2026-09-25 returned `confidence=0.89` for `choice='a'`. Recorded at https://github.com/Alberto-Codes/judgevet/issues/186#issuecomment-5825514560. That comment elides the probabilities. `probabilities={'b': 0.05, 'a': 0.95}` is recorded only in the body of https://github.com/Alberto-Codes/judgevet/issues/187. The 0.10.2 production smoke on 2026-09-25 returned `confidence=0.9` for `choice='a'`, with the probabilities elided. Recorded at https://github.com/Alberto-Codes/judgevet/issues/183#issuecomment-5824552631. The differential probe `tests/live/test_choice_confidence_live.py` ran once on 2026-09-30 with 2, 3 and 4 options on a duplicate-charge state. Each call returned `confidence=1.0` with `probabilities[choice]=1.0` and every other option at `0.0`, recorded at https://github.com/Alberto-Codes/judgevet/issues/193#issuecomment-5923966685. Every candidate spread measure equals 1.0 there, so that run distinguishes none. Probe 2 on 2026-09-30 used an ambiguous state. It returned `confidence` 0.99, 0.94 and 0.92 for 2, 3 and 4 options, against chosen-option probabilities 1.0, 0.97 and 0.94. Recorded at https://github.com/Alberto-Codes/judgevet/issues/193#issuecomment-5924550851. The vendor's demo approximation, generalised to `(n × largest − 1) / (n − 1)`, matches four of the five soft runs within 0.01 and misses the 3-option run by 0.015. The top-two margin also matches four within 0.01 and misses the 4-option run by 0.03. The vendor publishes no formula; the formula is unverified |
| `model` in a response is the **resolved** version, not the alias sent | verified — the live test caught `jev-1.13.0` where `jev-latest` was sent |
| fake and real adapter produce identical outcomes | verified — contract tests on 16 hand-authored fixtures. The fixtures are inferred from docs/reference/api.md with two exceptions. The oversized-request fixture replays the body recorded at https://github.com/Alberto-Codes/judgevet/issues/39#issuecomment-5825759575. `ollama_documented_response` copies Ollama's documented body from https://ollama.com/blog/ollama-now-supports-jev-style-decision-models and stays inferred from the docs. It is consistent with the one observed Ollama call but replays the docs' rounded numbers, not that call's (#268). The shipped `judgevet.testing` fakes match the adapter's whole response, error type and status, spend counters and audit record on every fixture (#171, #189) |
| the hosted adapter parses Ollama's `/v1/systemone` response for choice, noul and score | **observed once** — the judgevet CLI 0.15.0 at 62c6490 against local Ollama 0.35.0 with `nimble:latest` (9.0B, Q8_0) on 2026-09-30, `JEV_API__BASE_URL=http://localhost:11434`, `JEV_API__TIMEOUT_SECONDS=120`. Probabilities arrived at full float precision and `model` echoed the tag. The score equalled the probability-weighted level average. Recorded at https://github.com/Alberto-Codes/judgevet/issues/268#issuecomment-5917968541. A first attempt at the default 30 s timeout failed while the model loaded. On 2026-10-05 Ollama 0.35.1 returned the documented `{"error": "<string>"}` body with a 400 for a 27-option Choice. The 0.18.0 adapter carried the string into `JevRequestError`. Recorded at https://github.com/Alberto-Codes/judgevet/issues/296#issuecomment-5997566707. Other Ollama error statuses, `tev1` and judgment quality are unverified |
| the hosted adapters pass the provider conformance kit against local Ollama `nimble` | **observed twice** — `tests/live/test_ollama_kit_live.py` on 2026-09-30 against Ollama 0.35.0, `nimble:latest` digest `24e550a16a7081881be2f1f0d91e8cc13a597472735c04119f035a0a85c67e0c` (qwen35, 9.0B, Q8_0), adapter `timeout_seconds=120.0`: `10 passed, 2 skipped in 9.14s`. The port-shape, typed-answers, failure, scope and media-refusal rules passed for the sync adapter and the three async rules passed. The two media-port rules skipped because the hosted adapters supply no media port. The failure rule used a closed loopback port, so it says nothing about how Ollama fails. Recorded at https://github.com/Alberto-Codes/judgevet/issues/267#issuecomment-5922154877. The async base then grew to nine rules. A second run on 2026-10-01 at main 128c867 returned `14 passed, 4 skipped in 10.74s` against the same server, model and digest. The seven sync rules and the same seven async rules passed. These include the four async scope and media-refusal rules that had never run live. The two media-port rules skipped in each class. Recorded at https://github.com/Alberto-Codes/judgevet/issues/267#issuecomment-5932674842 |
| an off-list Choice option or probability key raises JevResponseError | **inferred** — offline only (#195); the check runs where the response is bound to the questions; no live call has returned one |
| `state_fingerprint` is HMAC-SHA-256 over the raw pre-redaction state under a caller-held key, and `None` without one | **inferred** — offline tests against `httpx.MockTransport` and a fixed test vector (#191); no live call has written a fingerprint |
| 401 and 422 error responses become JevAuthError and JevRequestError with retryable=False | **verified** — live tests, 2026-09-21 |
| the adapter drops the `input` field from 422 bodies to avoid echoing caller data | **verified** — live test asserts test state does not leak |
| API keys do not leak in error str/repr | **verified** — live tests assert key not in str or repr |
| secret guard redacts API key from test output | **verified** — `test_secret_guard.py` proves guard scrubs key from pytest report with `--showlocals` |


README and API documentation remain draft. Unseen 429/529 bodies prevent stable
status. Synthetic contract and policy tests do not establish model accuracy or
confidence calibration. The observed fields above do not verify every field.

Redirect handling is synthetic evidence: tests cover 301, 302, 304 and 308,
with redirects disabled and raw `httpx.HTTPStatusError` propagation. It is not
new live-service evidence. [Supported imports and compatibility](compatibility.md)
describes the public-versus-legacy policy validation distinction.

## Operational limits

- Intermittent MCP initialization failures, including `invalid_data`, have no
  established cause or remedy. A successful fresh launcher does not prove an
  existing host session loaded its tools. See [connection checks](../how-to/install.md#when-mcp-does-not-connect).
- Diagnostic redaction is bounded. Protocol errors, MCP tool error results,
  CLI error envelopes and arbitrary tracebacks can disclose service-supplied
  content. See [SECURITY](../../SECURITY.md).
- Release automation uses release-environment credentials without a
  `GITHUB_TOKEN` fallback. [Credential-scope evidence](https://github.com/Alberto-Codes/judgevet/issues/102)
  preserves the migration record. That record does not establish compromise.
- Failed base/MCP smoke checks prevent publication. Independent failure proofs
  are recorded in the [base run](https://github.com/Alberto-Codes/judgevet/actions/runs/35686353515)
  and [MCP run](https://github.com/Alberto-Codes/judgevet/actions/runs/35699666984).
