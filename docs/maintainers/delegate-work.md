---
status: draft
---

# Delegate a bounded change

Status: **draft**.

Use this procedure for supervised implementation in judgevet, whatever the model or harness.
The supervisor selects work, decides boundaries, verifies behaviour and commits.
The worker implements a scoped change and returns evidence.
Apply the [bounded execution limits](../../AGENTS.md#bounded-execution) before dispatch.
Use one validation path. Do not add another harness to repeat required repository checks.

## Worker harnesses

judgevet has three verified worker harnesses.
The [worker run contract](../reference/worker-runs.md) records launch evidence for each.

- **pi** runs local models through the `delegate-to-pi` skill.
- **Claude sub agents** run through the Agent tool with definitions in `.claude/agents/`.
- **Cursor CLI** runs Cursor-pool models such as `cursor-grok-4.6-medium` in print mode.
- **Codex CLI** runs `codex exec` with a named model through `scripts/harness_build.sh`. It stays unverified until a run lands.

The Claude definitions are `builder.md`, `acceptance-reviewer.md`, `specifier.md` and `ledger-auditor.md`.

| Job | Harness and model |
|---|---|
| Lookups and file search | Agent tool, `haiku` |
| Research and documentation reads | Agent tool, `sonnet` |
| Implementation and gate repairs | Agent tool, `opus` with `builder`; pi with a local coder model; Cursor CLI with a Cursor-pool model; or Codex CLI with a named model through `scripts/harness_build.sh` |
| Acceptance review | Agent tool, `opus` with `acceptance-reviewer` |
| Specification | Agent tool, `opus` with `specifier`; or pi with a local reasoning model |
| Ledger claim review | Agent tool, `opus` with `ledger-auditor` |

Read the pools with the `quota` skill before you route a mechanical slice.
Follow `.claude/skills/delegate-to-harness/SKILL.md` for the dispatch.

The `delegate-to-pi` skill names the local models and their settings.
The supervisor assigns acceptance to a fresh reviewer who authored none of the reviewed changes.
This includes authorized supervisor contributions and repairs.
No author accepts their own work. A builder never reviews its own implementation.

## 1. Make the task ready

Follow [Define and prove one deliverable](https://github.com/Alberto-Codes/judgevet/blob/main/CONTRIBUTING.md#define-and-prove-one-deliverable).
The issue is the durable task record.
Its accepted specification lives in an issue comment, never on disk.
The worker reads it with `gh issue view <N> --comments`.
A restricted worker receives the [exact evidence packet](../reference/worker-runs.md#restricted-worker-evidence).
Pass the exact comment URL in the brief. Never substitute the latest comment.

Label mechanical and machine-checkable work `pi-fit`.
That label means the work is delegable to any worker harness.
Label work that needs the orchestrating model `judgment`.

Request a read-only specification pass only when a concrete design question remains.
The `specifier` agent or a pi reasoning model can answer it.
Review its answer before implementation.
Skip that pass for a known defect with a decided fix and regression.

For behavioural changes, require a regression that fails before the fix.
Check that the failure shows missing behaviour, not a broken fixture.
Keep the test and implementation in the same deliverable and the same dispatch.

## 2. Size by behaviour

Start with one behaviour across two to four production files, plus tests and documentation.
Treat this range as an initial tuning rule, not a measured worker capability.
Split independent behaviours even when they fit in one file.
Keep an invariant together when a split would leave an unsafe intermediate state.

| Task shape | Dispatch |
|---|---|
| Decided behaviour with a failing acceptance test | Implement directly |
| Several independent behaviours or acceptance commands | Split into named slices |
| Unresolved API, port or source decision | Resolve the decision first |
| Small mechanical correction with an obvious proof | Use a short repair brief |
| Broad failure after repeated repairs | Reassess the contract and split again |

One GitHub issue need not equal one worker task.
Name the parent issue and slice in every dispatch.

## 3. Launch with a bounded brief

Use the template below. Replace every placeholder before dispatch.
Keep task context short. Link precise files and evidence instead of copying history.

Use one writer per checkout.
Record the base revision and existing modifications before launch.
Keep temporary files under the ignored `scratchpad/` directory.

For pi, inspect the installed harness help before choosing options.
For a Claude sub agent, pass `model` on every Agent call and name the agent definition.
For Cursor, supply the full evidence packet because `git` and `gh` are denied.
Planning stays read-only. Review keeps the reviewed checkout read-only.
A review brief may name an isolated scratch copy for mutations.
Implementation needs local edit and test permissions.

```text
Role: bounded implementation worker. The supervisor owns acceptance and the commit.
Supervisor / worker / harness: <actual assignments; requested model or alias>
Issue and slice: <issue number, one behaviour>
Base revision and existing modifications: <exact values>
Accepted specification: <exact issue comment URL; embed packet for restricted workers>
Validation owner: <builder by default, or supervisor for integration>
Input snapshot: <source, tests, configuration and environment evidence>
Decision and reason: <settled shape and why>
Read first: <targeted files and cited source URLs>
Allowed edits: <production, test and documentation paths>
Out of scope: <adjacent work and tempting incorrect fixes>

Acceptance:
- <observable invariant, exact command, expected result>
- <regression that must stay unchanged>
Run the acceptance test before implementation. Preserve its red output.
Do not weaken the acceptance test to obtain green output.
Run focused checks needed during edits.
The assigned validation owner runs the complete hook stages once per input snapshot.
Report required checks you did not run and their assigned owner.

Skip session bookkeeping and backlog sweeps.
Do not edit the verification ledger, CLAUDE.md or policy files unless this brief assigns them.
Do not commit, push, pass --no-verify or add a gate suppression.
Preserve unrelated changes. Do not reset, clean, stash or restore them.
If required edits exceed the allowed scope, return the missing scope.

Return: changed paths, red/green commands and output, unrun checks,
remaining gaps and your model identity. Leave the diff for review and stop.
```

### Brief checklist

Check each rule below before you dispatch a brief.

- A new docs page needs an entry in `scripts/doc_examples.json`, or the doc-example-inventory commit hook and the doc-python-examples push hook fail.
- A new root export needs an entry in `EXPECTED_EXPORTS` in `tests/unit/test_public_surface.py` and in the allowed-name set in `scripts/policy_artifact_check.py`.
- A call-site sweep covers `scripts/` as well as `src`, `tests`, `docs` and README. `ty` checks scripts too.
- A change to a message or behaviour needs a grep of `tests/` for the old message. Also grep for each assertion on the changed error, including `not in` checks. Name every file that pins the old behaviour in the allowed edits. See #223.
- Name one mechanical validation owner. The owner runs both complete hook stages under the validation rules below.
- Write each URL citation as its own short sentence in the form "Source: <url>." A parenthesised URL merges two sentences for the plain-English checker.
- A verified-table row in the verification ledger cites a recorded run, not a test name.

## 4. Accept behaviour and finish

Read the diff against the agreed scope.
Assign a fresh reviewer who authored none of the reviewed changes.
Give the reviewer both the accepted contract and the parent consumer outcome.
The reviewer challenges each through real public interfaces, not a fake's return values.
For Python probes, record the imported package path and prove it belongs to the tested snapshot.
An internal helper probe alone does not establish a consumer outcome.

Require a relevant negative probe or an executed mutation that detects the defect.
A claimed mutation without its observed failure is not proof.
For policy changes, inspect the operative instructions and exercise a real bounded task.
Do not substitute text-matching tests for semantic acceptance.

### Validation ownership

The brief assigns one mechanical validation owner per input snapshot.
The builder owns it by default. The supervisor may own integration validation instead.
Other roles use the owner's evidence and run only probes needed for their assigned claims.
The owner runs `uv run pre-commit run --files <changed files>` and
`uv run pre-commit run --hook-stage pre-push --files <changed files>`.
Include every changed file. Do not narrow scope to avoid a failure.
These complete stages cover the [gate inventory](../../AGENTS.md#build-and-gates).
Do not also run each covered table command by hand.
Actual commit, commit-message and push hooks remain mandatory.

Record commands, outputs, owner and tested snapshot with the evidence.
A snapshot includes the base revision, diff and untracked task inputs.
Record relevant source, tests, configuration, dependency and environment inputs.
Compare these inputs before reusing a passing result.
A matching HEAD alone cannot prove freshness for an uncommitted diff.
Never reuse evidence from another package location or changed relevant inputs.

A repair invalidates the checks whose inputs it changes.
Rerun those checks and record why any retained results still apply.
If impact is uncertain, the owner reruns the complete stages.
A hook that changes a file creates a new snapshot; validate that result.
Never run validation while another actor mutates the tested checkout.
Record unrun, stale and failed checks explicitly. Never call them green.

### Isolated failure proof

Keep the reviewed checkout unchanged throughout acceptance.
The review brief names a unique scratch directory under `scratchpad/`.
Only that assigned copy may receive review mutations.
Copy the tested snapshot and record its origin before changing it.
Do not share mutable source, tests, configuration or generated files with the reviewed checkout.
Verify the imported package path inside the scratch copy before the probe.
Run the unmutated probe, then the mutation, then record the expected failure.
Keep mutation evidence distinct from validation of the accepted snapshot.
Do not run gates against a copy another actor is mutating.
Scratch permission never permits edits to the reviewed checkout or unrelated files.

### Review dispositions and continuation

| Disposition | Meaning |
|---|---|
| Accepted | Every required assertion has current independent evidence; no blocking finding or required check remains open |
| Rejected | Evidence contradicts a required assertion; name the failing input, impact and correction |
| Incomplete | Required evidence is missing, stale, blocked or outside the review budget; acceptance is unproven |

Start acceptance review with eight tool calls or three minutes, whichever comes first.
At the boundary, return verified claims, findings and outstanding assertions separately.
Budget exhaustion means incomplete, never accepted.
The supervisor may continue that review with an explicit budget and only its outstanding assertions.
Reuse current evidence. Do not restart a full review merely because the first budget ended.
Before exceeding the repository dispatch limits, name the unresolved assertion and why another dispatch can settle it.

Return a demonstrated defect with a narrow repair brief.
The default is one repair dispatch per behaviour under the bounded execution rules.
After repair, the independent reviewer checks the repair and affected claims against the new snapshot.
Retain unaffected evidence only under the freshness rules above.
If the supervisor authors a change, assign fresh acceptance to a reviewer who authored none of it.
Never treat supervisor confidence or mechanical gates as independent acceptance.

Workers return their assigned deliverable and stop.
The supervisor continues authorized slices until the parent goal's stopping condition.
The supervisor publishes each accepted deliverable directly to `main` through required hooks.
The commit carries factual trailers from reported identities.
Passing tests do not authorize a live API call.

## 5. Record outcomes and tune

Record proof and remaining work on the issue.
Keep one record per slice. Link the commit instead of copying its evidence.

| Field | Evidence |
|---|---|
| Identity | Issue, slice, base revision, supervisor, worker model, harness and session identifier |
| Input | Accepted specification, planning or implementation |
| Size | Behaviour count, production files, tests and documentation |
| Cost | Elapsed time, reported tokens if available, supervisor repair time |
| Outcome | Accepted, rejected or incomplete; repair disposition and any external blocker |
| Proof | Red and green output, public probe and import origin, negative or mutation result, gate owner and freshness, reviewed and accepted snapshots |
| Lesson | Specification, implementation, test, harness, environment or external failure |

Compare accepted behaviour and supervisor repair time, not lines written or worker confidence.
Group measurements by model, harness, reasoning setting, task type and size.
Treat unavailable measurements as unknown. Do not combine unlike token counters.
Separate external blocking from implementation failure.
Persist recurring rules here. Keep task facts in the accepted contract.
