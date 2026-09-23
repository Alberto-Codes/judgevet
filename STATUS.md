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

[#145](https://github.com/Alberto-Codes/judgevet/issues/145) is in progress.
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

#10 has a [navigation foundation](docs/index.md): all current pages have draft
metadata and visible status, with separate user and maintainer paths. Final
navigation acceptance remains open for the final reading-path audit. Tutorial,
explanation and error-reference destinations now exist; #12 validates site links.

#149 supplies explanations of question types, local policy decisions and evidence
limits. The shared support-ticket scenario uses labeled synthetic values. Its
policy example executes offline; numeric illustrations were checked. No model
accuracy, calibration or new live-service claim is made.

#11 explains the library-first architecture, entry-point choices, typed ports,
explicit ownership and optional MCP runtime. Source and lifecycle tests support
the package claims; they do not promote service behavior. Diagrams remain #73.

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

## Gates

**1084 tests pass, 6 live tests deselected.** The last measured coverage is
**94.20%** (1430/1518 statements).
The documentation rounds retain the existing local gates: suppressions,
dependencies, test hygiene, Ruff lint/format, ty, import contracts, docvet
(diff/all), pytest and pytest with coverage. Hooks remain enabled.
Ordinary tests exclude live service calls. The coverage floor is 90%.

#12 adds the strict MkDocs build to commit/push hooks and CI. It checks authored
local links, generated Python references and final HTML links/anchors offline.
Nine acceptance tests cover link parsing and strict source-reference resolution.
Independent symbol, target and anchor mutations fail the build; restoration
passes. A fresh development-only installation builds without MCP or API keys.
The site is local only. Example execution and editorial checks remain separate.

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
