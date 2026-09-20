"""Contract tests for CLI adapter."""

from unittest.mock import MagicMock, patch

import pytest

from jev_client.adapters.inbound.cli import (
    build_response_data,
    format_answer,
    main,
    output_response,
    parse_questions,
    parse_raw_answers,
)


class TestBuildResponseData:
    """Tests for build_response_data function."""

    def test_build_response_data(self) -> None:
        """Test building response data."""
        raw_response = {
            "model": "jev-1.13.0",
            "usage": {"input_tokens": 100, "output_tokens": 10},
        }
        answers = {}
        response_data = build_response_data(raw_response, answers)
        assert response_data["model"] == "jev-1.13.0"
        assert "answers" in response_data


class TestOutputResponse:
    """Tests for output_response function."""

    def test_output_response_json(self) -> None:
        """Test JSON output."""
        response_data = {
            "model": "jev-1.13.0",
            "usage": {"input_tokens": 100, "output_tokens": 10},
            "answers": {},
        }
        with patch("jev_client.adapters.inbound.cli.print") as mock_print:
            output_response(response_data, as_json=True)
            mock_print.assert_called_once()

    def test_output_response_text(self) -> None:
        """Test text output."""
        response_data = {
            "model": "jev-1.13.0",
            "usage": {"input_tokens": 100, "output_tokens": 10},
            "answers": {},
        }
        with patch("jev_client.adapters.inbound.cli.print") as mock_print:
            output_response(response_data, as_json=False)
            assert mock_print.call_count > 0

    def test_output_response_text_with_answers(self) -> None:
        """Test text output with answers."""
        response_data = {
            "model": "jev-1.13.0",
            "usage": {"input_tokens": 100, "output_tokens": 10},
            "answers": {
                "q1": {"name": "q1", "type": "noul", "noul": 0.5},
            },
        }
        with patch("jev_client.adapters.inbound.cli.print") as mock_print:
            output_response(response_data, as_json=False)
            assert mock_print.call_count > 0


class TestParseRawAnswers:
    """Tests for parse_raw_answers function."""

    def test_parse_raw_answers_noul(self) -> None:
        """Test parsing noul answers."""
        raw_response = {
            "answers": {
                "q1": {"type": "noul", "noul": 0.75},
            }
        }
        answers = parse_raw_answers(raw_response)
        assert "q1" in answers

    def test_parse_raw_answers_choice(self) -> None:
        """Test parsing choice answers."""
        raw_response = {
            "answers": {
                "q1": {
                    "type": "choice",
                    "choice": "option1",
                    "confidence": 0.95,
                    "probabilities": {"option1": 0.95},
                    "legend": None,
                },
            }
        }
        answers = parse_raw_answers(raw_response)
        assert "q1" in answers

    def test_parse_raw_answers_score(self) -> None:
        """Test parsing score answers."""
        raw_response = {
            "answers": {
                "q1": {
                    "type": "score",
                    "score": 2.5,
                    "confidence": 0.8,
                    "probabilities": {"0": 0.1},
                    "legend": {"0": "low"},
                },
            }
        }
        answers = parse_raw_answers(raw_response)
        assert "q1" in answers

    def test_parse_raw_answers_unknown_type(self) -> None:
        """Test parsing unknown answer type."""
        raw_response = {
            "answers": {
                "q1": {"type": "unknown", "value": "test"},
            }
        }
        with patch("jev_client.adapters.inbound.cli.print") as mock_print:
            answers = parse_raw_answers(raw_response)
            assert "q1" not in answers
            mock_print.assert_called_once()


class TestParseQuestionsError:
    """Tests for parse_questions error paths."""

    def test_parse_questions_unknown_type(self) -> None:
        """Test parse_questions with unknown type raises ValueError."""
        questions_json = '{"q1": {"type": "unknown"}}'
        with pytest.raises(ValueError, match="Unknown question type"):
            parse_questions(questions_json)


class TestFormatAnswerError:
    """Tests for format_answer error paths."""

    def test_format_answer_unknown_type(self) -> None:
        """Test format_answer with unknown type raises TypeError."""

    class FakeAnswer:
        pass

    with pytest.raises(TypeError, match="Unknown answer type"):
        format_answer("q1", FakeAnswer())


class TestMain:
    """Tests for main function."""

    def test_main_success(self) -> None:
        """Test successful main execution."""
        with (
            patch("jev_client.adapters.inbound.cli.parse_args") as mock_args,
            patch(
                "jev_client.adapters.inbound.cli.HTTPSystemOneAdapter"
            ) as mock_adapter,
            patch("jev_client.adapters.inbound.cli.parse_questions"),
            patch("jev_client.adapters.inbound.cli.json.loads") as mock_json_loads,
            patch("jev_client.adapters.inbound.cli.print"),
        ):
            mock_args.return_value.api_key = "test-key"
            mock_args.return_value.state = "test"
            mock_args.return_value.questions = "{}"
            mock_args.return_value.model = "test-model"
            mock_args.return_value.json = False
            mock_json_loads.return_value = {}

            mock_adapter_instance = MagicMock()
            mock_adapter_instance.system_one.return_value = {
                "model": "jev-1.13.0",
                "answers": {},
                "usage": {"input_tokens": 10, "output_tokens": 0},
            }
            mock_adapter.return_value.__enter__ = MagicMock(
                return_value=mock_adapter_instance
            )
            mock_adapter.return_value.__exit__ = MagicMock(return_value=False)

            result = main()
            assert result == 0

    def test_main_error(self) -> None:
        """Test main function with error."""
        with (
            patch("jev_client.adapters.inbound.cli.parse_args") as mock_args,
            patch(
                "jev_client.adapters.inbound.cli.HTTPSystemOneAdapter"
            ) as mock_adapter,
            patch("jev_client.adapters.inbound.cli.print"),
        ):
            mock_args.return_value.api_key = "test-key"
            mock_args.return_value.state = "test"
            mock_args.return_value.questions = "{}"
            mock_args.return_value.json = False

            mock_adapter.side_effect = ValueError("Test error")

            result = main()
            assert result == 1

    def test_main_error_json(self) -> None:
        """Test main function with error and JSON output."""
        with (
            patch("jev_client.adapters.inbound.cli.parse_args") as mock_args,
            patch(
                "jev_client.adapters.inbound.cli.HTTPSystemOneAdapter"
            ) as mock_adapter,
            patch("jev_client.adapters.inbound.cli.print"),
            patch("jev_client.adapters.inbound.cli.json.dumps") as mock_json_dumps,
        ):
            mock_args.return_value.api_key = "test-key"
            mock_args.return_value.state = "test"
            mock_args.return_value.questions = "{}"
            mock_args.return_value.json = True

            mock_adapter.side_effect = ValueError("Test error")

            result = main()
            assert result == 1
            mock_json_dumps.assert_called_once()
