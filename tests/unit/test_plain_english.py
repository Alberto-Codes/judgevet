"""Acceptance tests for structural prose extraction and local writing rules."""

import importlib
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "text",
    [
        "# A robust library\n",
        "- A **powerful** client.\n",
        "| Feature | Detail |\n|---|---|\n| Client | Seamless setup |\n",
        "A [blazing client](https://example.com).\n",
        "A cutting-edge adapter.\n",
    ],
)
def test_banned_adjectives_in_prose(text: str, tmp_path: Path) -> None:
    checker = importlib.import_module("scripts.check_plain_english")
    path = tmp_path / "page.md"
    path.write_text(text)
    findings = checker.findings_for(path)
    assert len(findings) == 1
    assert "marketing adjective" in findings[0]
    assert f"{path}:" in findings[0]


@pytest.mark.parametrize(
    "text",
    [
        "Use `robust` as the literal value.\n",
        "```python\nrobust = 'powerful'\n```\n",
        "~~~text\nseamless\n~~~\n",
        "    robust = True\n",
        "Read [the reference](https://example.com/robust).\n",
        "<!-- robust -->\nRead the guide.\n",
        "---\nstatus: robust\n---\nRead the guide.\n",
        "Use version 0.7.0, e.g. for this example.\n",
    ],
)
def test_literal_syntax_is_not_prose(text: str, tmp_path: Path) -> None:
    checker = importlib.import_module("scripts.check_plain_english")
    path = tmp_path / "page.md"
    path.write_text(text)
    assert checker.findings_for(path) == []


def test_sentence_limit_keeps_abbreviations(tmp_path: Path) -> None:
    checker = importlib.import_module("scripts.check_plain_english")
    path = tmp_path / "page.md"
    path.write_text("A " + "word " * 12 + "e.g. " + "word " * 12 + "ends.\n")
    findings = checker.findings_for(path)
    assert len(findings) == 1
    assert "27 words" in findings[0]
    assert f"{path}:1:" in findings[0]


def test_sentence_boundary_and_exact_limit(tmp_path: Path) -> None:
    checker = importlib.import_module("scripts.check_plain_english")
    path = tmp_path / "page.md"
    path.write_text("word " * 24 + "ends.\n" + "word " * 24 + "ends.\n")
    assert checker.findings_for(path) == []


def test_docstrings_use_ast_sections_and_source_lines(tmp_path: Path) -> None:
    checker = importlib.import_module("scripts.check_plain_english")
    path = tmp_path / "module.py"
    path.write_text(
        '# robust comment\nVALUE = "powerful"\n\n'
        "def run(robust: str) -> None:\n"
        '    """Read a value.\n\n'
        "    Args:\n        robust: A seamless value.\n\n"
        '    Examples:\n        >>> robust = "blazing"\n'
        "        >>> print(robust)\n        blazing\n"
        '    """\n'
    )
    findings = checker.findings_for(path)
    assert len(findings) == 1
    assert f"{path}:8:" in findings[0]
    assert "seamless" in findings[0]


def test_source_syntax_error_is_not_silently_skipped(tmp_path: Path) -> None:
    checker = importlib.import_module("scripts.check_plain_english")
    path = tmp_path / "broken.py"
    path.write_text("def broken(\n")
    with pytest.raises(SyntaxError):
        checker.findings_for(path)
