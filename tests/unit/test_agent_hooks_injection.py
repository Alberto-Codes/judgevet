"""Prove the prompt-injection screen recipe in examples/agent-hooks (#311).

The question file must parse with the `--questions-file` grammar, and the
labelled fixture set must be well formed. No test calls a model.
"""

import json
from pathlib import Path

import pytest

from judgevet.adapters.inbound.cli import parse_questions
from judgevet.domain.questions import Noul

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
QUESTION = ROOT / "examples" / "agent-hooks" / "injection_question.json"
TEXTS = ROOT / "tests" / "fixtures" / "agent_hooks" / "injection_texts.jsonl"


def _rows() -> list[dict[str, object]]:
    """Read every fixture row."""
    lines = TEXTS.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def test_question_file_parses_as_one_noul_with_both_criteria() -> None:
    questions = parse_questions(QUESTION.read_text(encoding="utf-8"))
    assert list(questions) == ["injection"]
    question = questions["injection"]
    assert isinstance(question, Noul)
    assert isinstance(question.instructions, str)
    assert "AI agent" in question.instructions
    assert question.criteria is not None
    assert set(question.criteria) == {"true", "false"}


def test_fixture_rows_are_well_formed() -> None:
    rows = _rows()
    assert len(rows) >= 20
    for row in rows:
        assert set(row) == {"id", "label", "text"}
        assert isinstance(row["id"], str)
        assert isinstance(row["label"], bool)
        assert isinstance(row["text"], str)
        assert row["text"].strip()
    assert len({row["id"] for row in rows}) == len(rows)


def test_fixture_has_enough_positives_and_negatives() -> None:
    labels = [row["label"] for row in _rows()]
    assert labels.count(True) >= 8
    assert labels.count(False) >= 10
