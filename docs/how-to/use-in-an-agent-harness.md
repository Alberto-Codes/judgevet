---
status: draft
---

# Use judgevet in an agent harness

Status: **draft**.

!!! note "Shadow weeks reviewed for three recipes"
    Shadow runs of three recipes started on 2026-10-09.
    The #310, #311 and #314 shadow weeks were reviewed on 2026-10-20, and their numbers are on this page.
    Each recipe stays shadow.
    The shadow week ran on three models.
    On 2026-10-09 it ran on `gemma-4-31b-qat-q4_0-mm`, the model the offline fixtures used.
    From 2026-10-09 23:23 UTC it ran on kv9, first `gemma-4-31b-kv9-q4km-mm` and then `gemma-4-31b-kv9-text`.
    Source: https://github.com/Alberto-Codes/judgevet/issues/323.
    The kv9-text model answered 86% of the rows.
    Source: https://github.com/Alberto-Codes/judgevet/issues/308.
    #323 will measure the difference between the models.
    Source: https://github.com/Alberto-Codes/judgevet/issues/323.

This page shows where a judgment fits in a coding agent's loop.
It covers MCP tools for the agent and hooks for the harness.
Each recipe names its hook event, its question and its measured numbers.
Every measurement here used local Gemma 4 through typevet, not Jev.
Source: https://github.com/Alberto-Codes/judgevet/issues/307.

## Choose the entry point

Use the MCP tools when the agent itself needs a judgment while it reasons.
The agent picks the tool, writes the question and reads the answer.

