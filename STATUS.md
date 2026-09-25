# STATUS

Last written: 2026-09-23. Current evidence ledger. Detailed implementation,
release and credential history remains in Git and the linked issues.

## Published release

judgevet 0.10.2 is published. Library, CLI and optional MCP share one version.
This release makes the domain accept two-decimal probability rounding on the
wire and rejects nonfinite answer values with normalised response errors.
Dependency and action pins moved through Dependabot; runtime requirements are
unchanged. The documentation site is [live](https://alberto-codes.github.io/judgevet/).

| Artifact | Evidence |
|---|---|
| Release/tag | `v0.10.2`, commit `8ecfc6065818b6048d97dcd8d0b19337f072a8ac` |
| Accepted candidate | none; the maintainer merged and published without a TestPyPI round |
| Wheel SHA-256 | `4a6a94341cee10fa35fa0bd2f5b9edf510d462a731b6a23e5c7691fb5f49b0a5` |
| Source distribution SHA-256 | `ddebbe4a4d2d4323d5cb958be6d4c4c54ff6886f551c9024054b799741030589` |
| Actual PyPI download | Index wheel is byte-identical to the workflow artifact; JSON digests agree |
| Library | Isolated base import, typing marker, live examples and all four policy examples passed on the index wheel; policy examples also type-checked |
| CLI | Installed live CLI test passed on the index wheel; one test, no skip |
| MCP | Isolated MCP smoke passed on the index wheel; registry launcher discovery and all three tools passed |
| Published launcher | not rechecked through a fresh uvx cache for 0.10.2 |
| Registry | Manifest validated and submitted; independent query lists `io.github.Alberto-Codes/judgevet` 0.10.2 active and latest, published `2026-09-25T00:26:59.691261Z`, package and launcher fields match |

[Release tracker](https://github.com/Alberto-Codes/judgevet/issues/183) records the
non-live and live evidence separately.
[PyPI publication](https://github.com/Alberto-Codes/judgevet/actions/runs/36077169568)
passed its wheel and MCP smoke checks before upload, on `actions/upload-artifact@v7`,
`actions/download-artifact@v8` and `astral-sh/setup-uv@v10.2.0`.
No source-archive rebuild outside the checkout was done for this release.
No unseen API body, other model, modern protocol path or gateway became verified.

Prior [0.10.1 evidence](https://github.com/Alberto-Codes/judgevet/issues/165)
retains its TestPyPI candidate round, source-archive rebuild and registry
submission checks; the paragraphs below are its record.

[Candidate acceptance](https://github.com/Alberto-Codes/judgevet/issues/165#issuecomment-5807947133)
and [production evidence](https://github.com/Alberto-Codes/judgevet/issues/165#issuecomment-5808070601)
record commands, hashes, submission and acceptance separately.
[Release CI](https://github.com/Alberto-Codes/judgevet/actions/runs/35957836048),
[TestPyPI publication](https://github.com/Alberto-Codes/judgevet/actions/runs/35957559456)
and [PyPI publication](https://github.com/Alberto-Codes/judgevet/actions/runs/35958128842)
passed. Both publication workflows passed base/MCP smoke checks before upload.

The downloaded source archive also built outside the checkout with no cache.
Its rebuilt wheel passed the same isolated checks, including the live CLI test.
All package files match the index wheel except the generator marker and its
RECORD checksum. The archive build used uv_build 0.11.33; the workflow wheel
records uv 0.12.18. The rebuilt wheel is not byte-identical to the index wheel.
The actual index files are byte-identical across both publication workflows.

The [active registry listing](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.Alberto-Codes%2Fjudgevet)
reports `io.github.Alberto-Codes/judgevet` version `0.10.2`, published at
`2026-09-25T00:26:59.691261Z`; 0.10.1 stays listed as an earlier active version. Package and launcher fields match the release
manifest. Registry acceptance does not verify a host installation or reload.
No unseen API body, other model, modern protocol path or gateway became verified.

Prior [0.10.0 evidence](https://github.com/Alberto-Codes/judgevet/issues/160)
retains its initial unexplained launcher failure and successful fresh recheck.
Prior [0.9.0 evidence](https://github.com/Alberto-Codes/judgevet/issues/157)
retains its gateway/redaction and exact-documentation checks.
The [0.8.0 evidence](https://github.com/Alberto-Codes/judgevet/issues/155)
retains its container exercise; it did not exercise this release.

## Onboarding release

[#165](https://github.com/Alberto-Codes/judgevet/issues/165) includes the host
survey, setup recipes, host checks, contributor setup, contribution policy
and issue templates. The
[#162 survey](https://github.com/Alberto-Codes/judgevet/issues/162#issuecomment-5806538121)
records current primary sources, host schemas, credential mechanisms,
installation alternatives and source disagreements. It is research, not
host integration evidence. Pi uses the existing CLI route, explicitly outside
MCP. The complete landed scope has now been reviewed for 0.10.1.
Runtime sources and dependencies are unchanged; this is an onboarding and
repository-tooling patch. Published artifact evidence appears above.

The [user-approved revision](https://github.com/Alberto-Codes/judgevet/issues/162#issuecomment-5806551798)
accepts cited documentation and mechanical checks for unavailable hosts.
Those routes must remain labeled not host-tested. Available hosts still need
actual host checks. Desktop uses documented manual setup for this release.
The Desktop bundle is deferred to [#166](https://github.com/Alberto-Codes/judgevet/issues/166).
Checks on another machine, including Windows or a suitable Linux environment,
are tracked in [#167](https://github.com/Alberto-Codes/judgevet/issues/167).
Neither follow-up is a release requirement. New host observations below
exercise existing service paths only.

[#163](https://github.com/Alberto-Codes/judgevet/issues/163) adds distinct host
recipes and Pi CLI access. Persistent pip/uv-tool installs and uvx execution
are alternatives. Direnv and source checkouts are optional. The documentation
schema gate checks 14 exact JSON/TOML blocks, including all five host templates
and three tool argument objects. Thirty-two new regression cases preserve
all prior tests. Isolated candidate installs execute the exact five host
launchers, both persistent installation commands and three Pi CLI commands
against synthetic HTTP answers. Credential substitutions are test fixtures,
not native host observations. Independent missing-extra mutations in the
Desktop and pip recipes make positive acceptance checks fail. Actual host
checks are recorded in the [#164 evidence](https://github.com/Alberto-Codes/judgevet/issues/164#issuecomment-5807036514).

### Native host observations

On 2026-09-23, actual hosts used the documented recipes and PyPI 0.10.0 on
Bazzite 44 x64. Initial uvx caches were fresh. Credential values stayed outside
configuration and transcripts. These observations are separate from candidate
transport tests and do not validate a future release artifact.

| Host | Measured result | Remaining limit |
|---|---|---|
| Codex CLI 0.156.1 | Three MCP calls returned structured answers, model and usage | Other Codex surfaces and platforms untested |
| Pi 0.86.1 | Bash executed all three exact base-CLI commands and returned live JSON | No MCP extension or skill route tested |
| Claude Code 2.1.280 | Native add produced the documented configuration; connected and discovered three tools | Account spend limit blocked calls |
| VS Code 1.134.0 | LocalProcess extension host started the server and discovered three tools | Copilot sign-in blocked Chat calls; Agent Host untested |
| Cursor IDE | Cited recipe, semantic checks and isolated launcher only | IDE unavailable; no native host evidence |
| Claude Desktop | Cited manual recipe, semantic checks and isolated launcher only | Desktop unavailable; no native host evidence |

Codex returned Noul 0.96, Choice `yes` and Score 2.79. Pi returned Noul 0.96,
Choice `yes` and Score 2.74. Each resolved `jev-1.13.0`; token usage was
275/22, 309/32 and 305/18 respectively. These are observed values, not fixed
acceptance targets or accuracy evidence. Pi ran without extensions or skills.

Claude's native add first rejected the previous option order. Moving the
server name before its variadic `--env` option passed and preserved literal
variable interpolation. Codex needed persisted project trust; a command-line
trust override did not load the project recipe. Its headless approval policy
then rejected calls until the three authorized tools received explicit approval.
Neither failure was a judgevet transport success.

Controlled missing-executable checks removed Codex discovery, failed Claude's
connection and produced VS Code's native missing-command error. Pi without a
credential returned the configuration error and command exit 1. Fresh sessions
or server restarts recovered the tested stages. Account-blocked calls remain
unverified and are carried by #167. Claude's account-limit response does not
verify a TypeSafe 429 body. No other model, gateway or modern protocol path
became verified.

### Published 0.10.1 host follow-up

Pi 0.86.1 ran all three exact released CLI commands through its Bash tool
with a fresh uvx cache. Extensions and skills were disabled. Actual successful
tool results returned Noul 0.96, Choice `yes` and Score 2.71. The resolved
model was `jev-1.13.0`; usage remained 275/22, 309/32 and 305/18 respectively.

Codex CLI 0.156.1 first reported no available tools and made no calls.
The cause is unproven. The next native configuration lookup confirmed the
enabled 0.10.1 launcher, but execution failed at the account usage limit.
No native 0.10.1 Codex tool call is claimed. Earlier 0.10.0 calls remain
historical evidence. Test-owned trust entries were removed; unrelated settings
were preserved. Account-enabled checks join the existing deferred rows in
[#167](https://github.com/Alberto-Codes/judgevet/issues/167#issuecomment-5808070810).
This account response does not verify a TypeSafe 429 body.

### Contributor setup

[#21](https://github.com/Alberto-Codes/judgevet/issues/21#issuecomment-5807239311)
adds the canonical [cold-clone route](docs/maintainers/contributor-setup.md).
The exact commands passed in a fresh public clone with new uv, pre-commit and
npm caches. No API credential resolved. All three executable hooks installed
before subsequent project commands; actionlint provisioned its Go environment.
Locked synchronization, CLI help and both full gate stages passed. An invalid
CLI option exited 2; restoring the documented help command exited 0.

The credential-free clone measured 1600 passed, 6 live deselected and 95.33%
coverage (1836/1926 statements). The lockfile remained unchanged. The walkthrough
used Bazzite 44 x64, Python 3.13.13, uv 0.11.20, Node 26.3.0 and npm 12.0.2.
Downloads and advisory checks need network access, but ordinary setup needs
no live service account. Windows and ChromeOS Linux remain unverified under
#167. No runtime behavior, dependencies or service evidence changed.

### Contribution policy

[#44](https://github.com/Alberto-Codes/judgevet/issues/44#issuecomment-5807371002)
adds [CONTRIBUTING.md](https://github.com/Alberto-Codes/judgevet/blob/main/CONTRIBUTING.md).
It explains issue-led work, authorized direct commits and the automated release
pull-request exception. It links the canonical contributor setup and detailed
rules instead of duplicating the setup sequence. README and the maintainer
index expose the policy. All three hook stages and factual issue footers remain
required.

Explicit link, prose and terminology checks passed for the new root guide.
A modified copy with broken setup links produced two missing-target findings;
the original passed again. Full push gates measured 1600 passed, 6 live
deselected and 95.33% coverage. No runtime or service-verification claim changed.

### Issue intake

[#36](https://github.com/Alberto-Codes/judgevet/issues/36#issuecomment-5807514716)
adds required Do / Do not / Prove task fields and a separate setup-problem form.
Setup reports capture host/version, environment, installation method, sanitized
configuration, reproduction, expected and observed behavior, and an acceptance
check. The chooser disables blank issues and links private security reporting.
GitHub API creation and later edits can still bypass the form's intake rules.

Fourteen new parsed-YAML acceptance cases pass. Independent mutations make
configuration optional, enable blank issues or prefill the proof; each causes
one failure. The original forms pass again. Full local push gates measure
1614 passed, 6 live deselected and 95.33% coverage (1836/1926 statements).
Parsed checks do not emulate GitHub's entire form engine or establish the
truth of a report. Published template bytes and exact-commit CI passed.
The browser required sign-in, so native form rendering and required-field
interaction remain deferred in #167. No service claim changed.

### Release preparation

[#168](https://github.com/Alberto-Codes/judgevet/issues/168#issuecomment-5807678611)
fixes the observed candidate mismatch between package 0.10.1 and host recipe
pins at 0.10.0. The original candidate failed thirteen tests. Release-please
now updates thirteen marked recipe blocks through its configured generic
updater. No version was edited manually and no pin assertion was weakened.

Four real-engine cases cover patch, minor, major and prerelease targets. They
require every package pin to change and all other document bytes to survive.
Removing the updater or one marker makes all four fail while registry cases
still pass. All eighteen Node checks pass. Full local push gates measure
1614 passed, 6 live deselected and 95.33% coverage. Subsequent candidate and
index artifact checks passed after the fixture correction below.

The regenerated candidate exposed a second fixture defect: pip read the direct
wheel requirement but still sought the unpublished base package on PyPI.
The fixture now exposes the wheel directory without changing documented argv.
A new no-index test verifies the installed wheel URL and SHA-256. Removing that
exposure or corrupting installed provenance makes the test fail. Both persistent
install routes and the provenance test pass against the unpublished candidate.
Full local gates now measure 1615 passed, 6 live deselected and 95.33% coverage.
The [pip evidence](https://github.com/Alberto-Codes/judgevet/issues/168#issuecomment-5807807946)
keeps artifact selection distinct from dependency installation and native hosts.
[Exact candidate CI](https://github.com/Alberto-Codes/judgevet/actions/runs/35957261086)
passed all 1615 tests with 95.33% coverage before TestPyPI publication.

## Documentation program

[#145](https://github.com/Alberto-Codes/judgevet/issues/145) is complete.
All 15 child deliverables landed with enabled gates and issue-hosted evidence.
The final fresh-environment walkthrough installed published 0.7.0, ran the exact
first-judgment tutorial live, and completed the offline policy tutorial and
live policy workflow. The judgment returned billing probability 0.98, resolved
model `jev-1.13.0` and 280 input tokens. The policy workflow compared Noul 0.94
with its documented zero floor. These calls confirm those paths only; no unseen
error body, calibration claim or other model became verified.

The final reader route reaches tutorials, policy tasks, error lookup and
explanations without issue history. All authored docs remain draft. README
package links and current example checks pass. Site publication was the
separate final follow-up [#41](https://github.com/Alberto-Codes/judgevet/issues/41).
That program did not change Pages settings or repository visibility.
The deployment-readiness follow-up below records completed Pages publication.
#146 landed in `b32afa2`: explicit key injection, adapter cleanup, matching
Choice labels, standalone examples and fresh-artifact selection. Both exact API
blocks execute offline against an isolated wheel and pass typing checks.
The packaging procedure verifies both wheel and installed typing markers.

#147 separates [maintainer procedures](docs/maintainers/index.md) from user
installation, compatibility and security guidance. The installation guide gives
safe checks for startup/discovery failures without claiming a known cure.
Prose relocation does not promote service evidence.

#46 adds the canonical [glossary](docs/reference/glossary.md). Repository
vocabulary guidance links to it. Definitions distinguish model numbers from
local decisions, preserve literal API names and retain observed/inferred limits.
Terminology enforcement remains #71; no checker or service evidence changed.

#10 completes the [navigation map](docs/index.md) and rendered navigation.
All 34 authored docs pages, README and SECURITY are reachable from the map.
Tutorials, how-to, reference and explanation remain distinct; maintainer
procedures have a separate audience. Draft metadata and visible labels agree.
Recovery and policy-handling paths link directly to error lookup. The final
navigation inventory and reading routes are recorded on #10; #12 checks their
source destinations and rendered links. No trust status was promoted.

#149 supplies explanations of question types, local policy decisions and evidence
limits. The shared support-ticket scenario uses labeled synthetic values. Its
policy example executes offline; numeric illustrations were checked. No model
accuracy, calibration or new live-service claim is made.

#11 explains the library-first architecture, entry-point choices, typed ports,
explicit ownership and optional MCP runtime. Source and lifecycle tests support
the package claims; they do not promote service behavior. #73 adds accessible SVG
call-path and disclosure diagrams with text equivalents. They distinguish the
structural contract, remote transfer and optional local policy evaluation.

#148 adds first-judgment and offline first-policy tutorials with explicit setup,
checkpoints, output interpretation and recovery guidance. Exact Python examples
are checked in isolation. Reciprocal tutorial links finish #149's reading path.
No additional service field or model is promoted by tutorial verification.

#150 supplies focused sync/async, service-error, MCP and troubleshooting recipes.
CLI guides include complete input files and status-aware automation. Staged-diff
setup names its checkout files and shell requirements. MCP instructions retain
legacy installation anchors and link verified official host configuration docs.
Example checks use synthetic answers and do not promote live-service evidence.

#151 begins with configuration and error reference: explicit library settings,
environment precedence, entry-point model overrides, error constructors and
retry metadata. Generated error docstrings now match those local contracts.
The completed API, CLI, MCP and policy references enumerate the shipped surfaces.
They retain the MCP state-schema discrepancy, mutable nested answer data and
strict-versus-legacy policy distinctions. Pricing and calibration claims are
removed from the API/root documentation; no runtime behavior changes.

#153 supplies a complete README/user-doc inventory (49 current blocks) and seven
acceptance tests. Each block has an explicit classification and reason. Commit,
push and CI gates reject inventory drift. An isolated-wheel gate now executes
and type-checks all 15 Python programs
with synthetic HTTP, secret-free environments and client cleanup checks. Seven
executor acceptance cases bring the inventory/executor total to fourteen.
Five CLI shell blocks now run against a loopback fixture using exact documented
question/policy JSON; four acceptance cases cover pipe input, invalid options
and policy exits. A separate optional-runtime gate validates all eight JSON/TOML blocks
against input decoders, MCP discovery and template/report contracts, with six
acceptance cases. The shared wheel builder now rejects nonempty output before building, with four
selection acceptance cases and a stale-artifact failure proof. Three continuation
acceptance cases cover exact saved tutorial commands and clean/met/unmet staged
review. A wrong-filename mutation fails the isolated command and restoration
passes. Separate disposable setup verification accounts for eight current installation
blocks; four credential/host shell templates remain explicitly
unexecuted. Offline examples do not verify live service behavior.

#70 adds a local plain-English profile: a 25-word sentence limit and five
banned marketing adjectives. Structural parsing covers README, SECURITY,
authored docs including maintainer pages, and package docstrings. Seventeen
acceptance cases cover prose, literal syntax, sentence boundaries and source
locations. Commit, push and CI run the complete declared scope. The
[writing guide](docs/maintainers/writing-guide.md) records exclusions and human
review criteria. This is not a claim of ASD-STE100 compliance.

#71 enforces the glossary table through explicit lexical contexts and safe
annotated local-name checks. Public/wire names and ambiguous technical contexts
remain intact. Twenty-one acceptance cases cover prohibited prose, literal
contracts, glossary-driven wording and typed locals. The writing guide records
semantic-review limits and optional model-assisted review. Commit, push and CI
run the complete declared terminology scope.

#152 makes the README a library-first entry path: install, ask one billing
question, interpret its probability and choose a next task. CLI and MCP routes
link to complete guides. Security and evidence limits stay visible; release
records remain in maintainer material. Absolute repository links work in package
descriptions and now receive offline destination/anchor checks. Three acceptance
cases prove valid targets and reject missing files or fragments. Duplicate README
examples were removed; the task guides retain their executable coverage.

## Registry manifest preparation

#47 adds `server.json` with explicit optional MCP installation, the existing
`judgevet-mcp` launcher and a secret TypeSafe key input. The official 2025-12-11
schema and production validation endpoint accept the manifest. Removing the
required name is rejected. This is validation, not a submitted or accepted listing.
The published 0.9.0 description lacks the ownership marker. Release 0.10.0
publishes it; the submission and confirmed listing are recorded above.

Fifteen regression cases cover schema/package/configuration agreement, version
drift, private key inputs and isolated candidate launches. The manifest-derived
command matches the executed VS Code converter. Its trailing package identity
argument is ignored by the existing launcher; other consumer conventions remain
unverified. The isolated candidate passes discovery and all three live tools.
Changing the launcher to the CLI, omitting the extra, or removing the entrypoint
from the candidate wheel makes the transport check fail. Base wheel imports and
policy examples still pass without MCP.

Three Node tests execute the configured release-please 17.3.0 updater for minor,
major and prerelease versions. All registry versions and the uvx pin update;
removing one updater makes all three tests fail. Commit, push and CI now check
schema/version agreement and actual updater behavior. The
[registry procedure](docs/maintainers/mcp-registry.md) separates candidate mapping,
index verification, submission and confirmed listing. Evidence remains on
[#47](https://github.com/Alberto-Codes/judgevet/issues/47). No new service body,
model, gateway deployment or modern protocol path is promoted.

## Generated issue references

#125 changes the release-please commit template label from `closes` to
`references`. Four real-renderer cases cover Closes-only, Refs-only and both
historical mixed-footer regressions. Generated notes otherwise match the
unmodified renderer byte for byte; links, subjects and parsed footer actions
remain intact. Seven runner/workflow cases cover engine delegation, fresh
manifests, consumed outputs, absent credentials, failure propagation and
sanitized workflow errors. Together with the three version-updater cases,
14 Node tests pass. Restoring the original label makes all four renderer
cases fail. GitHub closure still comes from factual commit trailers.

## MCP adapter decomposition

#80 moves discovery schemas and tool handlers out of the server factory.
The public factory signature, tool schemas, defaults, output and errors remain
unchanged. The original 17 direct tests remain intact. Seven characterization
cases cover complete serialized outputs and missing/wrong-answer failures.
Combined factory, schema and handler coverage is 109/109 statements (100%),
against the fresh 88/94 (93.62%) baseline. A deliberate text-output mutation
fails the characterization test. The suppression budget falls from 18 to 15;
architecture contracts remain unchanged. Changed functions have at most 36 code
lines and implementation modules at most 174 code lines.

The isolated local wheel passes base imports and CLI help without MCP, including
imports of the optional factory and entrypoint. Its optional installation passes
discovery and all three live tools. These calls exercise existing direct-service
paths only. No unseen body, other model, gateway or modern protocol path gains
verified status. Required push gates pass; commit gates and main CI are recorded
with the final round evidence on [#80](https://github.com/Alberto-Codes/judgevet/issues/80).

## Finite answer validation

[#170](https://github.com/Alberto-Codes/judgevet/issues/170) corrects numeric
answer validation and response errors. Direct constructors reject boolean or
nonnumeric values with `TypeError` and nonfinite values with `ValueError`.
Valid integers and floats retain existing ranges and distribution tolerance.
The shared parser translates answer validation failures to `JevResponseError`.
Both HTTP adapters reject malformed synthetic answers without retrying.
Public imports, optional MCP dependencies and architecture contracts remain.

The 322 new acceptance cases preserve all 1615 existing tests. Four policy
test modules retain their assertions and construct corrupted fixtures after
valid construction. Removing finite validation causes 24 acceptance failures.
Bypassing parser translation causes 121. Restored source passes all 322 cases.
The issue records the contract, pre-implementation failures and mutation proofs.
The [compatibility assessment](docs/reference/compatibility.md#finite-answer-validation-correction)
records stricter invalid-input handling relative to published 0.10.1.
This is a local correction. No release or live-service evidence is promoted.

## Gates

**1953 tests pass, 6 live tests deselected.** The last measured coverage is
**95.81%** (1850/1931 statements).
Local commit and push gates pass for #170. The issue holds delivery evidence.
The documentation rounds retain the existing local gates: suppressions,
dependencies, test hygiene, Ruff lint/format, ty, import contracts, file size
(300 code lines), docvet (diff/all), pytest and pytest with coverage.
Hooks remain enabled. The file-size gate `scripts/check_loc.py` is new at
commit and in CI; all 43 modules under `src` measure at or under 300 code
lines. Slice A of #8 adds nine boundary tests for the module cap and a
report-only function counter: the gate prints every function over 50 code
lines and still exits 0. No function under `src` is over 50; enforcement is
slice B. Slice A2 makes the module cap a single hard limit: 300 passes, 301
fails, and the 320 tier is gone.
`[tool.ty.src] include` pins ty to `src`, `tests` and `scripts` (#49). A
probe file with one type error in each root yields 3 diagnostics.
Ordinary tests exclude live service calls. The coverage floor is 90%.
#13 adds `.github/dependabot.yml` (uv and github-actions, weekly) and a
CodeQL workflow on push, pull request and a weekly cron. Both pass yamllint
and actionlint locally. No CodeQL run has been observed yet; the first run
on the pushed commit is post-landing evidence for the issue.

#12 adds the strict MkDocs build to commit/push hooks and CI. It checks authored
local links, generated Python references and final HTML links/anchors offline.
Nine acceptance tests cover link parsing and strict source-reference resolution.
Independent symbol, target and anchor mutations fail the build; restoration
passes. A fresh development-only installation builds without MCP or API keys.
Two further acceptance cases cover project-path assets and anchors while
preserving missing-target findings. Removing the prefix mapping fails the test.
Strict building does not prove publication. Example execution and editorial
checks remain separate; Pages deployment is tracked below.

#35 adds the native uv lockfile audit to pre-push and a required CI job.
CI pins verified uv 0.11.20 and enables its experimental audit command.
The public audit reports no known vulnerabilities or adverse project statuses
across 86 locked packages, including MCP and development dependencies.
This result is time-bound public advisory evidence, not a security guarantee.

Four execution cases verify the actual configured commands and failure status.
Four independent configuration mutations fail; restoration passes. Real uv
rejects a synthetic OSV advisory, an audit-service error and a stale copied
lockfile. All three preserve lockfile bytes. Full commit and push gates pass.
[Contract, red tests and proofs](https://github.com/Alberto-Codes/judgevet/issues/35)
remain on the issue. No runtime dependency or service claim changed.

#48 adds commit and push checks for lockfile consistency, YAML and workflows.
The lockfile hook precedes tools that can synchronize dependencies. CI retains
its existing lock check and invokes the same YAML and workflow hooks.
Strict default yamllint covers every tracked YAML file. Upstream actionlint
v1.7.12 has a separate Go hook pin. The duplicate YAML key is removed;
formatting changes preserve parsed workflow commands and structure.

Thirteen acceptance cases exercise clean and failing fixtures at both stages
and verify required CI wiring. Independent repository mutations fail for stale
metadata, duplicate keys and invalid expressions; restoration passes. Three
mutations that bypass gates also fail the acceptance tests. Full commit and
push gates pass. The current public audit covers 87 packages after adding the
locked development tool and reports no known vulnerabilities or adverse statuses.
[Contract, red tests and proofs](https://github.com/Alberto-Codes/judgevet/issues/48)
remain on the issue. Runtime dependencies and live-service claims are unchanged.
Release publication and installed-artifact verification are recorded on #157.

## Deployment-readiness work

#154 records the public-source gateway contract on the
[research issue](https://github.com/Alberto-Codes/judgevet/issues/154#issuecomment-5804773817).
It compares HTTP and W3C standards with Apigee, Kong and Azure documentation.
The contract selects explicit authentication and metadata configuration,
bounded header validation, opt-in correlation and loopback acceptance tests.
The implementation below completes #63. No gateway deployment or new service
behavior was verified.

#63 adds root-exported `GatewayConfig` and `RequestMetadata`. Sync and async
adapters accept explicit authentication, immutable metadata defaults and per-call
overrides. CLI, policy CLI and MCP consume the same gateway settings. Direct
TypeSafe defaults remain unchanged. Scoped request IDs leave the process only
when a correlation header is configured; arbitrary logging context stays local.

The 169 gateway acceptance cases observe actual prefixed loopback requests,
protected fields, case-insensitive precedence, size bounds, retry snapshots,
concurrent calls, gateway-owned errors and disabled redirects. Independent
mutations break each selected property and all three composition paths; the
restored source passes. The exact gateway documentation program executes and
type-checks against an isolated wheel. Full commit and push gates pass, including
all-file docvet, isolated examples, strict docs and coverage. This is synthetic
client evidence, not gateway certification or new live-service verification.
[Specification, failures and proofs](https://github.com/Alberto-Codes/judgevet/issues/63)
remain on the issue. The supporting release gates #35 and #48 are complete under #157.

#53 adds the root-exported `StateRedactor` protocol and an optional callback on
both HTTP adapters. The shared preparation helper copies JSON state, invokes
the callback once and serializes the returned state before retry handling.
Configured retries reuse immutable bytes. Callback, copy and serialization
failures cause no request or original-state fallback. The default retains the
existing JSON path without copying. Questions and gateway metadata stay separate.

Fifty redaction cases and the existing adapter contracts cover nested ownership,
gateway composition, sync/async parity, invalid output, cancellation, concurrent
calls and mutation of retained output between attempts. Nine independent
mutations fail; restoration passes. The exact redaction example executes and
type-checks against an isolated wheel. SECURITY.md holds the complete egress
contract and limits. All local commit/push gates pass. No detection library,
remote retention guarantee or new live-service evidence was added.
[Contract, red tests and failure proofs](https://github.com/Alberto-Codes/judgevet/issues/53)
remain on the issue.

#33 adds opt-in bounded retries through the root-exported `RetryPolicy`.
The default remains one attempt. Sync and async adapters share classification,
exponential delay and jitter limits; transport replay requires separate opt-in.
CLI, policy CLI and MCP consume the environment settings. Synthetic tests cover
exhaustion, final causes, cancellation, final diagnostic status and actual
request counts through all three composition roots. Independent mutations
break recovery, attempt bounds, cancellation and each settings path.

#55 adds root-exported `NetworkConfig` and proxy/CA/verification settings.
Actual loopback TLS tests prove default rejection, explicit private-CA trust,
hostname checks and test-only verification-off. Loopback proxy tests observe
CONNECT selection and explicit precedence; they do not prove a deployed
corporate proxy. CLI, policy CLI and MCP consume every new setting. Independent
mutations break CA, proxy, secure defaults and each composition path.
The policy composition root extracts adapter construction into a helper; its
42 code lines remain below the 50-line function limit.

#61 adds lazy file and trusted command credential sources to settings.
Explicit arguments remain literal and override configured sources. Configured
literal keys precede files, and files precede commands. CLI, policy CLI and MCP
resolve once before constructing their adapters. Loopback tests observe the
resolved authorization headers and reject source failures before any request.
Command tests cover bounded output, deadlines, discarded stderr, closed stdin,
wrapped traceback locals and POSIX process-group cleanup. Independent mutations
break these limits, precedence and each composition path. Command execution is
not a sandbox; descendants that escape the process group remain outside cleanup.

#64 adds root-exported scoped `bind_request_id` correlation and the
[diagnostic event contract](docs/reference/events.md). HTTP events include
successful typed usage and filtered requested/resolved model identifiers.
Built-in events exclude arbitrary bound context; application events retain it.
Nested, concurrent and cancelled scopes restore their previous bindings.
Real CLI/MCP stream tests retain valid stdout and exact stderr fields.
Independent mutations break scope restoration, task isolation, field filtering
and response metadata. A request probe confirms correlation stays out of headers
and payloads. The artifact checker includes the new supported export identity.
The pi attempts and their defects remain recorded separately from Codex's
specification and implementation. No model-written specification was accepted.

#58 adds [container and serverless deployment guidance](docs/how-to/deploy.md).
The exact documented Dockerfile builds a base image without MCP. A non-root,
read-only rootless Podman run sends real synthetic HTTP requests with file and
command credentials. JSON stdout and diagnostic stderr remain separate.
The guide covers secret mounts, SELinux labels, connection ownership, rotation,
proxy/CA settings and deadline/retry budgets. Cloud Run, Lambda and Fargate
integration guidance cites platform documentation; no cloud account was deployed.
The initial source-built development wheel was not index evidence. The same
container checks now pass with the actual published 0.8.0 PyPI wheel.

The complete commit/push gates include strict docs, isolated examples and
coverage. Runtime evidence is local and synthetic; unseen service
errors stay inferred. Runtime dependencies remain unchanged. Release-please set the shared version
to 0.9.0; both index publications and the Pages site are verified.

## Pages deployment

#41 adds the strict-build Actions workflow and the project-path site URL.
Pages is configured with `build_type=workflow`; repository visibility remains
public. An isolated checkout with a nonexistent Python cross-reference fails
the strict build; restoration passes.
[Deployment run 35871720007](https://github.com/Alberto-Codes/judgevet/actions/runs/35871720007)
published commit `5a5997f245e88786c95eb034b923ed1ffb499eac`. Browser checks verify
project-path CSS/scripts, navigation, both architecture diagrams, generated
Python API anchors, and the deployment and event guides. No failing resource
requests or browser console errors were observed on those pages.
README and package metadata link the [live site](https://alberto-codes.github.io/judgevet/).
Published README links retain offline source and fragment validation.

## Operational limits

- Intermittent MCP initialization failures, including `invalid_data`, have no
  established cause or remedy. A successful fresh launcher does not prove an
  existing host session loaded its tools. See [connection checks](docs/how-to/install.md#when-mcp-does-not-connect).
- Diagnostic redaction is bounded. Protocol errors, CLI error envelopes and
  arbitrary tracebacks can disclose service-supplied content. See [SECURITY](SECURITY.md).
- Release automation uses release-environment credentials without a
  `GITHUB_TOKEN` fallback. [Credential-scope evidence](https://github.com/Alberto-Codes/judgevet/issues/102)
  preserves the migration record. That record does not establish compromise.
- Failed base/MCP smoke checks prevent publication. Independent failure proofs
  are recorded in the [base run](https://github.com/Alberto-Codes/judgevet/actions/runs/35686353515)
  and [MCP run](https://github.com/Alberto-Codes/judgevet/actions/runs/35699666984).

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
| probabilities on the wire are rounded to two decimals | observed once — a consumer call on 2026-09-24 against `jev-1.13.0` returned a four-level Score summing to 0.99 (#175); the tolerance is 0.005 per probability since that fix; not reproduced by this repository's live suite |
| `model` in a response is the **resolved** version, not the alias sent | verified — the live test caught `jev-1.13.0` where `jev-latest` was sent |
| fake and real adapter produce identical outcomes | verified — contract tests on 12 hand-authored fixtures, inferred from docs/reference/api.md |
| 401 and 422 error responses become JevAuthError and JevRequestError with retryable=False | **verified** — live tests, 2026-09-21 |
| the adapter drops the `input` field from 422 bodies to avoid echoing caller data | **verified** — live test asserts test state does not leak |
| API keys do not leak in error str/repr | **verified** — live tests assert key not in str or repr |
| secret guard redacts API key from test output | **verified** — `test_secret_guard.py` proves guard scrubs key from pytest report with `--showlocals` |


README and API documentation remain draft. Unseen 429/529 bodies prevent stable
status. Synthetic contract and policy tests do not establish model accuracy or
confidence calibration. The observed fields above do not verify every field.

Redirect handling is synthetic evidence: tests cover 301, 302, 304 and 308,
with redirects disabled and raw `httpx.HTTPStatusError` propagation. It is not
new live-service evidence. [Supported imports and compatibility](docs/reference/compatibility.md)
describes the public-versus-legacy policy validation distinction.
