"""Answer types returned by the Jev API."""

from __future__ import annotations


class NoulAnswer:
    """A yes/no answer with probability of true.

    See: https://jevaiguide.com/jev-api/
    """

    __slots__ = ("noul",)

    def __init__(self, noul: float) -> None:
        """Initialize a NoulAnswer.

        Args:
            noul: Probability of a yes answer or true statement, from 0 to 1.
        """
        self.noul = noul

    def __repr__(self) -> str:
        return f"NoulAnswer(noul={self.noul})"


class ChoiceAnswer:
    """A selected choice with probabilities and confidence.

    See: https://jevaiguide.com/jev-api/
    """

    __slots__ = ("choice", "confidence", "probabilities")

    def __init__(
        self,
        choice: str,
        confidence: float,
        probabilities: dict[str, float],
    ) -> None:
        """Initialize a ChoiceAnswer.

        Args:
            choice: The name of the choice with highest probability.
            confidence: Confidence in the selected choice, from 0 to 1.
            probabilities: Probability of each choice, keyed by choice name.
        """
        self.choice = choice
        self.confidence = confidence
        self.probabilities = probabilities

    def __repr__(self) -> str:
        return f"ChoiceAnswer(choice={self.choice!r}, confidence={self.confidence}, probabilities={self.probabilities})"


class ScoreAnswer:
    """A scored response with rubric and probabilities.

    See: https://jevaiguide.com/jev-api/
    """

    __slots__ = ("confidence", "legend", "probabilities", "score")

    def __init__(
        self,
        score: float,
        confidence: float,
        legend: dict[int, str],
        probabilities: dict[int, float],
    ) -> None:
        """Initialize a ScoreAnswer.

        Args:
            score: Expected score (probability-weighted average of rubric levels).
            confidence: Confidence in the score, from 0 to 1.
            legend: Rubric descriptions keyed by integer score.
            probabilities: Probability of each score level, keyed by integer score.
        """
        self.score = score
        self.confidence = confidence
        self.legend = legend
        self.probabilities = probabilities

    def __repr__(self) -> str:
        return f"ScoreAnswer(score={self.score}, confidence={self.confidence}, legend={self.legend}, probabilities={self.probabilities})"


Answer = NoulAnswer | ChoiceAnswer | ScoreAnswer
"""Union type for all possible answers."""
