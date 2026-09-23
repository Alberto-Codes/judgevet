"""Answer types returned by the Jev API.

The domain checks noul and confidence against [0,1] on construction. It checks
that probabilities sum to 1 and contain the selected choice. It also checks
that score lies in legend range and legend/probability keys match. Frozen
dataclasses prevent attribute reassignment; nested dictionaries remain mutable. Range comparisons
do not reject every nonfinite value. Public policy evaluation performs
additional finite-scalar checks.

Examples:
    ```python
    from judgevet.domain.answers import NoulAnswer, ChoiceAnswer, ScoreAnswer

    noul = NoulAnswer(noul=0.75)
    choice = ChoiceAnswer(
        choice="yes", confidence=0.8, probabilities={"yes": 0.8, "no": 0.2}
    )
    score = ScoreAnswer(
        score=2.5,
        confidence=0.9,
        legend={1: "poor", 2: "fair", 3: "good"},
        probabilities={1: 0.1, 2: 0.2, 3: 0.7},
    )
    ```

See Also:
    - [judgevet.domain.questions][]: Question types
    - [judgevet.domain.response][]: Response container
    - [judgevet.domain.usage][]: Token usage metadata
"""

from __future__ import annotations

from dataclasses import dataclass

PROBABILITY_SUM_TOLERANCE = 1e-6
"""Tolerance for probability sum validation.

Recorded sums in this repo deviate by 0.0. Float64 accumulation bound is k·ε
with ε = 2.22e-16. A 1000-key distribution accumulates at most ≈2.2e-13, so
1e-6 sits four orders of magnitude above the arithmetic worst case.

Open question: if the live service rounds probabilities to 2-3 decimals, a
normalized distribution can sum off by up to ~0.0005·k and would be rejected.
Change this tolerance only with observed evidence and record any rounding
behavior in docs/reference/api.md. Existing calls do not establish a general
rounding guarantee."""


@dataclass(frozen=True)
class NoulAnswer:
    """A yes/no answer with probability of true.

    See: https://docs.typesafe.ai/primitives/noul

    This is a frozen dataclass with validation in `__post_init__` to ensure
    noul is numeric (not bool) and in [0.0, 1.0].

    Attributes:
        noul (float): Probability of a yes answer or true statement, from 0 to 1.

    Examples:
        ```python
        answer = NoulAnswer(noul=0.75)
        assert 0.0 <= answer.noul <= 1.0
        ```

    See Also:
        - [judgevet.domain.answers.Answer][]: Union type for all answers
        - [judgevet.domain.response.SystemOneResponse][]: Response container
    """

    noul: float

    def __post_init__(self) -> None:
        """Validate noul is a float in [0.0, 1.0] and not a bool.

        Raises:
            TypeError: If noul is not a numeric type or is a bool.
            ValueError: If noul is outside [0.0, 1.0].
        """
        if isinstance(self.noul, bool) or not isinstance(self.noul, (int, float)):
            raise TypeError(f"noul must be float, got {type(self.noul).__name__}")
        if self.noul < 0.0 or self.noul > 1.0:
            raise ValueError(f"noul must be in [0.0, 1.0], got {self.noul}")


@dataclass(frozen=True)
class ChoiceAnswer:
    """A selected choice with probabilities and confidence.

    See: https://docs.typesafe.ai/primitives/choice

    This frozen dataclass validates values in `__post_init__`. Confidence and
    probabilities must be numeric and within [0.0, 1.0]. Probabilities must sum
    to 1.0 and contain the selected choice.

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
        - [judgevet.domain.answers.Answer][]: Union type for all answers
        - [judgevet.domain.response.SystemOneResponse][]: Response container
    """

    choice: str
    confidence: float
    probabilities: dict[str, float]

    def __post_init__(self) -> None:
        """Validate choice, confidence, and probabilities.

        Ensures confidence is numeric in [0.0, 1.0], all probability values are
        numeric in [0.0, 1.0], probabilities sum to 1.0, and choice is a key.

        Raises:
            TypeError: If confidence or any probability value is not numeric.
            ValueError: If confidence is outside [0.0, 1.0], any probability is
                outside [0.0, 1.0], probabilities do not sum to 1.0, or choice
                is missing from probabilities.
        """
        if isinstance(self.confidence, bool) or not isinstance(
            self.confidence, (int, float)
        ):
            raise TypeError(
                f"confidence must be float, got {type(self.confidence).__name__}"
            )
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")

        # Validate individual probability values first, then check sum
        for key, value in self.probabilities.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(
                    f"probability values must be float, got {type(value).__name__} for key '{key}'"
                )
            if value < 0.0 or value > 1.0:
                raise ValueError(
                    f"probability values must be in [0.0, 1.0], got {value} for key '{key}'"
                )

        if self.choice not in self.probabilities:
            raise ValueError(f"choice '{self.choice}' not in probabilities keys")

        total = sum(self.probabilities.values())
        if abs(total - 1.0) > PROBABILITY_SUM_TOLERANCE:
            raise ValueError(f"probabilities must sum to 1.0, got {total:.6f}")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(
                    f"probability values must be float, got {type(value).__name__} for key '{key}'"
                )
            if value < 0.0 or value > 1.0:
                raise ValueError(
                    f"probability values must be in [0.0, 1.0], got {value} for key '{key}'"
                )


