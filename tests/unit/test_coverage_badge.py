"""Pin the coverage badge script's figure-to-endpoint mapping (#50)."""

import json
from pathlib import Path

import pytest

from scripts.coverage_badge import badge, main, percent

# The shape of a real ``coverage json`` report (coverage.py 7.16.1, format 3).
META = {"format": 3, "version": "7.16.1", "branch_coverage": False}


def report(covered: object, valid: object) -> str:
    """Build a coverage JSON document with the given statement counts.

    Args:
        covered: The ``totals.covered_lines`` value.
        valid: The ``totals.num_statements`` value.

    Returns:
        The JSON text.
    """
    totals = {"covered_lines": covered, "num_statements": valid}
    return json.dumps({"meta": META, "files": {}, "totals": totals})


@pytest.mark.parametrize(
    ("covered", "valid", "expected"),
    [
        (2963, 3065, 97),
        (1, 1, 100),
        (0, 1, 0),
        (0, 0, 100),
        (1999, 2000, 99),
        (1, 2000, 1),
        (1789, 2000, 89),
        (1791, 2000, 90),
    ],
)
def test_percent_rounds_like_coverage_report(
    covered: int, valid: int, expected: int
) -> None:
    """Round to a whole percent, never to 100 or 0 unless exact."""
    assert percent(report(covered, valid)) == expected


@pytest.mark.parametrize(
    ("figure", "colour"),
    [
        (100, "brightgreen"),
        (95, "brightgreen"),
        (94, "green"),
        (90, "green"),
        (89, "yellow"),
        (80, "yellow"),
        (79, "orange"),
        (70, "orange"),
        (69, "red"),
        (0, "red"),
    ],
)
def test_badge_colour_boundaries(figure: int, colour: str) -> None:
    """Map each threshold boundary to its documented colour."""
    assert badge(figure) == {
        "schemaVersion": 1,
        "label": "coverage",
        "message": f"{figure}%",
        "color": colour,
    }


def test_main_writes_endpoint_json(tmp_path: Path) -> None:
    """Write the endpoint JSON, creating the parent directory."""
    source = tmp_path / "coverage.json"
    source.write_text(report(2963, 3065))
    target = tmp_path / "site" / "badges" / "coverage.json"
    assert main([str(source), str(target)]) == 0
    assert json.loads(target.read_text()) == {
        "schemaVersion": 1,
        "label": "coverage",
        "message": "97%",
        "color": "brightgreen",
    }


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        json.dumps({"meta": META}),
        report(covered=1, valid=0),
        report(covered="many", valid=10),
        report(covered=True, valid=10),
        report(covered=-1, valid=10),
        json.dumps({"totals": {"num_statements": 10}}),
    ],
)
def test_main_rejects_malformed_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str
) -> None:
    """Exit 1 on a malformed report and write no badge."""
    source = tmp_path / "coverage.json"
    source.write_text(text)
    target = tmp_path / "badge.json"
    assert main([str(source), str(target)]) == 1
    assert "coverage_badge:" in capsys.readouterr().err
    assert not target.exists()


def test_main_rejects_missing_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 1 when the report file does not exist."""
    target = tmp_path / "coverage.json"
    assert main([str(tmp_path / "absent.json"), str(target)]) == 1
    assert "coverage_badge:" in capsys.readouterr().err
    assert not target.exists()
