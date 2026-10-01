"""Acceptance for borrowed and factory-owned async provider lifetimes (#251).

`async_provider_scope` keeps the `provider_scope` guarantees for an
`AsyncSystemOnePort`. Each test drives its coroutine with `anyio.run`.
Source: https://github.com/Alberto-Codes/judgevet/issues/251#issuecomment-5923867707.
"""

from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

import anyio
import pytest

from judgevet import Noul, NoulAnswer, Question, SystemOneResponse, Usage, providers
from judgevet.ports import AsyncSystemOnePort
from judgevet.providers import ProviderUnavailableError, async_provider_scope
from judgevet.testing.conformance import AsyncProviderFactory as KitFactory

pytestmark = pytest.mark.unit


class AsyncRecordingProvider:
    """Record awaited calls and cleanup without an inference dependency."""

    def __init__(self) -> None:
        """Initialize call and cleanup counters."""
        self.closed = 0
        self.calls = 0

    async def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Return a typed fixture while the provider remains open."""
        assert not self.closed
        self.calls += 1
        return SystemOneResponse(
            model=model, usage=Usage(), answers={"q": NoulAnswer(0.9)}
        )

    async def aclose(self) -> None:
        """Count each cleanup call."""
        self.closed += 1


def owning(
    provider: AsyncRecordingProvider, entered: list[bool]
) -> Callable[[], AbstractAsyncContextManager[AsyncRecordingProvider]]:
    """Build a factory whose context enters once and closes the provider."""

    @asynccontextmanager
    async def factory() -> AsyncIterator[AsyncRecordingProvider]:
        entered.append(True)
        try:
            yield provider
        finally:
            await provider.aclose()

    return factory


async def judge(port: AsyncSystemOnePort) -> SystemOneResponse:
    """Await one judgment through the public port contract."""
    return await port.system_one("synthetic", {"q": Noul()}, "fixture-v1")


def test_kit_factory_is_the_providers_protocol() -> None:
    """The kit re-exports the providers Protocol, not a separate alias."""
    assert KitFactory is providers.AsyncProviderFactory


@pytest.mark.parametrize("failure", [False, True])
def test_borrowed_async_provider_remains_open(failure: bool) -> None:
    """Success and escaping failure do not transfer borrowed ownership."""
    provider = AsyncRecordingProvider()

    async def body() -> None:
        async with async_provider_scope(port=provider) as selected:
            assert selected is provider
            assert (await judge(selected)).model == "fixture-v1"
            if failure:
                raise RuntimeError("call failed")

    if failure:
        with pytest.raises(RuntimeError, match="call failed"):
            anyio.run(body)
    else:
        anyio.run(body)
    assert provider.closed == 0
    assert anyio.run(judge, provider).answers["q"] == NoulAnswer(0.9)


@pytest.mark.parametrize("failure", [False, True])
def test_async_factory_enters_and_exits_once(failure: bool) -> None:
    """The scope owns exit after successful factory entry."""
    provider = AsyncRecordingProvider()
    entered: list[bool] = []

    async def body() -> None:
        async with async_provider_scope(factory=owning(provider, entered)) as port:
            await judge(port)
            if failure:
                raise RuntimeError("render failed")

    if failure:
        with pytest.raises(RuntimeError, match="render failed"):
            anyio.run(body)
    else:
        anyio.run(body)
    assert entered == [True]
    assert provider.calls == 1
    assert provider.closed == 1


def test_async_factory_cannot_suppress_body_failure() -> None:
    """Factory cleanup observes the original failure but cannot swallow it."""
    provider = AsyncRecordingProvider()
    failure = RuntimeError("call failed")
    observed: list[BaseException] = []

    @asynccontextmanager
    async def factory() -> AsyncIterator[AsyncRecordingProvider]:
        try:
            yield provider
        except RuntimeError as exc:
            observed.append(exc)
        finally:
            await provider.aclose()

    async def body() -> None:
        async with async_provider_scope(factory=factory):
            raise failure

    with pytest.raises(RuntimeError) as caught:
        anyio.run(body)
    assert caught.value is failure
    assert observed == [failure]
    assert provider.closed == 1


def test_async_interruption_unwinds_owned_scope() -> None:
    """A BaseException cannot bypass acquired-context cleanup."""
    provider = AsyncRecordingProvider()

    async def body() -> None:
        async with async_provider_scope(factory=owning(provider, [])):
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        anyio.run(body)
    assert provider.closed == 1


def test_async_factory_rolls_back_failed_setup() -> None:
    """A factory cleans allocated resources when entry fails before yielding."""
    provider = AsyncRecordingProvider()

    @asynccontextmanager
    async def factory() -> AsyncIterator[AsyncRecordingProvider]:
        try:
            raise ProviderUnavailableError("install the application provider extra")
            yield provider
        finally:
            await provider.aclose()

    async def body() -> None:
        async with async_provider_scope(factory=factory):
            pytest.fail("failed setup must not enter the body")

    with pytest.raises(ProviderUnavailableError, match="application provider"):
        anyio.run(body)
    assert provider.closed == 1
    assert provider.calls == 0


def test_conflicting_async_selection_rejects_before_entry() -> None:
    """Two selections never call the supplied factory."""
    provider = AsyncRecordingProvider()

    @asynccontextmanager
    async def factory() -> AsyncIterator[AsyncRecordingProvider]:
        pytest.fail("conflicting selection entered factory")
        yield provider

    async def body() -> None:
        async with async_provider_scope(port=provider, factory=factory):
            pytest.fail("conflicting selection reached body")

    with pytest.raises(ValueError, match="exactly one of port or factory"):
        anyio.run(body)
    assert provider.closed == 0


def test_missing_async_selection_has_no_implicit_default() -> None:
    """The async ownership helper never constructs a hosted provider."""

    async def body() -> None:
        async with async_provider_scope():
            pytest.fail("missing selection reached body")

    with pytest.raises(ValueError, match="exactly one of port or factory"):
        anyio.run(body)


def test_invalid_borrowed_async_port_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A borrowed port without callable system_one never reaches the body."""
    provider = AsyncRecordingProvider()
    monkeypatch.setattr(provider, "system_one", None)

    async def body() -> None:
        async with async_provider_scope(port=provider):
            pytest.fail("invalid borrowed port reached body")

    with pytest.raises(ProviderUnavailableError, match="callable system_one"):
        anyio.run(body)
    assert provider.closed == 0


def test_invalid_yielded_async_port_still_unwinds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-entry validation cannot leak a factory-owned resource."""
    provider = AsyncRecordingProvider()
    monkeypatch.setattr(provider, "system_one", None)
    exits: list[BaseException] = []

    @asynccontextmanager
    async def factory() -> AsyncIterator[AsyncRecordingProvider]:
        try:
            yield provider
        except BaseException as exc:
            exits.append(exc)
            raise
        finally:
            await provider.aclose()

    async def body() -> None:
        async with async_provider_scope(factory=factory):
            pytest.fail("invalid port reached body")

    with pytest.raises(ProviderUnavailableError, match="callable system_one"):
        anyio.run(body)
    assert provider.closed == 1
    assert provider.calls == 0
    assert len(exits) == 1
    assert isinstance(exits[0], ProviderUnavailableError)
