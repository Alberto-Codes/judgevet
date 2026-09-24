"""Acceptance for finite public answer values and unchanged numeric bounds.

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


@pytest.mark.parametrize("kind", ["choice", "score"])
@pytest.mark.parametrize("delta", [0.0000005, 0.000002])
def test_probability_tolerance_unchanged(kind: str, delta: float) -> None:
    raw = numeric_payload(kind, "probabilities", 0.5)
    raw["probabilities"]["no" if kind == "choice" else "0"] += delta
    if delta < 0.000001:
        construct_answer(raw)
    else:
        with pytest.raises(ValueError):
            construct_answer(raw)


def test_no_new_argmax_or_expected_score_rule() -> None:
    assert ChoiceAnswer("yes", 0, {"yes": 0, "no": 1}).choice == "yes"
    assert ScoreAnswer(0, 0, {0: "Low", 1: "High"}, {0: 0, 1: 1}).score == 0


def test_large_integer_score_is_not_coerced_to_float() -> None:
    value = 10**1000
    assert ScoreAnswer(value, 1, {value: "Only"}, {value: 1}).score == value
