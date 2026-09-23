"""Strict typed policy evaluation over shared pure comparison functions.

The CLI compatibility bridge shares these comparisons while retaining its
historical answer checks. Public evaluation validates required scalars against
snapshotted question constraints and returns complete ordered reports.

Examples:
    ```python
    from judgevet.domain.answers import NoulAnswer
    from judgevet.domain.questions import Noul
    from judgevet.domain.policy_rules import NoulRule, Policy
    from judgevet.domain.policy_validation import validate_policy
    from judgevet.domain.policy_evaluation import evaluate_policy

    policy = validate_policy(Policy((NoulRule("q", 0.5),)), {"q": Noul()})
    assert evaluate_policy(policy, {"q": NoulAnswer(0.5)}).passed
    ```

See Also:
    - [judgevet.domain.policy_validation][]: Validated policy construction.
    - [judgevet.domain.policy_reports][]: Immutable report types.
"""

from collections.abc import Mapping

from judgevet.domain.answers import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.policy_checks import finite_number
from judgevet.domain.policy_comparisons import choice_report, range_report
from judgevet.domain.policy_errors import PolicyAnswerError, PolicyDefinitionError
from judgevet.domain.policy_reports import PolicyReport, RuleReport
from judgevet.domain.policy_rules import ChoiceRule, NoulRule, Rule, ScoreRule
from judgevet.domain.policy_validation import ValidatedPolicy


def _number(value: float, label: str, maximum: float | None) -> None:
    """Require a finite nonnegative answer scalar within its range.

    Args:
        value: Observed scalar.
        label: Fixed diagnostic label.
        maximum: Optional inclusive ceiling.

    Raises:
        PolicyAnswerError: If the scalar is invalid.
    """
    if not finite_number(value):
        raise PolicyAnswerError(f"{label} is nonfinite or not numeric")
    if value < 0 or (maximum is not None and value > maximum):
        raise PolicyAnswerError(f"{label} is outside the allowed range")


def _check_answer(
    rule: Rule, answer: Answer, constraint: frozenset[str] | int | None
) -> None:
    """Validate the required answer variant and selected scalars.

    Args:
        rule: Typed rule.
        answer: Observed answer.
        constraint: Snapshotted question constraints.

    Raises:
        PolicyAnswerError: If the answer type or values are invalid.
    """
    if isinstance(rule, NoulRule) and isinstance(answer, NoulAnswer):
        _number(answer.noul, "noul value", 1)
    elif isinstance(rule, ChoiceRule) and isinstance(answer, ChoiceAnswer):
        _number(answer.confidence, "choice confidence", 1)
        if (
            not isinstance(answer.choice, str)
            or not isinstance(constraint, frozenset)
            or answer.choice not in constraint
        ):
            raise PolicyAnswerError("choice value not found in question criteria")
    elif isinstance(rule, ScoreRule) and isinstance(answer, ScoreAnswer):
        _number(answer.confidence, "score confidence", 1)
        if not isinstance(constraint, int):
            raise PolicyAnswerError("score scale is invalid")
        _number(answer.score, "score", constraint)
    else:
        raise PolicyAnswerError("answer type mismatch for policy question")


def compare_rule(rule: Rule, answer: Answer) -> RuleReport:
    """Compute shared predicates for an already checked answer.

    Args:
        rule: Typed rule.
        answer: Matching answer variant.

    Returns:
        One immutable report with comparison details.

    Raises:
        PolicyAnswerError: If the answer does not match the rule type.
    """
    if isinstance(rule, NoulRule) and isinstance(answer, NoulAnswer):
        return RuleReport(rule.name, *range_report(rule, answer.noul, "noul", None))
    if isinstance(rule, ChoiceRule) and isinstance(answer, ChoiceAnswer):
        confidence = (
            None
            if rule.min_confidence is None
            else (answer.confidence, rule.min_confidence)
        )
        return RuleReport(
            rule.name, *choice_report(rule.name, rule.choice, answer.choice, confidence)
        )
    if isinstance(rule, ScoreRule) and isinstance(answer, ScoreAnswer):
        confidence = (
            None
            if rule.min_confidence is None
            else (answer.confidence, rule.min_confidence)
        )
        return RuleReport(
            rule.name, *range_report(rule, answer.score, "score", confidence)
        )
    raise PolicyAnswerError("answer type mismatch for policy question")


def evaluate_policy(
    policy: ValidatedPolicy, answers: Mapping[str, Answer]
) -> PolicyReport:
    """Evaluate every rule in order; unmet predicates return failed reports.

    Only selected answer scalars are checked. Probability distributions and
    legend metadata remain the answer types' responsibility.

    Args:
        policy: Validated immutable policy.
        answers: Typed answers keyed by question name.

    Returns:
        Every rule outcome with a derived aggregate verdict.

    Raises:
        PolicyDefinitionError: If policy is not validated.
        PolicyAnswerError: If required answers are missing or invalid.
    """
    if not isinstance(policy, ValidatedPolicy):
        raise PolicyDefinitionError("policy must be a ValidatedPolicy")
    if not isinstance(answers, Mapping):
        raise PolicyAnswerError("answers must be a mapping")
    reports = []
    for rule, constraint in zip(policy.rules, policy._constraints, strict=True):
        if rule.name not in answers:
            raise PolicyAnswerError("missing answer for policy question")
        answer = answers[rule.name]
        _check_answer(rule, answer, constraint)
        reports.append(compare_rule(rule, answer))
    return PolicyReport(tuple(reports))
