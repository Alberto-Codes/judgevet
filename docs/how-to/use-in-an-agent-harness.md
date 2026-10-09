---
status: draft
---

# Use judgevet in an agent harness

Status: **draft**.

!!! note "Shadow runs pending"
    One-week shadow runs of three recipes started on 2026-10-09.
    They cover #310, #311 and #314, and their review is on 2026-10-16.
    The numbers on this page come from offline fixture sets.
    They may change after that review.

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
| blocked found | 5 of 14 | 9 of 14 |
| question found | 0 of 14 | 2 of 14 |
| priority agreement, kappa | 51.2%, 0.24 | 56.1%, 0.27 |

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

### Done or not at Stop

- Hook event: `Stop`.
- Question: one Noul, `done`, over the last user request and the final assistant message.
- Snippet: [stop_check.md](https://github.com/Alberto-Codes/judgevet/blob/main/examples/agent-hooks/stop_check.md).
- Latency: p50 1.47 s on 20 cases.

All 20 synthetic cases were correct at 0.5 and 0.8.
This is weak evidence, because one builder wrote both the criteria and the cases.
The recipe does not hook `SubagentStop`.
That hook sees the subagent's closing text, not the report it hands back.
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

**Thresholds do not transfer between judge models.**
Every number on this page came from one local model and one wording.
Measure again on Jev or on any other provider before you reuse a threshold.

The [verification ledger](../reference/verification-ledger.md) records what has been verified against Jev.
