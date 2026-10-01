"""A provider test module the runner executes against the installed kit (#241).

A provider package writes a module like this one in its own test suite. It
subclasses the kit's base classes and overrides the fixtures that supply its
implementation. The installed-artifact runner runs it with pytest inside the
``conformance`` environment and requires every rule test to pass. The async
subclass covers the nine asynchronous rules, media rules included
(#246, #251, #252).
"""

from collections.abc import Callable, Mapping
from contextlib import nullcontext
from dataclasses import replace
from typing import Any

import pytest

from judgevet.domain.media import ImageEvidence, MediaCapabilities
from judgevet.domain.questions import Question
from judgevet.domain.response import SystemOneResponse
from judgevet.providers import ProviderFactory, ProviderTransportError
from judgevet.testing import AsyncFakeSystemOnePort, FakeSystemOnePort
from judgevet.testing.conformance import (
    VALID_ANSWERS,
    BaseAsyncProviderConformance,
    BaseProviderConformance,
)
from tests.fixtures.providers.provider_fixture import RecordingProvider


class KitMediaProvider(RecordingProvider):
    """The recording provider, answering media calls with the kit's answers."""

    def system_one_media(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        evidence: ImageEvidence,
    ) -> SystemOneResponse:
        """Record the media call, then answer the kit questions.

        Args:
            state: Received state.
            questions: Received questions.
            model: Received model.
            evidence: Received ordered evidence.

        Returns:
            The recorded response with the kit's valid answers.
        """
        recorded = super().system_one_media(state, questions, model, evidence=evidence)
        return replace(recorded, answers=dict(VALID_ANSWERS))


class TestInstalledProvider(BaseProviderConformance):
    """The public fake and the application fixture pass every rule."""

    @pytest.fixture
    def provider_factory(self) -> ProviderFactory:
        """Borrow a scripted fake per scope.

        Returns:
            A factory whose context yields a fake with the kit's answers.
        """
        return lambda: nullcontext(FakeSystemOnePort(answers=VALID_ANSWERS))

    @pytest.fixture
    def failing_port(self) -> RecordingProvider:
        """Raise a transport failure from every judgment.

        Returns:
            A recording provider configured to fail.
        """
        return RecordingProvider("installed-failing", fail=True)

    @pytest.fixture
    def media_port(self) -> KitMediaProvider:
        """Declare PNG and JPEG support only.

        Returns:
            A recording provider with media support.
        """
        return KitMediaProvider("installed-media")


class AsyncKitMediaFake(AsyncFakeSystemOnePort):
    """The public async fake, declaring PNG support and judging media as text."""

    def capabilities(self, model: str) -> MediaCapabilities:
        """Declare PNG support for every model.

        Args:
            model: The selected model.

        Returns:
            The static declaration.
        """
        return MediaCapabilities({"image/png"})

    async def system_one_media(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        evidence: ImageEvidence,
    ) -> SystemOneResponse:
        """Answer the kit questions as the async text fake does.

        Args:
            state: The content to judge.
            questions: Question names mapped to question definitions.
            model: The selected model.
            evidence: The ordered image evidence.

        Returns:
            The fake's scripted response.
        """
        return await self.system_one(state, questions, model)


class TestInstalledAsyncProvider(BaseAsyncProviderConformance):
    """The public async fake passes every async rule."""

    @pytest.fixture
    def provider_factory(self) -> Callable[[], nullcontext[AsyncFakeSystemOnePort]]:
        """Borrow a scripted async fake per scope.

        Returns:
            A factory whose async context yields a fake with the kit's answers.
        """
        return lambda: nullcontext(AsyncFakeSystemOnePort(answers=VALID_ANSWERS))

    @pytest.fixture
    def failing_port(self) -> AsyncFakeSystemOnePort:
        """Raise a transport failure from every awaited judgment.

        Returns:
            An async fake configured to fail.
        """
        return AsyncFakeSystemOnePort(error=ProviderTransportError("offline"))

    @pytest.fixture
    def media_port(self) -> AsyncKitMediaFake:
        """Supply an async media port with the kit's answers.

        Returns:
            An async fake with PNG support.
        """
        return AsyncKitMediaFake(answers=VALID_ANSWERS)
