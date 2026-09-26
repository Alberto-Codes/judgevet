---
status: draft
---

# Worker run contract

Status: **draft**.

This contract separates project requirements from the model and harness that run them.
The [delegation procedure](../maintainers/delegate-work.md) holds the task sequence and acceptance rules.

## Roles

| Role | Responsibility |
|---|---|
| Supervisor | Select work, settle decisions, own acceptance and commit to `main` |
| Specifier, when needed | Propose a bounded decision and executable contract; report uncertainty and evidence |
| Worker | Implement the assigned contract within its allowed paths and return evidence |
| Reviewer | Check the actual diff and independently exercise the defining behaviour |

Roles need not use different model families. A model name alone does not establish independent review.
The reviewer uses production evidence and independent probes, not the worker's completion claim.
Every change needs a fresh reviewer who authored none of it, including supervisor contributions.
No author accepts their own work. Follow the shared [acceptance rules](../maintainers/delegate-work.md#4-accept-behaviour-and-finish).
Changing models never expands permissions or authorizes a live API call.

## Harness boundary

judgevet has three verified worker harnesses.
pi runs local models through the `delegate-to-pi` skill.
Claude Code sub agents run through the Agent tool with definitions in `.claude/agents/`.
The Cursor CLI runs Cursor-pool models in print mode; #49 was its first accepted slice.
Choose the worker independently from the supervisor.

| Harness | Required launch evidence |
|---|---|
| pi | Installed version, provider/model, effective `--thinking` setting, instruction loading, tool permissions, session identifier |
| Claude sub agent | Requested alias (`haiku`, `sonnet` or `opus`), resolved model ID from the agent's return or `unknown`, effort, allowed tools, agent definition name |
| Cursor CLI | Installed version, requested model ID, identity the worker reports or `unknown`, `session_id` and usage from the JSON receipt, `.cursor/cli.json` deny list |
| Any other harness | The same role, context, isolation, observation and return requirements |

Read installed help and configuration before constructing a pi launch command.
Do not copy flags, approval modes or token limits between harnesses.
Keep planning read-only and the reviewed checkout unchanged.
A review brief may assign an isolated scratch directory for failure proofs.
Follow the shared [scratch rules](../maintainers/delegate-work.md#isolated-failure-proof).
Implementation needs only the permissions its assigned edits and checks require.

Launch a Cursor worker from the checkout root with the brief as the prompt:

```bash
cursor-agent -p --force --trust --output-format json \
  --model cursor-grok-4.6-medium "$(cat brief.md)" > receipt.json
```

`--force` applies edits without prompting, so `.cursor/cli.json` is the only guard.
It denies `git`, `gh`, `rm`, the policy files and the credential files.
Pass only `cursor-grok-*`, `grok-*`, `composer-*` or `gemini-*` IDs.
Other IDs and `auto` bill the Anthropic and OpenAI pool instead.
A `resource_exhausted` error before any edit is a service failure. Retry once.

A requested alias such as `opus` is not a resolved model identity.
Record both the requested alias and the resolved identity the agent reports.
If the harness does not expose the identity, record `unknown` rather than guessing.

## Restricted-worker evidence

Cursor cannot run `git` or `gh` under the repository deny list.
The supervisor supplies this packet before dispatch:

- The exact accepted issue comment URL and full contract text, plus the parent consumer outcome.
- The baseline commit and staged, unstaged and relevant untracked state.
- The relevant source and diff artifacts, with paths and content hashes for the tested snapshot.
- The validation owner, existing command outputs and their input snapshot.

Keep the issue comment authoritative. The embedded copy is a transport for that contract.
Record when the supervisor captured the packet and which revision it describes.
The worker compares available file contents with the packet before relying on it.
Missing or stale inputs mean an incomplete return naming the required evidence.
The supervisor refreshes the packet before work resumes.
Do not broaden permissions, remove deny rules or change user configuration to obtain evidence.
If a denied action is necessary, the supervisor performs it within the authorized scope.

All harnesses must report actual instruction loading and effective tool permissions.
A role prompt is not a sandbox. Do not claim isolation the harness does not enforce.
Record the harness actually used, even when a role definition came from another harness.

## Commit trailers

Trailers are evidence. This repository is partly an evaluation of its workers.

- A pi-written commit carries `Generated-By: <model> (local, via pi)`.
- A Claude sub agent commit carries `Generated-By: <resolved model id> (via Claude Code Agent tool, <agent name>)`.
- A Claude sub agent specification carries `Specified-By: <resolved model id> (via Claude Code Agent tool, specifier)`.
- A Cursor worker commit carries `Generated-By: <requested model id> (via Cursor CLI <version>, print mode)`.
- The supervisor's own commits carry no `Generated-By` trailer.
- Never invent a resolved ID. The ID comes from the agent's return, never from the requested alias.

## Run receipt

Keep this information in the issue acceptance record.
Do not introduce a second ledger that duplicates it.

| Field | Meaning |
|---|---|
| Assignment | Issue, slice, accepted comment, supervisor, worker role and allowed paths |
| Baseline | Base revision, staged and unstaged diff, relevant untracked inputs and acceptance-test revision |
| Configuration | Harness and version, requested and resolved model, effort or reasoning setting, loaded instructions and effective tool permissions |
| Observation | Session or agent identifier, start and end times, output location and final exit state |
| Outcome | Accepted, rejected or incomplete; reviewed and accepted snapshots, reviewer identity, public probe and import origin, negative or mutation evidence, repairs and gaps |
| Validation | Assigned owner, commands and outputs, relevant source, tests, configuration and environment inputs, freshness and invalidated evidence |
| Cost | Elapsed time, supervisor repair time, and reported tokens with their source |

Use the shared [validation and disposition rules](../maintainers/delegate-work.md#validation-ownership).
Report each unavailable usage counter as `unknown`, separately from available counters.
Never combine unlike token counters.

Record factual contributions separately when different models specify and implement a change.
Do not attribute supervisor corrections to the worker.
Store concise redacted evidence. Raw logs stay local unless checked and authorized for publication.
Never include `TYPESAFE_API_KEY` or environment dumps in briefs, receipts or issue comments.

## Preserve the baseline

Use one writer per checkout. Record HEAD and staged and unstaged changes before dispatch.
Record untracked task files the worker could overwrite, including files under `scratchpad/`.

After the worker stops, compare the baseline and the returned diff.
A clean final tree does not prove safety.
A worker can discard an earlier uncommitted change and leave no diff.
Investigate missing or unexpectedly restored files before accepting the run.
Check for an unexpected HEAD change, including a commit the brief forbade.
Do not restore files automatically while another actor may be editing them.

## Observe completion and classify failure

A launch command, live process, idle log or zero exit code alone does not prove completed work.
Confirm the final output, changed files and acceptance evidence.
Do not terminate another session or launch a competing writer because a log is silent.

| Failure class | Supervisor action |
|---|---|
| Specification | Correct the accepted contract; do not blame faithful implementation |
| Implementation | Return the failing input and expected behaviour as a bounded repair |
| Acceptance test | Repair the fixture or oracle without weakening the intended behaviour |
| Harness or configuration | Diagnose launch, model resolution, permissions, reasoning setting and completion state |
| Environment | Name the unavailable dependency or service and repair it within scope |
| External dependency | Record the blocking event and continue independent authorized work |

Do not shrink every task in response to a harness fault.
Do not call a tool failure a model-quality failure, or a missing metric a zero-cost run.
A regression needs a demonstrated failure on the defect or a deliberate local mutation.

## Change a model or harness with evidence

Start a replacement on one small slice with a known acceptance oracle.
Check that it loads instructions, uses permitted tools, preserves the baseline and reports completion.
Run the same acceptance contract and required gates used for the current worker.
Record repairs and configuration before expanding its scope.
One successful slice establishes compatibility for that slice, not general reliability.

Reuse existing tests and real issue slices. Do not build a benchmark project first.
Update the launch recipe when a recurring failure is specific to the harness.
Update shared policy only when the lesson applies across tasks and models.
Keep machine-specific paths, credentials and process identifiers out of shared policy.
