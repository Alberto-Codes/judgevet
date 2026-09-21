"""Unit tests for CLI adapter."""

import pytest

from judgevet.adapters.inbound.cli import (
    format_answer,
    parse_args,
    parse_questions,
)
from judgevet.domain.answers import ChoiceAnswer, NoulAnswer, ScoreAnswer


class TestParseQuestions:
    """Tests for parse_questions function."""

    def test_parse_noul(self) -> None:
        """Test parsing a noul question."""
        questions_json = '{"q1": {"type": "noul", "instructions": "Is this a test?"}}'
        questions = parse_questions(questions_json)
        assert "q1" in questions
        assert questions["q1"].instructions == "Is this a test?"

    def test_parse_choice(self) -> None:
        """Test parsing a choice question."""
        questions_json = """{
            "q1": {
                "type": "choice",
                "instructions": "What is the tone?",
                "criteria": {"calm": "Calm", "angry": "Angry"}
            }
        }"""
        questions = parse_questions(questions_json)
        assert "q1" in questions
        assert len(questions["q1"].criteria) == 2

    def test_parse_score(self) -> None:
        """Test parsing a score question."""
        questions_json = """{
            "q1": {
                "type": "score",
                "instructions": "Rate this",
                "criteria": ["low", "medium", "high"]
            }
        }"""
        questions = parse_questions(questions_json)
        assert "q1" in questions
        assert len(questions["q1"].criteria) == 3


class TestFormatAnswer:
    """Tests for format_answer function."""

    def test_format_noul(self) -> None:
        """Test formatting a noul answer."""
        answer = NoulAnswer(noul=0.75)
        formatted = format_answer("q1", answer)
        assert formatted["name"] == "q1"
        assert formatted["type"] == "noul"
        assert formatted["noul"] == 0.75

    def test_format_choice(self) -> None:
        """Test formatting a choice answer."""
        answer = ChoiceAnswer(
            choice="option1",
            confidence=0.95,
            probabilities={"option1": 0.95, "option2": 0.05},
        )
        formatted = format_answer("q1", answer)
        assert formatted["name"] == "q1"
        assert formatted["type"] == "choice"
        assert formatted["choice"] == "option1"

    def test_format_score(self) -> None:
        """Test formatting a score answer."""
        answer = ScoreAnswer(
            score=2.5,
            confidence=0.8,
            legend={0: "low", 1: "medium", 2: "high"},
            probabilities={0: 0.1, 1: 0.1, 2: 0.8},
        )
        formatted = format_answer("q1", answer)
        assert formatted["name"] == "q1"
        assert formatted["type"] == "score"
        assert formatted["score"] == 2.5


class TestParseArgs:
    """Tests for parse_args function."""

    def test_parse_args(self) -> None:
        """Test parsing command line arguments."""
        with pytest.raises(SystemExit):
            parse_args()  # Should exit due to missing required args

    def test_parse_args_with_state(self) -> None:
        """Test parsing args with state argument."""
        with pytest.raises(SystemExit):
            parse_args()  # Still needs questions arg
