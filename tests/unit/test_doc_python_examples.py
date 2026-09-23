"""Behavioral acceptance for exact offline Python documentation execution."""

import importlib
from pathlib import Path

import pytest


def execute(tmp_path: Path, code: str) -> str | None:
    """Execute a written example through the production runner."""
    path = tmp_path / "example.py"
    path.write_text(code)
    runner = importlib.import_module("scripts.doc_python_child")
    return runner.run_example(path, "guide.md:7")


def test_documented_call_runs_without_network(tmp_path: Path) -> None:
    finding = execute(
        tmp_path,
        "from judgevet import HTTPSystemOneAdapter, Noul\n"
        'with HTTPSystemOneAdapter(api_key="synthetic") as adapter:\n'
        '    answer = adapter.system_one("state", {"q": Noul()})\n'
        'assert answer.nouls["q"].noul == 0.85\n',
    )
    assert finding is None


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (
            "from judgevet import HTTPSystemOneAdapter\nHTTPSystemOneAdapter()",
            "ValueError",
        ),
        ("assert False", "AssertionError"),
        ("not valid python!", "SyntaxError"),
        (
            'import socket\nsocket.create_connection(("example.com", 443))',
            "RuntimeError",
        ),
        (
            (
                "from judgevet import HTTPSystemOneAdapter\n"
                'adapter = HTTPSystemOneAdapter(api_key="synthetic")'
            ),
            "unclosed client",
        ),
    ],
)
def test_documentation_defects_fail(tmp_path: Path, code: str, expected: str) -> None:
    finding = execute(tmp_path, code)
    assert finding is not None
    assert "guide.md:7" in finding
    assert expected in finding


def test_example_cannot_read_inherited_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UNRELATED_SECRET", "not-for-the-example")
    finding = execute(
        tmp_path,
        'import os\nassert "UNRELATED_SECRET" not in os.environ\n'
        'assert os.environ["JEV_API__KEY"] == "synthetic-doc-key"\n',
    )
    assert finding is None
