"""Observers and checks for the asynchronous provider scope rules.

`AsyncScopeRecorder` wraps an `AsyncProviderFactory` and records every async
context it constructs. The kit observes entry and exit itself instead of
trusting the provider. `exit_problem` and `body_problem` drive
`async_provider_scope` and describe a broken lifecycle. Each returns None when
the provider keeps the rule. The synchronous kit's `ScopeRecorder` does the same
for a `ProviderFactory`. None of these import pytest.
Source: https://github.com/Alberto-Codes/judgevet/issues/251.

Examples:
    ```python
    from contextlib import nullcontext

    import anyio

    from judgevet.providers import async_provider_scope
    from judgevet.testing import AsyncFakeSystemOnePort
    from judgevet.testing._conformance_async_scope import (
        AsyncScopeRecorder,
        body_problem,
        exit_problem,
    )

    recorder = AsyncScopeRecorder(lambda: nullcontext(AsyncFakeSystemOnePort()))


    async def enter_once():
        async with async_provider_scope(factory=recorder) as port:
            assert callable(port.system_one)


    anyio.run(enter_once)
    assert recorder.contexts[0].exits == [None]

    factory = lambda: nullcontext(AsyncFakeSystemOnePort())
    assert anyio.run(exit_problem, factory) is None
    assert anyio.run(body_problem, factory) is None
    ```

See Also:
    - [judgevet.testing._conformance_async][]: The rules that use these checks
    - [judgevet.testing._conformance_probes][]: The synchronous `ScopeRecorder`
    - [judgevet.providers][]: `async_provider_scope` and `AsyncProviderFactory`
"""

from contextlib import AbstractAsyncContextManager
from types import TracebackType

from judgevet.ports import AsyncSystemOnePort
from judgevet.providers import AsyncProviderFactory, async_provider_scope
from judgevet.testing._conformance_probes import BodyError


class AsyncRecordedContext(AbstractAsyncContextManager[AsyncSystemOnePort]):
    """Delegate to one async provider context and record its entry and exit.

    Attributes:
        inner (AbstractAsyncContextManager[AsyncSystemOnePort]): The provider's
            async context.
        enters (int): How many times entry ran.
        exits (list[BaseException | None]): The exception each exit received,
            or None for a clean exit.

    Examples:
        ```python
        from contextlib import nullcontext

        import anyio

        from judgevet.testing import AsyncFakeSystemOnePort

        recorded = AsyncRecordedContext(nullcontext(AsyncFakeSystemOnePort()))


        async def enter():
            async with recorded:
                pass


        anyio.run(enter)
        assert (recorded.enters, recorded.exits) == (1, [None])
        ```
    """

    def __init__(self, inner: AbstractAsyncContextManager[AsyncSystemOnePort]) -> None:
        """Wrap one async provider context.

        Args:
            inner: The async context the provider factory returned.
        """
        self.inner = inner
        self.enters = 0
        self.exits: list[BaseException | None] = []

    async def __aenter__(self) -> AsyncSystemOnePort:
        """Count the entry and enter the provider context.

        Returns:
            The port the provider context yields.
        """
        self.enters += 1
        return await self.inner.__aenter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        """Record the exit and pass the provider's suppression answer through.

        Args:
            exc_type: The escaping exception type, or None.
            exc: The escaping exception, or None.
            traceback: The escaping traceback, or None.

        Returns:
            The provider context's own return value.
        """
        self.exits.append(exc)
        return await self.inner.__aexit__(exc_type, exc, traceback)


class AsyncScopeRecorder:
    """Wrap an async provider factory and record every context it constructs.

    Attributes:
        factory (AsyncProviderFactory): The provider's own factory.
        contexts (list[AsyncRecordedContext]): One recorder per factory call.

    Examples:
        ```python
        from contextlib import nullcontext

        from judgevet.testing import AsyncFakeSystemOnePort

        recorder = AsyncScopeRecorder(lambda: nullcontext(AsyncFakeSystemOnePort()))
        recorder()
        assert len(recorder.contexts) == 1
        ```
    """

    def __init__(self, factory: AsyncProviderFactory) -> None:
        """Store the provider factory.

        Args:
            factory: The provider's own factory.
        """
        self.factory = factory
        self.contexts: list[AsyncRecordedContext] = []

    def __call__(self) -> AsyncRecordedContext:
        """Construct one provider context and start recording it.

        Returns:
            A recorder that delegates to the new provider context.
        """
        recorded = AsyncRecordedContext(self.factory())
        self.contexts.append(recorded)
        return recorded


async def exit_problem(factory: AsyncProviderFactory) -> str | None:
    """Enter two scopes and describe a shared context or a wrong exit count.

    Args:
        factory: The provider's factory.

    Returns:
        A failure message, or None when each scope has its own context that
        entered once and exited once cleanly.
    """
    recorder = AsyncScopeRecorder(factory)
    for _ in range(2):
        async with async_provider_scope(factory=recorder):
            pass
    first, second = (context.inner for context in recorder.contexts)
    if first is second:
        return (
            "provider_factory returned one shared context for two scopes, so its "
            "cleanup runs twice on the same resource. Construct a new context."
        )
    observed = [(c.enters, c.exits) for c in recorder.contexts]
    if observed != [(1, [None]), (1, [None])]:
        return f"Expected one entry and one clean exit per scope, observed {observed}."
    return None


async def _raise_in_scope(factory: AsyncProviderFactory, body: BodyError) -> None:
    """Raise an exception inside one async provider scope of a factory.

    Args:
        factory: The factory whose scope receives the exception.
        body: The exception to raise inside the scope body.

    Raises:
        BodyError: The body exception, when the scope lets it propagate.
    """
    async with async_provider_scope(factory=factory):
        raise body


async def body_problem(factory: AsyncProviderFactory) -> str | None:
    """Raise inside a scope and describe a lost, replaced or suppressed error.

    The check also enters one context directly, as `AsyncProviderFactory`
    callers may, and requires that its exit does not suppress the error.

    Args:
        factory: The provider's factory.

    Returns:
        A failure message, or None when the body exception reaches the caller
        unchanged and the scope exits once with it.
    """
    body = BodyError("raised inside the provider scope")
    recorder = AsyncScopeRecorder(factory)
    try:
        await _raise_in_scope(recorder, body)
    except BodyError as caught:
        if caught is not body:
            return "async_provider_scope replaced the body exception."
    else:
        return "async_provider_scope did not propagate the body exception."
    exits = [context.exits for context in recorder.contexts]
    if exits != [[body]]:
        return f"Expected one exit with the error, got {exits}."
    direct = recorder()
    await direct.__aenter__()
    if await direct.__aexit__(BodyError, body, None):
        return (
            "The provider context suppressed a body exception. Return a false "
            "value from __aexit__ so the exception propagates."
        )
    return None
