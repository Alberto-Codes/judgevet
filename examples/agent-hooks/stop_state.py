# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Build a stop-check state from Claude Code Stop or SubagentStop hook input.

The script reads the hook input JSON from stdin. It writes one JSON object to
stdout for `shadow_judge.py` to read. The object holds `hook_event_name`,
`session_id`, `last_user_request` and `final_assistant_message`.

Stop and SubagentStop input carries `last_assistant_message`, the text of the
final response, but no user request. Source: https://code.claude.com/docs/en/hooks.
The script therefore reads the last user request from the transcript. For
SubagentStop it reads `agent_transcript_path`, the subagent's own transcript,
and otherwise `transcript_path`. Source: https://code.claude.com/docs/en/hooks.

A user request is a `user` record with text content. The script skips meta
records, tool results, records whose `origin.kind` is not `human`, and text
that starts with `<`, such as command output and task notifications. A record
with `origin.kind` set to `human` always counts. These record shapes come from
local transcripts read on 2026-10-09; the hooks page does not document them.

The final message comes from `last_assistant_message`. The script falls back
to the last assistant text block in the transcript only when that field is
absent, because the transcript can lag the final message.
Source: https://code.claude.com/docs/en/hooks.

The script removes C0 control characters other than tab and newline, such as
the escape character of ANSI color codes. `--max-chars` then cuts each
message. The request keeps its start, where the ask usually is. The final
message keeps its end, where a next step usually is.

SubagentStop caveat: a subagent that runs with the `SubagentHandback` tool
delivers its report through that tool, and `last_assistant_message` then
holds only its closing text. Source: https://code.claude.com/docs/en/hooks.
The script does not read the handed-back report, so its SubagentStop state
can miss the work the subagent reported.

A missing or unreadable transcript sets `last_user_request` to null and exits
0. Unreadable hook input or bad arguments write nothing to stdout and exit 1.
The script never exits 2, so it never blocks a stop.

Examples:
    Pipe the state into the shadow judge from a Stop hook:

    ```bash
    uv run stop_state.py < hook.json | uv run shadow_judge.py \
        --provider app.judge:make --question stop_question.json \
        --state-field last_user_request --state-field final_assistant_message
    ```

See Also:
    - [judgevet.providers][]: Provider factories and resource ownership.
    - [judgevet.adapters.inbound.cli][]: Question grammar and answer shapes.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from types import TracebackType
from typing import Any, TextIO

