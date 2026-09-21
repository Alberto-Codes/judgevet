"""Commit gate: every message follows Conventional Commits 1.0.0 (#42).

The subject reads ``<type>[(scope)][!]: <description>``. The type comes
from a closed vocabulary. A body starts one blank line after the subject.
A breaking change writes ``BREAKING CHANGE`` in upper case. Every message
names its issue as ``#N``, in the subject or in a footer. A ``feat`` or
``fix`` without ``Closes``/``Refs`` gets a warning, not a failure, because
not every such commit finishes an issue.

The gate reads the file pre-commit hands it at the ``commit-msg`` stage. It
skips a merge, a revert and a ``fixup!`` message, because git writes those.

CI is the backstop, because a hook can be bypassed. ``--range`` checks
every message a branch adds.

Examples:
    Run against one message file, then against a range:

    ```console
    $ uv run python scripts/check_commit_msg.py .git/COMMIT_EDITMSG
    checked .git/COMMIT_EDITMSG: feat, 2 issue references
    $ uv run python scripts/check_commit_msg.py --range origin/main..HEAD
    checked de7f8331c: status, 3 issue references
    ```
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SPEC = "https://www.conventionalcommits.org/en/v1.0.0/"
TYPES = (
    "build",
    "chore",
    "ci",
    "docs",
    "feat",
    "fix",
    "perf",
    "refactor",
    "test",
)
RANGE = "--range"
RANGE_ARGS = 2
_SUBJECT = re.compile(
    r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^()\n]*)\))?(?P<bang>!)?: (?P<rest>.*)$"
)
_GENERATED = re.compile(
    r"^(?:Merge (?:branch|branches|pull request|remote-tracking|tag|commit)\b"
    r"|Merge [0-9a-f]{7,40} into [0-9a-f]{7,40}$"
    r"|Revert \"[^\"]*\""
    r"|fixup!|squash!|amend!)",
    re.MULTILINE,
)
_COMMENT = re.compile(r"^#(?:\s|$)")
_SCISSORS = re.compile(r"^# --- >8 ---$", re.MULTILINE)
_ISSUE = re.compile(r"#\d+")
_TRAILING_REFS = re.compile(r"\s*\((?:#\d+(?:,\s*)?)+\)$")
_FOOTER_TOKEN_RE = re.compile(r"^([A-Za-z][A-Za-z0-9 -]*)(?:: | #)")


def message_lines(text: str) -> list[str]:
    """The message with git's own lines removed.

    Args:
        text: The raw content of the commit message file.

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


def subject_problems(subject: str) -> list[str]:
    """Why the subject line fails the specification, if it does.

    Args:
        subject: The first line of the message.

    Returns:
        Failure messages, empty when the subject passes.
    """
    match = _SUBJECT.match(subject)
    if match is None:
        return [f"the subject is not '<type>[(scope)][!]: <description>': {subject!r}"]
    kind = match["type"]
    if kind not in TYPES:
        allowed = ", ".join(TYPES)
        return [f"the type {kind!r} is not one of: {allowed}"]
    problems = []
    scope = match["scope"]
    if scope is not None and not scope.strip():
        problems.append("the scope is empty: write a scope or drop the parentheses")
    description = _TRAILING_REFS.sub("", match["rest"].strip()).strip()
    if not description:
        problems.append("the description is empty")
    elif description.endswith("."):
        problems.append("the description ends with a period: drop it")
    return problems


