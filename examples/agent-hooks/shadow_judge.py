# /// script
# requires-python = ">=3.12"
# dependencies = ["judgevet"]
# ///
"""Judge a Claude Code hook event in shadow mode and log the answers.

A Claude Code hook cannot call an MCP tool, so this script is the command a
hook runs. It reads the hook input JSON from stdin. It builds the state from
the selected input fields and asks the selected provider the keyed questions.
It appends one JSON Lines record to the log. It writes nothing to stdout, so
Claude Code takes no decision from it.

Exit 0 means success. Exit 2 blocks the action on events that can block.
Any other exit code is a non-blocking error, and the action goes ahead.
Source: https://code.claude.com/docs/en/hooks.

A known failure exits 0 with an error record. Known failures are a timeout,
a judgevet or provider error, unreadable input, a bad file path, a bad
`--provider` value and bad arguments. An unexpected error exits 1, which is
non-blocking. A provider bug such as an `AttributeError` is unexpected.
Its stderr line names the error type only. The script never exits 2. Bad
arguments write a `UsageError` record to the default log.

The record holds the UTC timestamp, hook event, tool name, session ID,
question keys, answers, model and latency. A failed run adds an `error` field
that holds the error type only. The record never holds the state, an error
message or an environment value.

Examples:
    Run one PreToolUse event against an application provider:

    ```bash
    uv run shadow_judge.py --provider my_app.providers:judge --question q.json < hook.json
    ```

See Also:
    - [judgevet.providers][]: Provider factories and resource ownership.
    - [judgevet.adapters.inbound.cli][]: Question grammar and answer shapes.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import json
import os
import sys
import time
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any, TextIO

from judgevet.adapters.inbound.cli import build_response_data, parse_questions
from judgevet.adapters.inbound.cli_inputs import resolve_inputs
from judgevet.domain.errors import JudgevetError
from judgevet.domain.response import SystemOneResponse
from judgevet.providers import ProviderFactory, provider_scope

DEFAULT_FIELDS = (
    "hook_event_name",
    "tool_name",
    "tool_input",
    "tool_response",
    "last_assistant_message",
)
# Known failures during the judgment: judgevet and provider errors, the
# timeout, unreadable files and invalid values. Anything else propagates.
KNOWN_FAILURES = (JudgevetError, TimeoutError, ValueError, OSError)
# Preparation also fails known on stdin that is not an object and on a bad
# --provider value. These two types stay uncaught inside the judgment.
SETUP_FAILURES = (*KNOWN_FAILURES, ImportError, TypeError, AttributeError)


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
        prog="shadow_judge.py", description=__doc__.splitlines()[0]
    )
    parser.add_argument("--provider", required=True, help="module:factory")
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--question", required=True, help="Questions JSON file")
    parser.add_argument("--state-field", action="append", dest="fields")
    parser.add_argument("--max-state-chars", type=int, default=4000)
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--timeout", type=float, default=5.0)
    return parser.parse_args(argv)


def default_log_path() -> Path:
    """Return the default log path under the XDG state directory.

    An unset, empty or relative `XDG_STATE_HOME` falls back to
    `~/.local/state`.
    Source: https://specifications.freedesktop.org/basedir-spec/latest/.

    Returns:
        The `judgevet/shadow.jsonl` path under the state directory.
    """
    base = os.environ.get("XDG_STATE_HOME", "")
    root = Path(base) if os.path.isabs(base) else Path.home() / ".local" / "state"
    return root / "judgevet" / "shadow.jsonl"


def load_factory(spec: str) -> ProviderFactory:
    """Import a provider factory named as `module:attribute`.

    Args:
        spec: Module path and factory attribute, separated by a colon.

    Returns:
        The callable that returns a context yielding a judgment port.

    Raises:
        ValueError: If the specification has no colon or no attribute.
        TypeError: If the named attribute is not callable.
        ImportError: If the module cannot be imported.
        AttributeError: If the module has no such attribute.
    """
    module_name, separator, attribute = spec.partition(":")
    if not separator or not attribute:
        raise ValueError("--provider must name module:factory")
    factory = getattr(importlib.import_module(module_name), attribute)
    if not callable(factory):
        raise TypeError("--provider must name a callable factory")
    return factory


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


def build_state(hook: Mapping[str, Any], fields: list[str], limit: int) -> str:
    """Select dotted hook fields and serialize them within a budget.

    Args:
        hook: Decoded hook input.
        fields: Dotted paths into the hook input; missing paths are skipped.
        limit: Maximum number of state characters.

    Returns:
        A JSON object of the selected fields, cut to `limit` characters.
    """
    selected: dict[str, Any] = {}
    for field in fields:
        value: Any = hook
        for part in field.split("."):
            value = value.get(part) if isinstance(value, Mapping) else None
        if value is not None:
            selected[field] = value
    return json.dumps(selected, ensure_ascii=False, default=str)[:limit]


def judge_within(
    call: Callable[[], SystemOneResponse], timeout: float
) -> SystemOneResponse:
    """Run one judgment on a worker thread and wait at most `timeout` seconds.

    The worker is not joined, so a hung provider cannot hold the hook open.

    Args:
        call: Judgment to run.
        timeout: Seconds to wait for the judgment.

    Returns:
        The judgment response.

    Raises:
        TimeoutError: If the judgment does not finish in time.
    """
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        return executor.submit(call).result(timeout)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def prepare(
    options: argparse.Namespace, stdin: TextIO, record: dict[str, Any]
) -> tuple[Mapping[str, Any], dict[str, Any], ProviderFactory]:
    """Read the hook input, the questions and the provider factory.

    Args:
        options: Parsed command line.
        stdin: Stream that holds the hook input JSON.
        record: Log record that receives the hook identity fields.

    Returns:
        The hook input, the typed questions and the provider factory.
    """
    hook = read_hook(stdin)
    record["hook_event"] = hook.get("hook_event_name")
    record["tool_name"] = hook.get("tool_name")
    record["session_id"] = hook.get("session_id")
    _, text = resolve_inputs("hook", None, [], [options.question], parse_questions)
    return hook, parse_questions(text), load_factory(options.provider)


def judge(
    options: argparse.Namespace,
    hook: Mapping[str, Any],
    questions: dict[str, Any],
    factory: ProviderFactory,
) -> dict[str, Any]:
    """Ask the selected provider the keyed questions about one hook event.

    Args:
        options: Parsed command line.
        hook: Decoded hook input.
        questions: Typed questions keyed by name.
        factory: Provider factory.

    Returns:
        Answers keyed by question, in the CLI JSON output shape.
    """
    state = build_state(
        hook, options.fields or list(DEFAULT_FIELDS), options.max_state_chars
    )

    def call() -> SystemOneResponse:
        """Acquire the provider, judge once and release it.

        Returns:
            The provider response.
        """
        with provider_scope(factory=factory) as port:
            return port.system_one(
                state=state, questions=questions, model=options.model
            )

    return build_response_data(judge_within(call, options.timeout))["answers"]


def new_record(model: str | None, keys: list[str]) -> dict[str, Any]:
    """Start a log record with no hook identity and no answers.

    Args:
        model: Requested model, or None when the arguments did not parse.
        keys: Question keys.

    Returns:
        The record fields every run writes.
    """
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "hook_event": None,
        "tool_name": None,
        "session_id": None,
        "question_keys": keys,
        "model": model,
        "answers": None,
    }


def question_keys(path: str) -> list[str]:
    """Return the question keys of a questions file, or an empty list.

    Args:
        path: Questions JSON file.

    Returns:
        Question keys in file order.
    """
    with contextlib.suppress(OSError, ValueError, TypeError):
        return list(json.loads(Path(path).read_text(encoding="utf-8")))
    return []


def run(options: argparse.Namespace, stdin: TextIO) -> tuple[dict[str, Any], int]:
    """Judge one hook event and build its log record.

    Preparation treats a `TypeError` or `AttributeError` as a known failure.
    The judgment does not, so a provider bug of either type exits 1.

    Args:
        options: Parsed command line.
        stdin: Stream that holds the hook input JSON.

    Returns:
        The log record and the exit status. A known failure adds an `error`
        type name and keeps status 0. A `SystemExit` from the provider maps
        to status 1, so it can never block the action.
    """
    started = time.monotonic()
    record = new_record(options.model, question_keys(options.question))
    status = 0
    try:
        hook, questions, factory = prepare(options, stdin, record)
    except SETUP_FAILURES as error:
        record["error"] = type(error).__name__
    else:
        try:
            record["answers"] = judge(options, hook, questions, factory)
        except KNOWN_FAILURES as error:
            record["error"] = type(error).__name__
        except SystemExit:
            record["error"] = "SystemExit"
            status = 1
    record["latency_ms"] = round((time.monotonic() - started) * 1000)
    return record, status


def append(path: Path, record: Mapping[str, Any]) -> None:
    """Append one JSON Lines record, creating the directory when needed.

    Args:
        path: Log file path.
        record: Record to write.
    """
    with contextlib.suppress(OSError):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None, stdin: TextIO | None = None) -> int:
    """Run the shadow judge and return a status that never blocks.

    Args:
        argv: Arguments without the program name, or None for `sys.argv`.
        stdin: Hook input stream, or None for `sys.stdin`.

    Returns:
        0 for success, a known failure or bad arguments. 1 when the provider
        exits. Never 2. Bad arguments write a `UsageError` record to the
        default log, because `--log` may itself be unparsed.
    """
    with contextlib.redirect_stdout(sys.stderr):
        try:
            options = parse_args(argv)
        except SystemExit:
            usage = new_record(None, [])
            usage.update(error="UsageError", latency_ms=0)
            append(default_log_path(), usage)
            return 0
        record, status = run(options, sys.stdin if stdin is None else stdin)
        append(options.log or default_log_path(), record)
    return status


def report_type_only(
    kind: type[BaseException], error: BaseException, trace: TracebackType | None
) -> None:
    """Report an unexpected error by type name only.

    Python then exits with status 1, a non-blocking error. The message and
    traceback stay out of stderr, because either can hold a credential.

    Args:
        kind: Exception class.
        error: Exception instance, unused.
        trace: Traceback, unused.
    """
    print(f"shadow_judge: unexpected {kind.__name__}", file=sys.stderr)


if __name__ == "__main__":
    sys.excepthook = report_type_only
    exit_status = main()
    sys.stderr.flush()
    os._exit(exit_status)
