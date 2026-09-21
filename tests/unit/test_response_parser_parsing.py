"""Tests for judgevet.domain.response_parser - parsing tests."""

from __future__ import annotations

from judgevet.domain.answers import ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.response_parser import parse_system_one_response


class TestParseSystemOneResponse:
    """Tests for parse_system_one_response."""

    def test_parses_noul_answer(self) -> None:
        """Test parsing a response with noul answer."""
        raw = {
            "model": "jev-latest",
            "answers": {
                "q1": {
                    "type": "noul",
                    "noul": 0.75,
                }
            },
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        result = parse_system_one_response("req-1", raw)

        assert isinstance(result, SystemOneResponse)
        assert result.model == "jev-latest"
        assert len(result.answers) == 1
        assert isinstance(result.answers["q1"], NoulAnswer)
        assert result.answers["q1"].noul == 0.75
        assert result.usage.input_tokens == 100
        assert result.usage.output_tokens == 50

    def test_parses_choice_answer(self) -> None:
        """Test parsing a response with choice answer."""
        raw = {
            "model": "jev-latest",
            "answers": {
                "q1": {
                    "type": "choice",
                    "choice": "yes",
                    "confidence": 0.8,
                    "probabilities": {"yes": 0.8, "no": 0.2},
                }
            },
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        result = parse_system_one_response("req-1", raw)

        assert isinstance(result.answers["q1"], ChoiceAnswer)
        assert result.answers["q1"].choice == "yes"
        assert result.answers["q1"].confidence == 0.8
        assert result.answers["q1"].probabilities == {"yes": 0.8, "no": 0.2}

    def test_parses_score_answer(self) -> None:
        """Test parsing a response with score answer."""
        raw = {
            "model": "jev-latest",
            "answers": {
                "q1": {
                    "type": "score",
                    "score": 3.5,
                    "confidence": 0.9,
                    "legend": {"1": "poor", "2": "fair", "3": "good"},
                    "probabilities": {"1": 0.1, "2": 0.2, "3": 0.3, "4": 0.4},
                }
            },
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        result = parse_system_one_response("req-1", raw)

        assert isinstance(result.answers["q1"], ScoreAnswer)
        assert result.answers["q1"].score == 3.5
        assert result.answers["q1"].legend == {1: "poor", 2: "fair", 3: "good"}
        assert result.answers["q1"].probabilities == {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4}

    def test_parses_multiple_answers(self) -> None:
        """Test parsing a response with multiple answers."""
        raw = {
            "model": "jev-latest",
            "answers": {
                "noul_q": {
                    "type": "noul",
                    "noul": 0.75,
                },
                "choice_q": {
                    "type": "choice",
                    "choice": "yes",
                    "confidence": 0.8,
                    "probabilities": {"yes": 0.8, "no": 0.2},
                },
            },
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        result = parse_system_one_response("req-1", raw)

        assert len(result.answers) == 2
        assert isinstance(result.answers["noul_q"], NoulAnswer)
        assert isinstance(result.answers["choice_q"], ChoiceAnswer)

    def test_empty_answers(self) -> None:
        """Test parsing a response with empty answers."""
        raw = {
            "model": "jev-latest",
            "answers": {},
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        result = parse_system_one_response("req-1", raw)

        assert isinstance(result, SystemOneResponse)
        assert result.answers == {}
