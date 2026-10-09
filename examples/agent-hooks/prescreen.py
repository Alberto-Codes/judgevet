# /// script
# requires-python = ">=3.12"
# dependencies = ["judgevet==0.19.0"]
# ///
r"""Measure a three-question Noul pre-screen of a slice; #312 found it does not predict review.

The script asks the questions in `prescreen_questions.json` about one slice:
whether the diff stays inside the allowed paths, whether an existing test was
weakened or removed, and whether a new or changed test would fail without the
production change. A policy built with `judgevet.policy` requires each answer
to reach `--minimum`, 0.8 by default. Every rule must pass.

The state is a JSON object with four parts: `contract`, `allowed_paths`,
`diff` and `builder_report`. Each part has its own character budget. The diff
part starts with the list of changed files and their added and removed line
counts. Test-file hunks follow, then the other hunks. The cut at the budget
therefore drops production hunks before test hunks, and it never drops the
file list. The default budgets are 2,000 contract characters, 5,500 diff
characters and 1,000 report characters. With the questions, that state fit a
4,096-token llama.cpp context in the #312 measurement; a larger state did not.

The script prints one JSON report to stdout. It holds the policy result, the
failed rules, each answer, the model and the latency. It exits 0 when the
policy passes and 1 when it fails. A provider or usage error propagates.

This is a measurement aid, not a gate. In the #312 measurement it did not
predict the independent acceptance review. It matched 13 of 17 slices,
against 15 of 17 for always-accept. It passed both reconstructed defects,
which the cut hid, and its answers saturated at 1.0. Never use its result
to skip or reduce review.

Examples:
    Re-run the #312 measurement on one slice; do not gate review on the result:

    ```bash
    git diff main > slice.diff
    uv run --with my-app prescreen.py --provider my_app.judge:provider \\
        --contract contract.md --diff slice.diff --report report.txt \\
        --allowed src/pkg/core.py --allowed tests/unit/test_core.py
    ```

See Also:
    - [judgevet.policy][]: Typed policy rules and their evaluation.
    - [judgevet.providers][]: Provider factories and resource ownership.
    - [judgevet.adapters.inbound.cli][]: Question grammar and answer shapes.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
import time
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from judgevet import Answer, Noul, NoulAnswer, SystemOnePort
from judgevet.adapters.inbound.cli import parse_questions
from judgevet.policy import (
    NoulRule,
    Policy,
    ValidatedPolicy,
    evaluate_policy,
    validate_policy,
)
from judgevet.providers import ProviderFactory, provider_scope

HERE = Path(__file__).resolve().parent
BUDGETS = {"contract": 2000, "diff": 5500, "report": 1000}
DIFF_CUT = "\n[diff cut at the budget]"
TEXT_CUT = "\n[cut at the budget]"
_HEADER = re.compile(r"^diff --git a/(?P<old>.*?) b/(?P<new>.*)$")
_SECTION = re.compile(r"^(?=diff --git )", re.MULTILINE)


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
        prog="prescreen.py", description=__doc__.splitlines()[0]
    )
    parser.add_argument("--provider", required=True, help="module:factory")
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--diff", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--allowed", action="append", default=[])
    parser.add_argument(
        "--question", type=Path, default=HERE / "prescreen_questions.json"
    )
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--minimum", type=float, default=0.8)
    for part, chars in BUDGETS.items():
        parser.add_argument(f"--max-{part}-chars", type=int, default=chars)
    return parser.parse_args(argv)


def load_factory(spec: str) -> ProviderFactory:
    """Import a provider factory named as `module:attribute`.

    Args:
        spec: Module path and factory attribute, separated by a colon.

    Returns:
        The callable that returns a context yielding a judgment port.

    Raises:
        ValueError: If the specification has no colon or no attribute.
    """
    module_name, separator, attribute = spec.partition(":")
    if not separator or not attribute:
        raise ValueError("--provider must name module:factory")
    return getattr(importlib.import_module(module_name), attribute)


def load_questions(path: Path) -> dict[str, Noul]:
    """Read the question file and require every question to be a Noul.

    Args:
        path: JSON question file in the CLI question grammar.

    Returns:
        The questions by key, in file order.

    Raises:
        ValueError: If a question is not a Noul, or the file does not parse.
    """
    parsed = parse_questions(path.read_text(encoding="utf-8"))
    others = [key for key, question in parsed.items() if not isinstance(question, Noul)]
    if others:
        raise ValueError(f"not a Noul question: {', '.join(others)}")
    return {key: q for key, q in parsed.items() if isinstance(q, Noul)}


def build_policy(questions: Mapping[str, Noul], minimum: float) -> ValidatedPolicy:
    """Build a policy that requires every Noul answer to reach a floor.

    Args:
        questions: Noul questions by key.
        minimum: Inclusive floor for each answer, between 0 and 1.

    Returns:
        The validated policy, one rule per question in key order.
    """
    rules = tuple(NoulRule(key, minimum=minimum) for key in questions)
    return validate_policy(Policy(rules), dict(questions))


def is_test_path(path: str) -> bool:
    """Return whether a changed path is a test, fixture or test helper.

    Args:
        path: Repository-relative file path.

    Returns:
        True for a path under a `tests` or `test` directory, a `test_*` or
        `*_test.py` file, or a `conftest.py`.
    """
    parts = PurePosixPath(path).parts
    name = parts[-1] if parts else ""
    return (
        "tests" in parts
        or "test" in parts
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


def split_diff(diff: str) -> list[tuple[str, str]]:
    """Split a unified git diff into one section per file.

    Args:
        diff: Output of `git diff` or `git show`.

    Returns:
        Pairs of the new path and the section text, in diff order. Text
        before the first file header is dropped.
    """
    sections = []
    for part in _SECTION.split(diff):
        match = _HEADER.match(part.split("\n", 1)[0])
        if match is not None:
            sections.append((match["new"], part))
    return sections


def line_counts(section: str) -> tuple[int, int]:
    """Count the added and removed lines in one file section.

    Args:
        section: One file's diff text.

    Returns:
        The added and removed line counts after the first hunk header.
    """
    added = removed = 0
    in_hunk = False
    for line in section.splitlines():
        if line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line.startswith("+"):
            added += 1
        elif in_hunk and line.startswith("-"):
            removed += 1
    return added, removed


def trim_diff(diff: str, budget: int) -> str:
    """Order a diff for judgment and cut it to a character budget.

    Args:
        diff: Output of `git diff` or `git show`.
        budget: Maximum characters. A file list longer than the budget is
            kept whole, so the result can then exceed it.

    Returns:
        The changed-file list, a blank line, then the test-file sections and
        the other sections. A cut ends with a marker line.
    """
    sections = split_diff(diff)
    listing = "\n".join(
        "- {} (+{} -{})".format(path, *line_counts(text)) for path, text in sections
    )
    tests = [text for path, text in sections if is_test_path(path)]
    others = [text for path, text in sections if not is_test_path(path)]
    whole = f"Changed files:\n{listing}\n\n" + "".join(tests + others)
    if len(whole) <= budget:
        return whole
    keep = max(budget - len(DIFF_CUT), len("Changed files:\n") + len(listing))
    return whole[:keep] + DIFF_CUT


def cut(text: str, budget: int) -> str:
    """Keep the start of a text within a character budget.

    Args:
        text: Text to cut.
        budget: Characters to keep before the marker.

    Returns:
        The text, or its first `budget` characters and a marker line.
    """
    return text if len(text) <= budget else text[:budget] + TEXT_CUT


def build_state(
    contract: str,
    allowed: list[str],
    diff: str,
    report: str,
    budgets: Mapping[str, int],
) -> dict[str, str]:
    """Build the judgment state for one slice.

    Args:
        contract: Accepted contract text.
        allowed: Allowed paths from the brief; may be empty.
        diff: The builder's unified diff.
        report: Excerpt of the builder's return report; may be empty.
        budgets: Character budgets keyed `contract`, `diff` and `report`.

    Returns:
        The `contract`, `allowed_paths`, `diff` and `builder_report` parts.
    """
    return {
        "contract": cut(contract, budgets["contract"]),
        "allowed_paths": "\n".join(allowed) or "(none listed)",
        "diff": trim_diff(diff, budgets["diff"]),
        "builder_report": cut(report, budgets["report"]) or "(none given)",
    }


def noul(answer: Answer) -> float | None:
    """Return the value of a Noul answer.

    Args:
        answer: One typed answer from the response.

    Returns:
        The Noul probability, or None for another answer type.
    """
    return answer.noul if isinstance(answer, NoulAnswer) else None


def judge(
    port: SystemOnePort,
    state: dict[str, str],
    questions: dict[str, Noul],
    policy: ValidatedPolicy,
    model: str,
) -> dict[str, Any]:
    """Ask the questions in one call and evaluate the policy.

    Args:
        port: Judgment port from the provider.
        state: State from `build_state`.
        questions: Noul questions by key.
        policy: Policy from `build_policy`.
        model: Model name passed to the port.

    Returns:
        The policy result, the failed rule names, each Noul value, the
        answering model and the latency in milliseconds.
    """
    started = time.monotonic()
    response = port.system_one(state=state, questions=questions, model=model)
    latency_ms = round((time.monotonic() - started) * 1000)
    report = evaluate_policy(policy, response.answers)
    return {
        "passed": report.passed,
        "failed": [rule.question for rule in report.rules if not rule.passed],
        "answers": {key: noul(response.answers[key]) for key in questions},
        "model": response.model,
        "latency_ms": latency_ms,
    }


def main(argv: list[str] | None = None) -> int:
    """Pre-screen one slice and print the JSON report.

    Args:
        argv: Arguments without the program name, or None for `sys.argv`.

    Returns:
        0 when the policy passes, 1 when it fails.
    """
    options = parse_args(argv)
    questions = load_questions(options.question)
    policy = build_policy(questions, options.minimum)
    report = options.report.read_text(encoding="utf-8") if options.report else ""
    state = build_state(
        options.contract.read_text(encoding="utf-8"),
        options.allowed,
        options.diff.read_text(encoding="utf-8"),
        report,
        {part: getattr(options, f"max_{part}_chars") for part in BUDGETS},
    )
    with provider_scope(factory=load_factory(options.provider)) as port:
        result = judge(port, state, questions, policy, options.model)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
