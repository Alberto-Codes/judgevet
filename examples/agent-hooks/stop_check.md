# Check whether a stop left the task undone

An agent can stop while it still has work it said it would do.
This recipe asks one question at each stop and logs the answer.
It runs `shadow_judge.py` in shadow mode, so it never blocks or changes a stop.

## The question

`stop_question.json` holds one `noul` question with the key `done`.
Its instruction is the sentence that follows.

> The request in this transcript excerpt is fully completed, with no step the assistant said it would do still undone.

Its `true` and `false` criteria state what counts.
Noul criteria take a `true` and a `false` description.
Source: https://docs.typesafe.ai/primitives/noul.

The `true` side needs every requested item done and reported.
The final message announces no next step, no running background work and no failing check.
A question to the user counts as done only when it offers optional extra work.
A mention of optional follow-up work outside the request does not count against completion.
The `false` side covers an announced next step, pending background work and a failing check.
It also covers a partial report and a question the user must answer before the task can end.
A failing check counts as `false` even when the message also claims the task is done.

## The state

The state holds the last user request and the final assistant message.

Stop input carries `stop_hook_active`, `last_assistant_message`, `background_tasks` and `session_crons`.
Source: https://code.claude.com/docs/en/hooks.
SubagentStop input carries `stop_hook_active`, `agent_id`, `agent_type`, `agent_transcript_path` and `last_assistant_message`.
Source: https://code.claude.com/docs/en/hooks.
The docs say that `last_assistant_message` "contains the text content of Claude's final response".
Source: https://code.claude.com/docs/en/hooks.
Neither input carries the user request.

`stop_state.py` reads the user request from the transcript.
For SubagentStop it reads `agent_transcript_path`, the subagent's own transcript.
For Stop it reads `transcript_path`.
Source: https://code.claude.com/docs/en/hooks.
It takes the final message from `last_assistant_message`.
The docs warn that the transcript file "isn't guaranteed to include the final message at Stop time on all versions".
Source: https://code.claude.com/docs/en/hooks.
So the script reads the transcript for the final message only when that field is absent.

**Open question:** this recipe does not judge a SubagentStop.
The hooks page says this about the `SubagentHandback` tool:

> On Claude Code v2.1.271 or later, a subagent that runs with the `SubagentHandback` tool delivers its report through that tool before it stops. The `last_assistant_message` field then holds the subagent's closing text, if any, which is not the delivered report.

Source: https://code.claude.com/docs/en/hooks.
Judging a subagent needs the handed-back report, for example from the `SubagentHandback` tool input in `agent_transcript_path`.
That is not built.
`stop_state.py` reads `agent_transcript_path` for the request, but it does not read the handed-back report.
So the settings below add a Stop hook only.

The script picks the last `user` record that a person typed.
It skips meta records, tool results and records whose `origin.kind` is not `human`.
It also skips text that starts with `<`, such as command output and task notifications.
The hooks page does not document these transcript record shapes.
They come from local transcripts read on 2026-10-09 and can change in a later Claude Code version.

The script writes one JSON object to its stdout, which is the stdin of `shadow_judge.py`.
The object holds `hook_event_name`, `session_id`, `last_user_request` and `final_assistant_message`.
A missing or unreadable transcript sets `last_user_request` to null, and the judge still runs.
Unreadable hook input or bad arguments write nothing and exit 1.
The judge then logs a `JSONDecodeError` record.

## The budget

`stop_state.py --max-chars` cuts each message to 1800 characters by default.
The request keeps its start, where the ask usually is.
The final message keeps its end, where an announced next step usually is.
The two messages then hold at most 3600 characters of text.
At about four characters per token, that is at most about 900 tokens.

