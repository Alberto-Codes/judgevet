"""Tests for judgevet.domain.response_parser - error handling tests."""

from __future__ import annotations

import pytest

from judgevet.domain.errors import JevResponseError
from judgevet.domain.response_parser import parse_system_one_response


class TestParseSystemOneResponseErrors:
    """Tests for error handling in parse_system_one_response."""

    def test_missing_model_field(self) -> None:
        """Test that missing model field raises JevResponseError."""
        raw = {
            "answers": {},
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        with pytest.raises(JevResponseError) as exc_info:
            parse_system_one_response("req-1", raw)

        assert "Missing required field 'model'" in str(exc_info.value)

    def test_missing_usage_field(self) -> None:
        """Test that missing usage field raises JevResponseError."""
        raw = {
            "model": "jev-latest",
            "answers": {},
        }

        with pytest.raises(JevResponseError) as exc_info:
            parse_system_one_response("req-1", raw)

        assert "Missing required field 'usage'" in str(exc_info.value)

    def test_missing_answers_field(self) -> None:
        """Test that missing answers field raises JevResponseError."""
        raw = {
            "model": "jev-latest",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        with pytest.raises(JevResponseError) as exc_info:
            parse_system_one_response("req-1", raw)

        assert "Missing required field 'answers'" in str(exc_info.value)

    def test_unknown_answer_type(self) -> None:
        """Test that unknown answer type raises JevResponseError."""
        raw = {
            "model": "jev-latest",
            "answers": {
                "q1": {
                    "type": "unknown_type",
                }
            },
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        with pytest.raises(JevResponseError) as exc_info:
            parse_system_one_response("req-1", raw)

        assert "Unknown answer type 'unknown_type'" in str(exc_info.value)
        assert "q1" in str(exc_info.value)

    def test_missing_noul_field(self) -> None:
        """Test that missing noul field raises JevResponseError."""
        raw = {
            "model": "jev-latest",
            "answers": {
                "q1": {
                    "type": "noul",
                }
            },
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        with pytest.raises(JevResponseError) as exc_info:
            parse_system_one_response("req-1", raw)

        assert "Missing required field 'noul'" in str(exc_info.value)

    def test_noul_not_a_number(self) -> None:
        """Test that non-numeric noul raises JevResponseError."""
        raw = {
            "model": "jev-latest",
            "answers": {
                "q1": {
                    "type": "noul",
                    "noul": "not-a-number",
                }
            },
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        with pytest.raises(JevResponseError) as exc_info:
            parse_system_one_response("req-1", raw)

        assert "is not a number" in str(exc_info.value)

    def test_missing_choice_fields(self) -> None:
        """Test that missing choice fields raise JevResponseError."""
        raw = {
            "model": "jev-latest",
            "answers": {
                "q1": {
                    "type": "choice",
                    "choice": "yes",
                }
            },
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        with pytest.raises(JevResponseError) as exc_info:
            parse_system_one_response("req-1", raw)

        assert "Missing required field" in str(exc_info.value)

    def test_missing_score_fields(self) -> None:
        """Test that missing score fields raise JevResponseError."""
        raw = {
            "model": "jev-latest",
            "answers": {
                "q1": {
                    "type": "score",
                    "score": 3.5,
                }
            },
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        with pytest.raises(JevResponseError) as exc_info:
            parse_system_one_response("req-1", raw)

        assert "Missing required field" in str(exc_info.value)

    def test_invalid_legend_key(self) -> None:
        """Test that invalid legend key raises JevResponseError."""
        raw = {
            "model": "jev-latest",
            "answers": {
                "q1": {
                    "type": "score",
                    "score": 3.5,
                    "confidence": 0.9,
                    "legend": {"not-an-int": "poor"},
                    "probabilities": {"1": 0.1},
                }
            },
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        with pytest.raises(JevResponseError) as exc_info:
            parse_system_one_response("req-1", raw)

        assert "Legend key 'not-an-int'" in str(exc_info.value)

    def test_invalid_probability_key(self) -> None:
        """Test that invalid probability key raises JevResponseError."""
        raw = {
            "model": "jev-latest",
            "answers": {
                "q1": {
                    "type": "score",
                    "score": 3.5,
                    "confidence": 0.9,
                    "legend": {"1": "poor"},
                    "probabilities": {"not-an-int": 0.1},
                }
            },
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        with pytest.raises(JevResponseError) as exc_info:
            parse_system_one_response("req-1", raw)

        assert "Probabilities key 'not-an-int'" in str(exc_info.value)

    def test_usage_with_string_tokens(self) -> None:
        """Test that usage tokens can be strings that convert to int."""
        raw = {
            "model": "jev-latest",
            "answers": {},
            "usage": {
                "input_tokens": "100",
                "output_tokens": "50",
            },
        }

        with pytest.raises(JevResponseError) as exc_info:
            parse_system_one_response("req-1", raw)

        # The tokens should be integers, not strings
        assert "is not an integer" in str(exc_info.value)

    def test_bool_not_accepted_as_int(self) -> None:
        """Test that boolean values are not accepted as integers."""
        raw = {
            "model": "jev-latest",
            "answers": {},
            "usage": {
                "input_tokens": True,
                "output_tokens": 50,
            },
        }

        with pytest.raises(JevResponseError) as exc_info:
            parse_system_one_response("req-1", raw)

        assert "is not an integer" in str(exc_info.value)

    def test_bool_not_accepted_as_float(self) -> None:
        """Test that boolean values are not accepted as floats."""
        raw = {
            "model": "jev-latest",
            "answers": {
                "q1": {
                    "type": "noul",
                    "noul": True,
                }
            },
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        with pytest.raises(JevResponseError) as exc_info:
            parse_system_one_response("req-1", raw)

        assert "is not a number" in str(exc_info.value)
