# STATUS

Last written: 2026-09-23. Current evidence ledger. Detailed implementation,
release and credential history remains in Git and the linked issues.

## Published release

judgevet 0.7.0 is published. Library, CLI and optional MCP share one version.
The release adds supported root exports, pure typed policies and JSON decoding.
CLI contracts and MCP tools retain their previous behavior.

| Artifact | Evidence |
|---|---|
| Release/tag | `v0.7.0`, commit `cc1a3f48bd8ef8d09fc03f46b8e6f89299334e4a` |
| Wheel SHA-256 | `569eb78c355133b8735cda47c392a0e82ba07c4ee2d66f136c9696520a525ada` |
| Source distribution SHA-256 | `d321e451c4c80b86b8e78c1f40c53759945d13be54df6b0105dc47922c5efa47` |
| Actual TestPyPI/PyPI downloads | Match workflow artifacts and each other; isolated base/MCP imports, typing marker, examples and live calls passed |
| Library | Exact README and four policy-guide examples executed against the published wheel; policy examples also type-checked |
| CLI | Installed mixed live judgment passed with clean stderr |
| MCP | Discovery and all three live tools passed; fresh uvx launcher passed |

[Release evidence](https://github.com/Alberto-Codes/judgevet/issues/143) records
commands, hashes and limits. [Release CI](https://github.com/Alberto-Codes/judgevet/actions/runs/35807462370),
[TestPyPI publication](https://github.com/Alberto-Codes/judgevet/actions/runs/35807319494)
and [PyPI publication](https://github.com/Alberto-Codes/judgevet/actions/runs/35807568535)
passed. No unseen API body became verified.

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
package links and current example checks pass. Site publication remains the
separate final follow-up [#41](https://github.com/Alberto-Codes/judgevet/issues/41).
That program did not change Pages settings or repository visibility.
The deployment-readiness follow-up below now tracks Pages publication.
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

## Gates

**1309 tests pass, 6 live tests deselected.** The last measured coverage is
**94.75%** (1695/1789 statements).
The documentation rounds retain the existing local gates: suppressions,
dependencies, test hygiene, Ruff lint/format, ty, import contracts, docvet
(diff/all), pytest and pytest with coverage. Hooks remain enabled.
Ordinary tests exclude live service calls. The coverage floor is 90%.

#12 adds the strict MkDocs build to commit/push hooks and CI. It checks authored
local links, generated Python references and final HTML links/anchors offline.
Nine acceptance tests cover link parsing and strict source-reference resolution.
Independent symbol, target and anchor mutations fail the build; restoration
passes. A fresh development-only installation builds without MCP or API keys.
Two further acceptance cases cover project-path assets and anchors while
preserving missing-target findings. Removing the prefix mapping fails the test.
Strict building does not prove publication. Example execution and editorial
checks remain separate; Pages deployment is tracked below.

## Deployment-readiness work

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
The source-built development wheel is not evidence of index publication.

The complete commit/push gates include strict docs, isolated examples and
coverage. Runtime evidence is local and synthetic; unseen service
errors stay inferred. No runtime dependency or version changes in this round. The 0.8.0
release remains pending. The Pages site is live.

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
