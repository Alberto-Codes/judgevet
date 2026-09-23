"""Errors for local policy definitions and required answers.

Examples:
    ```python
    from judgevet.domain.policy_errors import PolicyDefinitionError, PolicyError

    assert issubclass(PolicyDefinitionError, PolicyError)
    ```

See Also:
    - [judgevet.policy][]: Supported policy facade.
"""


class PolicyError(ValueError):
    """Base error for local policy failures, independent of Jev service errors.

    Examples:
        ```python
        error = PolicyError("invalid policy data")
        assert isinstance(error, ValueError)
        ```
    """


class PolicyDefinitionError(PolicyError):
    """A policy definition violates its constructor or question constraints.

    Examples:
        ```python
        error = PolicyDefinitionError("invalid policy data")
        assert isinstance(error, ValueError)
        ```
    """


class PolicyAnswerError(PolicyError):
    """A required policy answer is missing or invalid.

    Examples:
        ```python
        error = PolicyAnswerError("invalid policy data")
        assert isinstance(error, ValueError)
        ```
    """