DEFAULT_MAX_CHARS = 1800
# C0 control characters other than tab and newline. JSON escapes each one as
# six characters, so ANSI escapes can inflate the serialized state.
CONTROL = {code: None for code in range(32) if chr(code) not in "\t\n"}


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command line.

    Args:
        argv: Arguments without the program name, or None for `sys.argv`.

    Returns:
        Parsed options.

    Raises:
        SystemExit: If the arguments are unusable or help was requested.
    """
    parser = argparse.ArgumentParser(
        prog="stop_state.py", description=__doc__.splitlines()[0]
    )
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    return parser.parse_args(argv)


def read_hook(stdin: TextIO) -> dict[str, Any]:
    """Read the hook input object from stdin.

    Args:
        stdin: Stream that holds the hook input JSON.

    Returns:
        The decoded hook input.

    Raises:
        json.JSONDecodeError: If the input is not valid JSON.
        TypeError: If the input is valid JSON but not an object.
    """
    hook = json.loads(stdin.read())
    if not isinstance(hook, dict):
        raise TypeError("hook input must be a JSON object")
    return hook


def records(path: Path) -> Iterator[Mapping[str, Any]]:
    """Yield the JSON object records of a JSON Lines transcript.

    Lines that are not JSON objects are skipped.

    Args:
        path: Transcript file.

    Yields:
        Each decoded record in file order.
    """
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            with contextlib.suppress(ValueError):
                record = json.loads(line)
                if isinstance(record, Mapping):
                    yield record


def text_of(record: Mapping[str, Any]) -> str | None:
    """Return the text content of a message record.

    Args:
        record: Transcript record.

    Returns:
        The string content or the joined text blocks. None when the content
        holds a tool result or no text.
    """
    message = record.get("message")
    content = message.get("content") if isinstance(message, Mapping) else None
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return None
    blocks = [block for block in content if isinstance(block, Mapping)]
    if any(block.get("type") == "tool_result" for block in blocks):
        return None
    texts = [b["text"] for b in blocks if b.get("type") == "text" and "text" in b]
    return "\n".join(texts) or None


def user_request(record: Mapping[str, Any]) -> str | None:
    """Return the text of a record when it is a request a person typed.

    Args:
        record: Transcript record.

    Returns:
        The request text, or None when the record is not a user request.
    """
    if record.get("type") != "user" or record.get("isMeta"):
        return None
    text = text_of(record)
    origin = record.get("origin")
    kind = origin.get("kind") if isinstance(origin, Mapping) else None
    if text is None or (kind is not None and kind != "human"):
        return None
    if kind is None and text.lstrip().startswith("<"):
        return None
    return text


def last_messages(path: Path) -> tuple[str | None, str | None]:
    """Find the last user request and the last assistant text in a transcript.

    Args:
        path: Transcript file.

    Returns:
        The last user request and the last assistant text, each None when absent.
    """
    request: str | None = None
    reply: str | None = None
    for record in records(path):
        if record.get("type") == "assistant":
            reply = text_of(record) or reply
        else:
            request = user_request(record) or request
    return request, reply


def transcript_of(hook: Mapping[str, Any]) -> Path | None:
    """Select the transcript that holds the request for this stop.

    Args:
        hook: Decoded hook input.

    Returns:
        The subagent transcript for SubagentStop, else the session transcript.
        None when the hook names no path.
    """
    path = hook.get("agent_transcript_path") or hook.get("transcript_path")
    return Path(path).expanduser() if isinstance(path, str) and path else None


def build_state(hook: Mapping[str, Any], limit: int) -> dict[str, Any]:
    """Build the state object for one stop.

    Args:
        hook: Decoded hook input.
        limit: Maximum characters for each message.

    Returns:
        The hook identity, the request cut from its start and the final
        message cut from its end, both without control characters.
    """
    request: str | None = None
    reply: str | None = None
    path = transcript_of(hook)
    if path is not None:
        with contextlib.suppress(OSError):
            request, reply = last_messages(path)
    final = hook.get("last_assistant_message")
    final = final if isinstance(final, str) else reply
    request = request.translate(CONTROL) if request else None
    final = final.translate(CONTROL) if final else None
    return {
        "hook_event_name": hook.get("hook_event_name"),
        "session_id": hook.get("session_id"),
        "last_user_request": request[:limit] if request else None,
        "final_assistant_message": final[-limit:] if final and limit > 0 else None,
    }


def main(
    argv: list[str] | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    """Write the stop state and return a status that never blocks.

    Args:
        argv: Arguments without the program name, or None for `sys.argv`.
        stdin: Hook input stream, or None for `sys.stdin`.
        stdout: State output stream, or None for `sys.stdout`.

    Returns:
        0 when the state was written. 1 for bad arguments, help or unreadable
        hook input, with nothing written. Never 2.
    """
    out = sys.stdout if stdout is None else stdout
    with contextlib.redirect_stdout(sys.stderr):
        try:
            options = parse_args(argv)
        except SystemExit:
            return 1
        try:
            hook = read_hook(sys.stdin if stdin is None else stdin)
        except (ValueError, TypeError, OSError) as error:
            print(f"stop_state: {type(error).__name__}", file=sys.stderr)
            return 1
        state = build_state(hook, options.max_chars)
    out.write(json.dumps(state, ensure_ascii=False) + "\n")
    return 0


def report_type_only(
    kind: type[BaseException], error: BaseException, trace: TracebackType | None
) -> None:
    """Report an unexpected error by type name only.

    Python then exits with status 1, a non-blocking error. The message and
    traceback stay out of stderr, because either can hold transcript text.

    Args:
        kind: Exception class.
        error: Exception instance, unused.
        trace: Traceback, unused.
    """
    print(f"stop_state: unexpected {kind.__name__}", file=sys.stderr)


if __name__ == "__main__":
    sys.excepthook = report_type_only
    exit_status = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_status)