@dataclass(frozen=True)
class ScoreAnswer:
    """A scored response with rubric and probabilities.

    See: https://docs.typesafe.ai/primitives/score

    This frozen dataclass validates values in `__post_init__`. Score must lie in
    legend range. Confidence and probabilities must be numeric and within
    [0.0, 1.0]. Probabilities must sum to 1.0, and legend/probability keys must match.

    Attributes:
        score (float): Expected score (probability-weighted average of rubric levels).
        confidence (float): Confidence in the score, from 0 to 1.
        legend (dict[int, str]): Rubric descriptions keyed by integer score.
        probabilities (dict[int, float]): Probability of each score level, keyed by integer score.

    Examples:
        ```python
        answer = ScoreAnswer(
            score=2.5,
            confidence=0.9,
            legend={1: "poor", 2: "fair", 3: "good"},
            probabilities={1: 0.1, 2: 0.2, 3: 0.7},
        )
        assert 1 <= len(answer.legend) == len(answer.probabilities)
        ```

    See Also:
        - [judgevet.domain.answers.Answer][]: Union type for all answers
        - [judgevet.domain.response.SystemOneResponse][]: Response container
    """

    score: float
    confidence: float
    legend: dict[int, str]
    probabilities: dict[int, float]

    def __post_init__(self) -> None:
        """Validate score, confidence, legend, and probabilities.

        Checks score against legend range and confidence against [0.0, 1.0].
        Checks numeric probabilities against [0.0, 1.0] and their sum against 1.0.
        Checks that legend/probability keys match.

        Raises:
            TypeError: If any numeric key or value is not the expected type.
            ValueError: If score is outside legend range, or confidence or any
                probability is outside [0.0, 1.0]. Also raised if probabilities
                do not sum to 1.0 or legend/probability keys do not match.
        """
        if isinstance(self.confidence, bool) or not isinstance(
            self.confidence, (int, float)
        ):
            raise TypeError(
                f"confidence must be float, got {type(self.confidence).__name__}"
            )
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")

        if set(self.legend.keys()) != set(self.probabilities.keys()):
            raise ValueError("legend keys must match probabilities keys")

        for key, value in self.probabilities.items():
            self._validate_numeric_key("probability", key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(
                    f"probability values must be float, got {type(value).__name__} for key {key}"
                )
            if value < 0.0 or value > 1.0:
                raise ValueError(
                    f"probability values must be in [0.0, 1.0], got {value} for key {key}"
                )

        total = sum(self.probabilities.values())
        if abs(total - 1.0) > PROBABILITY_SUM_TOLERANCE:
            raise ValueError(f"probabilities must sum to 1.0, got {total:.6f}")

        min_score = min(self.legend.keys())
        max_score = max(self.legend.keys())
        if self.score < min_score or self.score > max_score:
            raise ValueError(
                f"score must be in [{min_score}, {max_score}] (legend range), got {self.score}"
            )

    @staticmethod
    def _validate_numeric_key(name: str, key: object) -> None:
        """Validate that a key is an int and not a bool.

        Args:
            name: The name of the key for error messages.
            key: The key to validate.

        Raises:
            TypeError: If key is not an int or is a bool.
        """
        if not isinstance(key, int) or isinstance(key, bool):
            raise TypeError(f"{name} key must be int, got {type(key).__name__}")


Answer = NoulAnswer | ChoiceAnswer | ScoreAnswer
"""Union type for all possible answers."""
