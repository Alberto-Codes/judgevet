"""Question types for Jev API."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class Noul:
    """A yes/no question with optional descriptions for either outcome.

    See: https://docs.typesafe.ai/primitives/noul
    """

    __slots__ = ("criteria", "instructions")

    def __init__(
        self,
        instructions: str | dict[str, Any] | Sequence[Any] | None = None,
        criteria: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a Noul question.

        Args:
            instructions: The yes/no question or statement to evaluate.
            criteria: Optional descriptions of the yes and no outcomes.
        """
        self.instructions = instructions
        self.criteria = criteria

    def __repr__(self) -> str:
        return f"Noul(instructions={self.instructions!r}, criteria={self.criteria!r})"


class Choice:
    """A question that selects between named alternatives.

    See: https://docs.typesafe.ai/primitives/choice
    """

    __slots__ = ("criteria", "instructions")

    def __init__(
        self,
        criteria: Mapping[str, str | dict[str, Any] | Sequence[Any] | None],
        instructions: str | dict[str, Any] | Sequence[Any] | None = None,
    ) -> None:
        """Initialize a Choice question.

        Args:
            criteria: Labels mapped to descriptions, or None for undescribed labels.
            instructions: The question to ask.
        """
        self.criteria = dict(criteria)
        self.instructions = instructions

    def __repr__(self) -> str:
        return f"Choice(criteria={self.criteria!r}, instructions={self.instructions!r})"


class Score:
    """A question that assigns a score using an ordered rubric.

    See: https://docs.typesafe.ai/primitives/score
    """

    __slots__ = ("criteria", "instructions")

    def __init__(
        self,
        criteria: Sequence[str | dict[str, Any] | Sequence[Any]],
        instructions: str | dict[str, Any] | Sequence[Any] | None = None,
    ) -> None:
        """Initialize a Score question.

        Args:
            criteria: Ordered list of descriptions, one per score from zero.
            instructions: What the model should rate.
        """
        self.criteria = list(criteria)
        self.instructions = instructions

    def __repr__(self) -> str:
        return f"Score(criteria={self.criteria!r}, instructions={self.instructions!r})"


Question = Noul | Choice | Score
"""A question object."""
