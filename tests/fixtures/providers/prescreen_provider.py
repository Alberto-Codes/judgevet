"""Offline provider factories for the acceptance pre-screen tests (#312).

Each factory returns a context manager that yields a fake judgment port with
scripted Noul answers for the three pre-screen questions. None of them
performs inference or network access.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from judgevet import NoulAnswer
from judgevet.testing import Call, FakeSystemOnePort

KEYS = ("allowed_paths", "tests_kept", "test_fails_without")
CALLS: list[Call] = []


@contextmanager
def confident() -> Iterator[FakeSystemOnePort]:
    """Yield a port that answers every pre-screen question with 0.9.

    Yields:
        A fake port whose three answers all meet a 0.8 floor.
    """
    answers = {key: NoulAnswer(noul=0.9) for key in KEYS}
    port = FakeSystemOnePort(seed=7, answers=answers)
    try:
        yield port
    finally:
        CALLS.extend(port.calls)


@contextmanager
def doubtful() -> Iterator[FakeSystemOnePort]:
    """Yield a port that doubts the new test would fail without the change.

    Yields:
        A fake port that answers `test_fails_without` with 0.4 and the other
        two questions with 0.9.
    """
    answers = {key: NoulAnswer(noul=0.9) for key in KEYS}
    answers["test_fails_without"] = NoulAnswer(noul=0.4)
    yield FakeSystemOnePort(seed=7, answers=answers)
