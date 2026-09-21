"""Answer types returned by the Jev API.

Examples:
    ```python
    from jev_client.domain.answers import NoulAnswer, ChoiceAnswer, ScoreAnswer

    noul = NoulAnswer(noul=0.75)
    choice = ChoiceAnswer(
        choice="yes", confidence=0.8, probabilities={"yes": 0.8, "no": 0.2}
    )
    score = ScoreAnswer(
        score=3.5,
        confidence=0.9,
        legend={1: "poor", 2: "fair", 3: "good", 4: "excellent"},
        probabilities={1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4},
    )
    ```

See Also:
    - [jev_client.domain.questions][]: Question types
    - [jev_client.domain.response][]: Response container
"""

from __future__ import annotations


class NoulAnswer:
    """A yes/no answer with probability of true.

    See: https://docs.typesafe.ai/primitives/noul

    Attributes:
        noul (float): Probability of a yes answer or true statement, from 0 to 1.

    Examples:
        ```python
        answer = NoulAnswer(noul=0.75)
        assert 0.0 <= answer.noul <= 1.0
        ```

    See Also:
        - [jev_client.domain.answers.Answer][]: Union type for all answers
        - [jev_client.domain.response.SystemOneResponse][]: Response container
    """

    __slots__ = ("noul",)

    def __init__(self, noul: float) -> None:
        """Initialize a NoulAnswer.

        Args:
            noul: Probability of a yes answer or true statement, from 0 to 1.
        """
        self.noul = noul

    def __repr__(self) -> str:
        """Return a string representation of the NoulAnswer."""
        return f"NoulAnswer(noul={self.noul!r})"


class ChoiceAnswer:
    """A selected choice with probabilities and confidence.

    See: https://docs.typesafe.ai/primitives/choice

    Attributes:
        choice (str): The name of the choice with highest probability.
        confidence (float): Confidence in the selected choice, from 0 to 1.
        probabilities (dict[str, float]): Probability of each choice, keyed by choice name.

    Examples:
        ```python
        answer = ChoiceAnswer(
            choice="yes",
            confidence=0.8,
            probabilities={"yes": 0.8, "no": 0.2},
        )
        assert answer.choice in answer.probabilities
        ```

    See Also:
        - [jev_client.domain.answers.Answer][]: Union type for all answers
        - [jev_client.domain.response.SystemOneResponse][]: Response container
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
        """Return a string representation of the ChoiceAnswer."""
        return (
            f"ChoiceAnswer(choice={self.choice!r}, "
            f"confidence={self.confidence!r}, "
            f"probabilities={self.probabilities!r})"
        )


class ScoreAnswer:
    """A scored response with rubric and probabilities.

    See: https://docs.typesafe.ai/primitives/score

    Attributes:
        score (float): Expected score (probability-weighted average of rubric levels).
        confidence (float): Confidence in the score, from 0 to 1.
        legend (dict[int, str]): Rubric descriptions keyed by integer score.
        probabilities (dict[int, float]): Probability of each score level, keyed by integer score.

    Examples:
        ```python
        answer = ScoreAnswer(
            score=3.5,
            confidence=0.9,
            legend={1: "poor", 2: "fair", 3: "good", 4: "excellent"},
            probabilities={1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4},
        )
        assert 1 <= len(answer.legend) == len(answer.probabilities)
        ```

    See Also:
        - [jev_client.domain.answers.Answer][]: Union type for all answers
        - [jev_client.domain.response.SystemOneResponse][]: Response container
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
        """Return a string representation of the ScoreAnswer."""
        return (
            f"ScoreAnswer(score={self.score!r}, "
            f"confidence={self.confidence!r}, "
            f"legend={self.legend!r}, "
            f"probabilities={self.probabilities!r})"
        )


Answer = NoulAnswer | ChoiceAnswer | ScoreAnswer
"""Union type for all possible answers."""
