# /// script
# requires-python = ">=3.12"
# dependencies = ["judgevet"]
# ///
"""Score the labelled Bash commands and report agreement with the labels.

The script reads `bash_risk_question.json` and the labelled JSON Lines
fixture set. It asks the selected provider the Score question once per
command. The state holds the `tool_input.command` and `cwd` fields in the same
shape that `shadow_judge.py` builds from a `PreToolUse` hook input. The
predicted level is the level with the highest probability.

It prints the row count, exact agreement, unweighted Cohen's kappa, recall on
`destructive`, the confusion matrix, and the p50 and p95 latency per call.
A row whose call fails counts as a disagreement and is reported by error type.
With `--rows`, it also writes one JSON Lines record per command.

Examples:
    Score the fixture set through an application provider:

    ```bash
    uv run --with my-app measure_bash_risk.py --provider my_app.judge:provider \
        --model my-model --fixtures bash_risk_commands.jsonl
    ```

See Also:
    - [judgevet.providers][]: Provider factories and resource ownership.
    - [judgevet.adapters.inbound.cli][]: Question grammar and answer shapes.
"""

from __future__ import annotations

import argparse
import importlib
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

from judgevet.adapters.inbound.cli import parse_questions
from judgevet.domain.errors import JudgevetError
from judgevet.providers import ProviderFactory, provider_scope

LEVELS = ("none", "low", "medium", "high", "destructive")
HERE = Path(__file__).resolve().parent
# Known per-row failures, as in shadow_judge.py. Anything else propagates.
KNOWN_FAILURES = (JudgevetError, TimeoutError, ValueError, OSError)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command line.

    Args:
        argv: Arguments without the program name, or None for `sys.argv`.

    Returns:
        Parsed options.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--provider", required=True, help="module:factory")
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument(
        "--question", type=Path, default=HERE / "bash_risk_question.json"
    )
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--rows", type=Path, default=None, help="Per-row JSONL")
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


def state_for(row: dict[str, str]) -> str:
    """Build the state that `shadow_judge.py` builds for this command.

    Args:
        row: Fixture row with `command` and `cwd`.

    Returns:
        A JSON object keyed by the dotted state-field paths.
    """
    selected = {"tool_input.command": row["command"], "cwd": row["cwd"]}
    return json.dumps(selected, ensure_ascii=False)


def score_rows(
    factory: ProviderFactory, model: str, question: dict[str, Any], rows: list[dict]
) -> list[dict[str, Any]]:
    """Ask the Score question about each row through one provider scope.

    Args:
        factory: Provider factory.
        model: Requested model.
        question: Typed questions keyed by name, holding one Score.
        rows: Labelled fixture rows.

    Returns:
        One result per row with the label, prediction, score, error and
        latency in milliseconds.
    """
    name = next(iter(question))
    results = []
    with provider_scope(factory=factory) as port:
        for row in rows:
            result: dict[str, Any] = {"command": row["command"], "label": row["label"]}
            started = time.monotonic()
            try:
                answer = port.system_one(
                    state=state_for(row), questions=question, model=model
                ).answers[name]
            except KNOWN_FAILURES as error:
                result.update(predicted=None, score=None, error=type(error).__name__)
            else:
                level = max(answer.probabilities, key=answer.probabilities.__getitem__)
                result.update(predicted=LEVELS[level], score=answer.score, error=None)
                result["probabilities"] = answer.probabilities
            result["latency_ms"] = round((time.monotonic() - started) * 1000)
            results.append(result)
    return results


def cohen_kappa(pairs: list[tuple[str, str | None]]) -> float:
    """Compute unweighted Cohen's kappa between labels and predictions.

    Args:
        pairs: Label and prediction per row; a None prediction never agrees.

    Returns:
        Kappa, or 1.0 when expected agreement is already 1.
    """
    total = len(pairs)
    observed = sum(label == predicted for label, predicted in pairs) / total
    labels = Counter(label for label, _ in pairs)
    predictions = Counter(predicted for _, predicted in pairs)
    expected = sum(labels[k] * predictions[k] for k in LEVELS) / total**2
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


def report(results: list[dict[str, Any]]) -> str:
    """Format agreement, kappa, recall, confusion and latency as text.

    Args:
        results: Per-row results from `score_rows`.

    Returns:
        The report text.
    """
    pairs = [(r["label"], r["predicted"]) for r in results]
    agree = sum(label == predicted for label, predicted in pairs)
    destructive = [p for label, p in pairs if label == "destructive"]
    recall = sum(p == "destructive" for p in destructive) / max(len(destructive), 1)
    latency = [r["latency_ms"] for r in results]
    errors = Counter(r["error"] for r in results if r["error"])
    lines = [
        f"n={len(results)} agreement={agree / len(results):.3f} ({agree})",
        f"kappa={cohen_kappa(pairs):.3f} destructive_recall={recall:.3f}",
        (
            f"latency_ms p50={percentile(latency, 0.5):.0f}"
            f" p95={percentile(latency, 0.95):.0f}"
        ),
        f"errors={dict(errors)}",
        "confusion (rows=label, columns=predicted)",
        "label".ljust(12) + "".join(level.ljust(12) for level in LEVELS),
    ]
    for label in LEVELS:
        counts = Counter(p for lab, p in pairs if lab == label)
        lines.append(
            label.ljust(12) + "".join(str(counts[p]).ljust(12) for p in LEVELS)
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Score the fixture set and print the report.

    Args:
        argv: Arguments without the program name, or None for `sys.argv`.

    Returns:
        0 when the report was printed.
    """
    options = parse_args(argv)
    question = parse_questions(options.question.read_text(encoding="utf-8"))
    lines = options.fixtures.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    results = score_rows(load_factory(options.provider), options.model, question, rows)
    if options.rows is not None:
        options.rows.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results),
            encoding="utf-8",
        )
    print(report(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
