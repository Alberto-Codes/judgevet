# /// script
# requires-python = ">=3.12"
# dependencies = ["judgevet"]
# ///
r"""Judge a commit message in shadow mode from a git commit-msg hook.

A git `commit-msg` hook gets the path of the message file as its only
argument. It does not get Claude Code's hook JSON on stdin. This wrapper
builds that JSON from the message file and `git diff --cached --stat`, then
passes it to `shadow_judge.py`, which asks the questions and logs one JSON
Lines record. Source: https://git-scm.com/docs/githooks#_commit_msg.

The state holds three fields: `subject`, `body` and `diff_stat`. The subject
drops the commit type, so the judge forms its own view of the type. A
`Closes` or `Refs` footer becomes an `Issue` line, so the judge sees which
issue the commit names but not the author's verdict.

The wrapper always exits 0, so it never fails a commit. A missing message
file, a provider error, a provider bug and a provider exit all exit 0.

Examples:
    Judge the message git is about to commit:

    ```bash
    uv run --with my-app commit_shadow.py --provider my_app.judge:provider \\
        --question commit_questions.json .git/COMMIT_EDITMSG
    ```

See Also:
    - [judgevet.providers][]: Provider factories and resource ownership.
    - [judgevet.adapters.inbound.cli][]: Question grammar and answer shapes.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

# Failures the judgment can raise past `shadow_judge.main`: a bad message
# path, a provider bug, a provider exit and an unloadable judge. The process
# entry point exits 0 on anything else too.
EXPECTED_FAILURES = (
    OSError,
    ValueError,
    ImportError,
    LookupError,
    TypeError,
    AttributeError,
    RuntimeError,
    SystemExit,
)

HERE = Path(__file__).resolve().parent
FIELDS = ("subject", "body", "diff_stat")
_SUBJECT = re.compile(r"^[a-zA-Z]+(?:\((?P<scope>[^()\n]*)\))?!?: (?P<rest>.*)$")
_VERDICT = re.compile(r"^(?:Closes|Refs)(?:: | (?=#))(?P<value>.*)$")
_COMMENT = re.compile(r"^#(?:\s|$)")
_SCISSORS = re.compile(r"^# --- >8 ---$", re.MULTILINE)


def message_lines(text: str) -> list[str]:
    """Return the message lines without git's comment and scissors lines.

    Args:
        text: Raw content of the commit message file.

    Returns:
        The remaining lines, with trailing blank lines dropped.
    """
    cut = _SCISSORS.search(text)
    if cut is not None:
        text = text[: cut.start()]
    lines = [line for line in text.splitlines() if not _COMMENT.match(line)]
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def state_input(text: str, diff_stat: str) -> dict[str, str]:
    """Build the hook input JSON for one commit message.

    Args:
        text: Raw content of the commit message file.
        diff_stat: Output of `git diff --cached --stat`.

    Returns:
        The hook event name, the subject without its type, the body with
        each `Closes` or `Refs` footer turned into an `Issue` line, and the
        diff stat.
    """
    lines = message_lines(text) or [""]
    match = _SUBJECT.match(lines[0])
    subject = lines[0]
    if match is not None:
        scope = (match["scope"] or "").strip()
        subject = f"{scope}: {match['rest']}" if scope else match["rest"]
    body = [_VERDICT.sub(r"Issue: \g<value>", line) for line in lines[1:]]
    return {
        "hook_event_name": "commit-msg",
        "subject": subject,
        "body": "\n".join(body).strip(),
        "diff_stat": diff_stat.strip("\n"),
    }


def staged_stat() -> str:
    """Return the diff stat of the staged changes.

    Returns:
        The `git diff --cached --stat` output, or an empty string when git
        fails or is not at `/usr/bin/git`.
    """
    try:
        done = subprocess.run(
            ["/usr/bin/git", "diff", "--cached", "--stat"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    return done.stdout if done.returncode == 0 else ""


def load_shadow_judge() -> ModuleType:
    """Import `shadow_judge.py` from this directory.

    Returns:
        The imported shadow judge module.

    Raises:
        ImportError: If the module cannot be loaded.
    """
    spec = importlib.util.spec_from_file_location(
        "shadow_judge", HERE / "shadow_judge.py"
    )
    if spec is None or spec.loader is None:
        raise ImportError("shadow_judge.py not found")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def judge_message(argv: list[str], stat: Callable[[], str]) -> None:
    """Pass the message state to the shadow judge.

    Args:
        argv: `shadow_judge.py` options followed by the message file path.
        stat: Function that returns the staged diff stat.

    Raises:
        ValueError: If no message file path is given.
    """
    if not argv:
        raise ValueError("name the commit message file")
    text = Path(argv[-1]).read_text(encoding="utf-8")
    payload = json.dumps(state_input(text, stat()), ensure_ascii=False)
    options = argv[:-1]
    if "--state-field" not in options:
        options += [arg for field in FIELDS for arg in ("--state-field", field)]
    load_shadow_judge().main(options, io.StringIO(payload))


def main(
    argv: list[str] | None = None, staged_stat: Callable[[], str] = staged_stat
) -> int:
    """Judge one commit message and return 0 whatever happens.

    Args:
        argv: `shadow_judge.py` options followed by the message file path, or
            None for `sys.argv`.
        staged_stat: Function that returns the staged diff stat.

    Returns:
        0 after the judgment or after an expected failure. Any other error
        propagates to the entry point, which still exits 0.
    """
    try:
        judge_message(list(sys.argv[1:] if argv is None else argv), staged_stat)
    except EXPECTED_FAILURES as error:
        print(f"commit_shadow: {type(error).__name__}", file=sys.stderr)
    return 0


def option(argv: list[str], name: str) -> str | None:
    """Return the value of one `--name value` or `--name=value` option.

    Args:
        argv: Command line without the program name.
        name: Option name, such as `--log`.

    Returns:
        The last value given, or None when the option is absent.
    """
    value = None
    for index, arg in enumerate(argv):
        if arg == name and index + 1 < len(argv):
            value = argv[index + 1]
        elif arg.startswith(name + "="):
            value = arg.partition("=")[2]
    return value


def report_unexpected(argv: list[str], kind: type[BaseException]) -> None:
    """Report an unexpected error by type name to stderr and to the log.

    The message and the traceback stay out of both, because either can hold
    a credential. A failed log write is ignored.

    Args:
        argv: Command line without the program name.
        kind: Exception class.
    """
    print(f"commit_shadow: unexpected {kind.__name__}", file=sys.stderr)
    with contextlib.suppress(OSError, ImportError):
        judge = load_shadow_judge()
        keys = judge.question_keys(option(argv, "--question") or "")
        record = judge.new_record(option(argv, "--model") or "jev-latest", keys)
        record.update(hook_event="commit-msg", error=kind.__name__, latency_ms=None)
        log = option(argv, "--log")
        judge.append(Path(log) if log else judge.default_log_path(), record)


if __name__ == "__main__":
    # os._exit skips the join of a hung judgment thread and ends the process
    # with status 0, even when main raises an error it does not expect. Such
    # an error leaves its type name on stderr and in the log.
    try:
        main()
    finally:
        try:
            unexpected = sys.exc_info()[1]
            if unexpected is not None:
                report_unexpected(sys.argv[1:], type(unexpected))
        finally:
            sys.stderr.flush()
            os._exit(0)
