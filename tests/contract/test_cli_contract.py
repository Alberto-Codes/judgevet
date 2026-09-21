"""Contract tests for CLI adapter."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import typer.testing

from judgevet.adapters.inbound.cli import (
    app,
    build_response_data,
    format_answer,
    output_response,
    parse_questions,
)
from judgevet.domain.answers import ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage


class TestBuildResponseData:
    """Tests for build_response_data function."""

    def test_build_response_data_empty(self) -> None:
        """Test building response data with empty answers."""
        response = SystemOneResponse(
            model="jev-1.13.0",
            usage=Usage(input_tokens=100, output_tokens=10),
            answers={},
        )
        response_data = build_response_data(response)
        assert response_data["model"] == "jev-1.13.0"
        assert "answers" in response_data

    def test_build_response_data_with_answers(self) -> None:
        """Test building response data with answers."""
        response = SystemOneResponse(
            model="jev-1.13.0",
            usage=Usage(input_tokens=100, output_tokens=10),
            answers={
                "q1": NoulAnswer(noul=0.75),
            },
        )
        response_data = build_response_data(response)
        assert response_data["model"] == "jev-1.13.0"
        assert "answers" in response_data
        assert "q1" in response_data["answers"]


class TestOutputResponse:
    """Tests for output_response function."""

    def test_output_response_json(self) -> None:
        """Test JSON output."""
        response = SystemOneResponse(
            model="jev-1.13.0",
            usage=Usage(input_tokens=100, output_tokens=10),
            answers={},
        )
        response_data = build_response_data(response)
        with patch("judgevet.adapters.inbound.cli.print") as mock_print:
            output_response(response_data, as_json=True)
            mock_print.assert_called_once()

    def test_output_response_text(self) -> None:
        """Test text output."""
        response = SystemOneResponse(
            model="jev-1.13.0",
            usage=Usage(input_tokens=100, output_tokens=10),
            answers={},
        )
        response_data = build_response_data(response)
        with patch("judgevet.adapters.inbound.cli.print") as mock_print:
            output_response(response_data, as_json=False)
            assert mock_print.call_count > 0

    def test_output_response_text_with_answers(self) -> None:
        """Test text output with answers."""
        response = SystemOneResponse(
            model="jev-1.13.0",
            usage=Usage(input_tokens=100, output_tokens=10),
            answers={
                "q1": NoulAnswer(noul=0.5),
            },
        )
        response_data = build_response_data(response)
        with patch("judgevet.adapters.inbound.cli.print") as mock_print:
            output_response(response_data, as_json=False)
            assert mock_print.call_count > 0


class TestParseQuestionsError:
    """Tests for parse_questions error paths."""

    def test_parse_questions_unknown_type(self) -> None:
        """Test parse_questions with unknown type raises ValueError."""
        questions_json = '{"q1": {"type": "unknown"}}'
        with pytest.raises(ValueError, match="Unknown question type"):
            parse_questions(questions_json)


class TestFormatAnswer:
    """Tests for format_answer function."""

    def test_format_answer_noul(self) -> None:
        """Test formatting noul answer."""
        answer = NoulAnswer(noul=0.5)
        formatted = format_answer("q1", answer)
        assert formatted["type"] == "noul"
        assert formatted["noul"] == 0.5

    def test_format_answer_choice(self) -> None:
        """Test formatting choice answer."""
        answer = ChoiceAnswer(
            choice="yes",
            confidence=0.8,
            probabilities={"yes": 0.8, "no": 0.2},
        )
        formatted = format_answer("q1", answer)
        assert formatted["type"] == "choice"
        assert formatted["choice"] == "yes"

    def test_format_answer_score(self) -> None:
        """Test formatting score answer."""
        answer = ScoreAnswer(
            score=3.5,
            confidence=0.9,
            legend={1: "poor", 2: "good"},
            probabilities={1: 0.1, 2: 0.9},
        )
        formatted = format_answer("q1", answer)
        assert formatted["type"] == "score"
        assert formatted["score"] == 3.5


class TestFormatAnswerError:
    """Tests for format_answer error paths."""

    def test_format_answer_unknown_type(self) -> None:
        """Test format_answer with unknown type raises TypeError."""

        # This test verifies the else branch in format_answer raises TypeError.
        # We create a fake answer type that is not one of the known answer types.
        class FakeAnswer:
            pass

        answer: Any = FakeAnswer()
        with pytest.raises(TypeError, match="Unknown answer type"):
            format_answer("q1", answer)


class TestMain:
    """Tests for main function."""

    runner = typer.testing.CliRunner()

    def test_main_success(self) -> None:
        """Test successful main execution."""
        with (
            patch(
                "judgevet.adapters.inbound.cli.HTTPSystemOneAdapter"
            ) as mock_adapter_cls,
            patch("judgevet.adapters.inbound.cli.parse_questions"),
            patch("judgevet.adapters.inbound.cli.print"),
        ):
            mock_adapter_instance = MagicMock()
            mock_adapter_instance.system_one.return_value = SystemOneResponse(
                model="jev-1.13.0",
                usage=Usage(input_tokens=10, output_tokens=0),
                answers={},
            )
            mock_adapter_cls.return_value = mock_adapter_instance

            result = self.runner.invoke(
                app,
                [
                    "test",
                    "{}",
                    "--model",
                    "test-model",
                    "--api-key",
                    "test-key",
                ],
                standalone_mode=False,
            )

            assert result.return_value == 0

    def test_main_error(self) -> None:
        """Test main function with error."""
        with (
            patch(
                "judgevet.adapters.inbound.cli.HTTPSystemOneAdapter"
            ) as mock_adapter_cls,
        ):
            mock_adapter_instance = MagicMock()
            mock_adapter_instance.system_one.side_effect = ValueError("Test error")
            mock_adapter_cls.return_value = mock_adapter_instance

            result = self.runner.invoke(
                app,
                [
                    "test",
                    "{}",
                    "--api-key",
                    "test-key",
                ],
                standalone_mode=False,
            )

            assert result.return_value == 1
            assert "Error: Test error" in result.stderr

    def test_main_error_json(self) -> None:
        """Test main function with error and JSON output."""
        with (
            patch(
                "judgevet.adapters.inbound.cli.HTTPSystemOneAdapter"
            ) as mock_adapter_cls,
            patch("judgevet.adapters.inbound.cli.print"),
            patch("judgevet.adapters.inbound.cli.json.dumps") as mock_json_dumps,
        ):
            mock_adapter_instance = MagicMock()
            mock_adapter_instance.system_one.side_effect = ValueError("Test error")
            mock_adapter_cls.return_value = mock_adapter_instance

            result = self.runner.invoke(
                app,
                [
                    "test",
                    "{}",
                    "--api-key",
                    "test-key",
                    "--json",
                ],
                standalone_mode=False,
            )

            assert result.return_value == 1
            mock_json_dumps.assert_called_once()
