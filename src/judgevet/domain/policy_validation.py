"""Validate policy rules against immutable snapshots of question constraints.

Examples:
    ```python
    from judgevet.domain.questions import Noul
    from judgevet.domain.policy_rules import NoulRule, Policy
    from judgevet.domain.policy_validation import validate_policy

    validated = validate_policy(Policy((NoulRule("q", 0.5),)), {"q": Noul()})
    assert validated.rules[0].name == "q"
    ```

See Also:
    - [judgevet.domain.policy_rules][]: Typed policy definitions.
    - [judgevet.domain.policy_evaluation][]: Pure evaluation.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from judgevet.domain.policy_errors import PolicyDefinitionError
from judgevet.domain.policy_rules import ChoiceRule, NoulRule, Policy, Rule, ScoreRule
from judgevet.domain.questions import Choice, Noul, Question, Score


@dataclass(frozen=True, slots=True, init=False)
class ValidatedPolicy:
    """A validated policy with no retained mutable question objects.

    Construct through this class or validate_policy. Both paths validate.
    To change constraints, construct again with the new questions.

    Attributes:
        policy (Policy): Original immutable policy.
        rules (tuple): Rules in evaluation order.

    Examples:
        ```python
        validated = ValidatedPolicy(Policy((NoulRule("q", 0),)), {"q": Noul()})
        ```
    """

    policy: Policy
    _constraints: tuple[frozenset[str] | int | None, ...] = field(
        init=False, repr=False
    )

    def __init__(self, policy: Policy, questions: Mapping[str, Question]) -> None:
        """Validate every referenced question and snapshot its constraints.

        Args:
            policy (Policy): Ordered typed policy.
            questions: Typed questions keyed by name.

        Raises:
            PolicyDefinitionError: If policy or referenced questions are invalid.
        """
        if not isinstance(policy, Policy):
            raise PolicyDefinitionError("policy must be a Policy")
        if not isinstance(questions, Mapping):
            raise PolicyDefinitionError("questions must be a mapping")
        constraints = []
        for rule in policy.rules:
            if rule.name not in questions:
                raise PolicyDefinitionError("unknown question in rule")
            constraints.append(_constraint(rule, questions[rule.name]))
        object.__setattr__(self, "policy", policy)
        object.__setattr__(self, "_constraints", tuple(constraints))

    @property
    def rules(self) -> tuple[Rule, ...]:
        """Return rules in policy order.

        Returns:
            The immutable rule tuple.
        """
        return self.policy.rules


def _constraint(rule: Rule, question: Question) -> frozenset[str] | int | None:
    """Validate a question and retain only its policy-relevant constraints.

    Args:
        rule: Rule to validate.
        question (str): Referenced typed question.

    Returns:
        Choice labels, score ceiling, or None for Noul.

    Raises:
        PolicyDefinitionError: If question type or criteria do not match.
    """
    if isinstance(rule, NoulRule) and isinstance(question, Noul):
        return None
    if isinstance(rule, ChoiceRule) and isinstance(question, Choice):
        if not isinstance(question.criteria, Mapping):
            raise PolicyDefinitionError("choice criteria must be a mapping")
        if rule.choice not in question.criteria:
            raise PolicyDefinitionError("choice value not found in question criteria")
        if not all(isinstance(label, str) for label in question.criteria):
            raise PolicyDefinitionError("choice criteria labels must be strings")
        return frozenset(question.criteria)
    if isinstance(rule, ScoreRule) and isinstance(question, Score):
        if not isinstance(question.criteria, (list, tuple)) or not question.criteria:
            raise PolicyDefinitionError("score criteria must be a non-empty sequence")
        maximum = len(question.criteria) - 1
        if any(
            bound is not None and bound > maximum
            for bound in (rule.minimum, rule.maximum)
        ):
            raise PolicyDefinitionError("score bound is outside the question scale")
        return maximum
    raise PolicyDefinitionError("predicate does not match question type")


def validate_policy(
    policy: Policy, questions: Mapping[str, Question]
) -> ValidatedPolicy:
    """Validate a policy against typed questions without retaining mutable inputs.

    Args:
        policy (Policy): Typed ordered rules.
        questions: Question definitions keyed by name.

    Returns:
        A validated immutable policy.

    Raises:
        PolicyDefinitionError: If a definition or referenced question is invalid.
    """
    return ValidatedPolicy(policy, questions)
