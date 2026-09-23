"""Shared pure predicates for typed policies and the legacy CLI bridge.

Examples:
    ```python
    from judgevet.domain.policy_comparisons import range_report
    from judgevet.policy import NoulRule

    report = range_report(NoulRule("q", 0.5), 0.5, "noul", None)
    assert report[0]
    ```

See Also:
    - [judgevet.domain.policy_evaluation][]: Strict public answer validation.
    - [judgevet.domain.policy_reports][]: Immutable reports.
"""

from typing import Protocol


class RangePredicate(Protocol):
    """Read-only fields needed by inclusive range comparisons.

    Attributes:
        name (str): Question name.
        minimum (float | None): Inclusive lower bound.
        maximum (float | None): Inclusive upper bound.

    Examples:
        ```python
        from judgevet.policy import NoulRule

        rule: RangePredicate = NoulRule("q", 0.5)
        assert rule.name == "q"
        ```
    """

    @property
    def name(self) -> str:
        """Return the question name.

        Returns:
            The question name.
        """
        ...

    @property
    def minimum(self) -> float | None:
        """Return the inclusive lower bound.

        Returns:
            The bound, or None.
        """
        ...

    @property
    def maximum(self) -> float | None:
        """Return the inclusive upper bound.

        Returns:
            The bound, or None.
        """
        ...


def _verdict(passed: bool) -> str:
    """Render the historical textual verdict suffix.

    Args:
        passed: Predicate outcome.

    Returns:
        The pass/fail suffix.
    """
    return f" -> {'pass' if passed else 'fail'}"


def range_report(
    rule: RangePredicate,
    value: float,
    label: str,
    confidence: tuple[float, float] | None,
) -> tuple[bool, str]:
    """Compute inclusive range predicates and optional confidence conjunction.

    Args:
        rule: Validated bounds or historical CLI rule fields.
        value: Selected answer scalar.
        label: Fixed predicate name.
        confidence: Observed confidence and minimum, or None.

    Returns:
        Complete comparison detail and predicate outcome.
    """
    passed = (rule.minimum is None or value >= rule.minimum) and (
        rule.maximum is None or value <= rule.maximum
    )
    parts = []
    if rule.minimum is not None:
        parts.append(f"{label} {value} >= {rule.minimum}")
    if rule.maximum is not None:
        parts.append(f"{label} {value} <= {rule.maximum}")
    detail = " and ".join(parts) if parts else f"{label} {value}"
    if confidence is not None:
        observed, minimum = confidence
        passed = passed and observed >= minimum
        detail += f" and confidence {observed} >= {minimum}"
    return passed, detail + _verdict(passed)


def choice_report(
    name: str,
    expected: str | None,
    observed: str,
    confidence: tuple[float, float] | None,
) -> tuple[bool, str]:
    """Compute exact choice equality and optional confidence conjunction.

    Args:
        name: Question name.
        expected: Required choice label.
        observed: Observed choice label.
        confidence: Observed confidence and minimum, or None.

    Returns:
        Complete comparison detail and predicate outcome.
    """
    passed = observed == expected
    detail = f"choice '{observed}' == '{expected}'"
    if confidence is not None:
        value, minimum = confidence
        passed = passed and value >= minimum
        detail += f" and confidence {value} >= {minimum}"
    return passed, detail + _verdict(passed)
