"""Offline provider factory for the commit-msg shadow wrapper tests (#313).

The factory yields a port whose every call raises an error type that neither
the wrapper nor `shadow_judge.py` expects. Its message carries a canary
string, so a test can prove the wrapper never prints or logs the message.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from judgevet.testing import FakeSystemOnePort

CANARY = "sk-commit-canary-313-do-not-log"


@contextmanager
def dividing() -> Iterator[FakeSystemOnePort]:
    """Yield a port whose every call raises `ZeroDivisionError`.

    Yields:
        A fake port that raises `ZeroDivisionError` naming the canary.
    """
    yield FakeSystemOnePort(error=ZeroDivisionError("divided by " + CANARY))
