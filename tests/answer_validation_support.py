"""Synthetic answer fixtures for constructor, parser and HTTP acceptance.

Examples:
    ```python
    from tests.answer_validation_support import answer_payload, construct_answer

    assert construct_answer(answer_payload("noul")).noul == 0.5
    ```

See Also:
    - [judgevet.domain.answers][]: Public answer constructors
    - [judgevet.domain.response_parser][]: Response validation
"""

from typing import Any

from judgevet import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer

FIELDS = [
    ("noul", "noul"),
    ("choice", "confidence"),
    ("choice", "probabilities"),
    ("score", "score"),
    ("score", "confidence"),
    ("score", "probabilities"),
]
INVALID_NUMBERS = [float("nan"), float("inf"), -float("inf"), True, False, "bad", None]


def answer_payload(kind: str) -> dict[str, Any]:
    """Return a fresh valid answer with zero-to-one bounds."""
    if kind == "noul":
        return {"type": kind, "noul": 0.5}
    if kind == "choice":
        return {
            "type": kind,
            "choice": "yes",
            "confidence": 0.5,
            "probabilities": {"yes": 0.5, "no": 0.5},
        }
    return {
        "type": kind,
        "score": 0.5,
        "confidence": 0.5,
        "legend": {"0": "Low", "1": "High"},
        "probabilities": {"0": 0.5, "1": 0.5},
    }


def numeric_payload(kind: str, field: str, value: Any) -> dict[str, Any]:
    """Set one numeric field, preserving valid distribution sums when possible."""
    answer = answer_payload(kind)
    if field == "probabilities":
        selected, other = ("yes", "no") if kind == "choice" else ("1", "0")
        answer[field][selected] = value
        answer[field][other] = 1 - value if isinstance(value, (int, float)) else 0
    else:
        answer[field] = value
    return answer


def construct_answer(raw: dict[str, Any]) -> Answer:
    """Call public constructors, converting only Score wire keys."""
    if raw["type"] == "noul":
        return NoulAnswer(raw["noul"])
    if raw["type"] == "choice":
        return ChoiceAnswer(raw["choice"], raw["confidence"], raw["probabilities"])
    return ScoreAnswer(
        raw["score"],
        raw["confidence"],
        {int(k): v for k, v in raw["legend"].items()},
        {int(k): v for k, v in raw["probabilities"].items()},
    )


def response_payload(answer: dict[str, Any], question: str = "q") -> dict[str, Any]:
    """Wrap an answer in a synthetic successful service envelope."""
    return {
        "model": "fixture",
        "usage": {"input_tokens": 1, "output_tokens": 1},
        "answers": {question: answer},
    }


def invalid_distributions() -> list[dict[str, Any]]:
    """Return failures of the existing distribution and membership rules."""
    choice = answer_payload("choice")
    score = answer_payload("score")
    return [
        dict(choice, choice="absent"),
        dict(choice, probabilities={"yes": 0.2, "no": 0.2}),
        dict(choice, probabilities={}),
        dict(score, probabilities={"0": 0.2, "1": 0.2}),
        dict(score, probabilities={"0": 0.5, "2": 0.5}),
        dict(score, legend={}, probabilities={}),
    ]


MALFORMED_ANSWERS = [
    numeric_payload(kind, field, value)
    for kind, field in FIELDS
    for value in [*INVALID_NUMBERS, -0.1, 1.1]
] + invalid_distributions()
