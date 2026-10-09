"""Offline provider factory that records each state for the stop-check tests (#314).

The shell-pipe test runs `shadow_judge.py` in a child process, and its log
never holds the state. This factory writes each received state to the file
that `STOP_STATE_FILE` names, so the test can read what the judge sent.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from judgevet import NoulAnswer
from judgevet.testing import FakeSystemOnePort

STATE_FILE_ENV = "STOP_STATE_FILE"


@contextmanager
def recording() -> Iterator[FakeSystemOnePort]:
    """Yield a fake port and write each state it received to a file.

    Yields:
        A fake port that answers ``done`` with 0.9.
    """
    port = FakeSystemOnePort(seed=7, answers={"done": NoulAnswer(noul=0.9)})
    try:
        yield port
    finally:
        with Path(os.environ[STATE_FILE_ENV]).open("a", encoding="utf-8") as stream:
            stream.writelines(f"{state}\n" for state, _, _ in port.calls)
