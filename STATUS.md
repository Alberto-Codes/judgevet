# STATUS

Last written: 2026-09-22. This file reports current state; historical rounds
remain in Git history and their linked issues.

## Active CLI patch (#124)

Published 0.4.0 remains artifact-verified, but a post-release process test found
#123: malformed question JSON produces an error on stderr and exits 0. The
exact downloaded PyPI wheel reproduces it without a live request. This commit fixes that
exit contract through a thin Typer wrapper. Direct helpers retain integer
returns, the non-standalone callback retains success0, and adapter cleanup
still occurs before exit. #30's opt-in live installed-CLI coverage and the
next release remain pending. Published 0.4.0 still contains the defect.

Twenty-six new offline cases cover local failures with zero observed requests,
controlled HTTP failures, all three answer types, and helper/lifecycle behavior.
Before implementation, 18 process cases failed on exit0 and eight cases passed.
Removing exit propagation causes 18 failures; removing closure causes four.
The final base wheel passes six installed-console cases outside the checkout,
with isolated package import/entrypoint and no MCP runtime. These are synthetic
HTTP fixtures, not new live API trust claims.

The coder's first diff was rejected without application. The next function
matched the initial specification, but the full suite exposed a missing
callback-return compatibility requirement. Revised accepted specification
[5777155848](https://github.com/Alberto-Codes/judgevet/issues/123#issuecomment-5777155848)
preserves the existing test. Gatekeeper tests, integration and documentation
corrections are distinguished from model-generated wrapper code. Native MCP
claim-audit dogfood returned probability0.05 for release completion; this is
advisory evidence, and the release remains incomplete.

Backlog acceptance was reconciled while preserving historical issue bodies.
#34's async client/equivalence work, #22's release history and #19's documented
Noul criteria are fulfilled. A focused async/contract/public-surface/logging
run passed 53 tests; the existing all-question-types live test passed with
true/false criteria. These audits add no new API trust claims.

#3 remains the logging parent: #26 configuration exists, while #27 call-site
wiring and real-stream proof remain. Its named stderr test uses an explicit
StringIO and never captures actual stdout, so its name alone is not evidence
of default stderr behavior. #27 and #43 lost obsolete blocked labels. Current
acceptance for #43/#67/#68 reflects the released README, exports and clean CLI
help. #8 now requires the AGENTS.md hard limit of 300 code lines, not 320;
actual baseline inventory and decomposition must precede a green size gate.

## Published release

**judgevet 0.4.0 is published and verified.** The library, CLI and supported
`judgevet-mcp` command install from PyPI. MCP remains an optional extra.

Release commit: `c9907a2679ac8a0289ecbe791672667d1bc1b862`.
Release-please selected the version and updated all four version fields.
The release tree matches candidate `0200e1f4ef5e4c63b9f92fb819599d6253297293`.

Both actual TestPyPI and PyPI distributions match their Actions artifacts and
each other byte-for-byte:

| artifact | SHA-256 |
|---|---|
| wheel | `cc41725f53066430a725116f6c932338c31f7b1e5bbd6602a5bfc533c2344497` |
| source distribution | `204cf766b82dcf6c0a493b48b490b13dcfd6570b23a5b0579be239a2449b3a54` |

[TestPyPI run](https://github.com/Alberto-Codes/judgevet/actions/runs/35728419079)
and [production run](https://github.com/Alberto-Codes/judgevet/actions/runs/35728680925)
passed isolated base and MCP smoke checks before OIDC upload. Independent checks
of the actual index downloads passed outside the checkout. The published uvx
launcher passed with an empty cache: version 0.4.0, exactly three tools, and
live calls to `ask_noul`, `ask_choice` and `ask_score`.

[Artifact and launcher evidence](https://github.com/Alberto-Codes/judgevet/issues/121#issuecomment-5776734827)
records hashes, commands, limits and an initial probe-environment failure.
Native tools were available and dogfooded during development. Fresh transport
checks do not prove an already-running native agent session reloaded.

## Delivered scope

- [#103](https://github.com/Alberto-Codes/judgevet/issues/103): typed `nouls`,
  `choices` and `scores` accessors. Each read returns a fresh ordered dictionary
  of the same answer objects. Selection edits leave `answers` unchanged;
  subsequent source edits appear on the next read. Missing/wrong-variant keys
  raise `KeyError`. Nested answer values remain shared. Eighteen tests started
  red; actual ty checks and filter/type mutations prove the contract.
- [#16](https://github.com/Alberto-Codes/judgevet/issues/16): public CLI help
  retains usage, descriptions and defaults without developer sections. Complete
  developer docstrings remain. Two behavioral tests started red; removing
  explicit help makes them fail. Installed base-wheel help also passed.
- [#97](https://github.com/Alberto-Codes/judgevet/issues/97): explicit `--judge`
  enrichment in companion pi-forensics tooling. It lives in bazzite-dotfiles,
  not this distribution. The default remains stdlib-only; key presence does
  not enable paid calls. Gates and regex findings remain authoritative.

Shared tooling shipped as
[`5ba51d9`](https://github.com/Alberto-Codes/bazzite-dotfiles/commit/5ba51d9)
on its default `develop` branch. An isolated checkout excluded two unrelated
local commits. Existing local skills, templates, logs and submodule changes
were preserved. Judgevet work went directly to `main`; the only PR was the
release-please release PR.

The optional worker has a 45-second communication deadline, including imports,
request and cleanup. Missing input/key/dependency, malformed answers, API errors
and timeout retain the core report. Unexpected worker exits become fixed
`worker_failure` diagnostics. Eighteen offline tests pass, including actual
process reaping and secret-containing exception containment. Mutations removing
opt-in, failed-gate exit or timeout each fail acceptance tests.

Historical dogfood reconstructed #95's final TOML to recorded Git blob
`e058e8e14a4ba51b44bc72c2fffc986d7c44f23d`; its original checker exited 1 for
14 suppression codes against a budget of 10. Published judgevet 0.3.0 returned
probability 0.65 for its conflicting completion claim, resolved model
`jev-1.13.0`, 685 input/20 output tokens. Regex returned no claim warning,
so the report showed disagreement. This is one observation, not an accuracy
estimate. Historical failures were labelled separately from current green gates.

## Gates and model evidence

**537 tests pass, 5 live tests deselected, 95.63% coverage.**
The #123 local full-suite run confirms these figures. Published 0.4.0
[release CI](https://github.com/Alberto-Codes/judgevet/actions/runs/35728612308)
records its earlier baseline of 511 tests and 95.61% coverage. All eleven configured local gates passed:
suppressions, dependencies, test hygiene, ruff check/format, ty, import-linter,
docvet diff/all, pytest, and pytest with coverage. Commit and push hooks remain
enabled. Shared tooling also passes its unittest, lint and format checks.

Reasoning used Qwen3.8-27B-UD-Q4_K_M with explicit medium thinking; coding used
Qwen3-Coder-Next-UD-IQ4_XS with thinking off. Original prompts, raw returns,
accepted/revised specifications, red/green proofs and gatekeeper repairs are
preserved on each issue. Factual `Specified-By` and `Generated-By` trailers
keep roles separate and name gatekeeper-authored tests and corrections.
Measured limitations and outcomes are persisted in the delegation skill/log.

Existing [broken-library](https://github.com/Alberto-Codes/judgevet/actions/runs/35686353515)
and [broken-MCP](https://github.com/Alberto-Codes/judgevet/actions/runs/35699666984)
proofs show failed smoke checks prevent upload. #101 and #107 are complete.
#109 completed the remaining console-detector proof for #106 and #99; those
already-landed changes were not rebuilt. #111 closed the ty-suppression gap.
The suppression budget remains 18; this release did not weaken gates.

## What is verified, and what is not

| claim | status |
|---|---|
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

The implementation and artifact-verification scope of tracker #121 is
fulfilled. Final evidence-commit CI and milestone closure are recorded on that
tracker. Tracker #124 now owns the CLI patch described above. Unseen API bodies remain
inferred; no documentation is promoted to stable by this release.
