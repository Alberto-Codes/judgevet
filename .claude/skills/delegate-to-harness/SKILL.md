---
name: delegate-to-harness
description: Hand one mechanical, gate-checked builder slice to an external harness (Cursor or Codex, or pi through its own skill) when its usage pool has headroom. The supervisor still decides and verifies. The gates and the diff are the result, never the agent's summary.
---

# Delegate to a harness

Each harness bills a separate usage pool.
An external harness runs the build. The supervisor keeps every decision and every check.
The [worker run contract](../../../docs/reference/worker-runs.md#harnesses) holds the commands and the trailers.
The Codex CLI stays unverified in judgevet until a run lands.

## Trigger

Read the usage of each pool before you route a slice.
Run the `quota` skill. It reads every pool in one command, `quota-axi --full`, as used percent against elapsed percent.
A session never sees `/usage`, the status line or a dashboard. Run the skill instead.
Route a mechanical slice to a pool with headroom.
A pool over its allotment is not a target, for example 25 used of 22 elapsed.
Record the ratio that you read on the issue when you route.

| Pool | Row in the reader |
|---|---|
| Claude week | `claude seven_day` |
| Claude five-hour | `claude five_hour` |
| Fable week | `claude model:fable` |
| Codex | `codex weekly` |
| Cursor | `cursor included_usage` |
| pi | None. pi runs locally and costs time, not quota |

The rows come from the `quota` skill.

## Harnesses

- **Cursor.** The `cursor-agent` CLI in print mode with a named Cursor-pool model.
- **Codex.** The `codex exec` CLI with a named model. The CLI has no automatic routing.
- **pi.** The local harness. Follow the `delegate-to-pi` skill.

| Harness | Model | Effort | Use it for |
|---|---|---|---|
| Cursor | `cursor-grok-4.6-medium` (default) | None | Mechanical, gate-checked work |
| Codex | `gpt-6-luna` | `low` or `medium` | Mechanical, gate-checked work |
| Codex | `gpt-6.1-sol` | `medium` | Harder work with a clear contract |
| Codex | `gpt-6-astra` | `high` | Only on a stated supervisor reason |
| pi | `Qwen3-Coder-Next-UD-IQ4_XS` | None | Mechanical work with a decided shape |
| pi | `Qwen3.8-27B-UD-Q4_K_M` | `--thinking medium` | Specs and judgment in the pi skill |

The Codex model ids and the effort levels come from `~/.codex/models_cache.json`, read on 2026-10-09.
No judgevet run has exercised a Codex model yet.
Pass only `cursor-grok-*`, `grok-*`, `composer-*` or `gemini-*` IDs to Cursor.
The worker run contract records which pool other IDs and `auto` bill as an open question.

## When not

Do not send these to an external harness:

- the specifier,
- the acceptance reviewer,
- any judgment, ruling or verdict,
- a slice whose shape is undecided.

## The brief

Write the brief to a file. Put the whole brief in the prompt.
Codex reads `AGENTS.md`, not `CLAUDE.md`. In judgevet, `AGENTS.md` is a symlink to `CLAUDE.md`.
Give the same four parts as a Claude builder brief:

1. the goal,
2. the scope, with what is out of scope,
3. the context the agent lacks, with the contract text,
4. the return format.

Add the exact gate commands to run. Add the line "Do not commit."

## Run

Run the script from the repository root on an isolated worktree:

```bash
scripts/harness_build.sh cursor <worktree> <brief-file>
scripts/harness_build.sh codex <worktree> <brief-file> gpt-6-luna low
```

The script prints `result:`, `session:`, `usage:`, the status and the diff stat.
It exits with the agent's exit code.
The script stops a run after 1800 seconds.
pi stays on the `delegate-to-pi` skill. The script does not cover pi.

## Evidence

The gates and `git diff` are the result. The agent's summary is only an assertion.
Run each gate yourself on the worktree. Read the diff against the contract.
A fresh acceptance reviewer still accepts the slice before any commit.

## Trailers

| Harness | `Generated-By` value |
|---|---|
| Cursor | `<requested model id> (via Cursor CLI <version>, print mode)` |
| Codex | `codex <model> (effort <level>, via Codex CLI <version>)` |
| pi | `<model> (local, via pi)` |

## Caveats

- Neither sandbox stops a write outside the worktree, for example to `/tmp`.
- Cursor `Shell(git)` matches the first token only. A chained `cat x && git commit` passes the deny rule.

  Source: https://cursor.com/docs/cli/reference/permissions.

- Codex keeps `.git` read-only only in the macOS Seatbelt profile. On Linux the hook is the one dependable guard.

  Source: https://github.com/openai/codex/blob/main/codex-rs/core/README.md.

- The script sets a refusing `pre-commit` hook through the environment. `git commit --no-verify` skips that hook.
- The hook guards commits only. A chained `git push`, `git reset --hard` or `git checkout -- .` is not blocked.
- With `--force`, a Cursor agent can ask to rerun a blocked command "with full permissions". A private sibling project observed this on 2026-10-09; no judgevet run has shown it.
- Codex can start MCP servers from `~/.codex/config.toml`. A server can write into the worktree.
- Check `git status --short` for each untracked file before acceptance.
- Snapshot the worktree before a run with `git -C <worktree> diff HEAD > before.patch` and `git -C <worktree> status --short`.
- Never use `git stash` for the snapshot.
