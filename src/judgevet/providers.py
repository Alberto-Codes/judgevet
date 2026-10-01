"""Explicit provider selection and application-owned resource lifetimes.

There is no default provider, discovery or fallback in this module.
Source: https://github.com/Alberto-Codes/judgevet/issues/201#issuecomment-5850529268.
`provider_scope` and `ProviderFactory` serve a synchronous port.
`async_provider_scope` and `AsyncProviderFactory` serve an asynchronous port.
Source: https://github.com/Alberto-Codes/judgevet/issues/251.

Examples:
    ```python
    from judgevet.providers import ProviderError, ProviderUnavailableError

    error = ProviderUnavailableError("Install the application provider extra")
    assert isinstance(error, ProviderError)
    ```

See Also:
    - [judgevet.ports][]: Structural judgment ports.
    - [judgevet.domain.provider_errors][]: Neutral provider error classes.
"""

from collections.abc import AsyncIterator, Iterator
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    asynccontextmanager,
    contextmanager,
)
from typing import Protocol

from judgevet.domain.provider_errors import (
    ProviderCapabilityError,
    ProviderError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderTransportError,
    ProviderUnavailableError,
)
from judgevet.ports import AsyncSystemOnePort, SystemOnePort

__all__ = [
    "AsyncProviderFactory",
    "ProviderCapabilityError",
    "ProviderError",
    "ProviderFactory",
    "ProviderRequestError",
    "ProviderResponseError",
    "ProviderTransportError",
    "ProviderUnavailableError",
    "async_provider_scope",
    "provider_scope",
]


class ProviderFactory(Protocol):
    """Construct a context that owns a synchronous provider.

    The application owns rollback if entry fails before returning a port.

    Attributes:
        __call__ (method): Construct the provider's owning context.

    Examples:
        ```python
        from contextlib import nullcontext

        from judgevet import NoulAnswer
        from judgevet.providers import ProviderFactory
        from judgevet.testing import FakeSystemOnePort

        factory: ProviderFactory = lambda: nullcontext(
            FakeSystemOnePort(answers={"q": NoulAnswer(0.9)})
        )
        with factory() as port:
            response = port.system_one("synthetic", {"q": {"type": "noul"}}, "fixture")
        assert response.answers["q"] == NoulAnswer(0.9)
        ```
    """

    def __call__(self) -> AbstractContextManager[SystemOnePort]:
        """Return a context responsible for provider acquisition and cleanup.

        Returns:
            A context yielding the selected judgment port.

        Raises:
            ProviderUnavailableError: Application support is unavailable.
        """
        ...


class AsyncProviderFactory(Protocol):
    """Construct an async context that owns an asynchronous provider.

    This Protocol mirrors `ProviderFactory` for an `AsyncSystemOnePort`.
    The application owns rollback if entry fails before returning a port.
    Source: https://github.com/Alberto-Codes/judgevet/issues/251.

    Attributes:
        __call__ (method): Construct the provider's owning async context.

    Examples:
        ```python
        from contextlib import nullcontext

        import anyio

        from judgevet import NoulAnswer
        from judgevet.providers import AsyncProviderFactory
        from judgevet.testing import AsyncFakeSystemOnePort

        factory: AsyncProviderFactory = lambda: nullcontext(
            AsyncFakeSystemOnePort(answers={"q": NoulAnswer(0.9)})
        )


        async def main():
            async with factory() as port:
                return await port.system_one(
                    "synthetic", {"q": {"type": "noul"}}, "fixture"
                )


        assert anyio.run(main).answers["q"] == NoulAnswer(0.9)
        ```
    """

    def __call__(self) -> AbstractAsyncContextManager[AsyncSystemOnePort]:
        """Return an async context responsible for acquisition and cleanup.

        Returns:
            An async context yielding the selected asynchronous judgment port.

        Raises:
            ProviderUnavailableError: Application support is unavailable.
        """
        ...


def _validate_port(port: SystemOnePort | AsyncSystemOnePort) -> None:
    """Require a callable judgment method without performing inference.

    Both scopes share this check, so a synchronous or an asynchronous port
    is accepted.

    Args:
        port: The selected synchronous or asynchronous provider to inspect.

    Raises:
        ProviderUnavailableError: The provider has no callable judgment method.
    """
    if not callable(getattr(port, "system_one", None)):
        raise ProviderUnavailableError("Provider must expose callable system_one")


@contextmanager
def provider_scope(
    *, port: SystemOnePort | None = None, factory: ProviderFactory | None = None
) -> Iterator[SystemOnePort]:
    """Borrow a port or enter an application's owning provider context.

    Selection and validation occur on entry. Borrowed resources remain open.
    Once factory entry succeeds, exit runs exactly once, including invalid-port
    validation and BaseException interruption. A context cannot suppress an
    escaping body exception. An exception raised by cleanup itself propagates
    with the original failure as its exception context.

    Args:
        port: A caller-owned judgment port.
        factory: A callable returning an owning context for a judgment port.

    Yields:
        The explicitly selected provider, unchanged.

    Raises:
        ValueError: Neither or both selection arguments are supplied.
        ProviderUnavailableError: The selected port lacks callable system_one.
        BaseException: Acquisition, body and cleanup failures propagate.
    """
    if port is not None:
        if factory is not None:
            raise ValueError("Supply exactly one of port or factory")
        _validate_port(port)
        yield port
        return
    if factory is None:
        raise ValueError("Supply exactly one of port or factory")

    context = factory()
    selected = context.__enter__()
    try:
        _validate_port(selected)
        yield selected
    except BaseException as exc:
        context.__exit__(type(exc), exc, exc.__traceback__)
        raise
    else:
        context.__exit__(None, None, None)


@asynccontextmanager
async def async_provider_scope(
    *,
    port: AsyncSystemOnePort | None = None,
    factory: AsyncProviderFactory | None = None,
) -> AsyncIterator[AsyncSystemOnePort]:
    """Borrow an async port or enter an application's owning async context.

    This scope keeps every `provider_scope` guarantee for an asynchronous port.
    Selection and validation occur on entry. Borrowed resources remain open.
    Once factory entry succeeds, exit runs exactly once, including invalid-port
    validation and BaseException interruption. A context cannot suppress an
    escaping body exception. An exception raised by cleanup itself propagates
    with the original failure as its exception context.
    Source: https://github.com/Alberto-Codes/judgevet/issues/251.

    Args:
        port: A caller-owned asynchronous judgment port.
        factory: A callable returning an owning async context for a port.

    Yields:
        The explicitly selected provider, unchanged.

    Raises:
        ValueError: Neither or both selection arguments are supplied.
        ProviderUnavailableError: The selected port lacks callable system_one.
        BaseException: Acquisition, body and cleanup failures propagate.
    """
    if port is not None:
        if factory is not None:
            raise ValueError("Supply exactly one of port or factory")
        _validate_port(port)
        yield port
        return
    if factory is None:
        raise ValueError("Supply exactly one of port or factory")

    context = factory()
    selected = await context.__aenter__()
    try:
        _validate_port(selected)
        yield selected
    except BaseException as exc:
        await context.__aexit__(type(exc), exc, exc.__traceback__)
        raise
    else:
        await context.__aexit__(None, None, None)
