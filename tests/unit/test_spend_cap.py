"""Behavioral acceptance tests for the opt-in library spend cap (#56 slice A)."""

import asyncio
import threading
from collections.abc import Callable

import httpx
import pytest

from judgevet import JevBudgetExceededError, RetryPolicy, SpendCap
from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain.errors import JevError, JevServiceError

QUESTIONS = {"q": {"type": "noul"}}
RETRY_FIVE = RetryPolicy(max_attempts=5, retry_base_delay=0)


def success(input_tokens: int = 60) -> httpx.Response:
    """Return a synthetic successful judgment reporting the given input tokens."""
    usage = {"input_tokens": input_tokens, "output_tokens": 0}
    return httpx.Response(
        200,
        json={
            "model": "jev-1.13.0",
            "usage": usage,
            "answers": {"q": {"type": "noul", "noul": 0.8}},
        },
    )


def recorder(
    reply: Callable[[int], httpx.Response],
) -> tuple[list[httpx.Request], Callable[[httpx.Request], httpx.Response]]:
    """Return a request log and a handler that records each physical request."""
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return reply(len(calls))

    return calls, handle


def sync_adapter(
    handle: Callable[[httpx.Request], httpx.Response],
    cap: SpendCap | None,
    retry: RetryPolicy | None = None,
) -> HTTPSystemOneAdapter:
    """Build a sync adapter over a mock transport, passing the cap only when set."""
    if cap is None:
        return HTTPSystemOneAdapter(
            api_key="synthetic", transport=httpx.MockTransport(handle), retry=retry
        )
    return HTTPSystemOneAdapter(
        api_key="synthetic",
        transport=httpx.MockTransport(handle),
        retry=retry,
        spend_cap=cap,
    )


def async_adapter(
    handle: Callable[[httpx.Request], httpx.Response],
    cap: SpendCap,
    retry: RetryPolicy | None = None,
) -> AsyncHTTPSystemOneAdapter:
    """Build an async adapter over a mock transport with the given cap."""
    return AsyncHTTPSystemOneAdapter(
        api_key="synthetic",
        transport=httpx.MockTransport(handle),
        retry=retry,
        spend_cap=cap,
    )


def test_no_cap_leaves_behaviour_unchanged() -> None:
    """Without a cap, retries exhaust the policy and the last service error surfaces."""
    calls, handle = recorder(lambda _: httpx.Response(503))
    with sync_adapter(handle, None, RETRY_FIVE) as adapter:
        with pytest.raises(JevServiceError):
            adapter.system_one("synthetic", QUESTIONS)
        assert len(calls) == 5
        calls.clear()
    ok_calls, ok_handle = recorder(lambda _: success())
    with sync_adapter(ok_handle, None) as adapter:
        for _ in range(3):
            assert adapter.system_one("synthetic", QUESTIONS).model == "jev-1.13.0"
    assert len(ok_calls) == 3


def test_attempt_cap_is_hard_across_retries() -> None:
    """Each retry claims a slot, and the third attempt is refused before sending."""
    calls, handle = recorder(lambda _: httpx.Response(503))
    cap = SpendCap(max_attempts=2)
    with (
        sync_adapter(handle, cap, RETRY_FIVE) as adapter,
        pytest.raises(JevBudgetExceededError) as caught,
    ):
        adapter.system_one("synthetic", QUESTIONS)
    assert len(calls) == 2
    error = caught.value
    assert isinstance(error, JevError)
    assert (error.limit, error.cap, error.spent) == ("attempts", 2, 2)
    assert error.retryable is False


def test_token_cap_refuses_the_next_call_before_sending() -> None:
    """Settled input tokens reach the cap, so the next call sends nothing."""
    calls, handle = recorder(lambda _: success(60))
    cap = SpendCap(max_input_tokens=100)
    with sync_adapter(handle, cap) as adapter:
        assert adapter.system_one("synthetic", QUESTIONS).usage.input_tokens == 60
        adapter.system_one("synthetic", QUESTIONS)
        with pytest.raises(JevBudgetExceededError) as caught:
            adapter.system_one("synthetic", QUESTIONS)
    assert len(calls) == 2
    error = caught.value
    assert (error.limit, error.cap, error.spent) == ("input_tokens", 100, 120)


def test_token_cap_counts_the_first_call() -> None:
    """One 60-token call below a 60-token cap blocks the second call at spent 60."""
    calls, handle = recorder(lambda _: success(60))
    cap = SpendCap(max_input_tokens=60)
    with sync_adapter(handle, cap) as adapter:
        adapter.system_one("synthetic", QUESTIONS)
        with pytest.raises(JevBudgetExceededError) as caught:
            adapter.system_one("synthetic", QUESTIONS)
    assert len(calls) == 1
    assert (caught.value.limit, caught.value.spent) == ("input_tokens", 60)


