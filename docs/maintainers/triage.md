---
status: draft
---

# Triage issues

Status: **draft**.

Use this procedure to read a filed issue and give it a state, a priority,
a fit and a size. The labels drive every view. There are no sprints and no
boards to maintain. Ported from the gepa-adk project-management page on
2026-10-20 and adapted to this repository's rules.

- Labels are metadata. A saved search slices them; nobody moves cards.
- A blocker that is an issue is a GitHub native `blocked by` relation.
  The `blocked` label covers blockers that are not issues.
- Work is release-driven. Work P1 and P2 until empty, release, then re-read P3.

## Priority

Priority measures impact, not urgency. The scale is shared with gepa-adk.

| Label | Meaning |
|---|---|
| `P1` | Wrong output, a leaked secret, or a claim the repo cannot support |
| `P2` | An output a session or Alberto reads and acts on is wrong |
| `P3` | The record, the process, a gate, or a capability |
| `P4` | Drift and nits |

An issue with no `P` label is ungroomed.

## Fit and size

Fit says who does the work. Size says whether a worker can take it whole.
Both follow [size by behaviour](delegate-work.md#2-size-by-behaviour).

| Label | Meaning |
|---|---|
| `pi-fit` | Mechanical and machine-checkable. Delegate to any worker harness. |
| `judgment` | Needs the orchestrating model: design, verdicts, done-ness |
| `size-S` | One file, one gate. A worker run under about 10 minutes. |
| `size-M` | A few files behind one acceptance check. About 10 to 25 minutes. |
| `size-L` | Too big to delegate whole. Split before assigning. |

## State

| Label | Meaning |
|---|---|
| `needs-triage` | Filed, not yet read by Alberto |
| `question` | A decision or a missing fact must be settled before work can start |
| `ready` | An accepted definition of ready and done sits in an issue comment |
| `blocked` | Waits on a named commit, key, release or date; the body names it |

`ready` is the definition of ready. An issue earns it when a comment records
the decision, the necessary evidence, the allowed repairs and the stopping
condition. [Bounded execution](../../AGENTS.md#bounded-execution) keeps that
comment under 150 words. The `specifier` agent writes that comment when the brief authorizes
posting. The supervisor may write it directly. A `P` label alone does not make
an issue ready.

Issues labelled `ready` before 2026-10-20 may lack that comment. A session that
pulls one posts the comment first, then starts.

`blocked` is a label because the native `is:blocked` filter sees only
issue-to-issue relations. Use both: the label for a release, a credential or a
date, and the native relation for another issue.

## Status is inferred

| Status | How it is determined |
|---|---|
| Ungroomed | No `P` label, or `needs-triage` |
| Triaged | Has `P`, fit and size labels, no contract comment yet |
| Ready | Has `ready`, no assignee, not blocked |
| In progress | Assigned to someone |
| Blocked | Has `blocked`, or a native `blocked by` relation |
| Done | Closed |

## Searches

`-l` alone cannot see native relations. Every actionable query goes through
`--search` with `-is:blocked`.

```bash
# dispatchable now
gh issue list --search "is:open label:ready -label:blocked -is:blocked no:assignee"
# wrong outputs and wrong records, specify next
gh issue list --search "is:open label:P1,P2 -label:blocked -is:blocked"
# work a worker harness can take whole
gh issue list --search "is:open label:pi-fit -label:size-L -label:blocked -is:blocked"
# split before assigning (inventory, so blocked issues stay in)
gh issue list -l size-L
# untriaged
gh issue list --search "is:open -label:P1 -label:P2 -label:P3 -label:P4"
```

## Groom an issue

1. Read the issue. Treat its claims as a hypothesis until they reproduce.
2. Ask the local judgment backend before labelling. Ask the readiness Choice
   and the size and priority Scores, with the label definitions above copied
   into `criteria`. Record each answer beside your own decision in the triage
   comment, for example `judgevet-gemma: size-M (0.91)`. The answer is advisory.
   Confidence is not accuracy; see
   [measured agreement](../how-to/use-in-an-agent-harness.md).
3. Add one `P` label by impact, one fit label and one size label.
4. Add `blocked` and name the blocker in the body, or add a native relation.
5. To make it `ready`, post the definition of ready and done, then add `ready`.

## Release cycle

1. Work until the P1 and P2 search is empty, epics excepted.
2. Release.
3. Re-read every open P3. Promote one whose impact grew to `P2`.
   Demote one that turned into drift to `P4`.
4. Check the untriaged search for anything missed.

## Dependencies

GitHub supports native issue dependencies. See
[the GitHub documentation](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-dependencies-to-issues).

```bash
R=repos/Alberto-Codes/judgevet
# read the blockers of issue N
gh api $R/issues/N/dependencies/blocked_by --jq '[.[].number]'
# the numeric id of the blocking issue B, which the add call needs
gh api $R/issues/B --jq .id
# add one
gh api -X POST $R/issues/N/dependencies/blocked_by -F issue_id=<id of B>
```

Verified on 2026-10-20 against this repository: the add call returned the
relation and the read call listed it.

GitHub refuses a cycle and a duplicate, so read before you add. The relation
moves no label. When a blocker lands, the supervisor checks each dependant and
flips it to `ready` only when every prerequisite holds.

## Maintenance

| Task | When |
|---|---|
| Groom new issues | At the start of a session |
| Review blocked issues | Weekly |
| Re-prioritize P3 | After each release |
