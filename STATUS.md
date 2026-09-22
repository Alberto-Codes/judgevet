# STATUS

Last written: 2026-09-22. This file reports current state; historical rounds
remain in Git history and their linked issues.

## Published release

**judgevet 0.4.1 is published and verified.** The patch fixes handled CLI
failures returning success to shell scripts. The library, CLI and supported
`judgevet-mcp` command install from PyPI. MCP remains optional.

Release commit: `b12fb3c6085a16187ed50d97e2a4000cc50a5a29`.
Release-please selected the version and updated all four version fields.
The release tree matches candidate `ecd62452855b90b82c36a3ef1570c531b30b0b01`.

Actual TestPyPI and PyPI distributions match their Actions artifacts and each
other byte-for-byte:

| artifact | SHA-256 |
|---|---|
| wheel | `f5c59808917975fef7f79f2598ce02c5314e3d453149345d56528e159b3445c5` |
| source distribution | `3aced27ca3fb5caa0edb8aa5946db9b1daa54409f65a0f654f30514bed2deb7f` |

[TestPyPI run](https://github.com/Alberto-Codes/judgevet/actions/runs/35735298922)
and [production run](https://github.com/Alberto-Codes/judgevet/actions/runs/35735744611)
passed isolated base and MCP smoke checks before OIDC upload. Independent checks
of actual index downloads passed outside the checkout: library examples,
CLI help, live mixed CLI judgment, six offline CLI process cases, and all three
MCP tools. Base installs omit MCP and the wheel includes `py.typed`.

The published uvx launcher passed from a temporary working directory with an
empty cache: version 0.4.1, exactly three tools, and live calls to `ask_noul`,
`ask_choice` and `ask_score`. Its first probe returned a sanitized transport
failure; a help probe and fresh empty-cache transport retry passed without a
product/config change. Cause remains unproven. Fresh transport checks do not
prove an already-running native agent session reloaded.

[Artifact and launcher evidence](https://github.com/Alberto-Codes/judgevet/issues/124#issuecomment-5777743633)
records commands, hashes, runs and limits. The installation guide now pins the
verified published version. Native tools were available and dogfooded during
#123 development; judgment output was advisory, never a substitute for gates.

## Current developer-workflow round

The accepted #68 design is tracked by #131, milestone "Next release: reusable
questions and developer policy". #127 adds explicit --questions-file and
--state-file inputs, including opt-in stdin. Legacy positional input and output
remain compatible. Input conflicts precede reads; invalid files stop before HTTP
with sanitized diagnostics. Policy #128, integration #129 and publication #130
remain pending. These source changes are not in published 0.4.1.

The installed-process baseline was 55 failing new cases and two passing legacy
cases. After implementation, 60 process cases pass, including CRLF preservation.
Twenty-seven direct resolver/command cases cover source selection and parsing.
Removing duplicate-key detection causes four failures. Removing early state
validation causes one failure after the diagnostic assertion was strengthened;
its initial mutation survived fallback parsing and was not counted as proof.

The local coder's first whole-file test return was rejected. The bounded test
and resolver artifacts were reused with named gatekeeper repairs to field names,
mapping access, diagnostics, types and documentation. Codex supplied the process
harness, negative/boundary tests, CLI integration and user documentation. Raw
returns, prompts, accepted specification and red/green evidence live on #127.
The shared delegation log records the observed failures without a causal claim.

## Delivered scope

- [#123](https://github.com/Alberto-Codes/judgevet/issues/123): the installed
  CLI exits 1 for handled failures and 0 for success. Direct helpers and the
  non-standalone success callback retain integer return contracts. Existing
  arguments/output and adapter cleanup remain compatible. Twenty-six offline
  cases cover observed requests, all answer types, errors and lifecycle.
  Eighteen process cases started red. Removing exit propagation causes 18
  failures; removing closure causes four. Commit `97fff00`.
- [#30](https://github.com/Alberto-Codes/judgevet/issues/30): one opt-in live
  installed-console request covers Noul, Choice and Score with typed output,
  model/usage/legend and stream checks. Seventeen offline oracle checks cover
  corrupt output, missing key/executable, configured failure and real-child
  cleanup. Model-check and cleanup mutations fail. Default collection excludes
  live tests even with a configured key. Actual downloaded TestPyPI and PyPI
  wheels passed this live path. Commit `dd23d59`.
- Backlog reconciliation preserved historical issue bodies and posted current
  acceptance. #34 async support, #22 release history and #19 Noul criteria are
  fulfilled. #3 remains the logging parent; #27 wiring/real-stream proof remains.
  #43/#67/#68 now distinguish existing features from remaining design work.
  #8's acceptance and title use hard limits of 300/50 code lines. Obsolete
  blocked/pi-fit labels were corrected. Commit `5f2c346`.

The accepted #68 design now governs tracker #131. #125 records release-please's generated
"closes" wording for `Refs` links. Reviewed release notes distinguish references
from actual closures; no generated changelog entries were hand-maintained.

## Gates and model evidence

**641 tests pass, 6 live tests deselected, 95.85% coverage.** All eleven configured
local gates passed: suppressions, dependencies, test hygiene, ruff check/format,
ty, import-linter, docvet diff/all, pytest, and pytest with coverage. Commit and
push hooks remain enabled. The new #127 source commit still needs its own remote CI verification. Prior
main, candidate and
[release CI](https://github.com/Alberto-Codes/judgevet/actions/runs/35735621182)
passed. Final evidence-commit CI is recorded on tracker #124.

Reasoning used Qwen3.8-27B-UD-Q4_K_M with explicit medium thinking; coding used
Qwen3-Coder-Next-UD-IQ4_XS with thinking off. Prompts, original returns, accepted
and revised specifications, red/green proofs and named corrections live on the
issues. Factual `Specified-By` and `Generated-By` trailers keep roles separate
and identify gatekeeper tests, integration and repairs. Rejected returns were
not credited as working implementation.

The #123 full suite caught a callback-return requirement missed by the initial
specification. The #30 positive fixture rejected a validator whose negative
checks otherwise passed. Whole-file coder returns invented source fields;
bounded artifacts still needed semantic corrections. These observations do not
establish general model accuracy or the cause of improvement between prompts.

Seven task-specific delegation records and scoped skill observations shipped
as [3992e38](https://github.com/Alberto-Codes/bazzite-dotfiles/commit/3992e38) on the
shared tooling default `develop` branch. An isolated checkout excluded unrelated
local commits, templates and submodule changes. Local `.serena/`, ignored
`.codex/config.toml` and unrelated shared work remain preserved.

The existing [broken-library](https://github.com/Alberto-Codes/judgevet/actions/runs/35686353515)
and [broken-MCP](https://github.com/Alberto-Codes/judgevet/actions/runs/35699666984)
proofs show failed smoke checks prevent upload. #101/#107 and the remaining
#109 console-detector proof for #106/#99 were already complete and not rebuilt.
#97's optional companion pi-forensics audit shipped with the earlier goal.
No suppression budget or gate was weakened.

## What is verified, and what is not

| claim | status |
|---|---|
| installed CLI sends a mixed live request and renders typed answers with success status and clean stderr | verified — #30 live test on development install and actual TestPyPI/PyPI wheels |
| endpoint, auth header, three answer shapes, usage | verified — probe + official reference |
| noul has no confidence; score is continuous; legend is a map | verified — both sources |
| noul criteria keys `true`/`false` are read by the service — inverted criteria moved the measured answer by ≥ 0.13, while `yes`/`no` (normal and inverted) did not move it | **verified** — live differential test, issue #105 |
| score `legend` echoes the sent criteria list exactly | **verified** — live test asserts legend equals `{0: "Poor", 1: "Fair", 2: "Good", 3: "Excellent"}` |
| 401 returns `{"detail": {"error_type", "message"}}` | **verified** — live call with an invalid key, 2026-09-21 |
| 422 returns `{"detail": [ {type, loc, msg, input} ]}` | **verified** — live call omitting `questions`, 2026-09-21 |
| `detail` is polymorphic: an object for auth, an array for validation | **verified** — the two calls above disagree in shape |
| a 422 body echoes the request payload back under `input` | **verified**, and the adapter discards it (#85) |
| 429 and 529 | still unseen. 429 needs abusing the service and 529 cannot be forced |
| every other field name | inferred from documentation |
| resolved models other than `jev-1.13.0` | untested; both `jev-latest` and explicit `jev-1.13.0` have been called |
| `model` in a response is the **resolved** version, not the alias sent | verified — the live test caught `jev-1.13.0` where `jev-latest` was sent |
| fake and real adapter produce identical outcomes | verified — contract tests on 12 hand-authored fixtures, inferred from docs/reference/api.md |
| 401 and 422 error responses become JevAuthError and JevRequestError with retryable=False | **verified** — live tests, 2026-09-21 |
| the adapter drops the `input` field from 422 bodies to avoid echoing caller data | **verified** — live test asserts test state does not leak |
| API keys do not leak in error str/repr | **verified** — live tests assert key not in str or repr |
| secret guard redacts API key from test output | **verified** — `test_secret_guard.py` proves guard scrubs key from pytest report with `--showlocals` |

#17 and #29 have landed, so the error rows above are observations now, not
inferences. `README.md` and `docs/reference/api.md` are `draft` for the verified
success and 401/422 shapes. Unseen 429/529 bodies still prevent `stable`.

The 3xx fallthrough in `system_one` is pinned as of #96, parametrized over
301, 302, 304 and 308. It asserts the raw `httpx.HTTPStatusError` propagates
with `__cause__` and `__context__` both `None`, and that the client has
redirects off — without that last line the test would silently stop meaning
what its name says if the client were ever reconfigured.

A note for whoever breaks it next: returning a `JevRequestError` instead of
`None` does fail the test, but not through the type assertion.
`JevRequestError` validates its own status range, so a 3xx cannot be
constructed at all. The domain invariants from #77 are load-bearing here in a
way nobody planned.

## Remaining work

Finish #128 explicit policy, #129 developer integration and #130 publication in
that order under #131. Verify the next actual index artifacts before describing
this developer workflow as released. #67/#66 broader research remains separate.


Tracker #124's implementation and artifact-verification scope is fulfilled.
Final evidence-commit CI and milestone closure are recorded on that tracker.
Unseen API bodies remain inferred; no documentation becomes stable here.
