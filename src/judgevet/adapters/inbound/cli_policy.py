"""Compatibility wrapper for the historical CLI policy parser.

Examples:
    ```python
    from judgevet import Noul
    from judgevet.adapters.inbound.cli_policy import parse_policy

    rules = parse_policy(
        '{"rules":[{"question":"q","pass":{"noul":{"min":0.5}}}]}',
        {"q": Noul()},
    )
    assert rules[0].minimum == 0.5
    ```

See Also:
    - [judgevet.policy_json][]: Supported JSON decoding.
    - [judgevet.adapters.inbound.cli_policy_eval][]: Legacy evaluation bridge.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from judgevet.adapters.inbound.cli_inputs import InputFailure
from judgevet.domain.questions import Question, Score
from judgevet.policy import ChoiceRule, NoulRule, PolicyError, ScoreRule
from judgevet.policy_json import parse_policy as parse_typed_policy


@dataclass(frozen=True)
class Rule:
    """A validated policy rule.

    Attributes:
        name (str): Question name from the policy.
        kind (str): Question type: 'noul', 'choice', or 'score'.
        minimum (float | None): Minimum value for range predicates.
        maximum (float | None): Maximum value for range predicates.
        choice (str | None): Exact choice label for choice predicates.
        min_confidence (float | None): Minimum confidence for Choice/Score predicates.
        score_min (float): Minimum allowed score value (0 for all scores).
        score_max (float): Maximum allowed score value (len(criteria)-1).

    Examples:
        ```python
        rule = Rule("clear", "noul", minimum=0.8)
        assert rule.minimum == 0.8
        ```
    """

    name: str
    kind: str
    minimum: float | None = None
    maximum: float | None = None
    choice: str | None = None
    min_confidence: float | None = None
    score_min: float = 0.0
    score_max: float = 0.0


def _legacy_rule(
    rule: NoulRule | ChoiceRule | ScoreRule, questions: Mapping[str, Question]
) -> Rule:
    """Convert a validated typed rule to its historical CLI representation.

    Args:
        rule: Validated typed rule.
        questions: Original typed questions for score metadata.

    Returns:
        A legacy rule with the original field shape.
    """
    if isinstance(rule, NoulRule):
        return Rule(rule.name, "noul", rule.minimum, rule.maximum)
    if isinstance(rule, ChoiceRule):
        return Rule(
            rule.name, "choice", choice=rule.choice, min_confidence=rule.min_confidence
        )
    question = questions[rule.name]
    maximum = float(len(question.criteria) - 1) if isinstance(question, Score) else 0.0
    return Rule(
        rule.name,
        "score",
        rule.minimum,
        rule.maximum,
        min_confidence=rule.min_confidence,
        score_max=maximum,
    )


def parse_policy(text: str, questions: Mapping[str, Question]) -> tuple[Rule, ...]:
    """Decode through the shared JSON facade with historical CLI errors.

    Args:
        text: Raw JSON policy text.
        questions: Typed question definitions.

    Returns:
        Tuple of historical CLI rules in policy order.

    Raises:
        InputFailure: If policy decoding or validation fails.
    """
    try:
        policy = parse_typed_policy(text, questions)
    except PolicyError as error:
        raise InputFailure(f"--policy: {error}", code=1) from None
    return tuple(_legacy_rule(rule, questions) for rule in policy.rules)
