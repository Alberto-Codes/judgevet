"""Bound opt-in retries without changing service-error classifications.

Defaults and jitter follow the timing values documented at
https://docs.typesafe.ai/sdk/python/api/retries.md. Unlike that SDK, judgevet
requires opt-in for retries and separately for transport failures.

Examples:
    ```python
    from judgevet.adapters.outbound.retries import RetryPolicy

    assert RetryPolicy().max_attempts == 1
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: HTTP call sites.
    - [judgevet.domain.errors][]: Retryable error classifications.
"""

import asyncio
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from random import SystemRandom

from judgevet.domain.errors import JevError

random = SystemRandom()


@dataclass(frozen=True)
class RetryPolicy:
    """Hold validated attempt and delay limits.

    Attributes:
        max_attempts (int): Total attempts including the initial request.
        retry_base_delay (float): Initial delay ceiling in seconds.
        retry_max_delay (float): Maximum delay ceiling in seconds.
        retry_transport (bool): Permit replay when a transport failure has no status.

    Examples:
        ```python
        policy = RetryPolicy(max_attempts=3)
        assert policy.retry_transport is False
        ```
    """

    max_attempts: int = 1
    retry_base_delay: float = 0.5
    retry_max_delay: float = 5.0
    retry_transport: bool = False

    def __post_init__(self) -> None:
        """Reject limits that cannot provide bounded attempts and delays.

        Raises:
            ValueError: If attempts are not a positive integer or delays are invalid.
        """
        if type(self.max_attempts) is not int or self.max_attempts < 1:
            raise ValueError("max_attempts must be a positive integer")
        for name in ("retry_base_delay", "retry_max_delay"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")

    def permits(self, error: JevError, attempt: int) -> bool:
        """Decide whether the failed attempt permits another request.

        Args:
            error: The translated service error.
            attempt: Number of requests already attempted.

        Returns:
            Whether the error and remaining attempt budget permit replay.
        """
        return (
            attempt < self.max_attempts
            and error.retryable
            and (error.status_code is not None or self.retry_transport)
        )

    def run[T](self, operation: Callable[[], T]) -> T:
        """Run a synchronous operation with bounded retry delays.

        Args:
            operation: One request with translated errors.

        Returns:
            The successful operation result.

        Raises:
            JevError: The final error when replay is disallowed or exhausted.
        """
        attempt = 1
        delay = min(self.retry_base_delay, self.retry_max_delay)
        while True:
            try:
                return operation()
            except JevError as error:
                if not self.permits(error, attempt):
                    raise
                time.sleep(delay * (1 - 0.25 * random.random()))
                delay = min(delay * 2, self.retry_max_delay)
                attempt += 1

    async def arun[T](self, operation: Callable[[], Awaitable[T]]) -> T:
        """Await an operation and cancellable retry delays.

        Args:
            operation: One asynchronous request with translated errors.

        Returns:
            The successful operation result.

        Raises:
            JevError: The final error when replay is disallowed or exhausted.
        """
        attempt = 1
        delay = min(self.retry_base_delay, self.retry_max_delay)
        while True:
            try:
                return await operation()
            except JevError as error:
                if not self.permits(error, attempt):
                    raise
                await asyncio.sleep(delay * (1 - 0.25 * random.random()))
                delay = min(delay * 2, self.retry_max_delay)
                attempt += 1
