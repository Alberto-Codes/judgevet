# STATUS

Last written: 2026-09-22. This file reports current state; historical rounds
remain in Git history and their linked issues.

## Published release

**judgevet 0.5.0 is published and verified.** Developers can keep reusable
questions and an explicit acceptance policy in version control, read state from
files or stdin, and distinguish an unmet policy from input/service failures.
The library, CLI and optional supported MCP command remain independently usable.

Release commit: `3f77287a0c487e9e828ee0781ab6d60059002908`.
Release-please selected the version and updated all four version fields. The
release tree equals candidate `06f29ef9b96a15fb620a2aeaef0e628007bbd634`.

Actual TestPyPI/PyPI downloads match their Actions artifacts and each other:

| artifact | SHA-256 |
|---|---|
| wheel | `7f5b659b9eeec20dae5b7a4c6398bbda78127a7218f3bd743291d9b937be01df` |
| source distribution | `1fbfafc8d4c721857cef5b576f79a13ddf27541036bcf6d669806c0076aecea9` |

[TestPyPI run](https://github.com/Alberto-Codes/judgevet/actions/runs/35794248340)
and [production run](https://github.com/Alberto-Codes/judgevet/actions/runs/35794710780)
passed isolated base/MCP smoke checks before upload. Independent actual-wheel
checks passed outside checkout: library examples, CLI help, mixed live installed
CLI, MCP discovery/all three tools and eight offline staged-workflow cases.
Base installs omit MCP; the wheel includes `py.typed`.

The published uvx launcher passed from a temporary cwd and empty cache with
version 0.5.0, exactly three tools and all three live calls. Its first probe
returned a sanitized transport error; a help probe and fresh empty-cache retry
passed without a product/config change. Cause remains unknown (#133). This does
not prove that an already-running agent session reloaded its native tools.
The actual PyPI wheel also ran the staged-diff workflow live, returning valid
unmet-policy status 3. The verdict is not a judgment-quality guarantee.

[Artifact and launcher evidence](https://github.com/Alberto-Codes/judgevet/issues/130#issuecomment-5785649938)
records commands, hashes, runs and limits. Native tools were available and all
three were dogfooded as advisory aids during development.

Replacing the generated release PR body prevented release-please from parsing
it. Restoring that body and rerunning the same release-commit workflow created
the correct draft/tag. Unintended unmerged PR #132 was closed. The release guide
now preserves that machine-parsed structure; no index files were replaced.

## Delivered developer workflow

The accepted #68 design is tracked by #131, milestone "Next release: reusable
questions and developer policy". #127 supplies explicit file/stdin input. #128
adds opt-in --policy validation, typed inclusive predicates and ordered reports.
Valid judgments exit 0 for a met policy and 3 for an unmet policy. Input/service
errors exit 1; usage conflicts exit 2. Legacy low probabilities still exit 0.
Integration #129 supplies an opt-in staged-diff example with versioned questions
and policy. These changes are published in 0.5.0; #130 records artifact verification.

The #128 installed-command baseline was 57 failing new cases. The final round
adds 146 tests: 50 parser, 28 evaluator, 57 installed-process and 11 lifecycle
cases. Independent mutations cause failures when conjunction (4 cases), inclusive
bounds (7), confidence (2) or adapter cleanup (6) is removed. All mutations were
restored. No live-service verification claim changed.

The coder's toolless parser was rejected. Its tool-enabled parser needed four
runtime-case and four type-diagnostic repairs. The evaluator needed exact return
annotations and documentation repairs, with no runtime logic changed. Codex
supplied integration, process/adversarial tests and user documentation. Initial
integration broke two legacy help assertions; the existing help contract is
restored. Raw returns, prompts, acceptance and repair evidence live on #128.

The delegation skill and existing prompt template now require executable coverage
of every known relevant requirement, exact interfaces and bounded context. The
log distinguishes coder self-repair, supervisor repairs and retries. Local-model
usage is recorded; historical per-artifact supervisor usage is unavailable because
start checkpoints were not captured. Lower supervisor cost remains a hypothesis.

The #129 example captures only staged changes, rejects producer failures before
calling the installed CLI, and forwards stdin with exact argument checks. Eight
isolated Git/HTTP cases cover pass, unmet policy, auth error, no staged changes,
producer failure, partial producer output, invalid policy and usage. Removing
producer rejection causes one failure; cleanup removal causes seven; masking CLI
status causes three. A live isolated staged-README call returned valid policy
failure (exit 3), jev-1.13.0, an approve answer and empty stderr. That observation
proves wiring, not judgment quality or deterministic policy acceptance.

The first example dispatch needed a corrected supervisor fixture and a stronger
stdin oracle. The bounded retry fixed stdin; Codex corrected remaining docs.
The full-matrix handoff has not demonstrated lower total repair cost. Shared
skill, template and delegation records are committed in bazzite-dotfiles
3802e7e; unrelated local changes there were excluded through an isolated worktree.

The #127 input proofs remain: 60 installed-process and 27 direct cases, with
mutations detecting duplicate-key and early state-validation removal.

## Delivered scope

- #133: the launcher probe reports fixed stage/reason labels for spawn,
  initialization, discovery, each tool call, shutdown and cleanup. A cleanup
  failure cannot replace the first session failure. Fourteen deterministic
  cases cover stage distinctions and cleanup; removing the diagnostic labels
  causes all fourteen to fail. Existing transport and cancellation checks pass.
  Two new published 0.5.0 probes used separate empty caches and temporary working
  directories. Both passed identity/version, exact discovery, all three live
  tool calls and cleanup (1.95s and 1.92s). The historical failure did not recur;
  its cause remains unknown. This diagnostic work does not establish a cure.

- #136: malformed diagnostic fields use the existing HTTP status-only fallback
  in both sync and async adapters. Valid object and validation-list messages
  retain their formatting; input fields and malformed containers are excluded.
  Seventy-eight offline cases cover typed errors, fallback and valid shapes.
  Sixty started red; restoring the old parser causes the same sixty failures.
  These synthetic cases add no live-service verification.

- #135: both CLI paths handle synthetic rate limits with status 1, empty stdout
  and text/JSON stderr diagnostics. Eight offline process/lifecycle cases cover
  both paths and output modes, secrecy and exact adapter closure. All eight
  started red; removing either handler addition causes four failures. Live 429
  remains unseen. The current coverage measurement is from the local hook run;
  the earlier release measurement remains historical evidence.

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

**895 tests pass, 6 live tests deselected, 95.38% coverage** (1176/1233 statements). All eleven configured
local gates passed: suppressions, dependencies, test hygiene, ruff check/format,
ty, import-linter, docvet diff/all, pytest, and pytest with coverage. Commit and
push hooks remain enabled. [#127 CI](https://github.com/Alberto-Codes/judgevet/actions/runs/35788246669)
passed. [#128 CI](https://github.com/Alberto-Codes/judgevet/actions/runs/35792578365)
passed. [#129 CI](https://github.com/Alberto-Codes/judgevet/actions/runs/35794073659),
[candidate CI](https://github.com/Alberto-Codes/judgevet/actions/runs/35794111885)
and [release CI](https://github.com/Alberto-Codes/judgevet/actions/runs/35794411245)
passed. Final evidence-commit CI is tracked on #131.

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

The developer-workflow release requirements are fulfilled. Final evidence-commit
CI and milestone closure are tracked on #131. #133 now supplies stage diagnostics and a bounded reproduction; the historical
first fresh-launcher failure remains unexplained. #67/#66 remain broader research outside
this release. No inferred API claim was promoted and no quality gate was weakened.
