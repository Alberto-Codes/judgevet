"""Hold the opt-in cap on attempts and settled input tokens a caller may spend.

A SpendCap is opt-in. A port without one sends every attempt its retry policy
permits. A port with one claims a slot before each physical attempt, including
every retry, and refuses with JevBudgetExceededError when a limit is already
reached. Nothing is sent on a refusal. The HTTP adapters and the offline fakes
in `judgevet.testing` accept the same object.

Each attempt counts, failed or not. The AWS SDK retry quota also charges
failed retries.
Source: https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html.
Input tokens settle from the response `usage.input_tokens` after the attempt.
A failed attempt, or a response without that count, settles zero. Whether the
service bills a failed attempt is an open question on #56.

The counters use `threading.Lock`, because both the sync and async adapters
share them and an `asyncio.Lock` guards one event loop only. The lock is held
for the counter update alone, never across an await.
Source: https://docs.python.org/3/library/asyncio-sync.html.

The attempt limit is hard. The token limit is checked before sending, so
attempts already in flight can settle past it.

Examples:
    ```python
    from judgevet.domain.errors import JevBudgetExceededError
    from judgevet.domain.spend import SpendCap

    cap = SpendCap(max_attempts=1)
    cap.claim()
    try:
        cap.claim()
    except JevBudgetExceededError as error:
        assert (error.limit, error.cap, error.spent) == ("attempts", 1, 1)
    ```

See Also:
    - [judgevet.adapters.outbound.spend][]: Wraps adapter attempts in the cap.
    - [judgevet.testing][]: Offline fakes that accept `spend_cap=`.
    - [judgevet.domain.errors.JevBudgetExceededError][]: The refusal error.
"""

import threading

from judgevet.domain.errors import JevBudgetExceededError


def _validated(name: str, value: int | None) -> int | None:
    """Accept None or a positive integer for one limit.

    Args:
        name: The constructor argument name, for the message.
        value: The proposed limit.

    Returns:
        The limit unchanged.

    Raises:
        ValueError: If the limit is not None and not a positive integer.
    """
    if value is not None and (type(value) is not int or value < 1):
        raise ValueError(f"{name} must be None or a positive integer")
    return value


class SpendCap:
    """Hold lock-guarded attempt and input-token counters that never reset.

    Every adapter given the same object draws from the same counters. A limit
    left as None does not bound that counter.

    Attributes:
        max_attempts (int | None): Physical attempts allowed, retries included.
        max_input_tokens (int | None): Settled input tokens after which the cap
            refuses further attempts.
        attempts (int): Attempts claimed so far.
        input_tokens (int): Input tokens settled so far.

    Examples:
        ```python
        cap = SpendCap(max_input_tokens=100)
        cap.claim()
        cap.settle(60)
        assert (cap.attempts, cap.input_tokens) == (1, 60)
        ```
    """

    def __init__(
        self, max_attempts: int | None = None, max_input_tokens: int | None = None
    ) -> None:
        """Validate the limits and start both counters at zero.

        Args:
            max_attempts: Physical attempts allowed, or None for no bound.
            max_input_tokens: Input tokens allowed, or None for no bound.

        Raises:
            ValueError: If a limit is not None and not a positive integer.
        """
        self.max_attempts = _validated("max_attempts", max_attempts)
        self.max_input_tokens = _validated("max_input_tokens", max_input_tokens)
        self._lock = threading.Lock()
        self._attempts = 0
        self._input_tokens = 0

    @property
    def attempts(self) -> int:
        """Return the attempts claimed so far.

        Returns:
            The attempt counter.
        """
        return self._attempts

    @property
    def input_tokens(self) -> int:
        """Return the input tokens settled so far.

        Returns:
            The input-token counter.
        """
        return self._input_tokens

    def claim(self) -> None:
        """Claim one attempt slot, or refuse when a limit is already reached.

        Raises:
            JevBudgetExceededError: If attempts or settled input tokens have
                reached their cap.
        """
        with self._lock:
            attempts, tokens = self._attempts, self._input_tokens
            if self.max_attempts is not None and attempts >= self.max_attempts:
                raise JevBudgetExceededError("attempts", self.max_attempts, attempts)
            if self.max_input_tokens is not None and tokens >= self.max_input_tokens:
                raise JevBudgetExceededError(
                    "input_tokens", self.max_input_tokens, tokens
                )
            self._attempts += 1

    def settle(self, input_tokens: int | None) -> None:
        """Add the input tokens one attempt reported.

        Args:
            input_tokens: The response `usage.input_tokens`; None adds zero.
        """
        if input_tokens:
            with self._lock:
                self._input_tokens += input_tokens