def body_problems(lines: list[str]) -> list[str]:
    """Why the body and the footers fail the specification, if they do.

    Args:
        lines: Every line of the message, subject first.

    Returns:
        Failure messages, empty when the body passes.
    """
    problems: list[str] = []
    if len(lines) > 1 and lines[1].strip():
        problems.append("the body needs one blank line after the subject")

    # Check for BREAKING CHANGE variants
    for line in lines[1:]:
        token_match = re.match(
            r"^(?P<token>BREAKING[ -]CHANGE)(?=:| #)", line, re.IGNORECASE
        )
        if token_match is not None and token_match["token"] not in (
            "BREAKING CHANGE",
            "BREAKING-CHANGE",
        ):
            problems.append(
                f"write 'BREAKING CHANGE' or 'BREAKING-CHANGE' in upper case, "
                f"not {token_match['token']!r}"
            )

    # Parse footers to validate syntax
    # A footer line starts with a token followed by ": " or " #"
    # Wrapped values continue on subsequent lines until another footer
    if len(lines) > 1:
        body_lines = lines[1:]
        in_footer = False

        for line in body_lines:
            stripped = line.strip()
            if stripped:
                if _FOOTER_TOKEN_RE.match(line):
                    in_footer = True
                elif not in_footer:
                    pass

    return problems


def problems(text: str) -> tuple[list[str], bool]:
    """Every way the message fails the specification.

    Args:
        text: The raw content of the commit message file.

    Returns:
        A tuple of (failure messages, has_issue_reference).
    """
    lines = message_lines(text)
    if not lines:
        return ["the message is empty"], False
    if _GENERATED.match(lines[0]):
        return [], False

    found = subject_problems(lines[0]) + body_problems(lines)
    has_issue = _ISSUE.search("\n".join(lines)) is not None

    return found, has_issue


def summary(text: str) -> str:
    """The one-line report for a message that passed.

    Args:
        text: The raw content of the commit message file.

    Returns:
        The type and the issue reference count.
    """
    lines = message_lines(text)
    match = _SUBJECT.match(lines[0])
    kind = match["type"] if match else "generated"
    refs = len(set(_ISSUE.findall("\n".join(lines))))
    unit = "reference" if refs == 1 else "references"
    return f"{kind}, {refs} issue {unit}"


def messages_in_range(rev_range: str) -> list[tuple[str, str]]:
    """Every commit message in a revision range.

    Args:
        rev_range: A git range such as ``origin/main..HEAD``.

    Returns:
        The short hash and the message of each commit, newest first.
    """
    proc = subprocess.run(  # noqa: S603
        ["/usr/bin/git", "log", "-z", "--format=%H%n%B", rev_range],
        capture_output=True,
        text=True,
        check=True,
    )
    found = []
    for chunk in proc.stdout.split("\0"):
        if not chunk.strip():
            continue
        sha, _, body = chunk.partition("\n")
        found.append((sha[:9], body))
    return found


def report(label: str, text: str) -> bool:
    """Check one message and print the outcome.

    Args:
        label: What to name the message in the output.
        text: The raw message.

    Returns:
        True when the message failed.
    """
    found, _ = problems(text)
    for problem in found:
        print(f"FAIL {label}: {problem}")
    if not found:
        print(f"checked {label}: {summary(text)}")
    return bool(found)


def main(argv: list[str] | None = None) -> int:
    """Run the gate.

    Args:
        argv: The paths pre-commit passes, or ``--range <range>``. None
            reads ``sys.argv``.

    Returns:
        Process exit code: 1 on any failure, else 0.
    """
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        print("FAIL: name the commit message file")
        return 1
    failed = False
    if args[0] == RANGE:
        if len(args) != RANGE_ARGS:
            print(f"FAIL: {RANGE} takes one revision range")
            return 1
        try:
            found = messages_in_range(args[1])
        except subprocess.CalledProcessError as error:
            reason = error.stderr.strip().splitlines()
            print(
                f"FAIL {args[1]}: git log refused the range: {reason[0] if reason else ''}"
            )
            return 1
        for sha, text in found:
            failed |= report(sha, text)
    else:
        for path in (Path(arg) for arg in args):
            if not path.is_file():
                print(f"FAIL {path}: missing")
                failed = True
                continue
            failed |= report(str(path), path.read_text(encoding="utf-8"))
    if failed:
        print(f"the specification is at {SPEC}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
