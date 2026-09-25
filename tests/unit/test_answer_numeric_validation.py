"""Acceptance for finite answer values, numeric bounds and the sum allowance.

Examples:
    ```python
    from judgevet import NoulAnswer

    assert NoulAnswer(0).noul == 0
    ```

See Also:
    - [judgevet.domain.answers][]: Validated answer types
"""

from typing import Any

import pytest

from judgevet import ChoiceAnswer, ScoreAnswer
from tests.answer_validation_support import (
    FIELDS,
    INVALID_NUMBERS,
    construct_answer,
    invalid_distributions,
    numeric_payload,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("kind,field", FIELDS)
@pytest.mark.parametrize("value", INVALID_NUMBERS)
def test_invalid_numeric_values(kind: str, field: str, value: Any) -> None:
    expected = ValueError if isinstance(value, float) else TypeError
    with pytest.raises(expected):
        construct_answer(numeric_payload(kind, field, value))


@pytest.mark.parametrize("kind,field", FIELDS)
@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_finite_out_of_range(kind: str, field: str, value: float) -> None:
    with pytest.raises(ValueError):
        construct_answer(numeric_payload(kind, field, value))


@pytest.mark.parametrize("kind,field", FIELDS)
@pytest.mark.parametrize("value", [0, 1, 0.0, -0.0, 1.0, 0.25])
def test_valid_numeric_values(kind: str, field: str, value: float) -> None:
    answer = construct_answer(numeric_payload(kind, field, value))
    actual = getattr(answer, field)
    if field == "probabilities":
        actual = actual["yes" if kind == "choice" else 1]
    assert actual == value
    assert type(actual) is type(value)


@pytest.mark.parametrize("raw", invalid_distributions())
def test_domain_distribution_errors_remain_value_errors(raw: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        construct_answer(raw)


ROUNDED_FOUR = [0.1, 0.2, 0.3, 0.39]
"""Four two-decimal probabilities that sum to 0.99, as seen in issue #175."""


def test_rounded_four_level_score_constructs() -> None:
    legend = {1: "a", 2: "b", 3: "c", 4: "d"}
    probabilities = dict(zip(legend, ROUNDED_FOUR, strict=True))
    answer = ScoreAnswer(2.96, 0.39, legend, probabilities)
    assert answer.probabilities == probabilities


def test_rounded_four_label_choice_constructs() -> None:
    probabilities = dict(zip("abcd", ROUNDED_FOUR, strict=True))
    answer = ChoiceAnswer("d", 0.39, probabilities)
    assert answer.probabilities == probabilities


@pytest.mark.parametrize(
    "values",
    [[0.25, 0.25, 0.25, 0.22], [0.5, 0.485]],
    ids=["four_sum_0.97", "two_sum_0.985"],
)
def test_sum_beyond_per_entry_allowance_raises(values: list[float]) -> None:
    legend = {level: str(level) for level in range(len(values))}
    probabilities = dict(zip(legend, values, strict=True))
    with pytest.raises(ValueError, match=r"probabilities must sum to 1\.0"):
        ScoreAnswer(0, 0.5, legend, probabilities)
    with pytest.raises(ValueError, match=r"probabilities must sum to 1\.0"):
        ChoiceAnswer("0", 0.5, {str(k): v for k, v in probabilities.items()})


@pytest.mark.parametrize("kind", ["choice", "score"])
def test_float64_noise_constructs(kind: str) -> None:
    raw = numeric_payload(kind, "probabilities", 0.5)
    raw["probabilities"]["no" if kind == "choice" else "0"] += 0.0000005
    construct_answer(raw)
    assert ScoreAnswer(1, 1, {1: "a", 2: "b", 3: "c"}, {1: 0.1, 2: 0.2, 3: 0.7})


def test_no_new_argmax_or_expected_score_rule() -> None:
    assert ChoiceAnswer("yes", 0, {"yes": 0, "no": 1}).choice == "yes"
    assert ScoreAnswer(0, 0, {0: "Low", 1: "High"}, {0: 0, 1: 1}).score == 0


def test_large_integer_score_is_not_coerced_to_float() -> None:
    value = 10**1000
    assert ScoreAnswer(value, 1, {value: "Only"}, {value: 1}).score == value
