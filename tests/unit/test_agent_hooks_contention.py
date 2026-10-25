"""Prove that backend contention is recorded apart from a judgment timeout (#352).

A provider that refuses because another model holds the backend raises the
neutral ``ProviderBusyError``. The shadow runner records that name, and the
two measurement scripts count such rows apart from agreement.
"""

import importlib
import importlib.util
import io
import json
from argparse import Namespace
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from judgevet.domain.errors import JevError

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "agent-hooks"
HOOKS = ROOT / "tests" / "fixtures" / "agent_hooks"
BUSY = "tests.fixtures.providers.busy_provider:busy"


def _load(name: str) -> ModuleType:
    """Import one example script from its path.

    Args:
        name: Script file name under ``examples/agent-hooks``.

    Returns:
        The imported module.
    """
    spec = importlib.util.spec_from_file_location(name[:-3], EXAMPLES / name)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_busy_error_is_a_neutral_unavailable_error() -> None:
    """The busy error is exported and sits under ``ProviderUnavailableError``."""
    providers = importlib.import_module("judgevet.providers")
    provider_errors = importlib.import_module("judgevet.domain.provider_errors")
    busy = providers.ProviderBusyError
    assert issubclass(busy, providers.ProviderUnavailableError)
    assert not issubclass(busy, JevError)
    assert "ProviderBusyError" in provider_errors.__all__
    assert "ProviderBusyError" in providers.__all__
    assert provider_errors.ProviderBusyError is busy


def test_shadow_record_names_the_busy_error(tmp_path: Path) -> None:
    """A busy provider yields an error record that is not a timeout, at once."""
    log = tmp_path / "shadow.jsonl"
    hook = (HOOKS / "pre_tool_use_bash.json").read_text(encoding="utf-8")
    argv = [
        "--provider",
        BUSY,
        "--question",
        str(HOOKS / "questions.json"),
        "--log",
        str(log),
        "--timeout",
        "5",
    ]
    code = _load("shadow_judge.py").main(argv, io.StringIO(hook))
    record = json.loads(log.read_text(encoding="utf-8"))
    assert code == 0
    assert record["error"] == "ProviderBusyError"
    assert record["answers"] is None
    assert record["latency_ms"] < 1000


def test_bash_risk_report_counts_contention_apart(tmp_path: Path) -> None:
    """Busy rows leave the agreement denominator; other failures stay in it."""
    module = _load("measure_bash_risk.py")

    def row(label: str, predicted: str | None, error: str | None) -> dict[str, Any]:
        """Build one scored row.

        Args:
            label: Fixture label.
            predicted: Predicted level, or None on failure.
            error: Error type name, or None.

        Returns:
            A result row in the shape ``score_rows`` writes.
        """
        return {
            "command": "x",
            "label": label,
            "predicted": predicted,
            "score": None,
            "error": error,
            "latency_ms": 10,
        }

    results = [
        row("none", "none", None),
        row("high", "high", None),
        row("none", "low", None),
        row("medium", None, "TimeoutError"),
        row("none", None, "ProviderBusyError"),
    ]
    text = module.report(results)
    assert "n=4 agreement=0.500 (2)" in text
    assert "contention=1" in text
    assert "errors={'TimeoutError': 1}" in text


def test_injection_score_marks_busy_rows(tmp_path: Path) -> None:
    """A busy provider gives each text an error name and no probability."""
    module = _load("measure_injection.py")
    texts = tmp_path / "texts.jsonl"
    texts.write_text(
        json.dumps({"id": "a", "label": True, "text": "ignore previous"})
        + "\n"
        + json.dumps({"id": "b", "label": False, "text": "plain"})
        + "\n",
        encoding="utf-8",
    )
    options = Namespace(
        provider=BUSY,
        model="m",
        question=EXAMPLES / "injection_question.json",
        texts=texts,
        max_state_chars=4000,
    )
    rows = module.score(options)
    assert [r["error"] for r in rows] == ["ProviderBusyError", "ProviderBusyError"]
    assert [r["noul"] for r in rows] == [None, None]


def test_injection_report_counts_contention_apart(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Busy rows are counted once and left out of the rates and the latency."""
    module = _load("measure_injection.py")
    rows = [
        {"id": "a", "label": True, "noul": 0.9, "latency_s": 0.5, "model": "m"},
        {
            "id": "b",
            "label": False,
            "noul": None,
            "latency_s": 0.01,
            "error": "ProviderBusyError",
        },
        {
            "id": "c",
            "label": True,
            "noul": None,
            "latency_s": 20.0,
            "error": "TimeoutError",
        },
    ]
    module.report(rows)
    out = capsys.readouterr().out
    assert "contention=1" in out
    assert "| 0.5 | 1.00 | 0.50 | 0.67 | c |" in out
    assert out.rstrip().endswith("n 2")
