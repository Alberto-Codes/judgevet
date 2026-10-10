#!/usr/bin/env bash
# Run one builder brief on an external harness: Cursor or Codex.
# Usage: scripts/harness_build.sh <cursor|codex> <worktree> <brief-file> [model] [effort]
# The script prints the agent's result, its session, its usage and the worktree diff.
# The supervisor accepts the gates and the diff, never the result text.
# The script exits with the agent's exit code.
# Neither sandbox stops a write outside the worktree, for example to /tmp.
# pi is not covered here. pi follows the delegate-to-pi skill.
set -euo pipefail

usage() {
	echo "usage: $0 <cursor|codex> <worktree> <brief-file> [model] [effort]" >&2
	echo "cursor: model defaults to cursor-grok-4.6-medium. Cursor ignores effort." >&2
	echo "codex: a named model is required. Effort defaults to medium." >&2
	exit 2
}

[ "$#" -ge 3 ] && [ "$#" -le 5 ] || usage
harness="$1"
worktree="$2"
brief="$3"
model="${4:-}"
effort="${5:-medium}"
[ -d "$worktree" ] || usage
[ -f "$brief" ] || usage
# The hook guard below owns GIT_CONFIG_COUNT. Refuse to overwrite a caller's value.
if [ -n "${GIT_CONFIG_COUNT:-}" ]; then
	echo "harness_build: FAIL: GIT_CONFIG_COUNT is already set. Unset it first." >&2
	exit 1
fi
case "$harness" in
cursor)
	# judgevet commits the deny file. Refuse to run Cursor without it.
	if [ ! -f "$worktree/.cursor/cli.json" ]; then
		echo "harness_build: FAIL: $worktree/.cursor/cli.json is missing. Cursor runs only behind it." >&2
		exit 1
	fi
	;;
codex)
	# Codex has no automatic routing. A run without a named model never starts.
	if [ -z "$model" ]; then
		echo "harness_build: codex needs a named model." >&2
		usage
	fi
	;;
*)
	usage
	;;
esac

out="$(mktemp)"
last="$(mktemp)"
hooks="$(mktemp -d)"
trap 'rm -rf "$out" "$last" "$hooks"' EXIT

# Commit guard for both harnesses: a pre-commit hook that refuses every commit.
# A chained "cat x && git commit" can get past the Cursor deny rule Shell(git).
# Codex keeps .git read-only only under macOS Seatbelt, so on Linux the hook is the guard.
# The environment sets core.hooksPath. The repository config stays unchanged.
# shortcut: "git commit --no-verify" skips the hook.
printf '#!/bin/sh\necho "harness_build: commits are blocked. The supervisor commits." >&2\nexit 1\n' \
	>"$hooks/pre-commit"
chmod +x "$hooks/pre-commit"
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0="$hooks"

status=0
case "$harness" in
cursor)
	timeout 1800 cursor-agent -p --trust --force --sandbox enabled --output-format json \
		--model "${model:-cursor-grok-4.6-medium}" --workspace "$worktree" "$(cat "$brief")" \
		>"$out" || status=$?
	echo "result:"
	jq -r '.result' "$out" 2>/dev/null || cat "$out"
	echo "session:"
	session="$(jq -r '.session_id // empty' "$out" 2>/dev/null || true)"
	echo "${session:-unknown}"
	echo "usage:"
	cursor_usage="$(jq -c '.usage // empty' "$out" 2>/dev/null || true)"
	echo "${cursor_usage:-unknown}"
	;;
codex)
	# Effort levels: low, medium, high and xhigh, per ~/.codex/models_cache.json on 2026-10-09.
	# The script passes the value through.
	timeout 1800 codex exec -C "$worktree" -s workspace-write \
		-c approval_policy=never -c model_reasoning_effort="$effort" \
		-m "$model" --json -o "$last" - <"$brief" >"$out" || status=$?
	echo "result:"
	cat "$last"
	echo
	echo "session:"
	# The thread.started event carries thread_id.
	# Source: https://github.com/openai/codex/blob/main/codex-rs/exec/src/exec_events.rs
	session="$(jq -r 'select(.type == "thread.started") | .thread_id // empty' "$out" 2>/dev/null | head -n 1 || true)"
	echo "${session:-unknown}"
	echo "usage:"
	codex_usage="$(jq -c 'select(.type == "turn.completed") | .usage' "$out" 2>/dev/null || true)"
	echo "${codex_usage:-unknown}"
	jq -c 'select(.type == "turn.failed" or .type == "error")' "$out" 2>/dev/null || true
	;;
esac

echo "status:"
git -C "$worktree" status --short
echo "diff:"
git -C "$worktree" diff --stat
exit "$status"
