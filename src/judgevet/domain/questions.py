"""Question types for Jev API.

`question_types` maps each question id to its wire type name for audit records.

Examples:
    ```python
    from judgevet.domain.questions import Noul, Choice, Score

    noul = Noul(
        instructions="Is this a valid question?",
        criteria={"true": "It is valid", "false": "It is not valid"},
    )
    choice = Choice(
        criteria={"a": "Option A", "b": "Option B"},
        instructions="Choose one:",
    )
    score = Score(
        criteria=["Poor", "Fair", "Good", "Excellent"],
        instructions="Rate the response:",
    )
    ```

See Also:
    - [judgevet.domain.answers][]: Answer types
    - [judgevet.domain.response][]: Response container
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class Noul:
    """A yes/no question with optional descriptions for either outcome.

    See: https://docs.typesafe.ai/primitives/noul

    Construction is keyword-only; a positional argument raises `TypeError`.

    Attributes:
        instructions (str | dict | Sequence | None): Question or statement to evaluate.
        criteria (dict | None): Optional. An object with `true` and `false`
            descriptions of what a yes and a no mean.

    Examples:
        ```python
        question = Noul(
            instructions="Is this a valid question?",
            criteria={"true": "It is valid", "false": "It is not valid"},
        )
        assert question.instructions is not None
        ```

    See Also:
        - [judgevet.domain.questions.Question][]: Union type for all questions
        - [judgevet.domain.answers.NoulAnswer][]: Answer type for this question
    """

    __slots__ = ("criteria", "instructions")

    def __init__(
        self,
        *,
        instructions: str | dict[str, Any] | Sequence[Any] | None = None,
        criteria: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a Noul question.

        Every argument is keyword-only.

        Args:
            instructions: The yes/no question or statement to evaluate.
            criteria: Optional descriptions of the yes and no outcomes.
        """
        self.instructions = instructions
        self.criteria = criteria

    def __repr__(self) -> str:
        """Return a string representation of the Noul."""
        return f"Noul(instructions={self.instructions!r}, criteria={self.criteria!r})"


class Choice:
    """A question that selects between named alternatives.

    See: https://docs.typesafe.ai/primitives/choice

    Construction is keyword-only; a positional argument raises `TypeError`.

    Attributes:
        criteria (Mapping[str, str | dict | Sequence | None]): Labels mapped to
            descriptions. Each description takes one of four forms. A string
            describes the option in plain text. A live call has sent only the
            string form. An object gives structured guidance, such as what the
            option covers and what it does not. Source:
            https://docs.typesafe.ai/primitives/choice#structured-instructions-and-criteria.
            An array is an accepted form with no vendor example. Source:
            https://docs.typesafe.ai/primitives/choice. `None` means the
            option needs no extra detail. Source: https://docs.typesafe.ai/api.
            The object, array and `None` forms are inferred from those pages.
            No call has exercised them.
        instructions (str | dict | Sequence | None): The question to ask.

    Examples:
        ```python
        question = Choice(
            criteria={"a": "Option A", "b": "Option B"},
            instructions="Choose one:",
        )
        assert len(question.criteria) == 2
        ```

    See Also:
        - [judgevet.domain.questions.Question][]: Union type for all questions
        - [judgevet.domain.answers.ChoiceAnswer][]: Answer type for this question
    """

    __slots__ = ("criteria", "instructions")

    def __init__(
        self,
        *,
        criteria: Mapping[str, str | dict[str, Any] | Sequence[Any] | None],
        instructions: str | dict[str, Any] | Sequence[Any] | None = None,
    ) -> None:
        """Initialize a Choice question.

        Every argument is keyword-only.

        Args:
            criteria: Labels mapped to descriptions, or None for undescribed labels.
            instructions: The question to ask.
        """
        self.criteria = dict(criteria)
        self.instructions = instructions

    def __repr__(self) -> str:
        """Return a string representation of the Choice."""
        return f"Choice(criteria={self.criteria!r}, instructions={self.instructions!r})"


class Score:
    """A question that assigns a score using an ordered rubric.

    See: https://docs.typesafe.ai/primitives/score

    Construction is keyword-only; a positional argument raises `TypeError`.

    Attributes:
        criteria (Sequence[str | dict | Sequence]): Ordered list of descriptions.
        instructions (str | dict | Sequence | None): What the model should rate.

    Examples:
        ```python
        question = Score(
            criteria=["Poor", "Fair", "Good", "Excellent"],
            instructions="Rate the response:",
        )
        assert len(question.criteria) >= 2
        ```

    See Also:
        - [judgevet.domain.questions.Question][]: Union type for all questions
        - [judgevet.domain.answers.ScoreAnswer][]: Answer type for this question
    """

    __slots__ = ("criteria", "instructions")

    def __init__(
        self,
        *,
        criteria: Sequence[str | dict[str, Any] | Sequence[Any]],
        instructions: str | dict[str, Any] | Sequence[Any] | None = None,
    ) -> None:
        """Initialize a Score question.

        Every argument is keyword-only.

        Args:
            criteria: Ordered list of descriptions, one per score from zero.
            instructions: What the model should rate.
        """
        self.criteria = list(criteria)
        self.instructions = instructions

    def __repr__(self) -> str:
        """Return a string representation of the Score."""
        return f"Score(criteria={self.criteria!r}, instructions={self.instructions!r})"


Question = Noul | Choice | Score
"""A question object."""

_TYPE_NAMES: tuple[tuple[type, str], ...] = (
    (Noul, "noul"),
    (Choice, "choice"),
    (Score, "score"),
)


def question_types(questions: Mapping[str, Any]) -> dict[str, str | None]:
    """Map each question id to its wire type name, never its instructions.

    A typed question maps to `noul`, `choice` or `score`. A raw wire dictionary
    maps to its `type` value when that value is a string. The wire type names
    follow https://docs.typesafe.ai/api.

    Args:
        questions: Question objects or raw wire dictionaries keyed by id.

    Returns:
        The id to type mapping; None where a raw question has no string type.
    """
    types: dict[str, str | None] = {}
    for name, value in questions.items():
        kind = next((n for cls, n in _TYPE_NAMES if isinstance(value, cls)), None)
        if kind is None and isinstance(value, dict):
            raw = value.get("type")
            kind = raw if isinstance(raw, str) else None
        types[name] = kind
    return types
