"""Offline provider factory for the backend-contention tests (#352).

The factory yields a port whose every call raises the neutral busy error,
the answer a provider gives when another model holds the backend and no
judgment ran. Nothing here performs inference or network access.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from judgevet.providers import ProviderBusyError
from judgevet.testing import FakeSystemOnePort


@contextmanager
def busy() -> Iterator[FakeSystemOnePort]:
    """Yield a port whose every call raises ``ProviderBusyError``.

    Yields:
        A fake port that refuses before any judgment runs.
    """
    yield FakeSystemOnePort(error=ProviderBusyError("another model holds the backend"))
