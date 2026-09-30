"""Questions, answers and the policy the provider conformance kit uses.

The kit asks one Noul, one Choice and one Score question. `VALID_ANSWERS`
matches each question kind and passes the kit policy. Each entry of
`INVALID_ANSWERS` is a complete answer set with one answer that the public
policy evaluator rejects with `PolicyAnswerError`. The policy bounds admit any
well-typed answer, so a real provider passes whatever values its model returns.
`policy_problem` describes why a response fails the kit policy, so the
synchronous and asynchronous kits share one check. The data is synthetic and
needs no pytest.
Source: https://github.com/Alberto-Codes/judgevet/issues/241#issuecomment-5902293909.

Examples:
    ```python
    from judgevet.policy import evaluate_policy
    from judgevet.testing._conformance_cases import (
        CONFORMANCE_POLICY,
        CONFORMANCE_QUESTIONS,
        VALID_ANSWERS,
    )

    assert set(VALID_ANSWERS) == set(CONFORMANCE_QUESTIONS)
    assert evaluate_policy(CONFORMANCE_POLICY, VALID_ANSWERS).passed
    ```

    ```python
    from judgevet.domain.response import SystemOneResponse
    from judgevet.testing._conformance_cases import policy_problem

    assert policy_problem({}, "system_one") == (
        "system_one returned dict, not SystemOneResponse."
    )
    ```

See Also:
    - [judgevet.testing.conformance][]: The base class that asks these questions
    - [judgevet.policy][]: The evaluator that accepts or rejects the answers
    - [judgevet.domain.answers][]: The answer types and their validators
"""

from collections.abc import Mapping
from types import MappingProxyType

from judgevet.domain.answers import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.questions import Choice, Noul, Question, Score
from judgevet.domain.response import SystemOneResponse
from judgevet.policy import (
    ChoiceRule,
    NoulRule,
    Policy,
    PolicyAnswerError,
    ScoreRule,
    ValidatedPolicy,
    evaluate_policy,
    validate_policy,
)

CONFORMANCE_MODEL = "conformance-model"
"""The default model label the kit passes to a provider."""

CONFORMANCE_STATE = "A customer reports that one invoice was charged twice."
"""The synthetic state every kit judgment receives."""

CONFORMANCE_QUESTIONS: Mapping[str, Question] = MappingProxyType(
    {
        "conformance_noul": Noul(
            instructions="Does the state report a duplicate charge?"
        ),
        "conformance_choice": Choice(
            criteria={
                "billing": "A payment problem",
                "technical": "A product fault",
            },
            instructions="Which team should handle the state?",
        ),
        "conformance_score": Score(
            criteria=["calm", "concerned", "angry"],
            instructions="How upset is the customer?",
        ),
    }
)
"""One question of each kind, keyed by question name."""

VALID_ANSWERS: Mapping[str, Answer] = MappingProxyType(
    {
        "conformance_noul": NoulAnswer(noul=0.8),
        "conformance_choice": ChoiceAnswer(
            choice="billing",
            confidence=0.7,
            probabilities={"billing": 0.85, "technical": 0.15},
        ),
        "conformance_score": ScoreAnswer(
            score=1.2,
            confidence=0.4,
            legend={0: "calm", 1: "concerned", 2: "angry"},
            probabilities={0: 0.2, 1: 0.4, 2: 0.4},
        ),
    }
)
"""Typed answers that pass `CONFORMANCE_POLICY`, keyed by question name."""

INVALID_ANSWERS: Mapping[str, Mapping[str, Answer]] = MappingProxyType(
    {
        "noul_for_choice": MappingProxyType(
            {**VALID_ANSWERS, "conformance_choice": NoulAnswer(noul=0.9)}
        ),
        "choice_off_list": MappingProxyType(
            {
                **VALID_ANSWERS,
                "conformance_choice": ChoiceAnswer(
                    choice="refund", confidence=1.0, probabilities={"refund": 1.0}
                ),
            }
        ),
        "score_off_scale": MappingProxyType(
            {
                **VALID_ANSWERS,
                "conformance_score": ScoreAnswer(
                    score=4.0,
                    confidence=0.5,
                    legend={0: "a", 1: "b", 2: "c", 3: "d", 4: "e"},
                    probabilities={0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 1.0},
                ),
            }
        ),
    }
)
"""Named answer sets that the public policy evaluator rejects."""

CONFORMANCE_POLICY: ValidatedPolicy = validate_policy(
    Policy(
        (
            NoulRule("conformance_noul", minimum=0.0),
            ChoiceRule("conformance_choice", "billing"),
            ScoreRule("conformance_score", minimum=0.0),
        )
    ),
    CONFORMANCE_QUESTIONS,
)
"""A policy that accepts any well-typed answer to the kit questions."""

ANSWER_TYPES: Mapping[type, type] = MappingProxyType(
    {Noul: NoulAnswer, Choice: ChoiceAnswer, Score: ScoreAnswer}
)
"""The answer type each question type requires."""


def _type_mismatches(answers: Mapping[str, object]) -> str:
    """Describe answers whose type does not match their question kind.

    `evaluate_policy` enforces the answer types. This helper only names the
    mismatched questions in the failure message.

    Args:
        answers: The answers the provider returned, keyed by question name.

    Returns:
        One sentence per mismatched answer, or an empty string.
    """
    notes = []
    for name, question in CONFORMANCE_QUESTIONS.items():
        expected = ANSWER_TYPES[type(question)]
        answer = answers.get(name)
        if not isinstance(answer, expected):
            got = type(answer).__name__
            notes.append(f" {name} needs {expected.__name__}, got {got}.")
    return "".join(notes)


def policy_problem(response: object, source: str) -> str | None:
    """Describe why a response fails the kit policy.

    Args:
        response: The value the provider returned.
        source: The call that produced the response, for the message.

    Returns:
        A failure message when the response is not a `SystemOneResponse`,
        names other questions, or carries answers the policy rejects, or None
        when the policy accepts it.
    """
    if not isinstance(response, SystemOneResponse):
        return f"{source} returned {type(response).__name__}, not SystemOneResponse."
    if set(response.answers) != set(CONFORMANCE_QUESTIONS):
        return f"Answer names {sorted(response.answers)} differ from the questions."
    try:
        evaluate_policy(CONFORMANCE_POLICY, response.answers)
    except PolicyAnswerError as error:
        return (
            f"evaluate_policy rejected the answers: {error}."
            f"{_type_mismatches(response.answers)}"
        )
    return None
