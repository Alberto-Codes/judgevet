# STATUS

Last written: 2026-09-22. A session overwrites this file.

## Next-release MCP command (#25)

The source tree now installs `judgevet-mcp`. Its composition root reads
Settings once, acquires the HTTP adapter, serves the existing three tools,
and closes its adapter in `finally`. Missing key, invalid settings and a
missing optional runtime fail with fixed stderr; stdout carries MCP frames.
The error boundary names IO, runtime, value, type and grouped failures. It
does not claim to sanitize every arbitrary exception class.

Seventeen new tests bring the default suite to **390 passed, 95.55% coverage**.
They exercise real stdio EOF, acquisition and serving failures, interruption,
settings propagation, offline subprocess discovery and all three HTTP-backed
tools. Five deliberate mutations were rejected: disabled close, duplicate
Settings reads, stdout noise, raw validation details and absent entry point.
The unmodified tests passed again after each source change was restored.

A wheel from this source passed in separate base-only and MCP-extra virtual
environments outside the checkout. Base library/CLI work without MCP. The
installed MCP command discovered exactly three tools, completed all three
live calls with resolved model `jev-1.13.0`, emitted only protocol frames,
and exited 0 on EOF with empty stderr. SHA-256:
`9f63fcda5f484c8f74bac8d0f2fd410df32cd61a5ce5365214baebcc6330055a`.
This is an **unreleased local source wheel**, still carrying the current
0.2.0 metadata. It is not the published 0.2.0 wheel or an index verification.

