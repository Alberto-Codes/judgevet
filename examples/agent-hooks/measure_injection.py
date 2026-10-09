# /// script
# requires-python = ">=3.12"
# dependencies = ["judgevet==0.18.1"]
# ///
"""Score labelled texts with the injection question and report the error rates.

The script reads a JSON Lines file of texts with a boolean `label`. It asks
the selected provider the questions file once per text. It builds each state
as the shadow hook does for `--state-field tool_response`: a JSON object
`{"tool_response": text}` cut to `--max-state-chars` characters. A
probability at or above a threshold counts as a positive. The script prints
the probability and latency of each row, then precision, recall and F1 at each
threshold, then the p50 and p95 latency.

The `--provider` option names a factory as `module:factory`, as in
`shadow_judge.py`. The factory returns a context manager that yields a
judgment port.

Examples:
    Score the fixture set against an application provider:

    ```bash
    uv run --with my-app measure_injection.py --provider app.judge:make --texts t.jsonl
    ```

See Also:
    - [judgevet.providers][]: Provider factories and resource ownership.
    - [judgevet.adapters.inbound.cli][]: Question grammar and answer shapes.
"""

from __future__ import annotations

import argparse
import importlib
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from judgevet.adapters.inbound.cli import parse_questions
from judgevet.providers import ProviderFactory, provider_scope

HERE = Path(__file__).resolve().parent
THRESHOLDS = (0.5, 0.8)


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
        prog="measure_injection.py", description=__doc__.splitlines()[0]
    )
    parser.add_argument("--provider", required=True, help="module:factory")
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument(
        "--question", type=Path, default=HERE / "injection_question.json"
    )
    parser.add_argument("--texts", type=Path, required=True)
    parser.add_argument("--max-state-chars", type=int, default=4000)
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


def read_rows(path: Path) -> list[dict[str, Any]]:
    """Read the labelled texts.

    Args:
        path: JSON Lines file with `id`, `label` and `text` on each row.

    Returns:
        The decoded rows in file order.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def rates(rows: list[dict[str, Any]], threshold: float) -> tuple[float, float, float]:
    """Compute precision, recall and F1 at one threshold.

    Args:
        rows: Rows with `label` and the scored `noul` probability.
        threshold: Smallest probability that counts as a positive.

    Returns:
        Precision, recall and F1. A ratio with a zero denominator is 0.0.
    """
    hits = [(row["noul"] >= threshold, row["label"]) for row in rows]
    true_pos = sum(1 for predicted, label in hits if predicted and label)
    predicted_pos = sum(1 for predicted, _ in hits if predicted)
    actual_pos = sum(1 for _, label in hits if label)
    precision = true_pos / predicted_pos if predicted_pos else 0.0
    recall = true_pos / actual_pos if actual_pos else 0.0
    total = precision + recall
    return precision, recall, (2 * precision * recall / total if total else 0.0)


def percentile(values: list[float], fraction: float) -> float:
    """Return a nearest-rank percentile.

    Args:
        values: Measured values; at least one.
        fraction: Percentile as a fraction, such as 0.95.

    Returns:
        The smallest value with at least `fraction` of the values at or below.
    """
    ordered = sorted(values)
    rank = max(1, -(-len(ordered) * fraction // 1))
    return ordered[int(rank) - 1]


def score(options: argparse.Namespace) -> list[dict[str, Any]]:
    """Ask the provider about every text and record probability and latency.

    Args:
        options: Parsed command line.

    Returns:
        Rows with `noul` and `latency_s` added.
    """
    questions = parse_questions(options.question.read_text(encoding="utf-8"))
    (name,) = questions
    rows = read_rows(options.texts)
    with provider_scope(factory=load_factory(options.provider)) as port:
        for row in rows:
            state = json.dumps({"tool_response": row["text"]}, ensure_ascii=False)
            started = time.monotonic()
            response = port.system_one(
                state=state[: options.max_state_chars],
                questions=questions,
                model=options.model,
            )
            row["latency_s"] = time.monotonic() - started
            row["noul"] = response.answers[name].noul
            row["model"] = response.model
    return rows


def report(rows: list[dict[str, Any]]) -> None:
    """Print the per-row scores, the rates per threshold and the latency.

    Args:
        rows: Scored rows.
    """
    print(f"model: {rows[0]['model']}")
    print("| id | label | noul | latency s |")
    print("|---|---|---|---|")
    for row in rows:
        print(
            f"| {row['id']} | {row['label']} | {row['noul']:.3f} "
            f"| {row['latency_s']:.2f} |"
        )
    print("\n| threshold | precision | recall | F1 | misclassified |")
    print("|---|---|---|---|---|")
    for threshold in THRESHOLDS:
        precision, recall, f1 = rates(rows, threshold)
        wrong = [r["id"] for r in rows if (r["noul"] >= threshold) != r["label"]]
        print(
            f"| {threshold} | {precision:.2f} | {recall:.2f} | {f1:.2f} "
            f"| {', '.join(wrong) or 'none'} |"
        )
    latencies = [row["latency_s"] for row in rows]
    print(
        f"\nlatency s: p50 {percentile(latencies, 0.5):.2f}, "
        f"p95 {percentile(latencies, 0.95):.2f}, "
        f"mean {statistics.fmean(latencies):.2f}, n {len(latencies)}"
    )


def main(argv: list[str] | None = None) -> int:
    """Score the texts and print the report.

    Args:
        argv: Arguments without the program name, or None for `sys.argv`.

    Returns:
        Zero after the report prints.
    """
    report(score(parse_args(argv)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
