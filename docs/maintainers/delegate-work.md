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

The Claude definitions are `builder.md`, `acceptance-reviewer.md`, `specifier.md` and `status-auditor.md`.

| Job | Harness and model |
|---|---|
| Lookups and file search | Agent tool, `haiku` |
| Research and documentation reads | Agent tool, `sonnet` |
| Implementation and gate repairs | Agent tool, `opus` with `builder`; pi with a local coder model; or Cursor CLI with a Cursor-pool model |
| Acceptance review | Agent tool, `opus` with `acceptance-reviewer` |
| Specification | Agent tool, `opus` with `specifier`; or pi with a local reasoning model |
| STATUS claim review | Agent tool, `opus` with `status-auditor` |

The `delegate-to-pi` skill names the local models and their settings.
The supervisor never spawns a sub agent to verify its own work.
The supervisor never asks a worker to double-check itself.
An acceptance review runs in a fresh agent, separate from the builder.

## 1. Make the task ready

Follow [Define and prove one deliverable](https://github.com/Alberto-Codes/judgevet/blob/main/CONTRIBUTING.md#define-and-prove-one-deliverable).
The issue is the durable task record.
Its accepted specification lives in an issue comment, never on disk.
The worker reads it with `gh issue view <N> --comments`.
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
For Cursor, paste the full contract into the brief, because `gh` is denied to the worker.
Planning and review stay read-only. Implementation needs local edit and test permissions.

```text
Role: bounded implementation worker. The supervisor owns acceptance and the commit.
Supervisor / worker / harness: <actual assignments; requested model or alias>
Issue and slice: <issue number, one behaviour>
Base revision and existing modifications: <exact values>
Accepted specification: <exact issue comment URL>
Decision and reason: <settled shape and why>
Read first: <targeted files and cited source URLs>
Allowed edits: <production, test and documentation paths>
Out of scope: <adjacent work and tempting incorrect fixes>

Acceptance:
- <observable invariant, exact command, expected result>
- <regression that must stay unchanged>
Run the acceptance test before implementation. Preserve its red output.
Do not weaken the acceptance test to obtain green output.
Run focused checks during edits, then the CLAUDE.md gate table.
Report required checks you did not run.

Skip session bookkeeping and backlog sweeps.
Do not edit STATUS.md, CLAUDE.md or policy files.
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
- Every builder runs `uv run pre-commit run --files <changed files>` at the commit stage and again with `--hook-stage pre-push` before returning, because the hand-run rows do not run every hook.
- Write each URL citation as its own short sentence in the form "Source: <url>." A parenthesised URL merges two sentences for the plain-English checker.
- A verified-table row in STATUS.md cites a recorded run, not a test name.

## 4. Accept behaviour and finish

Read the diff against the agreed scope.
Run an independent probe of the defining behaviour.
Test real production behaviour, not a fake's own return values.
Confirm that the regression can detect the original defect.

The gate inventory is the gate table in the [repository rules](../../AGENTS.md#build-and-gates) and `.pre-commit-config.yaml`.
Never weaken a gate or report an unrun gate as green.

Return a failed assertion and a narrow correction brief when review finds a defect.
After two unsuccessful repairs of the same defect, reassess the contract.
Preserve the useful diff and evidence during reassessment.

The supervisor publishes by committing directly to `main`.
The commit carries factual trailers from the worker's reported identity.
The pre-commit and pre-push hooks are the gate before the branch.
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
| Outcome | Accepted unchanged, accepted after repair, rejected or externally blocked |
| Proof | Red and green output, independent probe, gate results, accepted commit |
| Lesson | Specification, implementation, test, harness, environment or external failure |

Compare accepted behaviour and supervisor repair time, not lines written or worker confidence.
Group measurements by model, harness, reasoning setting, task type and size.
Treat unavailable measurements as unknown. Do not combine unlike token counters.
Separate external blocking from implementation failure.
Persist recurring rules here. Keep task facts in the accepted contract.