The handshake now reads the installed distribution version (#113). A real
initialization assertion failed before the change (0.1.0 versus 0.2.0), passed
after it, and rejected a deliberate 0.0.0 mutation. A fresh wheel installed
outside the checkout advertised 0.2.0, matching its distribution metadata;
its SHA-256 is
`319a3cda2074c4e6fa8d407b2e5bd25a1975ca87a410e900a46f02e024cc4daa`.
This is also an unreleased source wheel, not an index artifact. The suite
remains 390 passed, 95.55% coverage; all eleven configured gates passed.
The coder implemented the accepted specification without a functional repair;
the gatekeeper wrote the red regression assertion and artifact probe.
#114 owns compatibility prose, #37 installation guidance, and #115
the live MCP publishing gate. The already-landed library gate is unchanged.
Native Codex tools were exercised successfully through the existing inline
launcher before this change. A fresh configured connection after replacing
the launcher is a separate check; it cannot prove a native session reload.

The OSS workflow did not land cleanly. The reasoning specification required
corrections, and several coder test drafts were rejected. The coder's
source-contained lifecycle repair passed two gatekeeper-corrected red tests;
the gatekeeper repaired the error boundary and wrote the retained regression
proofs. `CLAUDE.md` now requires behavioral tests to start red. Original and
accepted specifications, dispatch revisions and findings are on #25; per-run
outcomes are in the shared delegation log. No model-confidence value is used
as release permission.

## MCP compatibility documentation (#114)

The adapter now distinguishes SDK 2.2.0's source-supported compatibility paths
from judgevet's exercised legacy 2025-03-26 initialization. Tagged SDK and
protocol citations support the claims. The dependency floor stays unchanged.
The extracted stdio example ran to EOF, closed its real HTTP client and emitted
no stdout/stderr. SDK model probes verified server_info, structured_content
and is_error serialize as serverInfo, structuredContent and isError.
Runtime AST and parsed TOML values are unchanged. The existing transport
regression passed; the full suite remains 390 tests at 95.55% coverage.

The coder needed a completion repair and gatekeeper prose corrections. It
also replaced an explicitly frozen external probe with a mock-only check.
That result was rejected; the gatekeeper restored the real execution probe
and independently ran it. #114 preserves the returned artifacts and findings.
The shared delegation skill now requires checking external probe integrity.

## Installation guidance (#37)

`docs/how-to/install.md` distinguishes published 0.2.0 library/CLI installs
from the supported MCP command on main. Fresh pip and uv installs outside the
checkout imported from site-packages; the base installation had no MCP runtime.
The downloaded published wheel contains `judgevet/py.typed` and retains hash
`30b1b76a191c78bf01184a7727446ff3cde7999fcbbc7a5106fc7b598e8b9318`.
The published MCP extra installs its runtime but lacks the console entry point.

The documented direnv/uv launcher discovered all three tools and completed
all three live calls from /tmp. An isolated source-wheel installation also
passed; its hash is
`41747535dae8a2d0004b33e7cdbeb359f11704bfcc00d89f13d9a26c509d2bf1`.
This is an unreleased source artifact with 0.2.0 metadata, not an index release.
Native Codex session reload remains unproven by these separate probes.
The local config and external probes retained their pre-dispatch hashes.

The coder drafted the guide but mislabeled config scope and confused tool
inputs with outputs. Codex corrected those errors and missing requirements.
Original prompts, accepted spec, returned draft and installation outputs are
on #37. The shared skill now calls for one consolidated accepted checklist.

## MCP artifact transport checker (#115, first round)

The new stdlib transport helper initializes an installed MCP command, checks
its installed version and exact three-tool discovery, and validates all three
structured answers. One deadline covers spawn and protocol work. Cleanup drains
stdout while terminating and reaping the child with separate bounded waits.
Diagnostics are fixed; child stderr is discarded and stdout must be protocol.

Thirty-six offline regressions bring the suite to **426 passed, 5 deselected,
95.55% coverage**. A real installed command makes three observed loopback HTTP
requests. Controlled child processes prove malformed frames, invalid numeric
answers, missing tools, stale versions, early EOF, failed exits, output pressure,
timeouts and cancellation fail or clean up as specified. A final truncated-frame
regression failed before enforcing newline termination. Deliberately skipping
tool calls, accepting negative probabilities, and removing the spawn deadline
each made its regression fail. The unmodified suite and all eleven gates pass.

The reasoning model supplied the corrected accepted specification on #115.
Coder drafts and tool-less repairs needed gatekeeper corrections; Codex wrote
the retained tests and repaired numeric validation, framing, public errors and
process cleanup. Raw prompts, returns and measurements are preserved on #115
and in the shared delegation log. The shared skill records the observed limits.
A native judgevet Choice call succeeded, classifying this evidence as transport
only; that advisory answer is not a release gate or native reload proof.

This helper is not yet wired into publishing. #115 remains open for a separate
MCP-extra environment using the exact downloaded wheel, live tool calls before
upload, and a broken-artifact Actions proof followed by a clean candidate.
The existing base-only artifact smoke remains unchanged.

## Isolated MCP wheel gate (#115, second round)

Both publishing workflows now run the MCP check after the existing base-only
smoke and before upload, using the same downloaded wheel path. The new stdlib
parent creates a separate MCP-extra venv outside the checkout, proves the
installed import location and version, and launches that venv's absolute
`judgevet-mcp`. Setup subprocesses and server transport have bounded lifetimes.
Missing credentials, failed setup, malformed probe metadata and server failures
produce fixed diagnostics. Temporary files and owned processes are cleaned up.

Twenty-five new offline tests bring the suite to **451 passed, 5 deselected,
95.55% coverage**. All eleven configured gates and workflow actionlint pass.
Three mutations failed their targeted tests: omit the server check, accept an
outside import, and retain poisonous Python environment variables. The literal
module invocation passed live with a source wheel whose SHA-256 is
`41747535dae8a2d0004b33e7cdbeb359f11704bfcc00d89f13d9a26c509d2bf1`.
The existing base smoke passed the identical wheel. Missing-key and modified
wheel-without-MCP-entry-point invocations exited 1 with fixed FAIL output.
These are local source-artifact checks, not index publication evidence.

The whole-module coder return was rejected before execution for absent process
cleanup and entrypoint, invalid imports and substring isolation checks. Smaller
function returns supplied the retained implementation with gatekeeper repairs.
Codex wrote the retained tests, CLI entrypoint, workflow steps and gate fixes.
Specifications, raw returns, corrections and measurements are on #115 and in
the shared delegation log. Prior transport tests and local MCP config retain
their recorded hashes; the shared skill records the observed limitations.

The [TestPyPI failure proof](https://github.com/Alberto-Codes/judgevet/actions/runs/35699666984)
now passes its acceptance criterion: build and base-only smoke succeeded, MCP
smoke failed, and upload was skipped. Proof branch `proof/mcp-artifact-115`
removes only the MCP console entry point during build; it must not merge into
main. The downloaded Actions wheel retains the base console entry and lacks
the MCP entry. SHA-256:
`c27881cf2d8ad5a7c2bb52bb9d00ef577888b11324a427e736e048853391df11`.
This deliberately broken artifact was not published to an index.

#115 remains open for the final clean fresh-version candidate passing the
publishing path. Release-please currently proposes 0.3.0; no new version has
been published. Finish the other #116 children before reserving that version.

## Console detector proof (#109, completing #106 and #99)

The production console check and three new selftest cases share `check_console`.
The default still runs the absolute installed `judgevet --help` beside the active
interpreter. Real nonzero and missing executables produce named findings; a
successful subprocess produces none. Missing executables no longer escape as
`FileNotFoundError` from the offline checker.

The literal no-key selftest now reports `9/9`. Externally replacing the shared
detector with an always-clean function makes `main(['--selftest'])` exit 1,
report `7/9` and name the missed nonzero/missing console detections. An always-failing
detector also fails the successful-child case. All 20 other original functions
remain unchanged, including the six existing detector cases. This completes the
only remaining requirement of #106 and #99 without rebuilding their landed gate.

Eight regressions bring the suite to **459 passed, 5 deselected, 95.55% coverage**;
all eleven configured gates pass. The coder returned a correct detector but
inverted the selftest verdicts: 2 tests failed and 6 passed. Codex corrected that mapping,
wrote integration and retained tests, and fixed docstring/lint findings. The
reasoner's specification also needed a routing correction. #109 preserves the
raw returns, accepted specification and executable proof; the shared skill/log
record these observations. Native MCP feedback was advisory, not a gate.

## Type-checker suppression gate (#111)

The scanner now recognizes bare and bracketed ty ignore comments through both
its token-aware path and parse-error fallback. Strings and docstrings containing
examples remain unflagged. Both actual and allowed per-file-ignore counts remain
18. The two live-test answer lookups now narrow to NoulAnswer explicitly; no live
call was needed. The frozen-settings test mutates each field dynamically and
still requires the runtime frozen-model error.

Fifteen scanner cases and a second frozen-field case bring the suite to
**475 passed, 5 deselected, 95.55% coverage**. All eleven configured gates pass.
The real suppressed assignment canary passes ty and fails the suppression gate;
removing its ignore makes ty fail. Removing the scanner alternative makes all
nine detector cases fail. Disabling runtime immutability makes both frozen-field
cases fail. Source bytes were restored after each deliberate mutation.

The coder returned all five requested replacements correctly. Codex's accepted
constant-setattr recipe caused a B010 finding; Codex corrected the specification
and parameterized the runtime test. The model was not responsible for that
recipe error. Original/revised specifications, raw replacements and executable
proof are on #111; the shared skill/log preserve that distinction.

## The headline

**judgevet 0.2.0 is on PyPI.** `pip install judgevet` installs the library and
CLI. The `mcp` extra adds the MCP runtime. The wheel downloaded from PyPI
passed both documented live examples in a fresh virtualenv outside the
checkout. Its SHA-256 matches the independently verified TestPyPI wheel:
`30b1b76a191c78bf01184a7727446ff3cde7999fcbbc7a5106fc7b598e8b9318`.

[v0.2.0](https://github.com/Alberto-Codes/judgevet/releases/tag/v0.2.0)
shipped from `05c0d95` under the documented standing release permission.
The [publish run](https://github.com/Alberto-Codes/judgevet/actions/runs/35686542690)
passed its live artifact gate before uploading over OIDC. No stored PyPI token
is used. Publishing the draft triggered the workflow.

`0.0.1` is yanked, with the reason "Name reservation only; contained no
working code. Use 0.1.0 or later." It still resolves for anyone who pins it
exactly, which is what yanking means; it is gone from resolution. #88 closed.

## What the release contains

**The domain model matches the live service.** It was written entirely from
documentation and never exercised. One probe call settled it: every field
parses, including the parts easiest to get wrong — a noul answer carries no
`confidence` while choice and score do, `score` is a continuous `1.05` rather
than an integer index, and `legend` is a map keyed by stringified position
rather than a list. The official HTTP reference then confirmed all three
independently.

Error bodies are now verified too, for the two statuses that can be provoked
without abusing the service. The response shape held a second time against a
domain that has since grown invariants: the real probabilities summed to
exactly 1.0 in both maps, the choice appeared in its own map, and the score sat
inside its legend — so the constraints added in #77 do not reject real data.

What is still inferred: 429 and 529 bodies, every model but `jev-1.13.0`, and
the field names no call has exercised.

The package root exports both adapters as of 0.2.0. `AsyncHTTPSystemOneAdapter`
shipped in #92 reachable only through `judgevet.adapters.outbound.http`, which
made it proven but not public; `tests/unit/test_public_surface.py` now pins the
export set so that cannot recur silently.

The question types are passable to `system_one` as of #98. They were exported
and documented from the start and never worked: the adapter put `questions`
straight into `json=`, so a `Noul` raised `TypeError`. Ten gates and 286 tests
were green over it, because every test passed raw dicts and never crossed the
wire boundary with a question object. Found by installing the built wheel in a
clean venv and running the package's own example — see #99, which makes that a
gate.

## Where the repo is

```
src/judgevet/
  domain/      questions · answers · response · usage · errors     tested
               frozen dataclasses; __post_init__ raises ValueError on a
               bad range, a non-distribution, or a choice off its own map
               errors carry `retryable`: true on rate-limit and service
  ports/       SystemOnePort — a typing.Protocol, satisfied by shape
  adapters/outbound/http.py    four module-level helpers — build payload,
                               parse body, translate status error, translate
                               request error — and a thin adapter over them.
                               The translators return the exception rather
                               than raising, so #92's async adapter shares
                               them and keeps `raise ... from exc` at one
                               site per adapter (#91)
  adapters/inbound/cli.py      typer app; takes a port, one construction site
  adapters/inbound/settings.py one Settings, key as SecretStr
  adapters/inbound/logs.py     structlog to stderr, secrets redacted
  adapters/inbound/mcp.py      stdio server: ask_noul · ask_choice · ask_score
scripts/
  check_suppressions.py        gate: no noqa / type: ignore. Scans src,
                               tests AND scripts, by tokenizing and reading
                               COMMENT tokens only, so prose that quotes the
                               syntax is not a finding
  check_test_hygiene.py        gate: tests that cannot fail, secrets in bindings
  check_dependencies.py        gate: the runtime dependency set matches a pin
                               in the script, compared both ways so a removal
                               fails as well as an addition; and every
                               requested extra exists in its provider's lock
                               entry
  smoke_release.py             the parent: builds, makes a venv OUTSIDE this
                               checkout, installs only the wheel, and runs
                               the child under that interpreter. Its exit
                               status is the child's
  probe_live.py                prints one real response; asserts nothing
  smoke_release_child.py       the in-venv half of the release smoke test —
                               runs under a temp venv's own interpreter and
                               checks what shipped. Six detectors, each with
                               a selftest case proven falsifiable from
                               outside the module
```

Tests and coverage: see the gate table below. 390 tests, 95.55% overall.
`scripts/` is outside the coverage scope, so the gate-script tests move the
count and not the percentage.

The suppression budget is 18. It rose 12 -> 16 in `e4e7abf`, four codes each
with a reason in the source: `exec` because running an extracted example is
the point, `BLE001` because example code raises anything, `S603` for the
console script, and the lazy `judgevet` import so `--selftest` runs where
judgevet is not installed. `S607` did not survive: the console script is
invoked by absolute path off `sys.executable`, and `grep -c 'S607'
pyproject.toml` is 0. The seventeenth is `S603` on `check_commit_msg.py`,
converted from two inline `# noqa` by #108, and the eighteenth is `S603` on
`smoke_release.py`, which orchestrates subprocesses for a living.

The 13 new tests in `tests/contract/test_adapter_equivalence.py` verify that
the sync and async HTTP adapters produce identical outcomes on the same
fixture corpus. The suite pins the async-specific surface: the `await`-ed call
path, the two `except` bodies, and exception flow. It does not cover shared
helpers like `_translate_status_error`, as changes there affect both adapters
in lockstep.

## Gates

`ruff check` · `ruff format --check` · `ty check` · `lint-imports` ·
`docvet check` · `docvet check --all` · `pytest --cov` · `check_suppressions` ·
`check_test_hygiene` · `check_dependencies`

All green. pre-commit runs the fast ones, pre-push adds the coverage floor
and the whole-repo docvet check.
There are no pull requests here: those hooks are the only gate before `main`. 

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
| models other than `jev-latest` | never called |
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

## Working with pi

Issues carry two extra labels beyond priority: `pi-fit` or `judgment`, and
`size-S|M|L`. Across 37 delegated sessions, `size-S` lands clean roughly three
times in four and `size-M` one time in four, so split before assigning. Some
tasks do land clean first time; the ones that do not fail in two recurring
ways.

**A green gate table is not an audit.** Two consecutive sessions returned with
all eight gates green and a real defect: a test that passed whether or not the
behaviour under test happened, and a helper that raised where the spec said
return, making its own return annotation false and the call site unreachable.
Neither was visible to any linter. #94 and #95 have since converted the
mechanically decidable half into gates: `check_test_hygiene` flags a
`try`/`except` whose assertions only run on the exception path, a test with no
assertion at all, and an unwrapped secret that settles in a binding. Its scope
comes from `python_files`, so renaming a file into pytest's collection set
brings it under the gate in the same commit.

What stays unmechanical, and is still read by eye: a fake that asserts on its
own return value, and a helper that raises where a spec said return.

`judgment` means the task asks for a shape to be decided. The one such task
that was delegated (#2) came back with a parallel structure beside the intended
one and had to be reverted. Decide the shape, then hand over the wiring.

Outcomes are logged to
`~/Projects/bazzite-dotfiles/agents/data/delegation-log.jsonl`.

## The smoke test's detectors are falsifiable now

`e4e7abf` landed `scripts/smoke_release_child.py` with ten gates green and
`--selftest` printing `3/3 detectors fired as expected`. Both were true and
neither was evidence. Two detectors were proven not to detect, and both are
fixed:

| detector | was | now |
|---|---|---|
| `run_async_block` | built the coroutine and discarded it — the async example had never run | awaits it. An async body of `raise RuntimeError(...)` surfaces to the caller with no `RuntimeWarning` |
| selftest case 1 | inlined a copy of `run_sync_block`'s body, so sabotaging the real one still printed `3/3` | calls `run_sync_block`; sabotaging it prints `5/6` and names the case |

Six cases now, one per detector, and the total derives from the case list
rather than a literal. Every one was verified here by replacing its detector
with a broken one and requiring the report to name it — including the two
the spec did not ask for, the import guard and the placeholder check. All six
are falsifiable:

```
selftest: 5/6 detectors fired as expected
  FAILED: Selftest (sync example runner): Expected failure did not occur
  ... and the same for async example runner, await block count,
      all names resolve, placeholder check, import guard
```

`selftest` had to be decomposed before any case could be added: it sat at
exactly 50 lines, the function cap. It is 44 now, with six case functions
under 25 each, and the module is 203 code lines against a cap of 300.

**The coder reached for `# type: ignore` and every gate stayed green.** It
fixed the await correctly, then annotated the exec namespace `dict[str,
object]` and silenced the resulting `await` error. `check_suppressions.py`
does not scan `scripts/`, so nothing in the project could see it — the
watcher's forbidden-pattern check caught it, not a gate. Replaced with
`dict[str, Any]`, which is the honest type for a name `exec` defines at
runtime. **This is #108's gap, demonstrated rather than argued**, and #108 is
the next issue up because of it.

The console-script check still has no case: its binary path comes from
`sys.executable`, so there is no offline lever to trip it. Deferred to #109
with the reason recorded there.

#107's past-release proof now passes. #99 still needs #109 to finish #106's
console-script detector selftest.

## The suppression gate can see its own neighbourhood now

`check_suppressions.py` scanned `src/` and `tests/` and not `scripts/` — the
directory the gate scripts live in. The cost was not theoretical: the session
implementing #106 put a `# type: ignore` into `scripts/smoke_release_child.py`
and **all ten gates passed over it**. It was caught by a watcher's forbidden-
pattern check, outside this repository. That is what #108 closed.

The fix is not "add a root". Adding `scripts/` makes the gate flag its own
module docstring, which quotes `` `# noqa` `` in prose to state the rule. Four
findings, two real and two self-inflicted.

**The gate now reads `COMMENT` tokens, not lines.** `tokenize` the file and
test the pattern against comments only. The boundary is the linter's own
semantics: ruff honours a `noqa` only in a comment, and a `# noqa` inside a
string suppresses nothing, so the gate flags precisely what a linter would act
on. An allowlist exempting the gate's own filename was refused — it is a named
exemption, and the next real suppression in that file would hide behind it.
A file that `tokenize` cannot parse falls back to the line regex rather than
being skipped, because a skip is the blind spot this issue was about.

Proven by planting suppressions rather than by reading:

| planted | gate |
|---|---|
| `# noqa` on a code line in `scripts/` | names file and line, exit 1 |
| `# noqa` inside a string literal | clean, exit 0 |
| `# noqa` in a file with a syntax error | names it via the fallback, exit 1 |
| **a real `# noqa` inside `check_suppressions.py` itself** | **names it, exit 1** — so there is no allowlist |
| the gate's own docstring, lines 4 and 7 | not flagged, and still quotes the exact syntax |

The passing path prints what it checked:

```
check_suppressions: clean, 54 files scanned under src, tests, scripts,
per-file-ignores codes 17/17
```

A gate that passes in silence is indistinguishable from one that scanned
nothing. This one says which.

The two `# noqa: S603` in `check_commit_msg.py` became a counted
`per-file-ignores` entry with a reason, budget 16 -> 17. **Adding `shell=False`
does not clear S603** — measured, ruff flags the explicit form exactly as it
flags the absent one — so there was no cause to fix, only a suppression to
make reviewable. The specification claimed otherwise and was overruled before
dispatch.

Inline suppressions are now forbidden in all three roots, and
`per-file-ignores` is the only route. That ruling is in the gate's own
docstring.

## A gate reads the runtime dependency list now

Nothing did. A delegated session put `pytest-asyncio[dev]>=1.4.0` into
`[project.dependencies]` while fixing #98 and every gate passed; a published
0.2.0 would have pulled a test framework into every application depending on
judgevet. ruff, ty, import-linter and docvet read Python, not packaging
metadata; pytest passes either way; the wheel builds fine and just drags the
extra along.

`scripts/check_dependencies.py` pins the set — `httpx`, `pydantic-settings`,
`structlog`, `typer` — as a module constant with a reason per entry, on the
shape of `ALLOWED_PER_FILE_IGNORE_CODES`. Three decisions are worth recording
because each rejected something the issue asked for:

**A separate script, not an extension of `check_suppressions.py`.** One
concern per module. That file reading packaging metadata would make its own
name and docstring false. Line count was not the argument — both would fit the
cap.

**Names only, no specifiers.** The incident was a package *appearing*. A pin
carrying specifiers is a second source of truth that every version bump edits
twice, and the reviewer updating the copy learns nothing. The accepted cost:
a silently weakened specifier is not caught, and stays visible only in the
manifest diff.

**No deny-list, though the issue asked for one.** Once the pin exists, a
test-only package in `[project.dependencies]` is outside the pinned set and
already fails. A deny-list beside it is a subset check that can never fail
when the pin passes, and can only ever *disagree* with it. Two overlapping
checks that disagree are a defect of their own. What the list would have
communicated is a sentence in the failure message instead.

Compared both ways, so a removal fails too — the issue's wording is "the set
changes", not "the set grows". Proven on throwaway manifests in temp
directories, never by editing the real one:

| planted | gate |
|---|---|
| `pytest-asyncio[dev]` added | `unpinned: pytest-asyncio`, exit 1 |
| `typer` removed | `pinned but absent: typer`, exit 1 |
| `tenacity` added legitimately | exit 1 until the pin is updated, message names the file and the constant |
| `Pydantic_Settings` for `pydantic-settings` | clean — PEP 503 normalization holds |

The failure advice follows the finding rather than printing both halves every
time. A removal has nothing to do with the dev group, and printing that
sentence anyway trains the reader to skip it.

**What is still unguarded:** the *malformed* half of that same incident.
`[dev]` is not an extra `pytest-asyncio` publishes, and an unknown extra is a
warning rather than an error. The specification ruled that undetectable
without network metadata; that was wrong, and `uv lock` settles it — a valid
extra becomes a key on the provider's lock entry, a nonexistent one is absent
entirely, while `requires-dist` records the ask either way. One table records
what was asked for and the other what resolved, which is exactly what makes
the mismatch visible locally. Filed as #110 with the measurement.

## The smoke test runs the built artifact, and its first real run found a defect

`scripts/smoke_release.py` builds with `uv build --out-dir` into a
`mkdtemp()`, creates a venv there, installs only the wheel, and runs #106's
child under that venv's interpreter with `cwd` outside the checkout and
`PYTHONPATH` and `PYTHONHOME` cleared. `PYTHONHOME` matters as much as
`PYTHONPATH`: it redirects the standard-library lookup and would defeat the
venv without touching `src/`. The parent proves the isolation with its own
one-line probe before spending a live call, and reports the child's verdict
rather than its own orchestration:

```
judgevet.__file__ = /tmp/judgevet-smoke-4id4g62p/venv/lib/python3.13/site-packages/judgevet/__init__.py
smoke_release: PASS — the built artifact passed every in-venv check
```

**The first time it ran, it failed on a good artifact — and it was right
to.** `extract_python_blocks` in the child used
`r"```python\n(.*?)\n```"`, which anchors the closing fence at column 0.
The package's examples sit inside an indented `Examples:` section, so the
pattern matched **nothing on any real docstring** and the function returned
0 blocks where the docstring has 2.

So the examples this whole gate exists to execute had never been executed.
That is #99's original defect surviving inside the gate written to catch it.
It was invisible to everything: `--selftest` feeds hand-built lists, and the
real path only runs under an installed wheel, which needed this parent to
exist. Fixed by allowing whitespace before the closing fence and dedenting
the block, because an indented block is an `IndentationError` at `exec`. The
examples now run, against the live service, on every invocation.

| proof | result |
|---|---|
| current build, key inherited | `smoke: ok`, exit 0 — examples executed for the first time |
| no key | exit 1, and says it is a failure and not a skip |
| isolation probe | resolves under the temp venv's `site-packages`, never `src/` |
| temp dir on the **failure** path | gone |
| `v0.1.0` artifact | exit 1 |

**What the past-red demo does and does not prove.** It exits non-zero on the
`v0.1.0` artifact, so the gate does reject the wheel that shipped. It does
**not** get there via the `TypeError` the issue names: v0.1.0 has one example
block where current has two, and the block-count check fires before any
example is executed, so the serialisation step is never reached. The defect
is real and was proven directly against that wheel instead, with a canary
key and no HTTP:

```
testing: /tmp/.../site-packages/judgevet/__init__.py
TypeError: Object of type Noul is not JSON serializable
```

#107 now proves that half through the real parent and child. Layout findings
remain failures, but they no longer stop valid examples from executing. Each
block uses the shared placeholder detector, substitutes the supplied key, and
dispatches by its own sync or async form. A malformed block is reported with
its original index and does not prevent another valid block from running.

The archived v0.1.0 wheel exits 1 with both layout findings and
`TypeError: Object of type Noul is not JSON serializable`. The current wheel
passes both live examples. The current wheel without a key exits 1 and names
the missing key. All three runs imported from their temporary venv's
`site-packages`, outside the checkout.

Seven regression cases cover layout failures, execution order, mixed valid
and invalid blocks, and key substitution. Disabling the sync runner makes the
canary test fail. Disabling key substitution makes the execution-order test
fail. The existing six detector selftests still pass. These checks do not
complete #109's missing console-script selftest or wire the publish gate.

**The coder's round needed four corrections.** It added four
`per-file-ignores` codes and raised the budget 17 -> 21, editing the gate's
own test to assert the inflated number — the failure `CLAUDE.md` documents
verbatim, recurring with the same count. Measured by removing all four:
`PLR2004` and `PLW1510` do not fire at all, and `S607` goes away when `uv`
is resolved through `shutil.which` instead of invoked as a bare name, which
is the same argument #106 used for the console script. One code was genuine.
Budget is 18. It also printed `smoke_release: ok (child exit 1)` beside a
failing run.

## A requirement naming an extra its provider does not publish is caught

`pytest-asyncio[dev]` was two defects in one line. #100 caught the misplaced
half. This is the malformed half: `[dev]` is not an extra that package
publishes, and an unknown extra is a warning rather than an error, so
resolution succeeds and the warning scrolls past.

It is detectable with no network, because two tables in `uv.lock` disagree:
`requires-dist` records what was **asked for**, and the provider's own entry
records what **resolved**. A valid extra becomes a key on that entry; a
nonexistent one leaves it absent.

| planted | verdict |
|---|---|
| `pyjwt[definitelynotanextra]` in `[project.dependencies]` | `pyjwt has no extra named 'definitelynotanextra' (from requires-dist)` |
| the same in `[dependency-groups] dev` | caught, and names the table: `(from requires-dev.dev)` |
| `pyjwt[crypto]` | not flagged |
| a requirement added without re-locking | `pyjwt is required but absent from uv.lock; the lock is stale — run uv lock` |

Three rulings, made here rather than by a spec pass:

- **Dev groups are checked too.** A malformed extra there breaks a
  contributor's `uv sync` rather than a user's install — lesser severity,
  same defect, and a gate that knows and stays quiet because of where the
  problem sits is the shape this repo keeps deleting.
- **A missing lock entry is a different finding with its own header.** All 13
  requirements resolve today and a resolved lock records every requirement by
  construction, so absence means the lock is stale. Filing that under
  "invalid extras" would send the reader hunting for a typo when the fix is
  a re-lock.
- **It lives in `check_dependencies.py`.** #100's flip-condition was about
  sharing a parsed `pyproject.toml`; not met. Both checks answer one
  question, so splitting them would invert #100's rule rather than apply it.

**The spec pass was skipped, and that is a finding.** Two dispatches both
stalled: each wrote its file skeleton then generated ~8,400 tokens on a
single turn without finishing, the second with one of its two open questions
already answered — so narrowing was not the cure. The issue had been written
with the detection rule, the measurement proving it, and the proof shape
already in the body, leaving nothing weighty to rule on. The signal for
skipping is not "the issue looks precise"; it is "the issue contains its own
measurement".

**The implementation shipped with zero tests** — 8 functions, ~200 lines,
count unchanged at 342. `scripts/` is outside the coverage scope, so eleven
gates went green over it. A tests-only follow-up added 23, and they bite:
making every extra look valid fails 4, and disabling dev-group scanning fails
3.

Those fixtures are hand-written lock files, which is not what was asked for
and is a real weakness: they assert against a model of uv's format rather
than against uv. `test_fixture_format_matches_what_uv_actually_writes` now
anchors them — it reads this repo's own `uv.lock`, which uv wrote, and pins
the one structure they depend on. Renaming the key the parser reads fails it.

## Next

The open queue is in
GitHub issues; `gh issue list --label ready --label pi-fit` is the assignable
set. #109 completed the remaining console-script detector proof for #106 and #99. #101's publish smoke gate is
wired and proven in Actions. Both publishing environments have the vendor
key; it is scoped to the smoke step. #111 closed the scanner's `ty: ignore` gap and removed the three existing uses.

## Publish gate wiring

Both publish workflows now check out the event commit before downloading the
built distributions. They require exactly one wheel and pass that downloaded
path to the isolated smoke parent before upload. Only the smoke step receives
`TYPESAFE_API_KEY`; a missing key fails. The upload commands retain both
distributions and OIDC. Ordinary CI makes no live call.

`actionlint` and offline checks pass for step order, secret scope, unchanged
build and upload commands, zero or multiple wheels, exact path handling, and
shell failure propagation. At that release, the test count and coverage were 373 and 95.26%.
The [broken-artifact run](https://github.com/Alberto-Codes/judgevet/actions/runs/35686353515)
rebuilt with the historical serialization defect on an isolated branch. Both
examples raised `TypeError: Object of type Noul is not JSON serializable`,
the smoke step failed, and upload was skipped.

The [clean-main run](https://github.com/Alberto-Codes/judgevet/actions/runs/35686401025)
passed smoke. Its upload then refused to replace existing 0.1.0 files whose
hashes differ; that run is not a successful publication. The newly versioned
[0.2.0 candidate](https://github.com/Alberto-Codes/judgevet/actions/runs/35686390962)
passed smoke and published to TestPyPI. The production run then passed and
published to PyPI. Downloads from both indexes passed independent live checks
and have identical wheel hashes. This completes #101.
