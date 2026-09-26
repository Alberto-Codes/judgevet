"""Acceptance for explicit borrowed and factory-owned provider lifetimes."""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

import pytest

from judgevet import Noul, NoulAnswer, Question, SystemOneResponse, Usage
from judgevet.domain.errors import JevError, JudgevetError
from judgevet.providers import (
    ProviderCapabilityError,
    ProviderError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderTransportError,
    ProviderUnavailableError,
    provider_scope,
)


class RecordingProvider:
    """Record calls and cleanup without an inference dependency."""

    def __init__(self) -> None:
        """Initialize call and cleanup counters."""
        self.closed = 0
        self.calls = 0

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Return a typed fixture while the provider remains open."""
        assert not self.closed
        self.calls += 1
        return SystemOneResponse(
            model=model,
            usage=Usage(),
            answers={"q": NoulAnswer(0.9)},
        )

    def close(self) -> None:
        """Count each cleanup call."""
        self.closed += 1


def call(provider: RecordingProvider) -> SystemOneResponse:
    """Exercise the real public port contract."""
    return provider.system_one("synthetic", {"q": Noul()}, "fixture-v1")


@pytest.mark.parametrize("failure", [False, True])
def test_borrowed_provider_remains_usable(failure: bool) -> None:
    """Success and escaping failure do not transfer borrowed ownership."""
    provider = RecordingProvider()
    if failure:
        with (
            pytest.raises(RuntimeError, match="call failed"),
            provider_scope(port=provider) as selected,
        ):
            selected.system_one("synthetic", {"q": Noul()}, "fixture-v1")
            raise RuntimeError("call failed")
    else:
        with provider_scope(port=provider) as selected:
            response = selected.system_one("synthetic", {"q": Noul()}, "fixture-v1")
            assert response.model == "fixture-v1"
            assert response.usage.input_tokens is None
    assert provider.closed == 0
    assert call(provider).answers["q"] == NoulAnswer(0.9)


@pytest.mark.parametrize("failure", [False, True])
def test_factory_context_closes_once(failure: bool) -> None:
    """The scope owns exit after successful factory entry."""
    provider = RecordingProvider()
    entered = []

    @contextmanager
    def factory() -> Iterator[RecordingProvider]:
        entered.append(True)
        try:
            yield provider
        finally:
            provider.close()

    if failure:
        with (
            pytest.raises(RuntimeError, match="render failed"),
            provider_scope(factory=factory) as selected,
        ):
            selected.system_one("synthetic", {"q": Noul()}, "fixture-v1")
            raise RuntimeError("render failed")
    else:
        with provider_scope(factory=factory) as selected:
            selected.system_one("synthetic", {"q": Noul()}, "fixture-v1")
    assert entered == [True]
    assert provider.calls == 1
    assert provider.closed == 1


def test_factory_rolls_back_failed_setup() -> None:
    """A factory cleans allocated resources when entry fails before yielding."""
    provider = RecordingProvider()

    @contextmanager
    def factory() -> Iterator[RecordingProvider]:
        try:
            raise ProviderUnavailableError("install the application provider extra")
            yield provider
        finally:
            provider.close()

    with (
        pytest.raises(ProviderUnavailableError, match="application provider extra"),
        provider_scope(factory=factory),
    ):
        pytest.fail("failed setup must not enter the body")
    assert provider.closed == 1
    assert provider.calls == 0


def test_conflicting_selection_rejects_before_entry() -> None:
    """Two selections never call the supplied factory."""
    provider = RecordingProvider()

    @contextmanager
    def factory() -> Iterator[RecordingProvider]:
        pytest.fail("conflicting selection entered factory")
        yield provider

    with pytest.raises(ValueError), provider_scope(port=provider, factory=factory):
        pytest.fail("conflicting selection reached body")
    assert provider.closed == 0


def test_missing_selection_has_no_implicit_default() -> None:
    """The ownership helper never constructs a hosted provider."""
    with pytest.raises(ValueError), provider_scope():
        pytest.fail("missing selection reached body")


def test_invalid_yielded_provider_still_unwinds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-entry validation cannot leak a factory-owned resource."""
    provider = RecordingProvider()
    monkeypatch.setattr(provider, "system_one", None)

    @contextmanager
    def factory() -> Iterator[RecordingProvider]:
        try:
            yield provider
        finally:
            provider.close()

    with pytest.raises(ProviderUnavailableError), provider_scope(factory=factory):
        pytest.fail("invalid port reached body")
    assert provider.closed == 1
    assert provider.calls == 0


def test_interruption_unwinds_owned_scope() -> None:
    """A BaseException cannot bypass acquired-context cleanup."""
    provider = RecordingProvider()

    @contextmanager
    def factory() -> Iterator[RecordingProvider]:
        try:
            yield provider
        finally:
            provider.close()

    with pytest.raises(KeyboardInterrupt), provider_scope(factory=factory):
        raise KeyboardInterrupt
    assert provider.closed == 1


def test_invalid_borrowed_provider_stays_open(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject invalid borrowed ports without assuming resource ownership."""
    provider = RecordingProvider()
    monkeypatch.setattr(provider, "system_one", None)
    with pytest.raises(ProviderUnavailableError), provider_scope(port=provider):
        pytest.fail("invalid borrowed port reached body")
    assert provider.closed == 0
    assert provider.calls == 0


def test_factory_cannot_suppress_body_failure() -> None:
    """Factory cleanup observes the original failure but cannot swallow it."""
    provider = RecordingProvider()
    failure = RuntimeError("call failed")
    observed = []

    @contextmanager
    def factory() -> Iterator[RecordingProvider]:
        try:
            yield provider
        except RuntimeError as exc:
            observed.append(exc)
        finally:
            provider.close()

    with pytest.raises(RuntimeError) as caught, provider_scope(factory=factory):
        raise failure
    assert caught.value is failure
    assert observed == [failure]
    assert provider.closed == 1


@pytest.mark.parametrize(
    "error_type",
    [
        ProviderError,
        ProviderUnavailableError,
        ProviderRequestError,
        ProviderCapabilityError,
        ProviderTransportError,
        ProviderResponseError,
    ],
)
def test_provider_errors_are_neutral(error_type: type[ProviderError]) -> None:
    """Declared provider failures carry no invented service metadata."""
    error = error_type("safe application message")
    assert isinstance(error, JudgevetError)
    assert isinstance(error, ProviderError)
    assert not isinstance(error, JevError)
    assert str(error) == "safe application message"
    assert error.args == ("safe application message",)
    assert not hasattr(error, "status_code")
    assert not hasattr(error, "retryable")
