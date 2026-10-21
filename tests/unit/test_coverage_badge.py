"""Pin the coverage badge script's figure-to-endpoint mapping (#50)."""

import json
from pathlib import Path

import pytest

from scripts.coverage_badge import badge, main, percent

# The root line of a real Cobertura report from CI run 39528660965 at 392ce3b
# (coverage.py 7.16.1).
REAL_ROOT = (
    '<coverage version="7.16.1" timestamp="1792546913315" lines-valid="3904" '
    'lines-covered="3735" line-rate="0.9567" branches-covered="0" '
    'branches-valid="0" branch-rate="0" complexity="0">'
)
DECLARATION = '<?xml version="1.0" ?>\n'


def document(root: str, body: str = "") -> str:
    """Wrap a root tag and its body in a Cobertura document.

    Args:
        root: The opening ``<coverage ...>`` tag.
        body: The children of the root element.

    Returns:
        The XML text.
    """
    return f"{DECLARATION}{root}\n{body}</coverage>\n"


def report(covered: object, valid: object) -> str:
    """Build a Cobertura document with the given statement counts.

    Args:
        covered: The root ``lines-covered`` value.
        valid: The root ``lines-valid`` value.

    Returns:
        The XML text.
    """
    root = (
        f'<coverage version="7.16.1" lines-valid="{valid}" lines-covered="{covered}">'
    )
    return document(root)


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


def test_percent_reads_the_real_root_line() -> None:
    """Read 3735 of 3904 from the real CI root line as 96."""
    assert percent(document(REAL_ROOT)) == 96


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
    source = tmp_path / "coverage.xml"
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
        "not xml",
        "[]",
        document('<coverage version="7.16.1" lines-covered="5">'),
        report(covered=1, valid=0),
        report(covered="many", valid=10),
        report(covered=-1, valid=10),
        document(
            '<coverage version="7.16.1">',
            '<packages><package lines-covered="5" lines-valid="5"/></packages>\n',
        ),
    ],
)
def test_main_rejects_malformed_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str
) -> None:
    """Exit 1 on a malformed report and write no badge."""
    source = tmp_path / "coverage.xml"
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
    assert main([str(tmp_path / "absent.xml"), str(target)]) == 1
    assert "coverage_badge:" in capsys.readouterr().err
    assert not target.exists()
