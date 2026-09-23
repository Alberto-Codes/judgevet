# STATUS

Last written: 2026-09-23. This file reports current state; historical rounds
remain in Git history and their linked issues.

## Published release

**judgevet 0.6.0 is published and verified.** This release adds safe diagnostics,
CLI rate-limit handling, malformed HTTP error-detail validation and stage-aware
MCP smoke diagnostics. Release credentials are scoped to the main-only release
environment. The library, CLI and optional MCP command remain independently usable.

Release commit and tag: `1ca1459148ba9366f5fccb9aee71c99193a40803` (`v0.6.0`).
The release tree equals candidate `5e8dbe90fa72319ab525d75d5641877b2c537300`.
Release-please updated all four version fields; its generated PR body was preserved.

Actual TestPyPI/PyPI downloads match their Actions artifacts and each other:

| artifact | SHA-256 |
|---|---|
| wheel | `4f6ceef2b47694feec24e1d5d987f1ebc6d9c1f94b7ec5add4f0eda73f52e547` |
| source distribution | `0ddd2f7736b33f63e3f1598a4ab06da1a8f2a01eb6c1aca028ba049615e03b2d` |

[TestPyPI run](https://github.com/Alberto-Codes/judgevet/actions/runs/35801297889)
and [production run](https://github.com/Alberto-Codes/judgevet/actions/runs/35801671681)
passed isolated base/MCP checks before upload. Independent actual-wheel checks
passed for both indexes: library examples, CLI help, mixed live installed CLI
(one passed test each), MCP discovery and all three live tools. Base installs
omit MCP and include `py.typed`. [Release CI](https://github.com/Alberto-Codes/judgevet/actions/runs/35801525799)
passed with 929 tests, six live deselections and 95.44% coverage.

The published uvx launcher passed from a temporary cwd and empty cache in 2.18s:
version 0.6.0, exactly three tools and all three live calls, including clean shutdown.
The first local TestPyPI MCP runner invocation failed generically. A diagnostic
exercise and subsequent standard TestPyPI/PyPI checks passed; cause remains unknown.
No cache/timeout explanation or intermittent-failure cure is claimed. This does
not prove that an already-running agent session reloaded its native tools.

[Artifact and launcher evidence](https://github.com/Alberto-Codes/judgevet/pull/134#issuecomment-5786785252)
records commands, hashes, runs and limits. The pure policy API and
additive root exports are now implemented for 0.7.0 below. No unseen API body
became verified.
The release review also corrected current scope on twelve existing backlog issues.

## 0.7.0 work in progress

Release tracker #138 covers implementation and publication. #139 adds the fifteen
recommended root exports: ports, question/answer unions, typed answers, response,
usage and the existing Jev error hierarchy. All six existing exports and deep
import identities remain. Explicit sync/async adapter ownership is unchanged.

The export acceptance started with 16 failures and six passes. The final focused
suite passes 61 cases, including typed callers through both ports. Removing a
port export causes two failures; substituting its identity causes one. Both
mutations were restored. Static typing and architecture checks pass. Built and
published artifact verification remains required under #143.

#140 adds judgevet.policy: frozen typed rules, ordered policies, validated
question snapshots, immutable reports, pure validation/evaluation and distinct
local definition/answer errors. Direct ValidatedPolicy construction validates;
changing question constraints requires revalidation. Required answer scalars are
checked even without a confidence predicate. Existing answer constructors and
CLI semantics are unchanged; #141 will retain the legacy distinction explicitly.

The 95 new acceptance cases and 146 unchanged legacy policy cases pass together.
Independent isolated-cache mutations detect range validation (2), inclusive
bounds (2), conjunction (1), report truncation (2), mutable rule retention (1),
question validation (13) and finite-answer checks (6). All were restored. An
initial proof reused stale bytecode after source restoration; fresh per-mutation
cache directories removed that interference, and the full suite then passed.
Four import contracts pass, including the new pure policy facade contract.

#141 (JSON/CLI integration), #142 (documentation) and #143 (publication) remain open. The current published version is still 0.6.0.

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

- #43: README now leads with public installation, typed library/CLI/MCP use
  and explicit non-affiliation. An isolated PyPI 0.6.0 install passed the
  exact library and CLI examples, file-policy pass/unmet cases, and MCP
  discovery/all tools plus the documented tool arguments. Base installation
  includes py.typed and omits MCP. Local links resolve and external links
  return HTTP 200 (private reporting requires GitHub sign-in). The existing
  929-test/95.44% gate baseline and live verification limits are unchanged;
  final documentation-commit CI evidence is recorded on #14, #62 and #43.

- #62: SECURITY.md now separates settings-only HTTPS validation, HTTPX TLS
  verification and environment trust/proxy behavior from caller/platform
  responsibilities. It documents storage and Python memory limits without
  claiming zeroization, FIPS compliance or a fixed connection count.

- #14: SECURITY.md documents 0.6.0 credential sources, service disclosure and
  diagnostic boundaries. GitHub private vulnerability reporting was enabled
  with owner approval and its API returned `enabled: true`. MCP protocol
  errors and arbitrary tracebacks are not covered by diagnostic redaction.
  No runtime behavior or live API verification claim changed.

- #67/#66: sourced research recommends a supported pure typed policy API with
  separate JSON decoding, additive exports for ports/errors/answer types, and
  explicit adapter ownership. One distribution/version remains; scopes and
  release-note migration entries identify the affected public surfaces.
  [API decision](https://github.com/Alberto-Codes/judgevet/issues/67#issuecomment-5786388416)
  and [compatibility decision](https://github.com/Alberto-Codes/judgevet/issues/66#issuecomment-5786398764)
  record costs, change conditions, source evidence and corrected historical
  premises. An isolated published 0.5.0 base install confirms six root exports,
  py.typed and no MCP runtime; four public-surface tests pass. No proposed API,
  MCP policy feature or release configuration was implemented in this round.

- #27/#3: the CLI (both paths) and MCP roots configure existing stderr logging
  exactly once. Sync/async HTTP calls emit one opt-in debug terminal event with
  requested model, question count, status and outcome. Default output stays quiet;
  library imports do not configure logging and unconfigured calls stay silent.
  SDK warning/error diagnostics contain only a fixed event and severity, not raw
  exception text. Twenty-six new process/root cases prove streams, metadata,
  framing, canary exclusion and configuration ownership. Independent removal of
  events causes twenty failures, root configuration nine, and safe SDK routing
  one. All mutations were restored. MCP protocol error content is unchanged;
  this is a diagnostic non-disclosure contract, not a new protocol error schema.

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
  fulfilled. #3 and #27 are now fulfilled by logging wiring and real-stream proof.
  #43/#67/#68 now distinguish existing features from remaining design work.
  #8's acceptance and title use hard limits of 300/50 code lines. Obsolete
  blocked/pi-fit labels were corrected. Commit `5f2c346`.

The accepted #68 design now governs tracker #131. #125 records release-please's generated
"closes" wording for `Refs` links. Reviewed release notes distinguish references
from actual closures; no generated changelog entries were hand-maintained.

## Gates and model evidence

**1044 tests pass, 6 live tests deselected, 95.72% coverage** (1432/1496 statements). All eleven configured
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

#102 is fulfilled. The original PAT was migrated as destination-encrypted
ciphertext without plaintext retrieval or rotation. Repository metadata is
empty; release-environment metadata contains RELEASE_PLEASE_TOKEN, updated
2026-09-23T00:01:29Z. The environment permits main only. Both credential jobs
bind to it and have no GITHUB_TOKEN fallback. Fresh push run
[35800344761](https://github.com/Alberto-Codes/judgevet/actions/runs/35800344761),
created after repository-secret removal, passed both jobs and printed actual
HAS_PAT=true and PAT_IDENTITY=Alberto-Codes output. It updated the release branch
and PR #134, authored by Alberto-Codes. The one-time sealing workflow, encrypted
artifact and migration run were retired. Eight acceptance cases and independent
removal proofs cover scope, missing credentials, identity and fallback.
[Full credential evidence](https://github.com/Alberto-Codes/judgevet/issues/102)
records the sequence. That migration round did not publish a release; 0.6.0 is now
published with separate user authorization.

The developer-workflow release requirements are fulfilled. Final evidence-commit
CI and milestone closure are tracked on #131. #133 now supplies stage diagnostics and a bounded reproduction; the historical
first fresh-launcher failure remains unexplained. #67/#66 are being implemented
under #138; root exports and pure policy have landed, while JSON/CLI integration, docs and
release verification remain. The post-0.5.0 reliability and credential-scoping rounds are
fulfilled and published in 0.6.0 with user authorization. No inferred API claim was promoted and no quality gate was weakened.
