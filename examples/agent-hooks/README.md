# Shadow-mode agent hooks

A Claude Code hook runs a command, not an MCP tool.
`shadow_judge.py` is that command.
It reads the hook input JSON on stdin and asks your provider the keyed questions.
It appends one JSON Lines record to a log.
It writes nothing to stdout, so Claude Code takes no decision from it.

## Exit codes

Claude Code reads exit 0 as success.
Exit 2 blocks the action on events that can block, such as `PreToolUse`.
Any other exit code is a non-blocking error, and the action goes ahead.
Source: https://code.claude.com/docs/en/hooks.

A known failure exits 0 and writes an error record.
The known failures are a timeout, a judgevet or provider error and unreadable input.
A bad file path, a bad `--provider` value and bad arguments are known failures too.
Bad arguments write a `UsageError` record to the default log, because `--log` may be unparsed.
An unexpected error exits 1, which is non-blocking.
A provider bug such as an `AttributeError` or a `TypeError` is unexpected.
Its stderr line names the error type only.
A provider that calls `sys.exit` also gives exit 1.
The script never exits 2, so it never blocks an action.

## Run it from a hook

The script is a PEP 723 script, and its only dependency is `judgevet`.
Your provider comes from your own package.
Add that package with `uv run --with`.
The `--provider` option names a factory as `module:factory`.
The factory returns a context manager that yields a judgment port.
`judgevet.providers.provider_scope` takes the same factory.

Add this to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --with my-app \"$CLAUDE_PROJECT_DIR\"/examples/agent-hooks/shadow_judge.py --provider my_app.judge:provider --question \"$CLAUDE_PROJECT_DIR\"/hooks/bash-questions.json --state-field tool_input.command",
            "timeout": 30
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run --with my-app \"$CLAUDE_PROJECT_DIR\"/examples/agent-hooks/shadow_judge.py --provider my_app.judge:provider --question \"$CLAUDE_PROJECT_DIR\"/hooks/stop-questions.json --state-field last_assistant_message"
          }
        ]
      }
    ]
  }
}
```

The question file uses the `judgevet --questions-file` grammar.
Each key names one `noul`, `choice` or `score` question.

## Options

| option | meaning |
|---|---|
| `--provider` | Factory as `module:factory`. Required. |
| `--model` | Model name. The default is `jev-latest`. |
| `--question` | Questions JSON file. Required. |
| `--state-field` | Dotted hook-input path for the state. Repeat it for more fields. |
| `--max-state-chars` | State character budget. The default is 4000. |
| `--log` | Log path. The default is `$XDG_STATE_HOME/judgevet/shadow.jsonl`. |
| `--timeout` | Seconds to wait for the judgment. The default is 5. |

Without `--state-field`, the state holds the event name and the tool name.
It also holds `tool_input`, `tool_response` and `last_assistant_message` when present.
An unset `XDG_STATE_HOME` puts the log under `~/.local/state`.

## The record

Each record holds the UTC timestamp, hook event, tool name and session ID.
It also holds the question keys, answers, model and latency in milliseconds.
The answers use the `judgevet --json` answer shape.
A timeout, a provider error or unreadable input adds an `error` field.
That field holds the error type only.
The record never holds the state, an error message or an environment value.
