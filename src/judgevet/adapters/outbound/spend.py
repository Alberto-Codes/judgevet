"""Meter adapter attempts against an opt-in SpendCap.

`metered` and `ametered` claim a slot on the cap before each physical attempt
and settle the reported input tokens after it. The `SpendCap` class lives in
[judgevet.domain.spend][] and is imported here, so
`from judgevet.adapters.outbound.spend import SpendCap` keeps working. The cap
semantics and their citations are documented on that module.

Examples:
    ```python
    from judgevet.adapters.outbound.spend import SpendCap
    from judgevet.domain.errors import JevBudgetExceededError

    cap = SpendCap(max_attempts=1)
    cap.claim()
    try:
        cap.claim()
    except JevBudgetExceededError as error:
        assert (error.limit, error.cap, error.spent) == ("attempts", 1, 1)
    ```

See Also:
    - [judgevet.domain.spend][]: The cap, its counters and its citations.
    - [judgevet.adapters.outbound.http][]: Adapters that accept `spend_cap=`.
    - [judgevet.adapters.outbound.retries][]: Retry loop that stops on the refusal.
    - [judgevet.domain.errors.JevBudgetExceededError][]: The refusal error.
"""

from collections.abc import Awaitable, Callable

from judgevet.domain.response import SystemOneResponse
from judgevet.domain.spend import SpendCap


def metered(
    cap: SpendCap | None, send: Callable[[], SystemOneResponse]
) -> Callable[[], SystemOneResponse]:
    """Wrap one synchronous attempt with a claim before it and a settlement after.

    Args:
        cap: The shared cap, or None to leave the attempt unchanged.
        send: One physical attempt with translated errors.

    Returns:
        The attempt itself when cap is None, otherwise the metered attempt.
    """
    if cap is None:
        return send

    def attempt() -> SystemOneResponse:
        """Claim a slot, send, then settle the reported input tokens.

        Returns:
            The successful answer.

        Raises:
            JevBudgetExceededError: If the cap refuses the attempt.
        """
        cap.claim()
        answer = send()
        cap.settle(answer.usage.input_tokens)
        return answer

    return attempt


def ametered(
    cap: SpendCap | None, send: Callable[[], Awaitable[SystemOneResponse]]
) -> Callable[[], Awaitable[SystemOneResponse]]:
    """Wrap one asynchronous attempt with a claim before it and a settlement after.

    The lock is taken inside `claim` and `settle` only, never across the await.

    Args:
        cap: The shared cap, or None to leave the attempt unchanged.
        send: One physical asynchronous attempt with translated errors.

    Returns:
        The attempt itself when cap is None, otherwise the metered attempt.
    """
    if cap is None:
        return send

    async def attempt() -> SystemOneResponse:
        """Claim a slot, send, then settle the reported input tokens.

        Returns:
            The successful answer.

        Raises:
            JevBudgetExceededError: If the cap refuses the attempt.
        """
        cap.claim()
        answer = await send()
        cap.settle(answer.usage.input_tokens)
        return answer

    return attempt