def test_failed_attempt_and_missing_usage_settle_zero() -> None:
    """A 5xx attempt claims a slot but adds no tokens; a None count adds zero."""
    replies = {1: httpx.Response(503), 2: success(60)}
    calls, handle = recorder(lambda n: replies[n])
    cap = SpendCap(max_input_tokens=100)
    retry = RetryPolicy(max_attempts=2, retry_base_delay=0)
    with sync_adapter(handle, cap, retry) as adapter:
        adapter.system_one("synthetic", QUESTIONS)
    assert len(calls) == 2
    assert (cap.attempts, cap.input_tokens) == (2, 60)
    cap.settle(None)
    assert cap.input_tokens == 60


def test_adapters_sharing_a_cap_share_the_count() -> None:
    """Two adapters over one cap draw from the same attempt budget."""
    calls, handle = recorder(lambda _: success(1))
    cap = SpendCap(max_attempts=2)
    with sync_adapter(handle, cap) as first, sync_adapter(handle, cap) as second:
        first.system_one("synthetic", QUESTIONS)
        second.system_one("synthetic", QUESTIONS)
        with pytest.raises(JevBudgetExceededError) as caught:
            first.system_one("synthetic", QUESTIONS)
    assert len(calls) == 2
    assert (caught.value.limit, caught.value.spent) == ("attempts", 2)


def test_threads_cannot_overrun_the_attempt_cap() -> None:
    """Eight concurrent callers against four slots send exactly four requests."""
    lock = threading.Lock()
    calls, record = recorder(lambda _: success(1))

    def handle(request: httpx.Request) -> httpx.Response:
        with lock:
            return record(request)

    cap = SpendCap(max_attempts=4)
    barrier = threading.Barrier(8)
    outcomes: list[str] = []

    def call(adapter: HTTPSystemOneAdapter) -> None:
        barrier.wait()
        try:
            adapter.system_one("synthetic", QUESTIONS)
            outcome = "sent"
        except JevBudgetExceededError:
            outcome = "refused"
        with lock:
            outcomes.append(outcome)

    with sync_adapter(handle, cap) as adapter:
        threads = [threading.Thread(target=call, args=(adapter,)) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert len(calls) == 4
    assert sorted(outcomes) == ["refused"] * 4 + ["sent"] * 4


def test_async_attempt_cap_is_hard_across_retries() -> None:
    """The async adapter refuses the third attempt without sending it."""
    calls, handle = recorder(lambda _: httpx.Response(503))
    cap = SpendCap(max_attempts=2)

    async def run() -> JevBudgetExceededError:
        async with async_adapter(handle, cap, RETRY_FIVE) as adapter:
            with pytest.raises(JevBudgetExceededError) as caught:
                await adapter.system_one("synthetic", QUESTIONS)
        return caught.value

    error = asyncio.run(run())
    assert len(calls) == 2
    assert (error.limit, error.cap, error.spent) == ("attempts", 2, 2)
    assert error.retryable is False


def test_async_token_cap_refuses_before_sending() -> None:
    """The async adapter settles tokens and refuses the call past the cap."""
    calls, handle = recorder(lambda _: success(60))
    cap = SpendCap(max_input_tokens=60)

    async def run() -> JevBudgetExceededError:
        async with async_adapter(handle, cap) as adapter:
            await adapter.system_one("synthetic", QUESTIONS)
            with pytest.raises(JevBudgetExceededError) as caught:
                await adapter.system_one("synthetic", QUESTIONS)
        return caught.value

    error = asyncio.run(run())
    assert len(calls) == 1
    assert (error.limit, error.cap, error.spent) == ("input_tokens", 60, 60)


def test_sync_and_async_adapters_share_one_cap() -> None:
    """A cap passed to both adapter kinds counts their attempts together."""
    calls, handle = recorder(lambda _: success(1))
    cap = SpendCap(max_attempts=1)
    with sync_adapter(handle, cap) as adapter:
        adapter.system_one("synthetic", QUESTIONS)

    async def run() -> None:
        async with async_adapter(handle, cap) as adapter:
            await adapter.system_one("synthetic", QUESTIONS)

    with pytest.raises(JevBudgetExceededError):
        asyncio.run(run())
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("attempts", "tokens"),
    [(0, None), (True, None), (None, -1), (None, 0)],
)
def test_invalid_limits_are_rejected(attempts: int | None, tokens: int | None) -> None:
    """A limit must be None or a positive integer."""
    with pytest.raises(ValueError, match="positive integer"):
        SpendCap(max_attempts=attempts, max_input_tokens=tokens)


def test_budget_error_rejects_an_unknown_limit_name() -> None:
    """The error names one of the two counted limits."""
    with pytest.raises(ValueError, match="limit"):
        JevBudgetExceededError("dollars", 1, 1)
    error = JevBudgetExceededError("attempts", 3, 3)
    assert error.status_code is None
    assert "attempts" in str(error)
