"""Immutable typed rules and ordered policies.

Examples:
    ```python
    from judgevet.domain.policy_rules import NoulRule, Policy

    policy = Policy((NoulRule("clear", minimum=0.8),))
    assert policy.rules[0].name == "clear"
    ```

See Also:
    - [judgevet.policy][]: Supported facade and evaluation.
    - [judgevet.domain.policy_errors][]: Definition failures.
"""

from dataclasses import dataclass

from judgevet.domain.policy_checks import check_bound, check_name, check_range
from judgevet.domain.policy_errors import PolicyDefinitionError


@dataclass(frozen=True, slots=True)
class NoulRule:
    """Inclusive bounds for a Noul answer.

    Attributes:
        name (str): Question name.
        minimum (float | None): Optional inclusive probability floor.
        maximum (float | None): Optional inclusive probability ceiling.

    Examples:
        ```python
        rule = NoulRule("q", minimum=0.5)
        ```
    """

    name: str
    minimum: float | None = None
    maximum: float | None = None

    def __post_init__(self) -> None:
        """Validate and normalize local rule constraints.

        Raises:
            PolicyDefinitionError: If a name or bound is invalid.
        """
        check_name(self.name)
        object.__setattr__(self, "minimum", check_bound(self.minimum, "noul min", 1.0))
        object.__setattr__(self, "maximum", check_bound(self.maximum, "noul max", 1.0))
        check_range(self.minimum, self.maximum)


@dataclass(frozen=True, slots=True)
class ChoiceRule:
    """An exact Choice label and optional confidence floor.

    Attributes:
        name (str): Question name.
        choice (str): Required choice label.
        min_confidence (float | None): Optional inclusive confidence floor.

    Examples:
        ```python
        rule = ChoiceRule("q", "yes")
        ```
    """

    name: str
    choice: str
    min_confidence: float | None = None

    def __post_init__(self) -> None:
        """Validate the name, label type and confidence floor.

        Raises:
            PolicyDefinitionError: If a local constraint is invalid.
        """
        check_name(self.name)
        if not isinstance(self.choice, str):
            raise PolicyDefinitionError("choice value must be a string")
        object.__setattr__(
            self,
            "min_confidence",
            check_bound(self.min_confidence, "confidence min", 1.0),
        )


@dataclass(frozen=True, slots=True)
class ScoreRule:
    """Inclusive score bounds and an optional confidence floor.

    Attributes:
        name (str): Question name.
        minimum (float | None): Optional inclusive score floor.
        maximum (float | None): Optional inclusive score ceiling.
        min_confidence (float | None): Optional inclusive confidence floor.

    Examples:
        ```python
        rule = ScoreRule("q", minimum=0)
        ```
    """

    name: str
    minimum: float | None = None
    maximum: float | None = None
    min_confidence: float | None = None

    def __post_init__(self) -> None:
        """Validate bounds independent of a question's score scale.

        Raises:
            PolicyDefinitionError: If a local constraint is invalid.
        """
        check_name(self.name)
        object.__setattr__(
            self, "minimum", check_bound(self.minimum, "score min", None)
        )
        object.__setattr__(
            self, "maximum", check_bound(self.maximum, "score max", None)
        )
        check_range(self.minimum, self.maximum)
        object.__setattr__(
            self,
            "min_confidence",
            check_bound(self.min_confidence, "confidence min", 1.0),
        )


Rule = NoulRule | ChoiceRule | ScoreRule
"""The three supported policy rule variants."""


@dataclass(frozen=True, slots=True)
class Policy:
    """A nonempty ordered tuple of uniquely named typed rules.

    Attributes:
        rules (tuple): Rules in evaluation order, defensively copied into a tuple.

    Examples:
        ```python
        policy = Policy((NoulRule("q", minimum=0.5),))
        ```
    """

    rules: tuple[Rule, ...]

    def __post_init__(self) -> None:
        """Copy the rule sequence and validate its elements and names.

        Raises:
            PolicyDefinitionError: If rules are empty, malformed or duplicated.
        """
        if not isinstance(self.rules, (tuple, list)) or not self.rules:
            raise PolicyDefinitionError("rules must be a non-empty sequence")
        names = set()
        for rule in self.rules:
            if not isinstance(rule, (NoulRule, ChoiceRule, ScoreRule)):
                raise PolicyDefinitionError("rule must be a typed policy rule")
            if rule.name in names:
                raise PolicyDefinitionError("duplicate rule for question")
            names.add(rule.name)
        object.__setattr__(self, "rules", tuple(self.rules))
