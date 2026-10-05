# STATUS

Last written: 2026-10-05. Current evidence ledger. Detailed implementation,
release and credential history remains in Git and the linked issues.

## Published release

judgevet 0.18.0 is published to PyPI. Library, CLI and optional MCP share one
version. This release adds `judgevet.domain.provider_profiles` with
`ProviderProfile`, `OLLAMA_PROFILE` and `check_profile`, and an opt-in
`profile` keyword on both hosted adapters and the fake. It moves response
translation out of the httpx helpers without a behaviour change. Two provider
how-tos record Ollama v0.35.1 images and the unpublished OpenAI Decisions API.
Runtime requirements, the CLI surface and the MCP tool set are unchanged.

| Artifact | Evidence |
|---|---|
| Release/tag | `v0.18.0`, commit `ded6252ba6041454f184a535a20b72be0790e365` |
| Accepted candidate | none; the maintainer asked for the release, and it was merged and published without a TestPyPI round, as for 0.10.2 through 0.17.0 |
| Wheel SHA-256 | `baf90466d8f6b2b5dd74efa6f2ecd9b86461d2940d3d2ac68bf0d16b91b6d067` |
| Source distribution SHA-256 | `86ea394d536634b98194aa1e5e1f854fc185d6cae35605c161ef1d6c9e89c443` |
| Actual PyPI download | PyPI JSON digests equal the SHA-256 of the wheel and sdist attached to the GitHub release |
| Release files | 15 assets; `provenance.txt` names the tag commit and `complete: yes` |
| Attestations | `gh attestation verify` exits 0 for the wheel and the sdist |
| Library and CLI | The publish workflow's wheel smoke step passed before upload. A fresh Python 3.12 venv installed `judgevet[mcp]==0.18.0` from the PyPI index with no cache: the version reads 0.18.0, `judgevet --help` runs, and with socket connect blocked `OLLAMA_PROFILE` accepts 2 options and both `check_profile` and `HTTPSystemOneAdapter.system_one` raise `ProviderRequestError` on 27 |
| MCP | The publish workflow's installed MCP tools smoke step passed before upload. The index install's `judgevet-mcp` exits 2 without a key; with a dummy key it reports version 0.18.0 over stdio and lists `ask_noul`, `ask_choice`, `ask_score` and `evaluate_policy`. No tool was called |
| Registry | The maintainer ran `mcp-publisher login github -token`. The first `publish` of the release commit's `server.json` reported version 0.18.0 published. The listing is recorded below |

