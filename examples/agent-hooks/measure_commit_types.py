# /// script
# requires-python = ">=3.12"
# dependencies = ["judgevet==0.18.1"]
# ///
"""Ask the commit questions about past commits and compare with the written labels.

The script reads every commit on `main` or `origin/main`, newest first, with
`git log --stat`. It skips merge commits and release-please commits, whose
subject starts with `chore(main): release`. It also skips a commit whose
subject has no type from the type question's labels. It takes the last
`--limit` eligible commits. It builds the state that `commit_shadow.py`
builds for each one. The diff stat of the commit itself takes the place of
the staged diff stat. It asks both questions in one call.

The report gives type agreement with the written type, Cohen's kappa and the
confusion matrix. It gives Closes/Refs agreement on the commits whose footer
names exactly one of `Closes` and `Refs`. It gives the p50 and p95 latency per
call and the five most confident type disagreements.

Examples:
    Measure the last 200 eligible commits on main:

    ```bash
    uv run --with my-app measure_commit_types.py --provider my_app.judge:provider
    ```

See Also:
    - [judgevet.providers][]: Provider factories and resource ownership.
    - [judgevet.adapters.inbound.cli][]: Question grammar and answer shapes.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any

from judgevet.adapters.inbound.cli import parse_questions
from judgevet.domain.errors import JudgevetError
from judgevet.providers import ProviderFactory, provider_scope

HERE = Path(__file__).resolve().parent
VERDICTS = ("closes", "refs")
RELEASE = "chore(main): release"
KNOWN_FAILURES = (JudgevetError, TimeoutError, ValueError, OSError)
_TYPE = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\([^()\n]*\))?!?: ")
_FOOTER = re.compile(r"^(?P<token>Closes|Refs)(?:: | #)", re.MULTILINE)


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
        prog="measure_commit_types.py", description=__doc__.splitlines()[0]
    )
    parser.add_argument("--provider", required=True, help="module:factory")
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--question", type=Path, default=HERE / "commit_questions.json")
    parser.add_argument("--ref", choices=("main", "origin/main"), default="main")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--max-state-chars", type=int, default=4000)
    parser.add_argument("--rows", type=Path, default=None, help="JSONL output")
    return parser.parse_args(argv)


def load_module(name: str) -> ModuleType:
    """Import a sibling example script by file name.

    Args:
        name: Script name without the `.py` suffix.

    Returns:
        The imported module.

    Raises:
        ImportError: If the script cannot be loaded.
    """
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"{name}.py not found")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def git_log(ref: str) -> str:
    """Run `git log --stat` on `main` or `origin/main`.

    Each argument list is fixed, so no input reaches the command line.

    Args:
        ref: `origin/main` for the remote-tracking branch; any other value
            reads the local `main`.

    Returns:
        The log output, one record per commit.
    """
    if ref == "origin/main":
        done = subprocess.run(
            [
                "/usr/bin/git",
                "log",
                "--format=%x1e%H%x1f%P%x1f%B%x1f",
                "--stat",
                "origin/main",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    else:
        done = subprocess.run(
            [
                "/usr/bin/git",
                "log",
                "--format=%x1e%H%x1f%P%x1f%B%x1f",
                "--stat",
                "main",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    return done.stdout


def history(ref: str) -> list[tuple[str, int, str, str]]:
    """Read every commit on the branch, newest first, with its diff stat.

    Args:
        ref: `main` or `origin/main`.

    Returns:
        The hash, parent count, full message and `--stat` output of each
        commit.
    """
    found = []
    for chunk in git_log(ref).split("\x1e")[1:]:
        sha, parents, message, stat = chunk.split("\x1f")
        found.append((sha, len(parents.split()), message.strip("\n"), stat))
    return found


def written_labels(
    message: str, types: tuple[str, ...] = ()
) -> tuple[str | None, str | None]:
    """Read the written type and the issue verdict of one message.

    Args:
        message: Full commit message.
        types: Allowed types; empty allows any type.

    Returns:
        The subject type when `types` allows it, else None. Then `closes` or
        `refs` when the footer lines use exactly one of the two tokens, else
        None.
    """
    match = _TYPE.match(message)
    kind = match["type"] if match else None
    if types and kind not in types:
        kind = None
    tokens = {found["token"].lower() for found in _FOOTER.finditer(message)}
    verdict = tokens.pop() if len(tokens) == 1 else None
    return kind, verdict


def eligible(subject: str, parents: int) -> bool:
    """Say whether a commit enters the measurement.

    Args:
        subject: First line of the message.
        parents: Number of parent commits.

    Returns:
        True for a single-parent commit that release-please did not write.
    """
    return parents == 1 and not subject.startswith(RELEASE)


def commits(ref: str, limit: int, types: tuple[str, ...]) -> list[dict[str, Any]]:
    """Collect the last eligible commits with their written labels and state.

    Args:
        ref: `main` or `origin/main`.
        limit: Maximum number of commits.
        types: Type labels of the type question.

    Returns:
        Rows with `sha`, `subject`, `message`, `type`, `verdict` and `stat`.
    """
    rows: list[dict[str, Any]] = []
    for sha, parents, message, stat in history(ref):
        subject = message.split("\n", 1)[0]
        kind, verdict = written_labels(message, types)
        if not eligible(subject, parents) or kind is None:
            continue
        rows.append(
            {"sha": sha[:9], "subject": subject, "message": message, "type": kind}
            | {"verdict": verdict, "stat": stat.strip("\n")}
        )
        if len(rows) == limit:
            break
    return rows


def judge_rows(
    options: argparse.Namespace, questions: dict[str, Any], rows: list[dict[str, Any]]
) -> None:
    """Ask both questions about each commit and add the answers to its row.

    Args:
        options: Parsed command line.
        questions: Typed `type` and `closes` questions.
        rows: Rows from `commits`; each gains predictions and latency.
    """
    shadow = load_module("shadow_judge")
    commit_shadow = load_module("commit_shadow")
    fields = list(commit_shadow.FIELDS)
    with provider_scope(factory=load_factory(options.provider)) as port:
        for row in rows:
            payload = commit_shadow.state_input(row["message"], row["stat"])
            state = shadow.build_state(payload, fields, options.max_state_chars)
            started = time.monotonic()
            try:
                response = port.system_one(
                    state=state, questions=questions, model=options.model
                )
            except KNOWN_FAILURES as error:
                row.update(error=type(error).__name__, model=None)
                row.update(predicted=None, confidence=0.0, closes=None)
            else:
                kind, closes = response.answers["type"], response.answers["closes"]
                row.update(error=None, model=response.model)
                row.update(predicted=kind.choice, confidence=kind.confidence)
                row.update(closes=closes.choice, closes_confidence=closes.confidence)
            row["latency_ms"] = round((time.monotonic() - started) * 1000)


def cohen_kappa(pairs: list[tuple[str, str | None]], labels: tuple[str, ...]) -> float:
    """Compute unweighted Cohen's kappa between labels and predictions.

    Args:
        pairs: Label and prediction per row; a None prediction never agrees.
        labels: Every label.

    Returns:
        Kappa, or 1.0 when expected agreement is already 1.
    """
    total = len(pairs)
    observed = sum(label == predicted for label, predicted in pairs) / total
    written = Counter(label for label, _ in pairs)
    predicted = Counter(prediction for _, prediction in pairs)
    expected = sum(written[k] * predicted[k] for k in labels) / total**2
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def percentile(values: list[int], fraction: float) -> float:
    """Return a percentile by linear interpolation between ranks.

    Args:
        values: Latencies in milliseconds.
        fraction: Percentile as a fraction, such as 0.95.

    Returns:
        The interpolated value.
    """
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def agreement(
    pairs: list[tuple[str, str | None]], labels: tuple[str, ...]
) -> list[str]:
    """Format agreement, kappa and the confusion matrix as Markdown lines.

    Args:
        pairs: Written label and prediction per row.
        labels: Every label, in matrix order.

    Returns:
        Report lines.
    """
    if not pairs:
        return ["n=0"]
    agree = sum(label == predicted for label, predicted in pairs)
    lines = [
        (
            f"n={len(pairs)} agreement={agree / len(pairs):.3f} ({agree})"
            f" kappa={cohen_kappa(pairs, labels):.3f}"
        ),
        "",
        "| written \\ judged | " + " | ".join(labels) + " |",
        "|---" * (len(labels) + 1) + "|",
    ]
    for label in labels:
        counts = Counter(p for written, p in pairs if written == label)
        cells = " | ".join(str(counts[p]) for p in labels)
        lines.append(f"| {label} | {cells} |")
    return lines


def report(rows: list[dict[str, Any]], types: tuple[str, ...]) -> str:
    """Format the type and issue verdict agreement, latency and disagreements.

    Args:
        rows: Judged rows.
        types: Type labels in matrix order.

    Returns:
        The report text.
    """
    latency = [row["latency_ms"] for row in rows]
    errors = Counter(row["error"] for row in rows if row["error"])
    misses = [r for r in rows if r["predicted"] and r["predicted"] != r["type"]]
    misses.sort(key=lambda row: row["confidence"], reverse=True)
    lines = [f"model={next((r['model'] for r in rows if r['model']), None)}"]
    kinds = [(r["type"], r["predicted"]) for r in rows]
    verdicts = [(r["verdict"], r["closes"]) for r in rows if r["verdict"]]
    lines += ["", "type", *agreement(kinds, types)]
    lines += ["", "closes/refs", *agreement(verdicts, VERDICTS)]
    lines += [
        "",
        (
            f"latency_ms per call p50={percentile(latency, 0.5):.0f}"
            f" p95={percentile(latency, 0.95):.0f} errors={dict(errors)}"
        ),
        "",
        "most confident type disagreements",
    ]
    lines += [
        f"{r['sha']} written={r['type']} judged={r['predicted']}"
        f" ({r['confidence']:.3f}) {r['subject']}"
        for r in misses[:5]
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Judge the commits and print the report.

    Args:
        argv: Arguments without the program name, or None for `sys.argv`.

    Returns:
        0 when the report was printed.
    """
    options = parse_args(argv)
    questions = parse_questions(options.question.read_text(encoding="utf-8"))
    types = tuple(questions["type"].criteria)
    rows = commits(options.ref, options.limit, types)
    judge_rows(options, questions, rows)
    if options.rows is not None:
        with options.rows.open("w", encoding="utf-8") as stream:
            for row in rows:
                kept = {k: v for k, v in row.items() if k not in ("message", "stat")}
                stream.write(json.dumps(kept, ensure_ascii=False) + "\n")
    print(report(rows, types))
    return 0


if __name__ == "__main__":
    sys.exit(main())
