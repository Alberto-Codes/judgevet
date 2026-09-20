"""Unit tests for jev_client."""

import pytest

from jev_client.domain.answers import (
    ChoiceAnswer,
    NoulAnswer,
    ScoreAnswer,
)
from jev_client.domain.questions import Choice, Noul, Score
from jev_client.domain.response import SystemOneResponse
from jev_client.domain.usage import Usage


class TestDummy:
    """Dummy test to make coverage work."""

    @pytest.mark.unit
    def test_dummy(self) -> None:
        """A simple test that always passes."""
        assert True


class TestNoulAnswer:
    """Tests for NoulAnswer."""

    @pytest.mark.unit
    def test_init(self) -> None:
        """Test NoulAnswer initialization."""
        answer = NoulAnswer(0.5)
        assert answer.noul == 0.5


class TestNoul:
    """Tests for Noul question."""

    @pytest.mark.unit
    def test_init(self) -> None:
        """Test Noul initialization."""
        question = Noul(instructions="Is this a test?")
        assert question.instructions == "Is this a test?"


class TestChoice:
    """Tests for Choice question."""

    @pytest.mark.unit
    def test_init(self) -> None:
        """Test Choice initialization."""
        question = Choice(
            criteria={
                "option1": "First option",
                "option2": "Second option",
            }
        )
        assert len(question.criteria) == 2


class TestScore:
    """Tests for Score question."""

    @pytest.mark.unit
    def test_init(self) -> None:
        """Test Score initialization."""
        question = Score(
            criteria=["low", "medium", "high"],
            instructions="Rate this",
        )
        assert len(question.criteria) == 3


class TestChoiceAnswer:
    """Tests for ChoiceAnswer."""

    @pytest.mark.unit
    def test_init(self) -> None:
        """Test ChoiceAnswer initialization."""
        answer = ChoiceAnswer(
            choice="option1",
            confidence=0.95,
            probabilities={"option1": 0.95, "option2": 0.05},
        )
        assert answer.choice == "option1"
        assert answer.confidence == 0.95


class TestScoreAnswer:
    """Tests for ScoreAnswer."""

    @pytest.mark.unit
    def test_init(self) -> None:
        """Test ScoreAnswer initialization."""
        answer = ScoreAnswer(
            score=2.5,
            confidence=0.8,
            legend={0: "low", 1: "medium", 2: "high"},
            probabilities={0: 0.1, 1: 0.1, 2: 0.8},
        )
        assert answer.score == 2.5


class TestUsage:
    """Tests for Usage."""

    @pytest.mark.unit
    def test_init(self) -> None:
        """Test Usage initialization."""
        usage = Usage(input_tokens=100, output_tokens=10)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 10


class TestSystemOneResponse:
    """Tests for SystemOneResponse."""

    @pytest.mark.unit
    def test_init(self) -> None:
        """Test SystemOneResponse initialization."""
        usage = Usage(input_tokens=100)
        response = SystemOneResponse(
            model="jev-1.13.0",
            usage=usage,
            answers={"q1": NoulAnswer(0.5)},
        )
        assert response.model == "jev-1.13.0"
        assert len(response.answers) == 1


class TestRepr:
    """Tests for __repr__ methods."""

    @pytest.mark.unit
    def test_noul_answer_repr(self) -> None:
        """Test NoulAnswer __repr__."""
        answer = NoulAnswer(noul=0.5)
        assert "NoulAnswer" in repr(answer)

    @pytest.mark.unit
    def test_choice_answer_repr(self) -> None:
        """Test ChoiceAnswer __repr__."""
        answer = ChoiceAnswer(
            choice="option1",
            confidence=0.95,
            probabilities={"option1": 0.95},
        )
        assert "ChoiceAnswer" in repr(answer)

    @pytest.mark.unit
    def test_score_answer_repr(self) -> None:
        """Test ScoreAnswer __repr__."""
        answer = ScoreAnswer(
            score=2.5,
            confidence=0.8,
            legend={0: "low"},
            probabilities={0: 0.1},
        )
        assert "ScoreAnswer" in repr(answer)

    @pytest.mark.unit
    def test_usage_repr(self) -> None:
        """Test Usage __repr__."""
        usage = Usage(input_tokens=100, output_tokens=10)
        assert "Usage" in repr(usage)

    @pytest.mark.unit
    def test_noul_repr(self) -> None:
        """Test Noul __repr__."""
        question = Noul(instructions="Test?", criteria={"true": "Yes"})
        assert "Noul" in repr(question)

    @pytest.mark.unit
    def test_choice_repr(self) -> None:
        """Test Choice __repr__."""
        question = Choice(criteria={"a": None})
        assert "Choice" in repr(question)

    @pytest.mark.unit
    def test_score_repr(self) -> None:
        """Test Score __repr__."""
        question = Score(criteria=["a", "b"])
        assert "Score" in repr(question)

    @pytest.mark.unit
    def test_system_one_response_repr(self) -> None:
        """Test SystemOneResponse __repr__."""
        usage = Usage(input_tokens=100)
        response = SystemOneResponse(
            model="jev-1.13.0",
            usage=usage,
        )
        assert "SystemOneResponse" in repr(response)
