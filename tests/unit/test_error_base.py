"""Prove neutral error catches without changing published exception behavior."""

import pytest

import judgevet
from judgevet import (
    JevAuthError,
    JevBudgetExceededError,
    JevError,
    JevMaxTokensExceededError,
    JevRateLimitError,
    JevRequestError,
    JevResponseError,
    JevServiceError,
    JudgevetError,
)
from judgevet.domain import JudgevetError as DomainError
from judgevet.domain.errors import JudgevetError as OriginalError
from judgevet.policy import PolicyAnswerError, PolicyDefinitionError, PolicyError


@pytest.mark.parametrize(
    "error",
    [
        JevError("base"),
        JevAuthError("auth", 401),
        JevRequestError("request", 422),
        JevMaxTokensExceededError("budget", 400),
        JevRateLimitError("rate", 429),
        JevServiceError("transport"),
        JevResponseError("response", 200),
        JevBudgetExceededError("attempts", 1, 1),
    ],
)
def test_jev_errors_keep_old_catches_and_gain_neutral_catch(error: JevError) -> None:
    """A raised published exception retains identity through both catch paths."""
    with pytest.raises(JudgevetError) as neutral:
        raise error
    with pytest.raises(JevError) as legacy:
        raise error
    assert neutral.value is legacy.value is error
    assert getattr(judgevet, type(error).__name__) is type(error)


@pytest.mark.parametrize(
    "kind", [PolicyError, PolicyDefinitionError, PolicyAnswerError]
)
def test_policy_errors_preserve_value_error_catches(kind: type[PolicyError]) -> None:
    """Local errors gain the neutral catch while keeping their Python contract."""
    error = kind("local")
    with pytest.raises(JudgevetError) as neutral:
        raise error
    with pytest.raises(ValueError) as legacy:
        raise error
    assert neutral.value is legacy.value is error
    assert not isinstance(error, JevError)


def test_neutral_base_is_one_public_object() -> None:
    """Root, domain and original imports resolve to the same exception class."""
    assert JudgevetError is DomainError is OriginalError
    error = JudgevetError("safe message")
    assert error.args == ("safe message",)
    assert str(error) == "safe message"
    assert not isinstance(error, (JevError, ValueError))
    assert not isinstance(ValueError("ordinary validation"), JudgevetError)
