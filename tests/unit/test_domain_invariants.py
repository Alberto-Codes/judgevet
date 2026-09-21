"""Invariants of the domain answer types.

Each test fails before #77 and passes after.

The domain must refuse to hold a judgment it cannot vouch for: a
probability out of range, a distribution that does not sum, a choice the
distribution never assigned, or a record that mutates after construction.

Examples:
    ```python
    import pytest

    from judgevet.domain.answers import NoulAnswer

    with pytest.raises(ValueError, match="noul"):
        NoulAnswer(noul=42.0)
    ```

See Also:
    - [judgevet.domain.answers][]: The answer types
    - [judgevet.domain.usage][]: Token counts
    - [judgevet.domain.response][]: Response container
"""

import pytest

from judgevet.domain.answers import ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage


class TestInvariants:
    """Each test asserts a construction that must raise."""

    @pytest.mark.unit
    def test_noul_above_one_raises(self) -> None:
        """A noul above 1 is refused."""
        with pytest.raises(ValueError, match="noul"):
            NoulAnswer(noul=42.0)

    @pytest.mark.unit
    def test_noul_below_zero_raises(self) -> None:
        """A noul below 0 is refused."""
        with pytest.raises(ValueError, match="noul"):
            NoulAnswer(noul=-0.1)

    @pytest.mark.unit
    def test_negative_confidence_raises(self) -> None:
        """A negative confidence is refused."""
        with pytest.raises(ValueError, match="confidence"):
            ChoiceAnswer(
                choice="yes",
                confidence=-3.0,
                probabilities={"yes": 0.8, "no": 0.2},
            )

    @pytest.mark.unit
    def test_confidence_above_one_raises(self) -> None:
        """A confidence above 1 is refused."""
        with pytest.raises(ValueError, match="confidence"):
            ChoiceAnswer(
                choice="yes",
                confidence=1.5,
                probabilities={"yes": 0.8, "no": 0.2},
            )

    @pytest.mark.unit
    def test_probabilities_value_above_one_raises(self) -> None:
        """A probability above 1 is refused."""
        with pytest.raises(ValueError, match="probability"):
            ChoiceAnswer(
                choice="yes",
                confidence=0.5,
                probabilities={"yes": 1.5, "no": 0.5},
            )

    @pytest.mark.unit
    def test_probabilities_not_summing_to_one_raise(self) -> None:
        """A set of probabilities that does not sum to 1 is refused."""
        with pytest.raises(ValueError, match="probabilities"):
            ChoiceAnswer(
                choice="yes",
                confidence=0.5,
                probabilities={"yes": 0.1, "no": 0.1},
            )

    @pytest.mark.unit
    def test_choice_absent_from_probabilities_raises(self) -> None:
        """A choice the distribution never assigned is refused."""
        with pytest.raises(ValueError, match="choice"):
            ChoiceAnswer(
                choice="maybe",
                confidence=0.5,
                probabilities={"yes": 0.5, "no": 0.5},
            )

    @pytest.mark.unit
    def test_score_outside_legend_range_raises(self) -> None:
        """A score outside the range the legend describes is refused."""
        with pytest.raises(ValueError, match="score"):
            ScoreAnswer(
                score=2.5,
                confidence=0.8,
                legend={0: "low", 1: "medium", 2: "high"},
                probabilities={0: 0.1, 1: 0.1, 2: 0.8},
            )

    @pytest.mark.unit
    def test_score_legend_and_probability_keys_disagree_raises(self) -> None:
        """Legend keys and probability keys must agree."""
        with pytest.raises(ValueError, match=r"legend|probabilities"):
            ScoreAnswer(
                score=2.0,
                confidence=0.9,
                legend={1: "poor", 2: "good"},
                probabilities={1: 0.5, 3: 0.5},
            )

    @pytest.mark.unit
    def test_score_negative_usage_input_tokens_raises(self) -> None:
        """Negative input_tokens is refused."""
        with pytest.raises(ValueError, match="input_tokens"):
            Usage(input_tokens=-100, output_tokens=50)

    @pytest.mark.unit
    def test_score_negative_usage_output_tokens_raises(self) -> None:
        """Negative output_tokens is refused."""
        with pytest.raises(ValueError, match="output_tokens"):
            Usage(input_tokens=100, output_tokens=-50)

    @pytest.mark.unit
    def test_mutation_after_construction_raises(self) -> None:
        """An answer is a record; it cannot change after construction."""
        answer = NoulAnswer(noul=0.5)
        field = "noul"
        value = 99
        with pytest.raises(AttributeError):
            setattr(answer, field, value)

    @pytest.mark.unit
    def test_systemone_response_mutation_raises(self) -> None:
        """A SystemOneResponse is a record; it cannot change after construction."""
        usage = Usage(input_tokens=100, output_tokens=50)
        response = SystemOneResponse(
            model="jev-latest",
            usage=usage,
        )
        field = "model"
        value = "mutated"
        with pytest.raises(AttributeError):
            setattr(response, field, value)

    @pytest.mark.unit
    def test_usage_mutation_raises(self) -> None:
        """A Usage is a record; it cannot change after construction."""
        usage = Usage(input_tokens=100, output_tokens=50)
        field = "input_tokens"
        value = 1
        with pytest.raises(AttributeError):
            setattr(usage, field, value)
