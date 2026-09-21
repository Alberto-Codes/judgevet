"""Test that the CLI works with a fake SystemOnePort.

This test verifies that the CLI adapter can be driven through a minimal
fake port defined entirely within this test file, without importing anything
from judgevet.ports. This proves that SystemOnePort is a structural protocol
and that the CLI composition root is properly typed against it.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from typing import Any

import typer.testing

from judgevet.adapters.inbound.cli import app, cli_main
from judgevet.domain.answers import NoulAnswer
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage


class _FakePort:
    """Minimal class satisfying SystemOnePort without importing it.

    This class is defined entirely within this test to prove that
    SystemOnePort is a structural protocol - any class with the right
    signature can satisfy it, even one from outside the judgevet package.
    """

    def __init__(self) -> None:
        """Initialize the fake port."""
        self.state: str | dict[str, Any] | list[Any] | None = None
        self.questions: Mapping[str, Any] | None = None
        self.model: str | None = None
        self._answer_value: float = 0.75
        self._closed: bool = False
        self._parsed_questions: dict[str, Any] = {}

    def close(self) -> None:
        """Close the port."""
        self._closed = True

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Any],
        model: str,
    ) -> SystemOneResponse:
        """Return a minimal valid response for testing."""
        # Record the call for verification
        self.state = state
        self.questions = questions
        self.model = model

        # Build the response with the same question keys that were sent
        answers: dict[str, Any] = {}
        for name in questions:
            answers[name] = NoulAnswer(noul=self._answer_value)

        return SystemOneResponse(
            model=model,
            usage=Usage(input_tokens=10, output_tokens=5),
            answers=answers,
        )


class TestCLIWithFakePort:
    """Tests for CLI driven through a fake port."""

    def test_run_cli_with_fake_port(self, monkeypatch) -> None:
        """Test that the typer app drives a fake port.

        This test drives the CLI through typer's entry point, proving that
        the composition root properly wires the port.
        """
        port = _FakePort()

        def fake_adapter(**kwargs):
            return port

        monkeypatch.setattr(
            "judgevet.adapters.inbound.cli.HTTPSystemOneAdapter",
            fake_adapter,
        )

        runner = typer.testing.CliRunner()
        result = runner.invoke(
            app,
            [
                "test content",
                '{"q1": {"type": "noul", "instructions": "Is this true?"}}',
                "--model",
                "test-model",
                "--json",
            ],
            standalone_mode=False,
        )

        assert result.exit_code == 0
        assert result.exception is None
        assert port.state == "test content"
        assert port.questions is not None
        assert "q1" in port.questions
        assert isinstance(port.questions, Mapping)
        assert port.questions["q1"].instructions == "Is this true?"
        assert port.model == "test-model"

    def test_run_cli_with_choice_question(self, monkeypatch) -> None:
        """Test the typer app with a choice question type."""
        port = _FakePort()
        port._answer_value = 0.85

        def fake_adapter(**kwargs):
            return port

        monkeypatch.setattr(
            "judgevet.adapters.inbound.cli.HTTPSystemOneAdapter",
            fake_adapter,
        )

        runner = typer.testing.CliRunner()
        result = runner.invoke(
            app,
            [
                "some state",
                '{"q1": {"type": "choice", "instructions": "What is it?"}}',
                "--model",
                "test-model",
            ],
            standalone_mode=False,
        )

        assert result.exit_code == 0
        assert result.exception is None
        assert port.state == "some state"
        assert port.questions is not None
        assert "q1" in port.questions
        assert isinstance(port.questions, Mapping)
        assert port.questions["q1"].instructions == "What is it?"

    def test_cli_main_delegates_to_main(self, monkeypatch) -> None:
        """Test that cli_main delegates to main."""
        port = _FakePort()

        def fake_adapter(**kwargs):
            return port

        monkeypatch.setattr(
            "judgevet.adapters.inbound.cli.HTTPSystemOneAdapter",
            fake_adapter,
        )

        old_argv = sys.argv
        try:
            sys.argv = [
                "jev",
                "legacy state",
                '{"q1": {"type": "noul", "instructions": "legacy?"}}',
                "--model",
                "legacy-model",
                "--json",
            ]
            assert cli_main() == 0
        finally:
            sys.argv = old_argv

        assert port.state == "legacy state"
        assert port.model == "legacy-model"
        assert port.questions is not None
        assert isinstance(port.questions, Mapping)
        assert port.questions["q1"].instructions == "legacy?"