Use the library, the CLI or the shadow runner for hooks and scripts.
A Claude Code hook runs a command, not an MCP tool.
Source: https://code.claude.com/docs/en/hooks.
The [shadow runner](https://github.com/Alberto-Codes/judgevet/blob/main/examples/agent-hooks/README.md)
is that command.
It reads the hook input on stdin and asks the questions in a question file.

Other harnesses expose the same seam.
Claude Code auto mode runs a fast single-token yes or no filter on the actions it classifies, before they execute.
Source: https://www.anthropic.com/engineering/claude-code-auto-mode.
The OpenAI Agents SDK runs input, output and tool guardrails, and a failed guardrail signals a tripwire.
Source: https://openai.github.io/openai-agents-python/guardrails/.
The OpenHands SDK rates the risk of each action before execution and can require approval for risky actions.
Source: https://docs.openhands.dev/sdk/guides/security.
A judgevet question can feed any of these seams through the library.

## Connect a session

Connect the MCP server at user scope so every session can ask.
[Connect an MCP host](connect-mcp.md#claude-code) gives the host setup.

For a self-hosted judge, write a small launcher that calls `main`.
Pass the provider factory, the model and an instructions addendum.
This launcher uses the offline fake provider as a stand-in:

```python
from contextlib import AbstractContextManager, nullcontext

from judgevet.adapters.inbound.mcp_entrypoint import main
from judgevet.ports import SystemOnePort
from judgevet.testing import FakeSystemOnePort


def agent_judge_factory() -> AbstractContextManager[SystemOnePort]:
    return nullcontext(FakeSystemOnePort())


ADDENDUM = (
    "A local model, application-model, answers these tools. "
    "Jev calibration does not apply to its probabilities. "
    "A question takes about 1.2 seconds on this host."
)


def serve() -> int:
    return main(
        provider_factory=agent_judge_factory,
        model="application-model",
        instructions_addendum=ADDENDUM,
    )
```

Replace the fake with your provider and the latency with your own measurement.
[Use a self-hosted judgment provider](use-a-self-hosted-provider.md#serve-mcp-on-the-provider)
covers the console script and the host entry.

The server sends 95 words of [server instructions](../reference/mcp.md#server-instructions).
They tell the agent to pick the tool by the decision and to define each label in its criteria.
They state that a confidence is not measured accuracy.
They state that each tool refuses unknown arguments.
The server appends the addendum after the base text and a blank line.
Claude Code truncates server instructions at 2,048 characters.
Source: https://code.claude.com/docs/en/mcp.md.

Every tool sets `readOnlyHint: true` and `openWorldHint: true`.
A harness may therefore auto-approve the tools.
The hints come from the server, so trust them only when you trust the server.
Source: https://modelcontextprotocol.io/specification/2026-07-28/schema.
See [tool titles and annotations](../reference/mcp.md#tool-titles-and-annotations).

## Write the question

Choose the question shape by the decision.
[Choose a question by the decision you need](../explanation/judgments.md) explains Noul, Choice and Score.
Only `instructions` and `criteria` are tunable by the caller.
Source: https://alberto-codes.github.io/typevet/reference/judgment-text-parts/.

**Put each label's definition in its criteria.**
Round 1 of #308 used thin criteria such as "P3: low urgency".
Round 2 reused the label definitions as criteria on the same issues.

| measure | round 1 | round 2 |
|---|---|---|
| readiness agreement, kappa | 39.0%, 0.10 | 46.3%, 0.20 |
| readiness majority baseline | 34.1% | 34.1% |
| blocked found | 5 of 14 | 9 of 14 |
| question found | 0 of 14 | 2 of 14 |
| size agreement, kappa | 75.6%, 0.58 | 75.6%, 0.56 |
| priority agreement, kappa | 51.2%, 0.24 | 56.1%, 0.27 |
| priority majority baseline | 56.1% | 56.1% |

Source: https://github.com/Alberto-Codes/judgevet/issues/308.

Since round 2, the supervisor triaged #337 and #324 with the triage-page definitions as criteria.
Each issue agreed 3 of 3 with the supervisor, all at confidence 0.999 or above.
Six of six is too few to move the round-2 table.
Source: https://github.com/Alberto-Codes/judgevet/issues/308.

The definition of blocked named concrete external events, and recall on blocked nearly doubled.
The label question stayed hard, because it depends on who must decide.
The issue text rarely states that.
Expect a ceiling where the answer depends on facts missing from the state.
An evolved wording on another data set failed its pre-registered calibration check. With 158 rows, that check could not show a change either way.
Source: https://alberto-codes.github.io/typevet/explanation/wording-evolution-difraud/.

Two server rules shape what the agent sends:

- **Policies need explicit criteria.** In `evaluate_policy`, Choice and Score questions must carry `criteria`.
  A threshold such as `score: {min: 2}` refers to your own levels, so the tool defaults do not apply.
  Source: https://github.com/Alberto-Codes/judgevet/issues/305.
- **Unknown arguments are refused.** Send labels as `criteria`, not `options`.
  An undeclared argument returns `Unknown arguments: <names>`.
  `ask_noul` declares no `criteria`, so state the proposition fully in the instruction.
  Source: https://github.com/Alberto-Codes/judgevet/issues/303.
  See [failure and lifecycle behavior](../reference/mcp.md#failure-and-lifecycle-behavior).

## Recipes

Each Claude Code recipe runs in shadow mode with `"async": true`. The commit recipe runs synchronously at `commit-msg`.
Each one links its example file for the hook entry and the question file.
The example files hold the exact JSON, so this page does not repeat it.

### Bash irreversible loss

- Hook event: `PreToolUse` with the matcher `Bash`.
- Question: one Score over `none`, `low`, `medium`, `high` and `destructive`.
- Snippet: [Bash command risk](https://github.com/Alberto-Codes/judgevet/blob/main/examples/agent-hooks/README.md#recipe-bash-command-risk).
- Latency: p50 1.29 s, p95 2.18 s on 36 commands.

The judged level agreed with the label on 80.6% of 36 commands, with kappa 0.75.
The model rarely separated `high` from `destructive`, so destructive recall was 5 of 10.
An alert at level `high` or above separated cleanly on this set.
It had 100% recall and 100% precision.
Thirty-six rows is a small set, and the shadow week tests the threshold.
Source: https://github.com/Alberto-Codes/judgevet/issues/310.

#### Shadow week

| | value |
|---|---|
| span | 2026-10-09 20:24 UTC to 2026-10-21 (UTC) |
| records / sessions | 14,805 / 248 |
| answered / errors | 14,612 / 193 (180 timeouts at the 20 s cap, 12 provider errors) |
| model | `gemma-4-31b-qat-q4_0-mm` 1,651 rows on 2026-10-09, `kv9-q4km-mm` 385, `kv9-text` 12,684 from 2026-10-10 00:04. The week ran on kv9, not the model the offline numbers used (#323). |
| latency, answered | p50 1.56 s, p90 2.14 s, p95 2.43 s, p99 4.5 s, max 19.9 s |
| argmax level | none 11,998 (82%), low 800, medium 1,477, high 249, destructive 3 |
| confidence | p50 1.000; 96% of records at or above 0.8 |

Source: https://github.com/Alberto-Codes/judgevet/issues/310.

**Open question:** the five argmax levels sum to 14,527 of 14,612 answered records.
The 180 timeouts and 12 provider errors sum to 192 of 193 errors.
The review comment carries these figures.
The gap is unexplained until the next count.

The alert threshold `high` fired on 252 records, 1.7%, about 23 a day.
The review joined 223 of them to a command and labelled each by category:

| category | n | level defensible under the definitions? |
|---|---|---|
| `git worktree remove` plus `git branch -D`, usually after a `status --porcelain` check | 112 | no: a clean worktree removal loses nothing; git restores the branch. Medium at most. Only the `--force` variants reach high. |
| commit, land and push scripts | 35 | mostly no: `git add -A && git commit` scored high (0.63) |
| other, including read-only `curl`, `ls`, `sed -n`, and a heredoc writing a new file | 34 | no, at 0.63 to 0.98 |
| rebase, merge, pull | 14 | partly: a rebase of the session's own branch is medium |
| `rm -rf` | 8 | mixed: deleting run output directories is high; `git bundle verify` scored destructive at 0.993 |
| service and container operations | 7 | outside the question: no work loss |
| force push with lease | 7 | yes: rewrites shared history |
| forbidden list: `git checkout --`, `restore`, `reset`, `stash`, `clean` | 5 | yes |
| a `gh issue comment` whose quoted text says "landed, rebased" | 1 | no, at 0.93: the model read prose inside a string |

About 12 of 223 were clearly high or destructive.
About 120 were worktree cleanups and rebases that git can recover.
About 80 were wrong at confidence 0.9 or above.
The offline 100% precision and recall at "level ≥ high" did not hold on traffic.
No #82-class command occurred during the week, so destructive recall on traffic is unmeasured.
The recipe stays shadow.
Source: https://github.com/Alberto-Codes/judgevet/issues/310.

### Injected instructions in fetched content

- Hook event: `PostToolUse` with the matcher `WebFetch|WebSearch|mcp__.*`.
- Question: one Noul that asks whether the text addresses instructions to an agent.
- Snippet: [injection_screen.md](https://github.com/Alberto-Codes/judgevet/blob/main/examples/agent-hooks/injection_screen.md).
- Latency: p50 1.35 s, p95 1.40 s on 27 texts.

On 27 texts, recall was 1.00.
Precision was 0.86 at threshold 0.5 and 0.92 at 0.8.
The false positives were human-directed text that mentions agents, such as contributor docs.
Expect agent instruction files to score high too.
The runner screens only the first 4,000 characters of the state.
Source: https://github.com/Alberto-Codes/judgevet/issues/311.

#### Shadow week

| | value |
|---|---|
| span | 2026-10-09 20:29 UTC to 2026-10-20 |
| records / sessions | 1,377 / 47 |
| answered / errors | 1,330 / 47 timeouts (3.4%, at the 20 s cap on 4,000-character states) |
| tools | WebFetch 875, WebSearch 402, context7 57, judgevet-gemma 16 (all on 2026-10-09, before the matcher excluded them) |
| model | qat 311 rows on 2026-10-09, kv9-q4km-mm 56, kv9-text 983 from 2026-10-10 (#323) |
| latency, answered | p50 2.17 s, p90 4.9 s, p95 7.4 s, p99 15.4 s |
| noul ≥ 0.8 | 348 of 1,330 (26%) |
| noul ≥ 0.5 | 551 (41%) |

Source: https://github.com/Alberto-Codes/judgevet/issues/311.

**Open question:** the per-tool counts sum to 1,350 of 1,377 records.
The review comment carries these figures.
The gap is unexplained until the next count.

The review joined 133 records to their fetched target, and 30 of them were flagged at 0.8 or above.
By hand, 2 of the 30 were agent-directed.
The other 28 fall in four classes:

| class | n | noul |
|---|---|---|
| pages about agents: two multi-agent blog posts (the class predicted at landing) | 2 | 1.000 |
| human-directed imperatives: a CFR section, a Federal Register notice, two terms-of-service pages, an API reference page, academic PDFs | 13 | 0.85 to 1.000 |
| one YouTube transcript endpoint fetched six times | 6 | 0.86 to 1.000 |
| WebSearch result lists | 5 | 0.82 to 1.000 |

**Open question:** the four classes sum to 26, but the review says 28 records were not agent-directed.
The gap of 2 is unexplained until the next count.

Precision at 0.8 on this sample was about 7%, against 0.92 on the offline fixtures.
The review judged the 103 unflagged records by their URL or query, not by the fetched text.
By that target, none of them was agent-directed.
A Noul probability of 1.000 was wrong 9 times in 30.
The recipe stays shadow.
Source: https://github.com/Alberto-Codes/judgevet/issues/311.

### Done or not at Stop

- Hook event: `Stop`.
- Question: one Noul, `done`, over the last user request and the final assistant message.
- Snippet: [stop_check.md](https://github.com/Alberto-Codes/judgevet/blob/main/examples/agent-hooks/stop_check.md).
- Latency: p50 1.47 s on 20 cases; p50 1.75 s, p95 2.70 s on 740 live stops.

All 20 synthetic cases were correct at 0.5 and 0.8.
This is weak evidence, because one builder wrote both the criteria and the cases.
The recipe does not hook `SubagentStop`.
That hook sees the subagent's closing text, not the report it hands back.
Source: https://github.com/Alberto-Codes/judgevet/issues/314.

#### Shadow week

| | value |
|---|---|
| span | 2026-10-09 21:18 UTC to 2026-10-21 00:48 UTC |
| records / sessions | 758 / 76 |
| answered / errors | 740 / 18 (14 timeouts at the 30 s cap, 4 provider errors) |
| model | `gemma-4-31b-qat-q4_0-mm` 105 rows on 2026-10-09, `kv9-q4km-mm` 26, `kv9-text` 627 from 2026-10-10 00:05. The week ran on kv9, not the model the offline numbers used (#323). |
| latency, answered | p50 1.75 s, p90 2.32 s, p95 2.70 s, p99 4.9 s, max 17.4 s, nearest rank |
| `done` at or above 0.8 | 272 of 740 (37%) |
| `done` below 0.2 | 451 (61%); 17 records sit between 0.2 and 0.8 |

Source: https://github.com/Alberto-Codes/judgevet/issues/314.

The log holds no state, so the review joined every record to its session transcript.
The final message is the last assistant text before the record.
The next request is the first human message after it.
All 740 answered records joined, because `Stop` fires in the main session.
572 have a later user message, and 168 do not.
A record without a later user message may still have later assistant turns, driven by hooks or task notifications.
The join and the hand labels come from the transcripts, so only the counts table is reproducible from the log.

The review read the 199 flagged records that have a later user message against two labels.
The recipe's label of record is what the next user message asks.
The question's own criteria call a final message that names running work `false`.

| class | n | `done` right? |
|---|---|---|
| next message starts a different task or question | 124 | yes |
| next message asks to continue, fix or answer the same task | 24 | no |
| final message says a sub agent, CI watcher, commit hook or push is still running | 50 | no under the criteria; the recipe's label says no only for the 9 whose next message is `Continue` |
| ambiguous: a bare `yes` | 1 | unlabelled |

Precision at 0.8 on the 198 labelled records was 83% under the recipe's label and about 63% under the criteria.
The 50 in-flight finals scored 0.98 to 1.000.
Most are progress turns in supervisor sessions that end with words like "so I'm waiting".
In a random 100 of the records below 0.8, 99 were `false` under the criteria and 1 should have been `true`.
The recipe's label of record does not fit sessions where the user talks to a waiting session.
The recipe stays shadow.
Source: https://github.com/Alberto-Codes/judgevet/issues/314.

### Commit type and Closes or Refs

- Hook event: the git `commit-msg` stage through pre-commit, not a Claude Code event.
- Questions: two Choice questions, `type` over nine types and `closes` over `closes` and `refs`.
- Snippet: [commit_check.md](https://github.com/Alberto-Codes/judgevet/blob/main/examples/agent-hooks/commit_check.md).
- Latency: p50 2.91 s, p95 4.80 s per commit for both questions.

Over 200 commits, the judged type agreed with the written type on 72.5%, with kappa 0.68.
On 138 commits with one footer, the verdict agreed on 77.5%, with kappa 0.22.
The model judged `closes` for 132 of 138 and found 6 of 37 `refs` commits.
The state does not hold the issue's Done-when list, so the model cannot see what remains.
Strip the written type and footers from the state, so the model does not read the author's own labels.
Source: [commit_check.md](https://github.com/Alberto-Codes/judgevet/blob/main/examples/agent-hooks/commit_check.md) and https://github.com/Alberto-Codes/judgevet/issues/313.

### Acceptance pre-screen

- Tool: `evaluate_policy` over keyed questions and one acceptance rule.
- Status: **pending**. #312 has no recipe and no measurement yet.

Source: https://github.com/Alberto-Codes/judgevet/issues/312.

## Shadow mode first

Run every new hook in shadow mode before it gates anything:

1. Log each answer beside a label of record.
2. Measure agreement against that label before you trust a threshold.
3. Fail open: an error never stops the agent.
4. Never exit 2, the code that blocks an action in Claude Code.
5. Set `"async": true`, so the hook adds no wait and cannot block.

Claude Code does not enforce `timeout` on an async hook.
The runner's own `--timeout` bounds the call.
In `claude -p` mode, Claude Code cancels a running async hook at teardown, so that run logs nothing.
Source: https://code.claude.com/docs/en/hooks.

The shadow runner writes nothing to stdout.
A known failure exits 0 and writes an error record.
An unexpected error exits 1, which does not block.
The log holds answers, the model and the latency, never the state.
Source: https://github.com/Alberto-Codes/judgevet/issues/309.

Budget about 1.2 s per question on local Gemma 4.
The offline run measured each kind on a 214-token state, in seconds:

| kind | n | p50 | p95 | max |
|---|---|---|---|---|
| Noul | 20 | 1.22 | 2.06 | 2.12 |
| Choice, 5 labels | 20 | 1.20 | 1.27 | 1.37 |
| Score, 4 levels | 20 | 1.18 | 1.22 | 1.26 |
| 3 questions in one call | 5 | 3.67 | 6.62 | 6.62 |
| 3 separate calls, summed | 5 | 3.67 | 5.62 | 5.62 |

The shadow hooks measured these on live traffic, answered records only.
The live rows mix models, and kv9-text answered 86% of them.
Source: https://github.com/Alberto-Codes/judgevet/issues/308.

| question | state | n | p50 | p95 |
|---|---|---|---|---|
| Score, 5 levels (bash risk) | command plus cwd | 14,612 | 1.56 s | 2.43 s |
| Noul (injection) | up to 4,000 chars of tool output | 1,330 | 2.17 s | 7.4 s |
| Noul (stop: done?) | up to 8,000 chars of transcript | 740 | 1.75 s | 2.70 s |

Latency grows with state size.
The 4,000-character injection state timed out 3.4% of the time.
On a server that runs `--parallel 1`, several questions in one call cost the same as separate calls.
The cost of a hook is the sum of its questions, so a 5 s budget fits about three.
Source: https://github.com/Alberto-Codes/judgevet/issues/308.
Source: https://github.com/Alberto-Codes/typevet/issues/428.

## Limits

**A provider is compatible in shape, not equivalent in judgment.**
The port fixes the question and answer types, not what the model answers.
See [Use a self-hosted judgment provider](use-a-self-hosted-provider.md#compatible-in-shape-not-equivalent-in-judgment).

**Confidence is not accuracy.**
On readiness and priority, answers at confidence 0.8 or above were right about half the time.
Wrong answers at 0.99999 or above still occurred.
Source: https://github.com/Alberto-Codes/judgevet/issues/308.
On the Bash score, confidence p50 was 1.000 and 96% of records sat at or above 0.8.
Confidence carried no information at that question.
Source: https://github.com/Alberto-Codes/judgevet/issues/310.
On the Stop Noul, 98% of answers sat below 0.2 or at or above 0.8.
Of the 198 labelled answers at or above 0.8, 37% were wrong under the criteria.
Source: https://github.com/Alberto-Codes/judgevet/issues/314.
On the injection Noul, 1.000 was wrong 9 times in 30.
Source: https://github.com/Alberto-Codes/judgevet/issues/311.

**Thresholds do not transfer between judge models.**
Every number on this page came from one local model and one wording.
Measure again on Jev or on any other provider before you reuse a threshold.

The [verification ledger](../reference/verification-ledger.md) records what has been verified against Jev.
