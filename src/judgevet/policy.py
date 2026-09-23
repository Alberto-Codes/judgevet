"""Supported pure typed policy API.

Rules, policies and reports are immutable. Validation snapshots question
constraints without retaining mutable questions. Construct a new ValidatedPolicy
with new questions to change those constraints. Callers own all IO and adapters.

Examples:
    ```python
    from judgevet import Noul, NoulAnswer
    from judgevet.policy import NoulRule, Policy, validate_policy, evaluate_policy

    policy = Policy((NoulRule("clear", minimum=0.8),))
    validated = validate_policy(policy, {"clear": Noul(instructions="Clear?")})
    report = evaluate_policy(validated, {"clear": NoulAnswer(0.9)})
    assert report.passed
    ```

See Also:
    - [judgevet.domain.policy_rules][]: Typed rule definitions.
    - [judgevet.domain.policy_validation][]: Question-relative validation.
    - [judgevet.domain.policy_reports][]: Immutable reports.
    - [judgevet.domain.policy_errors][]: Definition and answer error hierarchy.
"""

from judgevet.domain.policy_errors import (
    PolicyAnswerError,
    PolicyDefinitionError,
    PolicyError,
)
from judgevet.domain.policy_evaluation import evaluate_policy
from judgevet.domain.policy_reports import PolicyReport, RuleReport
from judgevet.domain.policy_rules import ChoiceRule, NoulRule, Policy, Rule, ScoreRule
from judgevet.domain.policy_validation import ValidatedPolicy, validate_policy

__all__ = [
    "ChoiceRule",
    "NoulRule",
    "Policy",
    "PolicyAnswerError",
    "PolicyDefinitionError",
    "PolicyError",
    "PolicyReport",
    "Rule",
    "RuleReport",
    "ScoreRule",
    "ValidatedPolicy",
    "evaluate_policy",
    "validate_policy",
]
