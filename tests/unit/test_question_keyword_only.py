"""Acceptance tests for keyword-only question construction.

Examples:
    ```python
    from judgevet.domain.questions import Noul

    question = Noul(instructions="Is it valid?")
    assert question.instructions == "Is it valid?"
    ```

See Also:
    - [judgevet.domain.questions][]: The question types under test
"""

from __future__ import annotations

from typing import Any

import pytest

from judgevet.domain.questions import Choice, Noul, Score

pytestmark = pytest.mark.unit


def _construct_positionally(question_type: type[Any], value: object) -> object:
    """Call a constructor with one positional argument.

    The indirection keeps the type checker from rejecting the call statically.

    Args:
        question_type: The question class to construct.
        value: The single positional argument passed to the constructor.

    Returns:
        The constructed object, when the constructor accepts the call.
    """
    return question_type(value)


def test_noul_rejects_positional_construction() -> None:
    """Noul raises TypeError when instructions is passed positionally."""
    with pytest.raises(TypeError):
        _construct_positionally(Noul, "Is it valid?")


def test_choice_rejects_positional_construction() -> None:
    """Choice raises TypeError when criteria is passed positionally."""
    with pytest.raises(TypeError):
        _construct_positionally(Choice, {"a": "Option A", "b": "Option B"})


def test_score_rejects_positional_construction() -> None:
    """Score raises TypeError when criteria is passed positionally."""
    with pytest.raises(TypeError):
        _construct_positionally(Score, ["Poor", "Good"])


def test_keyword_construction_still_works() -> None:
    """All three classes accept their parameters by keyword."""
    noul = Noul(instructions="Is it valid?", criteria={"true": "yes", "false": "no"})
    choice = Choice(criteria={"a": "A", "b": None}, instructions="Pick one")
    score = Score(criteria=["Poor", "Good"], instructions="Rate it")

    assert noul.instructions == "Is it valid?"
    assert noul.criteria == {"true": "yes", "false": "no"}
    assert choice.criteria == {"a": "A", "b": None}
    assert choice.instructions == "Pick one"
    assert score.criteria == ["Poor", "Good"]
    assert score.instructions == "Rate it"
