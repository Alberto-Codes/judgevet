"""Errors for local policy definitions and required answers.

Policy errors inherit JudgevetError and preserve their ValueError catches.

Examples:
    ```python
    from judgevet.domain.policy_errors import PolicyDefinitionError, PolicyError

    assert issubclass(PolicyDefinitionError, PolicyError)
    ```

See Also:
    - [judgevet.policy][]: Supported policy facade.
"""

from judgevet.domain.errors import JudgevetError


class PolicyError(JudgevetError, ValueError):
    """Base error for local policy failures, independent of Jev service errors.

    The neutral base supports common catches while preserving ValueError catches.
    Source: https://github.com/Alberto-Codes/judgevet/issues/78#issuecomment-5850346340.

    Attributes:
        args (tuple): Standard exception arguments.

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
