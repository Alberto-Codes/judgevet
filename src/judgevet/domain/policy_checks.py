"""Shared scalar checks for pure policy construction.

Examples:
    ```python
    from judgevet.domain.policy_checks import finite_number

    assert finite_number(0.5)
    assert not finite_number(True)
    ```

See Also:
    - [judgevet.domain.policy_rules][]: Typed policy rules.
"""

import math

from judgevet.domain.policy_errors import PolicyDefinitionError


def finite_number(value: object) -> bool:
    """Check finite numeric values without treating bool as a number.

    Args:
        value: Candidate number.

    Returns:
        Whether the value is an int or finite float, excluding bool.
    """
    return not isinstance(value, bool) and (
        isinstance(value, int) or (isinstance(value, float) and math.isfinite(value))
    )


def check_name(name: str) -> None:
    """Require a nonempty question name.

    Args:
        name: Candidate name.

    Raises:
        PolicyDefinitionError: If the name is invalid.
    """
    if not isinstance(name, str) or not name:
        raise PolicyDefinitionError("question name must be a non-empty string")


def check_bound(value: float | None, label: str, maximum: float | None) -> float | None:
    """Validate and normalize an optional nonnegative bound.

    Args:
        value: Candidate bound.
        label: Fixed diagnostic label.
        maximum: Optional upper bound.

    Returns:
        A finite float or None.

    Raises:
        PolicyDefinitionError: If the bound is invalid.
    """
    if value is None:
        return None
    if not finite_number(value):
        raise PolicyDefinitionError(f"{label} must be a finite number")
    if value < 0 or (maximum is not None and value > maximum):
        raise PolicyDefinitionError(f"{label} is outside the allowed range")
    try:
        normalized = float(value)
    except OverflowError:
        raise PolicyDefinitionError(f"{label} must be a finite number") from None
    return normalized


def check_range(minimum: float | None, maximum: float | None) -> None:
    """Require at least one bound and ordered endpoints.

    Args:
        minimum: Lower bound.
        maximum: Upper bound.

    Raises:
        PolicyDefinitionError: If bounds are absent or inverted.
    """
    if minimum is None and maximum is None:
        raise PolicyDefinitionError("predicate requires at least one bound")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise PolicyDefinitionError("min cannot exceed max")
