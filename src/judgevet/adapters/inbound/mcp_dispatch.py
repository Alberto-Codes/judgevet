"""Serialize synchronous MCP providers outside the event loop.

Source: https://github.com/Alberto-Codes/judgevet/issues/202#issuecomment-5850906357.

Examples:
    ```python
    from judgevet.adapters.inbound.mcp_dispatch import ProviderDispatch
    from judgevet.testing import FakeSystemOnePort

    dispatch = ProviderDispatch(port=FakeSystemOnePort())
    assert dispatch.port is not None
    ```

See Also:
    - [judgevet.adapters.inbound.mcp][]: SDK server construction.
    - [judgevet.providers][]: Application ownership contexts.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator, Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from contextvars import ContextVar
from functools import partial
from typing import Any

from judgevet.domain.questions import Question
from judgevet.domain.response import SystemOneResponse
from judgevet.ports import SystemOnePort
from judgevet.providers import ProviderFactory, provider_scope

_current: ContextVar[ProviderDispatch | None] = ContextVar("mcp_dispatch", default=None)


async def _drain[T](operation: asyncio.Future[T]) -> T:
    """Wait through repeated cancellation until a submitted operation finishes.

    Args:
        operation: Submitted worker operation, protected from cancellation.

    Returns:
        The operation result if the caller was not canceled.

    Raises:
        asyncio.CancelledError: After completion if the caller was canceled.
        BaseException: The operation failed before caller cancellation.
    """
    cancellation = None
    while not operation.done():
        try:
            await asyncio.shield(operation)
        except asyncio.CancelledError as exc:
            cancellation = exc
        except BaseException:
            if cancellation is None:
                raise
    if cancellation is not None:
        if not operation.cancelled():
            operation.exception()
        raise cancellation
    return operation.result()


class ProviderDispatch:
    """Own one worker for a serving session and serialize its provider calls.

    Attributes:
        port (SystemOnePort | None): Selected provider once acquisition succeeds.

    Examples:
        ```python
        from judgevet.adapters.inbound.mcp_dispatch import ProviderDispatch
        from judgevet.testing import FakeSystemOnePort

        port = FakeSystemOnePort()
        dispatch = ProviderDispatch(port=port)
        assert dispatch.port is port
        ```
    """

    def __init__(
        self,
        *,
        port: SystemOnePort | None = None,
        factory: ProviderFactory | None = None,
    ) -> None:
        """Retain selection without acquiring resources.

        Args:
            port: Borrowed provider.
            factory: Owning application factory.
        """
        self.port = port
        self._factory = factory
        self._executor: ThreadPoolExecutor | None = None
        self._lock = asyncio.Lock()
        self._entered = False
        self._context = provider_scope(port=port, factory=factory)

    async def _run[T](self, operation: Callable[[], T]) -> T:
        """Submit an operation to the session worker and drain cancellation.

        Args:
            operation: Synchronous operation to execute.

        Returns:
            The operation result.

        Raises:
            RuntimeError: No session is active.
            BaseException: Operation failure or drained cancellation.
        """
        if self._executor is None:
            raise RuntimeError("Provider session is not active")
        return await _drain(
            asyncio.get_running_loop().run_in_executor(
                self._executor,
                operation,
            )
        )

    def _enter(self) -> None:
        """Acquire the selected provider on its owning worker.

        Raises:
            BaseException: Application acquisition or validation failed.
        """
        self._context = provider_scope(port=self.port, factory=self._factory)
        self.port = self._context.__enter__()
        self._entered = True

    @asynccontextmanager
    async def session(self) -> AsyncIterator[None]:
        """Keep acquisition, work and cleanup on one worker thread.

        Yields:
            Control while the selected provider is available.

        Raises:
            BaseException: Acquisition, serving, cleanup or cancellation failed.
        """
        if self._executor is not None:
            yield
            return
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="judgevet-mcp"
        )
        token = _current.set(self)
        try:
            await self._run(self._enter)
            yield
        finally:
            error = sys.exc_info()
            try:
                if self._entered:
                    await self._run(partial(self._context.__exit__, *error))
            finally:
                self._executor.shutdown(wait=True)
                self._executor = None
                self._entered = False
                _current.reset(token)

    async def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Serialize a judgment and never submit a canceled queued request.

        Args:
            state: Original caller state.
            questions: Original question definitions.
            model: Host-selected model.

        Returns:
            The provider's unchanged answer envelope.

        Raises:
            RuntimeError: Acquisition yielded no provider.
            BaseException: Provider failure or drained cancellation.
        """
        async with self._lock, self.session():
            if self.port is None:
                raise RuntimeError("Provider acquisition did not return a port")
            return await self._run(
                partial(
                    self.port.system_one,
                    state=state,
                    questions=questions,
                    model=model,
                )
            )


def dispatch_for(port: SystemOnePort) -> ProviderDispatch:
    """Reuse the composition root's worker for its selected provider.

    Args:
        port: Selected provider passed to the server factory.

    Returns:
        The active matching dispatcher or a new borrowed dispatcher.
    """
    current = _current.get()
    if current is not None and current.port is port:
        return current
    return ProviderDispatch(port=port)
