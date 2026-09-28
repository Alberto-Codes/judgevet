"""Write a shields.io endpoint badge from a coverage JSON report (#50).

The docs workflow runs the suite, writes ``coverage json`` and calls this
script. The script writes ``site/badges/coverage.json``, and GitHub Pages
publishes it. The README badge asks shields.io to render that file. The
endpoint schema has ``schemaVersion``, ``label``, ``message`` and ``color``:
https://shields.io/badges/endpoint-badge

The script reads ``totals.covered_lines`` and ``totals.num_statements`` from
the ``coverage json`` report (format 3). JSON needs only the standard
``json`` module; XML parsing would need ``xml.etree``, which the ruff ``S``
rules flag as unsafe for untrusted input. The CI ``test`` job still uploads
``coverage.xml`` for people.

The figure is statement coverage, rounded to a whole percent as
``coverage report`` rounds it: it shows 100 only when every statement ran,
and 0 only when none did. A report with no statements counts as 100.

The colour comes from the rounded figure:

| figure | colour |
|---|---|
| 95 and above | brightgreen |
| 90 to 94 | green (the local ``fail_under`` floor is 90) |
| 80 to 89 | yellow |
| 70 to 79 | orange |
| below 70 | red |

The script exits 0 after it writes the badge. It exits 1 on a missing or
malformed report and writes nothing.

Examples:
    Measure the suite, then write the badge:

    ```console
    $ uv run pytest -q -n auto --cov -m "not live"
    $ uv run coverage json -o coverage.json
    $ uv run python scripts/coverage_badge.py coverage.json site/badges/coverage.json
    coverage badge: 97% brightgreen -> site/badges/coverage.json
    ```

See Also:
    - [judgevet][]: Package whose coverage the badge reports.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA = "https://shields.io/badges/endpoint-badge"
# Lowest rounded figure for each colour, highest first.
COLOURS = (
    (95, "brightgreen"),
    (90, "green"),
    (80, "yellow"),
    (70, "orange"),
    (0, "red"),
)
FULL = 100


def percent(text: str) -> int:
    """Read statement coverage from a coverage JSON report.

    Args:
        text: The report text that ``coverage json`` writes.

    Returns:
        The whole percent, never 100 or 0 unless exact.

    Raises:
        ValueError: If the report is not JSON or its totals are not two
            non-negative integers with covered at most valid.
    """
    try:
        totals = json.loads(text)["totals"]
        covered = totals["covered_lines"]
        valid = totals["num_statements"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError(f"not a coverage JSON report: {error}") from error
    counts = (covered, valid)
    if any(type(count) is not int for count in counts):
        raise ValueError(f"totals are not integers: {counts}")
    if not 0 <= covered <= valid:
        raise ValueError(f"covered {covered} is outside 0..{valid}")
    if covered == valid:
        return FULL
    figure = round(FULL * covered / valid)
    if covered and figure == 0:
        return 1
    return min(figure, FULL - 1)


def badge(figure: int) -> dict[str, object]:
    """Build the shields.io endpoint document for a coverage figure.

    Args:
        figure: The whole percent.

    Returns:
        The endpoint JSON object.
    """
    colour = next(name for floor, name in COLOURS if figure >= floor)
    return {
        "schemaVersion": 1,
        "label": "coverage",
        "message": f"{figure}%",
        "color": colour,
    }


def main(argv: list[str] | None = None) -> int:
    """Read the report and write the badge endpoint JSON.

    Args:
        argv: Command-line arguments; ``None`` reads ``sys.argv``.

    Returns:
        0 after the badge is written, 1 on a missing or malformed report.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", type=Path, help="coverage json output")
    parser.add_argument("output", type=Path, help="endpoint JSON to write")
    args = parser.parse_args(argv)
    try:
        document = badge(percent(args.report.read_text(encoding="utf-8")))
    except (OSError, ValueError) as error:
        print(f"coverage_badge: {args.report}: {error}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document) + "\n", encoding="utf-8")
    print(f"coverage badge: {document['message']} {document['color']} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
