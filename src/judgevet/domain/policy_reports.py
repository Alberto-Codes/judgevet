"""Immutable ordered policy reports.

Examples:
    ```python
    from judgevet.domain.policy_reports import RuleReport, PolicyReport

    report = PolicyReport((RuleReport("q", False, "unmet"),))
    assert not report.passed
    ```

See Also:
    - [judgevet.domain.policy_evaluation][]: Report production.
"""

from dataclasses import dataclass

from judgevet.domain.policy_checks import check_name
from judgevet.domain.policy_errors import PolicyDefinitionError


@dataclass(frozen=True, slots=True)
class RuleReport:
    """The outcome of one rule.

    Attributes:
        question (str): Question name.
        passed (bool): Whether every predicate passed.
        detail (str): Human-readable comparisons.

    Examples:
        ```python
        report = RuleReport("q", True, "met")
        ```
    """

    question: str
    passed: bool
    detail: str

    def __post_init__(self) -> None:
        """Require a name, boolean outcome and textual detail.

        Raises:
            PolicyDefinitionError: If report fields are malformed.
        """
        check_name(self.question)
        if not isinstance(self.passed, bool) or not isinstance(self.detail, str):
            raise PolicyDefinitionError(
                "report requires a bool outcome and text detail"
            )


@dataclass(frozen=True, slots=True)
class PolicyReport:
    """All rule outcomes in policy order with a derived aggregate.

    Attributes:
        rules (tuple): Nonempty immutable rule reports.
        passed (bool): Whether every rule passed.

    Examples:
        ```python
        report = PolicyReport((RuleReport("q", True, "met"),))
        ```
    """

    rules: tuple[RuleReport, ...]

    def __post_init__(self) -> None:
        """Copy and validate reports.

        Raises:
            PolicyDefinitionError: If reports are empty, malformed or duplicated.
        """
        if not isinstance(self.rules, (tuple, list)) or not self.rules:
            raise PolicyDefinitionError("reports must be a non-empty sequence")
        if not all(isinstance(rule, RuleReport) for rule in self.rules):
            raise PolicyDefinitionError("reports must contain RuleReport objects")
        if len({rule.question for rule in self.rules}) != len(self.rules):
            raise PolicyDefinitionError("duplicate report for question")
        object.__setattr__(self, "rules", tuple(self.rules))

    @property
    def passed(self) -> bool:
        """Return the conjunction of all rule outcomes.

        Returns:
            True only when every rule passed.
        """
        return all(rule.passed for rule in self.rules)
