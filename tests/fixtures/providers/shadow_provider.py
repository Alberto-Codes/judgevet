"""Offline provider factories for the shadow-mode hook runner tests (#309).

Each factory returns a context manager that yields a judgment port. None of
them performs inference or network access. The failing factory embeds the
environment credential in its error message, so a test can prove the runner
never logs it.
"""

import os
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from judgevet import NoulAnswer, Question, SystemOneResponse
from judgevet.providers import ProviderTransportError
from judgevet.testing import FakeSystemOnePort

CREDENTIAL_ENV = "JEV_API__API_KEY"
DELAY_SECONDS = 2.0
CALLS: list[Any] = []


@contextmanager
def answering() -> Iterator[FakeSystemOnePort]:
    """Yield a fake port with one scripted answer and record its calls.

    Yields:
        A fake port that answers ``risky`` with 0.2.
    """
    port = FakeSystemOnePort(seed=7, answers={"risky": NoulAnswer(noul=0.2)})
    try:
        yield port
    finally:
        CALLS.extend(port.calls)


class SlowPort:
    """A port that answers only after a delay longer than the test timeout.

    Attributes:
        inner: Fake port that produces the answer.
    """

    def __init__(self) -> None:
        """Create the delayed port."""
        self.inner = FakeSystemOnePort(seed=7)

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str = "jev-latest",
    ) -> SystemOneResponse:
        """Sleep, then answer.

        Args:
            state: Received state.
            questions: Received questions.
            model: Received model.

        Returns:
            The fake port's answer.
        """
        time.sleep(DELAY_SECONDS)
        return self.inner.system_one(state, questions, model)


@contextmanager
def slow() -> Iterator[SlowPort]:
    """Yield a port slower than the runner timeout.

    Yields:
        The delayed port.
    """
    yield SlowPort()


@contextmanager
def failing() -> Iterator[FakeSystemOnePort]:
    """Yield a port whose every call raises an error that names the credential.

    Yields:
        A fake port that raises a provider transport error.
    """
    message = "upstream refused key " + os.environ.get(CREDENTIAL_ENV, "")
    yield FakeSystemOnePort(error=ProviderTransportError(message))


@contextmanager
def broken() -> Iterator[FakeSystemOnePort]:
    """Yield a port whose every call raises an unexpected error type.

    Yields:
        A fake port that raises ``RuntimeError`` naming the credential.
    """
    message = "bug near key " + os.environ.get(CREDENTIAL_ENV, "")
    yield FakeSystemOnePort(error=RuntimeError(message))


@contextmanager
def exiting() -> Iterator[FakeSystemOnePort]:
    """Yield a port whose every call exits with the blocking status 2.

    Yields:
        A fake port that raises ``SystemExit(2)``.
    """
    yield FakeSystemOnePort(error=SystemExit(2))


@contextmanager
def confused() -> Iterator[FakeSystemOnePort]:
    """Yield a port whose every call raises an ``AttributeError`` mid-judgment.

    Yields:
        A fake port that raises ``AttributeError`` naming the credential.
    """
    message = "'NoneType' has no attribute " + os.environ.get(CREDENTIAL_ENV, "")
    yield FakeSystemOnePort(error=AttributeError(message))