[PyPI publication](https://github.com/Alberto-Codes/judgevet/actions/runs/37260670602)
ran build, attest, release-files and publish. The live footprint was the
publish workflow's smoke calls; the exact call count was not recorded. The
index-wheel checks made no live call. No
source-archive rebuild outside the checkout was done. No unseen API body,
other model, modern protocol path or gateway became verified. The
`OLLAMA_PROFILE` limits come from the Ollama v0.35.1 API documentation. With
the maintainer's approval on 2026-10-05, the index install made one Jev call
(`jev-1.13.0`, `noul: 0.99`) and four Ollama v0.35.1 calls with `nimble`:
the how-to recipe, 26 options accepted with the profile, 27 options refused
with a 400 without it, and one malformed request. A raw `curl` of the
27-option body returned `{"error": ...}`. Recorded at
https://github.com/Alberto-Codes/judgevet/issues/296#issuecomment-5997566707.

Prior 0.17.0 evidence: tag `v0.17.0` at commit
`2ad9b86de8084d880641540bb3ef7f7454b8aba9`, wheel SHA-256
`519a89c2a6e277f2c6778dcfb5a7766655f087b81447a8354e03a9fc52b26c0c`, sdist SHA-256
`7f7bc76ca11db1de30ca4101e89c66e218d84758dd1138dadb77edd3086d9ab4`. Its registry
listing was published `2026-10-01T16:55:39.67306Z` on a retry after one 400.
[PyPI publication](https://github.com/Alberto-Codes/judgevet/actions/runs/36895249004)
for 0.17.0 ran build, attest, release-files and publish.

Prior 0.16.0 evidence: tag `v0.16.0` at commit
`e6aab4014183619d26a1cb0182a9e4105b3768c2`, wheel SHA-256
`b984e3a5642e188a4ecc9f580248aae81d31a4ad3778ad3bee949392c53b9018`, sdist SHA-256
`71e25e46513a436ae17e47d56ac88954ec1c332737d2f2deec002abb1d60c31e`. Its registry
listing was published `2026-10-01T13:57:12.153695Z` after a stale-checkout
duplicate refusal.
[PyPI publication](https://github.com/Alberto-Codes/judgevet/actions/runs/36871006827)
for 0.16.0 ran build, attest, release-files and publish.

Prior 0.15.0 evidence: tag `v0.15.0` at commit
`0d0bda02d0503b1274936361df1c91c0a38aaf1f`, wheel SHA-256
`10f961c31b2de61fad882f8a45115da8f025991553212efdcba9aae189477984`, sdist SHA-256
`df5368a9e52b4658127c021f1635392c99697390ebd510cdeea4d97372b46c3d`. Its registry
listing was published `2026-09-30T04:03:00.71939Z` on the third submission.
The first two returned 401 on an expired publisher login (#256).
[PyPI publication](https://github.com/Alberto-Codes/judgevet/actions/runs/36665560245)
for 0.15.0 ran build, attest, publish and release-files.

Prior 0.14.0 evidence: tag `v0.14.0` at commit
`bf5d15dcb5f5284ad4fa024d172f5197c40d0cab`, wheel SHA-256
`f7d1b08135e77928302a93602b4e083070d06c8fe8e4c2b7efa0ecb8fc7d394a`, sdist SHA-256
`54daf8785978f01195bd42181b1c0e81fc822036ced4e3cb51452da6c35f5d49`, registry
listing published `2026-09-29T14:24:44.289862Z`. Its
[release evidence](https://github.com/Alberto-Codes/judgevet/pull/207#issuecomment-5892265433)
records publication, hashes, attestations and registry separately.
[PyPI publication](https://github.com/Alberto-Codes/judgevet/actions/runs/36581978491)
for 0.14.0 ran build, attest, release-files and publish. The live footprint
was the publish workflow's smoke calls and the registry smoke's three tool calls;
the exact call count was not recorded. No source-archive rebuild outside the
checkout was done. No unseen API body, other model, modern protocol path or
gateway became verified.

Prior [0.13.0 evidence](https://github.com/Alberto-Codes/judgevet/issues/198)
retains its index-wheel library, CLI and MCP checks with six live calls.
Prior [0.12.0 evidence](https://github.com/Alberto-Codes/judgevet/issues/194)
retains its byte-identity and registry checks with a smaller live footprint.
Prior [0.11.0 evidence](https://github.com/Alberto-Codes/judgevet/issues/186)
retains its fuller production checks.
No source-archive rebuild outside the checkout was done for this release.
The generated release note for the breaking change named a private downstream
repository; the release notes, the merged release PR body and `CHANGELOG.md`
were corrected, and the commit message of 33d0c36 keeps the original text.
No unseen API body, other model, modern protocol path or gateway became verified.

Prior [0.10.2 evidence](https://github.com/Alberto-Codes/judgevet/issues/183)
retains its production checks without a TestPyPI round.
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
reports `io.github.Alberto-Codes/judgevet` version `0.18.0` as active with
`isLatest: true`, published at `2026-10-05T03:46:36.35978Z`. The versions 0.17.0, 0.16.0, 0.15.0, 0.14.0, 0.13.0, 0.12.0, 0.11.0, 0.10.2, 0.10.1 and 0.10.0 stay listed as earlier active versions. Package and launcher fields match the release
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

## Provider extension design

#200 accepts the generic provider extension design under #199.
The [accepted contract](https://github.com/Alberto-Codes/judgevet/issues/200#issuecomment-5850346214)
links the detailed decisions and independent review amendments.
Offline public-interface probes show that library injection already works.
The design identified missing CLI and MCP composition selection hooks.
Applications own translation, dependencies, inference and confidence semantics.
The design preserves hosted defaults and existing Jev error imports.

The implementation slices cover ownership, CLI, MCP, ordered image evidence
and installed artifact proofs. Each requires its own red test, independent
review and delivery evidence. Delivered boundaries are recorded below.
#204 remains deferred. No live call, release or model configuration changed.

## Neutral error base

#78 adds `JudgevetError` without renaming a published exception.
Jev errors inherit the neutral base. Policy errors also inherit it and retain
their `ValueError` catches. Root, domain and original imports share one class.
Ordinary Python validation errors keep their original types.
The [error issue](https://github.com/Alberto-Codes/judgevet/issues/78) records
the missing-import red test and independent public HTTP and policy probes.
Removing neutral inheritance in an isolated copy makes the HTTP probe fail.
This is a local compatibility contract, not new live-service evidence.

## Provider ownership boundary

#201 adds `judgevet.providers` for explicit borrowed ports and owned factories.
Borrowed resources stay open. Entered factory contexts close after success,
failure, invalid yielded ports and interruption. Factories own failed-setup
rollback. The helper has no hosted default or fallback.
Neutral provider errors add no HTTP status or retry guarantee.

Independent public policy and lifetime probes pass. Isolated mutations that
skip owned cleanup or close a borrowed resource each fail the ownership probe.
The [ownership issue](https://github.com/Alberto-Codes/judgevet/issues/201)
records the acceptance and gate evidence. The later sections record CLI, MCP,
media and installed proofs. No inference implementation is added.

## Application-selected CLI providers

#202 adds `create_cli_app` for borrowed ports or owned provider factories.
Independent applications retain their selections. Ordinary and policy commands
preserve state, instructions, question IDs, typed answers, models and usage.
Explicit selection bypasses hosted settings and never falls back. Validation
precedes acquisition. Owned contexts close after commands; borrowed ports stay
open. Existing hosted entrypoints and output/exit meanings remain supported.
Provider-owned audit and spend mechanisms remain opt-in.
The [CLI contract](https://github.com/Alberto-Codes/judgevet/issues/202#issuecomment-5850672112)
records the missing-import regression and exact acceptance boundary.
Independent generated-app probes pass against the checkout and isolated copy.
Replacing forwarded state in the copy makes the same probe fail. The complete
commit and push stages pass for this CLI slice. The later sections record MCP,
media and installed proofs.

## MCP provider dispatch and lifetime

#202 adds explicit borrowed/factory selection to the MCP entrypoint and
host-selected models to the server and runner. Explicit providers bypass hosted
settings. Existing tool schemas and result shapes remain supported.
Synchronous calls run serially outside the event loop. Queued cancellation
prevents dispatch. Running and acquisition cancellation drain before propagating,
including repeated cancellation. Factory setup, calls and cleanup share one
worker thread. Applications own provider deadlines and optional audit/spend.

Independent actual stdio probes preserve selected model, state, instructions
and usage. They prove borrowed lifetime, owned EOF cleanup, safe setup failure
and no remaining provider worker. Barrier probes prove cancellation ordering.
An isolated mutation that skips draining fails the independent probe.
The [MCP evidence](https://github.com/Alberto-Codes/judgevet/issues/202#issuecomment-5850970581)
records the scope and review. The later sections record media and installed
proofs. No inference implementation or live call is added.

## MCP policy tool

#202 adds `evaluate_policy` alongside the three original tools. It accepts
caller-keyed questions, state and the existing policy JSON grammar. The host
selects the model. Strict public policy parsing and evaluation produce the
ordinary answer envelope and ordered pass/unmet reports. Unmet policy remains
a successful tool response; declared failures return tool errors.
Unsupported tool and question fields fail before provider dispatch. Optional
Noul criteria and supported question values remain intact. Legacy CLI policy
behavior and the original three MCP schemas/results remain supported.

The [policy contract](https://github.com/Alberto-Codes/judgevet/issues/202#issuecomment-5851056470)
and [review repair](https://github.com/Alberto-Codes/judgevet/issues/202#issuecomment-5851113893)
record the missing-tool regression, independent consumer evidence and the
unsupported-field failure found beyond green gates. Provider-owned audit and
spend controls remain opt-in. The later sections record media and installed
proofs. No live inference or published-release capability is added.

## Image evidence library contract

#203 adds `judgevet.media` with immutable attachments, ordered question bindings,
static model capabilities and validated dispatch through an application provider.
Exact bytes, global order and per-question order remain intact. Empty optional
evidence keeps the original text route. Required missing evidence, unsupported
capabilities, transport failure and an explicitly declared insufficient-evidence
Choice remain distinct. Local ceilings are 16 images, 8 MiB per image and
32 MiB total; providers can lower them. Media results retain model and usage
metadata and must match caller question IDs, answer variants and Choice labels.

The [core contract](https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851219798)
and [review repair](https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851310878)
record exact types, red tests and the removal of unrequested criteria restrictions.
Independent consumer mutations detect dropped or swapped attachments, changed
bindings and text conversion. Repository-owned fake and translating-provider
fixtures exercise all three answer variants. These are offline boundary proofs.
Installed proofs appear below. No HTTP
media support, inference implementation, live verification or confidence
calibration is claimed.

## CLI image evidence

#203 adds optional `--evidence-file` for ordinary and policy commands. Strict
local manifests preserve image bytes, attachment order and question bindings.
Relative paths resolve against the manifest directory. Bounded reads and local
validation finish before provider acquisition. Missing required evidence has an
explicit diagnostic; malformed input, unsupported media and transport failures
produce no answer or policy envelope. Explicit insufficient-evidence Choice
answers retain ordinary success and policy-unmet behavior.

Public Typer command and option classes preserve legacy grammar, hosted empty
text calls, provider selection and per-invocation file state. The hosted adapter
rejects nonempty media before settings or credentials. Independent consumer
mutations detect dropped or swapped images and changed bindings. The
[CLI contract](https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851367000)
and [diagnostic repair](https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851476145)
record scope and evidence. Installed proofs appear below.

## MCP image evidence

#203 adds optional JSON-text `evidence` to `evaluate_policy`. Strict bounded
base64 decoding preserves exact bytes, attachment order and question bindings.
Decoding, capability validation and provider calls use the existing serialized
worker. Canceled queued requests submit no work. Running calls drain before
owned cleanup on that worker. Optional empty evidence retains text routing.

Independent SDK and actual stdio probes preserve instructions, all three answer
variants, model identity and known or unknown usage. Isolated dropped, swapped
and rebound image mutations fail the consumer oracle. Missing evidence,
unsupported capabilities and transport failures produce safe neutral errors.
Insufficient-evidence Choice remains an ordinary unmet policy. The original
three tool schemas remain unchanged.
The [MCP media contract](https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851508259)
records scope and limits. This is offline source evidence. Installed proofs
appear below; no live provider support is claimed.

## Optional media provenance

#203 adds `judgevet.media_audit` with immutable `MediaProvenance` and an explicit
keyed fingerprint helper. `JudgmentRecord.media_provenance` is its final optional
field and defaults to `None`. Schema version 1 and existing state fingerprints
remain unchanged. The pure domain holds metadata; hashing stays outside it.

Independent HMAC oracles verify versioned labels and length framing over exact
bytes, MIME, attachment order, question bindings and normalized question content.
Isolated unkeyed, omitted-content, order, binding and framing mutations fail.
Records retain opaque IDs, digests and caller-declared revisions without image
bytes, prompts or keys. Equal inputs under one key expose equality; callers own
key custody and rotation. Existing sink containment, terminal records, retry
attempt claims and known-only usage settlement remain intact.

The [provenance contract](https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851443210)
and [test repair](https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851753625)
record scope and evidence. The helper emits no records and cannot observe opaque
provider attempts or preprocessing. Installed proofs appear below.

## Installed provider extension proofs

#205 adds the offline `provider-artifacts` pre-push hook. CI runs the same hook.
It builds a source wheel and a second wheel from the source archive. Each wheel
passes in fresh base and MCP-extra environments outside the checkout. Receipts
record artifact hashes, version, dependency inventories and loaded module paths.
All judgevet imports resolve inside each environment's site-packages. Dependency
checks apply interpreter markers and reject missing or unexpected packages.

Repository-owned fixtures exercise library, CLI and MCP policy calls, selected
models, known and unknown usage, exact image bytes, order and question bindings.
Borrowed resources stay open. Entered provider contexts close after success,
call failure or an invalid port. Factories roll back failed setup.
Unsupported media and insufficient evidence retain distinct outcomes. MCP runs
through both raw stdio and the installed SDK client. An offline HTTP transport
checks hosted compatibility. Runtime bootstraps block network use before imports
and clear inherited credential, configuration and import-path variables.

Independent installed-artifact review passed all four environments. Bypassing
media dispatch in an isolated installed package made nine consumer checks fail.
The reviewer also rejected missing import receipts and checkout module paths.
The [accepted contract](https://github.com/Alberto-Codes/judgevet/issues/205#issuecomment-5851596797),
[repair](https://github.com/Alberto-Codes/judgevet/issues/205#issuecomment-5851983135)
and [receipt correction](https://github.com/Alberto-Codes/judgevet/issues/205#issuecomment-5852064351)
record scope and evidence. Complete local hook stages pass, with affected checks
refreshed after repairs. Actual commit, push and exact-commit CI remain delivery
checks. No package was published and no live provider was called. #199 and #205
retain deferred scope; #204 and live confidence research remain outside this work.
Applications still own provider translation, inference and quality validation.

#241 publishes the provider conformance kit `judgevet.testing.conformance`
behind the `conformance` extra, which then added only pytest. A provider subclasses
`BaseProviderConformance` and overrides the `provider_factory` and
`failing_port` fixtures. The fixtures `provider_port`, `provider_model` and
`media_port` are optional. Nine rule tests check the port signature, typed
answers through `evaluate_policy`, `ProviderError` on failure, the
`provider_scope` lifecycle, media refusal and media sending. judgevet's own
fakes pass. Each broken fake fails only its own rule in a pytester subprocess.
The `provider-artifacts` hook now also installs each wheel with `[conformance]` and
runs a provider subclass. The base install imports `judgevet.testing`, and
importing the kit there raises an `ImportError` that names the extra. No live
provider was called.
A unit test pins the sentence in the self-hosted provider guide that a
conforming provider is compatible in shape, not equivalent in judgment. The
test fails when that sentence changes (#249).
#247 adds the media-sending rule. It sends one kit-owned image of a declared
type through `judge_with_images` and requires answers that `evaluate_policy`
accepts. A media port whose `system_one_media` raises `RuntimeError` fails
only that rule, and so does one whose answers the policy rejects.
#246 adds `BaseAsyncProviderConformance` for `AsyncSystemOnePort` providers,
exported from the same module. It carries nine rules. Three are the base
rules: the port signature, typed answers through `evaluate_policy`, and
`ProviderError` on failure. Three are the scope rules over
`async_provider_scope` (#251). Three are the media rules over
`async_judge_with_images` (#252). Its test methods drive
coroutines with `anyio.run`, so it adds no pytest plugin and the
`conformance` extra is unchanged. `AsyncFakeSystemOnePort` passes, and each
broken async fake fails its own rule; the sync-port fake fails the typed-answer
and scope-entry rules, because both await a judgment. `judgevet.providers`
now exports the `AsyncProviderFactory` Protocol and `async_provider_scope`.
The async scope follows the sync rules: one argument, a borrowed port stays
open, a factory context exits once, and a body exception propagates. The #251 reviewer found
the async body-exception rule passed when the scope swallowed the error; the
repair added the missing check, and a kit test now fails under that mutation.
`judgevet.ports.media` now defines `AsyncMediaSystemOnePort` (#252). Its
`capabilities` stays synchronous and its `system_one_media` is awaited.
`judgevet.media` exports `async_judge_with_images`, a thin shell over the
same refusal checks as the sync function. The async judging rule fails a
synchronous `system_one_media` with a message naming "Declare it async def".
The builder's first kit test for that message stayed green without the check,
because the traceback printed the literal from the source. The test now
matches the full rendered message. The suite's eight skips are declared: six
from subclasses without a media port, two from media-capable subclasses that
skip the refusal rule. The `provider-artifacts` hook now requires 18 passed
rules in both conformance environments. The base environment still refuses
the kit with an error naming the extra.

## Gates

**3033 tests pass, 8 tests skip, 30 live tests deselected.** The last measured
coverage is **95.69%** (3661/3826 statements).
`judgevet.domain.provider_profiles` holds `ProviderProfile`, `OLLAMA_PROFILE`
and `check_profile` (#296). Both hosted adapters and the fake take an opt-in
`profile` keyword and refuse a request that breaks it before any call.
Eleven pin tests in `tests/unit/test_doc_contradictions.py` hold the sentences
#285 corrected. They cover the MCP `evaluate_policy` tool, the three-attempt
retry default, the opt-in audit sink, the review scope and the shipped-features
sentence. No live-service claim changed.
`tests/unit/test_doc_nav_coverage.py` fails when a `mkdocs.yml` nav page under
`docs/` is missing from `docs/index.md` (#288). The release procedure now records
the practised path; the TestPyPI round is optional. No release evidence changed.
`tests/unit/test_doc_version_anchors.py` fails on any `judgevet` pin or version
anchor outside a release-please marked block that differs from `__version__`
(#286). Three more pages now sit in `extra-files`; the updater check covers them.
`tests/unit/test_audit_sink_close_order.py` proves each hosted root closes the
settings-opened `JsonlAuditSink` once, after `adapter.close()` (#282). An
acceptance reviewer's no-op `close` and early-close mutations each failed it.
`judgevet.adapters.outbound.response_translation` holds `parse_success` and
`translate_status`, which take a status code and the response bytes (#57
slice 1). Both HTTP adapters call them; the 140 contract tests pass unchanged
and an import-linter contract keeps `httpx` out of the module.
CI now runs the dependency audit, `ty`, the doc schema check and docvet as
named steps of one `checks` job instead of three jobs. The three later steps
run when an earlier one fails, so no result is hidden. No check was dropped
and main has no required status check to rename (#219).
`SystemOneResponse.receipts` carries a provider's per-answer receipts as an
open mapping keyed by answer name, default empty (#281). The hosted adapters
leave it empty. `judgevet.ports.options` adds four narrow Protocols whose
methods take `provider_options`. The four existing ports, the HTTP adapters,
the fakes and the conformance kit are unchanged. A three-argument provider
still satisfies `SystemOnePort` under `ty`. `judge_with_images` and
`async_judge_with_images` forward `provider_options` only when it is set.
They bind the provider's signature first and raise `ProviderCapabilityError`
naming `provider_options` when it cannot take the keyword. A recording fake
in the contract fixtures proves `{"off_option_threshold": 0.25}` reaches the
provider. The maintainer chose the narrow-Protocol shape after a research pass
on typeshed, the .NET interface guideline and PEP 249; the decision is on the
issue. No live call has carried an option or returned a receipt.
`JsonlAuditSink`, exported from `judgevet`, is the reference audit sink (#54
slice 2). It appends one compact UTF-8 JSON object per `JudgmentRecord` to a
file opened with `O_APPEND` and requests mode `0o600` at creation. It writes
each line in one `os.write` under a lock and fails fast on a missing directory.
Errors propagate to the adapter's existing catch. Fourteen tests cover both
adapters, eight writer threads, a closed sink, the file mode, Score string
keys and provenance fields. The reviewer's five mutations each turned at least
one test red. No valid record can carry NaN, so that case has no test. CLI and
MCP wiring is slice 3.
Slice 3 adds `JEV_API__AUDIT_PATH` to `ApiSettings`. Unset means no sink, as
with the spend cap. The CLI `judge` command, the CLI policy command and
`judgevet-mcp` each open one `JsonlAuditSink` at that path and close it after
the adapter. An unopenable path exits the CLI with 1 before any request. The
MCP server reports it as a new `audit sink` startup stage. Ten tests cover the
three roots against a loopback peer. The CLI cases run in process and the MCP
cases start `judgevet-mcp`. The success cases assert one line per call and no
key in the file. The unset cases assert no file and the unopenable cases assert
no request. The reviewer's mutations are recorded on the issue. No live call
has written a record (#54 slice 3).
The offline hosted kit run now records each request. One test per adapter
asserts the `/v1/systemone` path, the `Authorization` header for the synthetic
key, and the request's question names and types. The expected side derives
from `CONFORMANCE_QUESTIONS`. A changed path at either call site and a dropped
header each turned the matching test red; a handler that recorded nothing
failed both (#275).
`judgevet.testing.conformance` now exports `AsyncProviderFactory` beside the
two kit bases. A pin test holds the module's nine public names, and the hosted
and Ollama kit modules import the alias from the public module; no test
imports `_conformance_async` any more. The reviewer's removal of the export
turned the pin test red (#277).
The `PostToolUse` hook, `scripts/vet_file.sh`, reads the `[tool.docvet]`
exclude list from `pyproject.toml` once per run. It skips only its docvet step
for a file under an excluded entry. Edits under `tests/` and `scripts/` no
longer return findings the real gate never raises. Ruff and `check_loc` run as
before. Three tests drive the hook as a subprocess: two through a `uv` shim in
a temporary project root, one against the repository's own list. The
reviewer's two mutations each turned the matching tests red (#276).
Inside an Agent-tool worktree the hook saw `.claude/worktrees/<name>/tests/...`
and matched nothing, so the noise came back there. The hook now strips one
worktree prefix before matching the list. Three shim tests cover the stripped
path, the `src` path under a worktree, and a second component that is not
stripped (#279).
The MCP smoke peer now writes its pid to a sibling file and renames it onto
the pid path. `require_reaped` therefore sees either no file or a complete
pid. One commit-stage run on 2026-09-30 read an empty pid file. The checker
sends terminate and kills after two seconds. A SIGTERM before the write would
fit; one occurrence cannot confirm it. That window now fails as a missing
file, which #280 tracks. A test asserts the temporary file holds the pid
before the rename (#278).
The smoke tests now accept that window as the checker's timeout path (#280).
A spy records the pid the checker spawns. `require_reaped` fails "checker
never launched the fixture" only when nothing was spawned. A present pid
file must equal the spawned pid, an absent file passes, and the spawned pid
must be gone. A new test delays the peer 30 s inside its own process and
runs the checker with a 0.5 s timeout. Five of the reviewer's six mutations
turned a test red; dropping only the reap check went unnoticed, as a guard on
the checker would. A checker that skips terminate fails the new test. The
checker script is unchanged.
Tests that launch `pre-commit` no longer write the user-level
`~/.cache/pre-commit/db.db`. A seed store under the user's XDG cache, keyed by
the config's repos and revs, the pre-commit version and the interpreter,
installs once per machine under a file lock. Each test copies only its
`db.db` into a home under the run directory. A red test pins that home. The
reviewer's empty-seed mutation failed every gate test with `FileNotFoundError`.
Twenty loaded runs on the first build and ten after the seed moved, each
beside an outside pre-commit loop, stayed green, and the user `db.db` mtime
did not move (#232).
The doc host launcher tests share one warmed uv cache per pytest run instead
of resolving from PyPI cold once per test. The cache sits at the run's
temporary root, or in `JUDGEVET_TEST_UV_CACHE_DIR` when set. A unit test pins
the shared path, the three broken-route cases still fail on their defects, and
two concurrent runs of the file passed where one failed before (#262).
A `live` module, `tests/live/test_ollama_kit_live.py`, runs both kit bases
against local Ollama. Its one approved run on 2026-09-30 passed ten tests and
skipped the two media-port rules; the receipt is on #267. #267 ask 2 decided
no client-side guard for Ollama's limits, since the adapter already surfaces
Ollama's error body (#267).
The provider conformance kit runs offline against `HTTPSystemOneAdapter`
and `AsyncHTTPSystemOneAdapter` over `httpx.MockTransport`, with a transport
that answers the kit's questions in the contract fixtures' wire shape. Twelve
tests pass: ten kit rules and two hosted checks. The kit skips its two media-port rules, because
the hosted adapters expose no media port. Disabling the adapter's off-list
choice check fails the hosted replay of contract fixture 15 (#272).
Four release smoke cases declare `torch` or `mcp` behind the relevant extra,
so the closure check passes in each. The inference-runtime check fires in the
base and MCP paths of `check_inventory` and in `check_conformance_inventory`,
and the `mcp` clause of the conformance inventory fires too. Disabling the
inference-runtime check fails three tests and removing the `mcp` clause fails
one (#264).
An Ollama `{"error": ...}` body now reaches the raised message, and a 16th
contract fixture replays Ollama's documented `/v1/systemone` response (#268).
`JevError` now derives from `ProviderError`, so hosted Jev failures pass the
conformance kit's provider error check (#259).
The async conformance kit also passes under pytest-asyncio `asyncio_mode = "auto"`,
and each broken async fake still fails only its own rule there (#257).
The `conformance` extra now declares `anyio>=4.15.1`, which the async kit
imports, and the `provider-artifacts` hook requires the extra to add exactly
pytest and anyio (#253).
Each conformance rejection case now names its rejecting check with `match=`,
and three mutations of those checks now fail a test (#260).
Every remote GitHub Action is pinned by full commit SHA with its tag as a
comment, and a test fails on any unpinned remote `uses:` line (#245).
Dependabot's `github-actions` entry lists `/` and `/.github/actions/*`, and a
test fails on any directory with a remote `uses:` line that no pattern covers
(#266). Whether Dependabot reads `.github/actions/supply-chain/action.yml`
through that pattern is an **open question** until its next weekly run shows it.
`.yamllint` raises yamllint's line limit to 100 so the pinned lines fit.
The public dependency audit on 2026-09-30 found GHSA-42vr-xj54-vc7v in
`pyjwt` 2.14.0, a dependency of `mcp[crypto]` behind the `mcp` extra. `uv.lock`
now pins `pyjwt` 2.15.1, and `uv audit --locked` reports no known
vulnerabilities and no adverse project statuses across 90 packages.

The CI `test` job uploads `coverage.xml` as the `coverage-xml` artifact. The
Pages build measures coverage again and publishes the README badge endpoint at
`badges/coverage.json` (#50). The local pre-push floor stays at 90.

The CI `sbom` job uploads the `supply-chain` artifact (#59). It holds CycloneDX
1.5 SBOMs for runtime, runtime with MCP and development dependencies, a licence
table per scope, the JSON audit and a provenance file with the `uv.lock` SHA-256.
Each SBOM is a source SBOM labelled with CycloneDX lifecycle `pre-build`.
`publish.yml` generates the same files through one shared composite action,
attests the wheel and sdist (build provenance) and the wheel's runtime SBOM,
and attaches the files to the GitHub release (#231). A scratch prerelease proved
it: run 36523121805 attached 11 files, and `gh attestation verify` passed for
the wheel and sdist. Since #237 the release also carries the wheel, the sdist
and both attestation bundles. Scratch run 36570472000 attached 15 files, and
`gh attestation verify --bundle` passed for each against the release bundles.
Release 0.14.0 ran it: run 36581978491 attached 15 files, and the
attestations verify.

CI and both pytest hooks run the suite on parallel workers (`-n auto`,
pytest-xdist). Local wall time fell from 93.6 s serial to 40.5 s on 4 workers,
with the same tests and coverage (#208). CI push run 36337960770 finished its
`test` job in 82 s (pytest 69.4 s), down from 233 s before #208.

The suite leaves nothing in the shared uv cache (#243). A session fixture gives
each pytest session a private uv cache and removes it at teardown. The
`scripts/smoke_release.py` uv helpers pass that cache to each uv child, or
run it uncached (`--no-cache` or `UV_NO_CACHE=1`) outside pytest. Before the
fix, one full run added 4 editable `judgevet` entries to
`~/.cache/uv/archive-v0`, from the `uv run yamllint` hook test. After it, two
consecutive full runs of the pre-repair tree added 0 entries each, and two
separate full runs of the final tree added 0 entries each.

`TestBuildChildEnv` now sets and removes variables through `monkeypatch`,
so `PATH` and `HOME` survive it on the same worker (#244). A regression
compares their fingerprints around the three tests and failed at 23c075c. The
`_uv` stub that #243 added to survive the lost `PATH` is removed.

#206 assigns one mechanical validation owner and preserves independent review.
The complete commit and push stages passed on 2026-09-26. The bounded trial
replayed #195's original fixture against its historical baseline and current
source. A fresh reviewer passed 16 public-interface cases and made an isolated
fake-validation mutation fail. The reviewer returned incomplete while final
gate evidence and this STATUS update were pending. The
[workflow issue](https://github.com/Alberto-Codes/judgevet/issues/206) records
the continuation, input snapshots and acceptance disposition.
Required delivery hooks remain enabled. No product code, model configuration
or live-service evidence changed. Worker and supervisor token counters are
unknown; the initial reviewer recorded eight shell calls and unknown tokens.

#191 adds an optional keyed `state_fingerprint` to `JudgmentRecord`, `None`
unless `fingerprint_key=` is set on an HTTP adapter or a fake. The value is
HMAC-SHA-256 over a versioned label and compact sorted-key JSON of the raw
state, computed before redaction, lowercase hex, untruncated. The key never
reaches a record, an event or an exception. `schema_version` stays 1. The
contract test compares the field between each fake and the adapter on every
fixture. No live call has written a fingerprint.
#195 adds `judgevet.domain.choice_options.check_choice_options`, a pure check
that both HTTP adapters run inside the attempt and both fakes run when they
bind answers: a Choice `choice` or probability key outside the question's
criteria raises `JevResponseError` with status 200, naming the question and
the option. A subset of probabilities passes. Contract fixture 15
`choice_off_list` proves the adapters and the fakes agree. No live call has
returned an off-list option.
#196 turns retries on by default: `RetryPolicy()` makes three attempts on 429
and every 5xx with the existing 0.5 s base, 5 s cap and subtractive jitter,
both HTTP adapters use it when `retry` is None, and the CLI and MCP attempts
setting defaults to 3. The opt-out is `retry=RetryPolicy(max_attempts=1)`.
`Retry-After` is still not honoured, the spend cap counts every attempt and
the audit record stays one per logical call. The contract tests pin one
attempt because they prove translation, not retries. Offline tests prove a 503
then a 200 returns the answer; no live call has exercised the default.
#189 slice (a) lets both fakes take scripted `usage=` and a scripted whole-call
`error=`. The contract test now runs every fixture through both fakes and the
HTTP adapter: whole-response equality on the five response fixtures and error
type plus `status_code` on the nine error fixtures. Slice (b) gives both fakes
the same `spend_cap=` and `audit=` options as the HTTP adapters: claim before
the call, settle on success, one `JudgmentRecord` per call including a refused
claim, sink failures contained. `SpendCap` now lives in `judgevet.domain.spend`
and `question_types` in `judgevet.domain.questions`; the adapter import paths
and `judgevet.SpendCap` are unchanged. The contract test compares counters and
records between each fake and the adapter on every fixture. No live-service
claim changes.
#54 slice 1 adds an opt-in `AuditSink` port and a frozen `JudgmentRecord`.
Both HTTP adapters write one record per logical call. A sink failure is
reported on `http.call` as `audit_error` and never changes the result. The
JSONL sink landed as slice 2 and the CLI and MCP settings as slice 3.
#56 slice A adds an opt-in library `SpendCap` for both HTTP adapters and
`JevBudgetExceededError`. Slice B reads `JEV_API__SPEND_MAX_ATTEMPTS` and
`JEV_API__SPEND_MAX_INPUT_TOKENS` into one cap per CLI process or MCP server
lifetime. A tripped cap exits the CLI with 1. Each MCP tool returns it as an
`isError` tool result that says a restart is required. The `ask_*` tools now
return every service error as a tool result, as `evaluate_policy` already did.
No live call has run the cap. #225 replaces the `ask_*` summary text from #211
with the serialized JSON of each result's `structuredContent`. #228 adds a
required `default_criteria` boolean to the `ask_score` result. It is true when
the server applied the default rubric because the call omitted `criteria`.
Local commit and push gates pass for #172. The issue holds delivery evidence.
#172 makes `Noul`, `Choice` and `Score` construction keyword-only with no
deprecation cycle; positional construction raises `TypeError`. The commit
carries a `BREAKING CHANGE` footer for release-please.
#173 exports `judgevet.VERIFIED_MODEL`; a test parses the verified table
below and keeps the constant equal to the model it names. Adapters, CLI and
MCP keep `jev-latest`.
#171 ships `judgevet.testing` with `FakeSystemOnePort` and
`AsyncFakeSystemOnePort` inside the wheel, no extra. An import contract keeps
the fakes off the adapters and the layers contract keeps the domain and ports
off the fakes. No live-service claim changes.
The documentation rounds retain the existing local gates: suppressions,
dependencies, test hygiene, Ruff lint/format, ty, import contracts, file size
(300 code lines), docvet (diff/all), pytest and pytest with coverage.
Hooks remain enabled. The file-size gate `scripts/check_loc.py` is new at
commit and in CI; all 44 modules under `src` measure at or under 300 code
lines. Slice A of #8 adds nine boundary tests for the module cap and a
report-only function counter: the gate prints every function over 50 code
lines and still exits 0. Slice A2 makes the module cap a single hard limit:
300 passes, 301 fails, and the 320 tier is gone. Slice B enforces the function
cap: a body of 50 code lines passes and 51 fails the gate. No function under
`src` is over 50; the largest measured 42 before slice B landed.
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
- Diagnostic redaction is bounded. Protocol errors, MCP tool error results,
  CLI error envelopes and arbitrary tracebacks can disclose service-supplied
  content. See [SECURITY](SECURITY.md).
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
| choice criteria string values | **verified** — every live call has sent string values only: `tests/live/test_cli_live.py::test_installed_cli_mixed_live` (`{"yes": "Clear", "no": "Unclear"}`) passed on the 0.10.2 index wheel and the release smoke's live run of the package-docstring Choice example (`{"a": "Option A", "b": "Option B"}`) returned a `ChoiceAnswer`, both recorded on #183, 2026-09-25; `tests/live/test_system_one_live.py::test_system_one_live_with_all_question_types` sends `{"cat": "Feline", ...}` and its legend assertion is the row above. Object, array and null forms are inferred from the vendor docs; no call has sent them (#174) |
| 401 returns `{"detail": {"error_type", "message"}}` | **verified** — live call with an invalid key, 2026-09-21 |
| 422 returns `{"detail": [ {type, loc, msg, input} ]}` | **verified** — live call omitting `questions`, 2026-09-21 |
| `detail` is polymorphic: an object for auth, an array for validation | **verified** — the two calls above disagree in shape |
| an oversized request returns 400 with `{"detail": {"error_type": "max_tokens_exceeded"}}` | **verified, observed once** — live call on 2026-09-25 with a 400,000-character state against `jev-1.13.0`, recorded at https://github.com/Alberto-Codes/judgevet/issues/39#issuecomment-5825759575. The body does not say which budget fired; the request exceeded both the 32k and the 64k budget. A second 400,000-character call on 2026-09-30 through `tests/live/test_max_tokens_live.py` returned the same status, recorded at https://github.com/Alberto-Codes/judgevet/issues/192#issuecomment-5924025204. A 180,000-character state of repeated English words was answered in the same run. Probe 2 on 2026-09-30 measured 10,798 input tokens for 60,000 characters of that text, then sent 222,263 characters, about 40,000 tokens, with one `noul` question; the service refused it with status 400 and the same body, recorded at https://github.com/Alberto-Codes/judgevet/issues/192#issuecomment-5924550998. **Verified, observed once:** the 32k state-plus-question budget fires on its own, below the 64k request budget. The boundary lies above about 32,394 tokens (the answered 180,000-character state by the measured rate) and below 40,000 tokens |
| a 2,959-byte JSON state with seven `choice` questions of up to 16 options fits the context budgets | **verified** — live call on 2026-09-25 against `jev-1.13.0` returned 200 with `input_tokens=3110`, recorded at https://github.com/Alberto-Codes/judgevet/issues/39#issuecomment-5825777868 |
| 400 with `detail.error_type` = `max_tokens_exceeded` becomes JevMaxTokensExceededError, retryable=False | **verified, observed once** — `tests/live/test_max_tokens_live.py` sent a 400,000-character state through the real adapter on 2026-09-30. It caught `JevMaxTokensExceededError` with `retryable is False` and `status_code == 400`, recorded at https://github.com/Alberto-Codes/judgevet/issues/192#issuecomment-5924025204. The body is the one the 2026-09-25 call returned, recorded at https://github.com/Alberto-Codes/judgevet/issues/39#issuecomment-5825759575 |
| an opt-in `SpendCap` refuses an attempt before sending once a limit is reached, and a failed attempt settles zero input tokens | **inferred** — offline tests against `httpx.MockTransport` only (#56 slice A); no live call has run the cap. Whether the service bills a failed attempt is an open question on #56 |
| an opt-in `AuditSink` receives one `JudgmentRecord` per logical call, never per attempt, with no state, and a sink failure never changes the result | **inferred** — offline tests against `httpx.MockTransport` only (#54 slice 1); no live call has written a record |
| a 422 body echoes the request payload back under `input` | **verified**, and the adapter discards it (#85) |
| 429 and 529 | still unseen. 429 needs abusing the service and 529 cannot be forced |
| every other field name | inferred from documentation |
| resolved models other than `jev-1.13.0` | untested; both `jev-latest` and explicit `jev-1.13.0` have been called |
| probabilities on the wire are rounded to two decimals | observed once — a consumer call on 2026-09-24 against `jev-1.13.0` returned a four-level Score summing to 0.99 (#175); the tolerance is 0.005 per probability since that fix. This repository's live suite asked a four-level Score once on 2026-09-24 (#184) and the resolved `jev-1.13.0` returned probabilities summing to exactly 1.0, which neither confirms nor refutes the rounding |
| Choice `confidence` sits below `probabilities[choice]` | **observed five times for soft distributions; equal at 1.0 three times**. The 0.12.0 production smoke on 2026-09-25 returned `ChoiceAnswer(choice='a', confidence=0.9, probabilities={'b': 0.05, 'a': 0.95})` with both values in one run record, at https://github.com/Alberto-Codes/judgevet/issues/194#issuecomment-5826847175. The 0.11.0 production smoke on 2026-09-25 returned `confidence=0.89` for `choice='a'`, recorded at https://github.com/Alberto-Codes/judgevet/issues/186#issuecomment-5825514560; that comment elides the probabilities, and `probabilities={'b': 0.05, 'a': 0.95}` is recorded only in the body of https://github.com/Alberto-Codes/judgevet/issues/187. The 0.10.2 production smoke on 2026-09-25 returned `confidence=0.9` for `choice='a'`, recorded at https://github.com/Alberto-Codes/judgevet/issues/183#issuecomment-5824552631, with the probabilities elided. The differential probe `tests/live/test_choice_confidence_live.py` ran once on 2026-09-30 with 2, 3 and 4 options on a duplicate-charge state. Each call returned `confidence=1.0` with `probabilities[choice]=1.0` and every other option at `0.0`, recorded at https://github.com/Alberto-Codes/judgevet/issues/193#issuecomment-5923966685. Every candidate spread measure equals 1.0 there, so that run distinguishes none. Probe 2 on 2026-09-30 used an ambiguous state. It returned `confidence` 0.99, 0.94 and 0.92 for 2, 3 and 4 options, against chosen-option probabilities 1.0, 0.97 and 0.94, recorded at https://github.com/Alberto-Codes/judgevet/issues/193#issuecomment-5924550851. The vendor's demo approximation, generalised to `(n × largest − 1) / (n − 1)`, matches four of the five soft runs within 0.01 and misses the 3-option run by 0.015. The top-two margin also matches four within 0.01 and misses the 4-option run by 0.03. The vendor publishes no formula; the formula is unverified |
| `model` in a response is the **resolved** version, not the alias sent | verified — the live test caught `jev-1.13.0` where `jev-latest` was sent |
| fake and real adapter produce identical outcomes | verified — contract tests on 16 hand-authored fixtures, inferred from docs/reference/api.md except the oversized-request fixture, which replays the body recorded at https://github.com/Alberto-Codes/judgevet/issues/39#issuecomment-5825759575, and `ollama_documented_response`, which copies Ollama's documented body from https://ollama.com/blog/ollama-now-supports-jev-style-decision-models and stays inferred from the docs: it is consistent with the one observed Ollama call but replays the docs' rounded numbers, not that call's (#268); the shipped `judgevet.testing` fakes match the adapter's whole response, error type and status, spend counters and audit record on every fixture (#171, #189) |
| the hosted adapter parses Ollama's `/v1/systemone` response for choice, noul and score | **observed once** — judgevet 0.15.0 CLI at 62c6490 against local Ollama 0.35.0 with `nimble:latest` (9.0B, Q8_0) on 2026-09-30, `JEV_API__BASE_URL=http://localhost:11434`, `JEV_API__TIMEOUT_SECONDS=120`; probabilities arrived at full float precision, `model` echoed the tag, and the score equalled the probability-weighted level average; recorded at https://github.com/Alberto-Codes/judgevet/issues/268#issuecomment-5917968541. A first attempt at the default 30 s timeout failed while the model loaded. On 2026-10-05 Ollama 0.35.1 returned the documented `{"error": "<string>"}` body with a 400 for a 27-option Choice, and the 0.18.0 adapter carried the string into `JevRequestError`; recorded at https://github.com/Alberto-Codes/judgevet/issues/296#issuecomment-5997566707. Other Ollama error statuses, `tev1` and judgment quality are unverified |
| the hosted adapters pass the provider conformance kit against local Ollama `nimble` | **observed twice** — `tests/live/test_ollama_kit_live.py` on 2026-09-30 against Ollama 0.35.0, `nimble:latest` digest `24e550a16a7081881be2f1f0d91e8cc13a597472735c04119f035a0a85c67e0c` (qwen35, 9.0B, Q8_0), adapter `timeout_seconds=120.0`: `10 passed, 2 skipped in 9.14s`; the port-shape, typed-answers, failure, scope and media-refusal rules passed for the sync adapter and the three async rules passed; the two media-port rules skipped because the hosted adapters supply no media port; the failure rule used a closed loopback port, so it says nothing about how Ollama fails; recorded at https://github.com/Alberto-Codes/judgevet/issues/267#issuecomment-5922154877. A second run on 2026-10-01 at main 128c867, after the async base grew to nine rules, returned `14 passed, 4 skipped in 10.74s` against the same server, model and digest: the seven sync rules and the same seven async rules passed, including the four async scope and media-refusal rules that had never run live, and the two media-port rules skipped in each class; recorded at https://github.com/Alberto-Codes/judgevet/issues/267#issuecomment-5932674842 |
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
new live-service evidence. [Supported imports and compatibility](docs/reference/compatibility.md)
describes the public-versus-legacy policy validation distinction.