`shadow_judge.py` cuts the serialized JSON at `--max-state-chars`, and it cuts the end.
JSON escapes such as `\n` and `\"` make the serialized state longer than its text.
The hook therefore sets `--max-state-chars 8000`, twice the text budget and room for the keys.
For ordinary text, the judge then keeps the end of the final message.
A control character serializes to six characters, such as `\u001b`.
`stop_state.py` removes C0 control characters other than tab and newline, which covers the escape character of ANSI color codes.
Text full of other escaped characters can still serialize to more than 8000 characters.
The judge then cuts the end of the final message.
On local Gemma 4, a 200-token state took about 1.2 seconds per question (#308).
A longer state costs more time.

## Add the hook

Add this to `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run \"$CLAUDE_PROJECT_DIR\"/examples/agent-hooks/stop_state.py --max-chars 1800 | uv run --with my-app \"$CLAUDE_PROJECT_DIR\"/examples/agent-hooks/shadow_judge.py --provider my_app.judge:provider --question \"$CLAUDE_PROJECT_DIR\"/examples/agent-hooks/stop_question.json --state-field last_user_request --state-field final_assistant_message --max-state-chars 8000 --timeout 30 --log \"$HOME\"/.local/state/judgevet/stop.jsonl",
            "async": true
          }
        ]
      }
    ]
  }
}
```

The shell gives the pipe the exit status of its last command, `shadow_judge.py`.
That script exits 0 or 1 and never exits 2.
Neither script writes to the hook's stdout.
The docs say that an async hook runs "in the background while Claude continues working".
They also say that "Async hooks can't block or control Claude's behavior".
Source: https://code.claude.com/docs/en/hooks.
Claude Code does not enforce `timeout` on a running async hook.
Source: https://code.claude.com/docs/en/hooks.
The judge `--timeout` option bounds the call instead.
In non-interactive mode with `-p`, Claude Code kills an async hook that still runs at teardown.
Source: https://code.claude.com/docs/en/hooks.
A stop at the end of a `-p` run can therefore write no record.

## The label of record for the shadow week

The label of record for a stop is what the user asks next.
If the next user message asks to continue or fix the same task, the stop was not done.
Otherwise the stop was done.
A stop with no later user message in the session gets no label.

Compute the label after the week from the transcript:

1. Read each record in the log for its `session_id` and `timestamp`.
2. Open that session's transcript under `~/.claude/projects/`.
3. Find the first user request after the record's timestamp.
   Use the same filter as `stop_state.py`: skip meta records, tool results and text that starts with `<`.
4. Mark the stop `not done` when that request asks to continue, finish or fix the same task.
   Examples are "continue", "you didn't run the tests" and "the build still fails".
5. Mark it `done` when that request starts a different task or only thanks the agent.

Step 4 is itself a judgment, so a person labels it, or a person checks a sample of machine labels.

A SubagentStop has no next user message, and this recipe does not hook it.

## Privacy

The state goes to the provider.
It holds the last user request and the final assistant message, cut to the budget.
A hosted provider therefore receives that text.
Use a local provider when that text must stay on the machine.
The log keeps only the answers, the hook identity, the model and the latency.
It never holds the state.

## The fixture set

`tests/fixtures/agent_hooks/stop_cases.jsonl` holds 20 synthetic stop states.
Each row has an `id`, a boolean `label`, a boolean `hard`, `last_user_request` and `final_assistant_message`.
Ten rows are done and ten are not done.
The not-done rows announce a next step, report running background work or end with a choice the user must make.
Others report partial work or a failing check.
Six rows are marked hard:

- `done-07` reports the task done and suggests optional future work.
- `done-08` answers the request and then offers optional extra work.
- `done-10` names an old pin and reports the fix.
- `open-05` says "Done" while it reports two type errors.
- `open-07` reports four of five scripts converted.
- `open-10` says "everything else is complete" while one test fails.

`tests/fixtures/agent_hooks/stop_transcript.jsonl` is a synthetic transcript for the tests.
It follows the local record shapes and holds invented content only.

## Measure the question

`measure_stop.py` scores the fixture set through a provider.
It builds each state as `stop_state.py` and `shadow_judge.py` do together.
A probability at or above a threshold predicts done.
It prints precision and recall for `done` and for `not done` at 0.5 and 0.8.
It also prints each probability and the p50 and p95 latency.

```bash
uv run --with my-app examples/agent-hooks/measure_stop.py --provider my_app.judge:provider --model my-model --cases tests/fixtures/agent_hooks/stop_cases.jsonl
```

A run on 2026-10-09 used local Gemma 4 through typevet 0.8.1 and judgevet 0.18.1.
The model was `gemma-4-31b-qat-q4_0-mm` on llama.cpp.

| threshold | done precision | done recall | not-done precision | not-done recall | misclassified |
|---|---|---|---|---|---|
| 0.5 | 1.00 | 1.00 | 1.00 | 1.00 | none |
| 0.8 | 1.00 | 1.00 | 1.00 | 1.00 | none |

Every done row scored 1.000 and every not-done row scored 0.000, the hard rows included.
The p50 latency was 1.47 seconds and the p95 latency was 1.57 seconds over 20 rows.
Another job may have shared the local server during the run.

These figures show that the fixture set separates cleanly on one model.
They do not show the error rate on real stops.
The same author wrote the criteria and the fixture rows, so the criteria name several fixture patterns.
The one-week shadow run in #314 measures the rate on real stops against the label of record.
