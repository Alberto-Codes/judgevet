"""Exercise the async media dispatch boundary offline (#252).

`async_judge_with_images` keeps the checks, their order and the errors of
`judge_with_images`, and awaits the provider. Source:
https://github.com/Alberto-Codes/judgevet/issues/252#issuecomment-5924224316.

Examples:
    Run the focused pytest module from the repository root.

See Also:
    - [judgevet.media][]: Public media contract.
"""

from collections.abc import Mapping
from typing import Any

import anyio
import pytest

from judgevet import (
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Question,
    SystemOneResponse,
    Usage,
)
from judgevet.media import (
    ImageAttachment,
    ImageEvidence,
    MediaCapabilities,
    MissingEvidenceError,
    async_judge_with_images,
)
from judgevet.ports import AsyncSystemOnePort
from judgevet.ports.media import AsyncMediaSystemOnePort
from judgevet.providers import (
    ProviderCapabilityError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderTransportError,
)

FIRST = ImageAttachment("first", b"opaque-encoded-image-A", "image/png")
SECOND = ImageAttachment("second", b"opaque-encoded-image-B", "image/png")
QUESTIONS = {
    "claim": Noul(instructions={"rule": "check exact evidence"}),
    "decision": Choice(criteria={"yes": "supported", "no": "unsupported"}),
}
RESPONSE = SystemOneResponse(
    model="fixture-resolved",
    usage=Usage(0, None),
    answers={
        "claim": NoulAnswer(0.9),
        "decision": ChoiceAnswer("yes", 0.8, {"yes": 0.8, "no": 0.2}),
    },
)


def evidence() -> ImageEvidence:
    """Use shared images with different global and question-specific orders.

    Returns:
        The offline fixture value.
    """
    return ImageEvidence(
        [FIRST, SECOND],
        {"claim": ["second", "first"], "decision": ["first"]},
        {"claim"},
    )


class AsyncRecordingMediaProvider:
    """Record capability lookup, awaited media submission and text calls.

    Attributes:
        calls (list): Captured media calls.
        models (list[str]): Capability lookups.
        text_calls (int): Text dispatch count.
        fail (bool): Inject transport failure.
        response (SystemOneResponse): Returned fixture.

    Examples:
        Exercise this offline fixture through the tests in this module.
    """

    def __init__(
        self, *, fail: bool = False, response: SystemOneResponse = RESPONSE
    ) -> None:
        """Initialize the repository-owned offline fixture."""
        self.calls: list[tuple[object, object, str, ImageEvidence]] = []
        self.models: list[str] = []
        self.text_calls = 0
        self.fail = fail
        self.response = response

    def capabilities(self, model: str) -> MediaCapabilities:
        """Return a static declaration without acquisition or inference.

        Returns:
            The offline fixture value.
        """
        self.models.append(model)
        return MediaCapabilities({"image/png"})

    async def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Keep the existing text route observable.

        Returns:
            The offline fixture value.
        """
        self.text_calls += 1
        return self.response

    async def system_one_media(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        evidence: ImageEvidence,
    ) -> SystemOneResponse:
        """Record exact inputs and return typed answers or a declared failure.

        Returns:
            The offline fixture value.

        Raises:
            ProviderTransportError: The fixture injects a transport failure.
        """
        self.calls.append((state, questions, model, evidence))
        if self.fail:
            raise ProviderTransportError("fixture transport failed")
        return self.response


class AsyncTextOnly:
    """Expose only the async text operation.

    Attributes:
        text_calls (int): Text dispatch count.

    Examples:
        Exercise this offline fixture through the tests in this module.
    """

    def __init__(self) -> None:
        """Start with no text dispatch."""
        self.text_calls = 0

    async def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Count a text dispatch that must not happen for media.

        Returns:
            The offline fixture value.
        """
        self.text_calls += 1
        return RESPONSE


class SyncMediaOnAsyncPort(AsyncTextOnly):
    """Declare media support but judge it synchronously.

    Attributes:
        calls (list): Captured media calls.

    Examples:
        Exercise this offline fixture through the tests in this module.
    """

    def __init__(self) -> None:
        """Start with no media dispatch."""
        super().__init__()
        self.calls: list[tuple[object, object, str, ImageEvidence]] = []

    def capabilities(self, model: str) -> MediaCapabilities:
        """Declare PNG support.

        Returns:
            The offline fixture value.
        """
        return MediaCapabilities({"image/png"})

    def system_one_media(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        evidence: ImageEvidence,
    ) -> SystemOneResponse:
        """Return the response without an awaitable.

        Returns:
            The offline fixture value.
        """
        self.calls.append((state, questions, model, evidence))
        return RESPONSE


def judge(
    port: AsyncSystemOnePort,
    submitted: ImageEvidence,
    state: str | dict[str, Any] | list[Any] = "text",
) -> SystemOneResponse:
    """Drive one async media judgment to completion.

    Args:
        port: The provider under test.
        submitted: The evidence to send.
        state: The caller state.

    Returns:
        The awaited response.
    """

    async def call() -> SystemOneResponse:
        """Await the dispatch.

        Returns:
            The response.
        """
        return await async_judge_with_images(
            port, state, QUESTIONS, "fixture-selected", evidence=submitted
        )

    return anyio.run(call)


@pytest.mark.unit
def test_async_media_port_is_structural() -> None:
    """The recording provider satisfies the async media protocol."""
    assert isinstance(AsyncRecordingMediaProvider(), AsyncMediaSystemOnePort)
    assert not isinstance(AsyncTextOnly(), AsyncMediaSystemOnePort)


@pytest.mark.unit
def test_declared_media_reaches_the_port_exactly() -> None:
    """Preserve bytes, both orders, bindings, question values, model and usage."""
    provider = AsyncRecordingMediaProvider()
    submitted = evidence()
    state = {"record": ["exact", "state"]}
    response = judge(provider, submitted, state)
    assert response is provider.response
    assert response.model == "fixture-resolved"
    assert response.usage == Usage(0, None)
    assert isinstance(response.answers["claim"], NoulAnswer)
    assert isinstance(response.answers["decision"], ChoiceAnswer)
    assert provider.models == ["fixture-selected"]
    assert provider.text_calls == 0
    assert len(provider.calls) == 1
    seen_state, seen_questions, model, seen = provider.calls[0]
    assert seen_state == state
    assert seen_questions == QUESTIONS
    assert model == "fixture-selected"
    assert [(i.id, i.data, i.media_type) for i in seen.images] == [
        ("first", b"opaque-encoded-image-A", "image/png"),
        ("second", b"opaque-encoded-image-B", "image/png"),
    ]
    assert dict(seen.by_question) == {
        "claim": ("second", "first"),
        "decision": ("first",),
    }
    assert seen.required == frozenset({"claim"})


@pytest.mark.unit
def test_text_only_async_port_is_refused_before_dispatch() -> None:
    """A text-only async port never receives media as text."""
    provider = AsyncTextOnly()
    with pytest.raises(ProviderCapabilityError):
        judge(provider, evidence())
    assert provider.text_calls == 0


@pytest.mark.unit
def test_undeclared_media_is_refused_before_dispatch() -> None:
    """A MIME type outside the declaration never reaches the media port."""
    provider = AsyncRecordingMediaProvider()
    gif = ImageAttachment("first", b"GIF89a", "image/gif")
    with pytest.raises(ProviderCapabilityError, match="MIME type"):
        judge(provider, ImageEvidence([gif], {"claim": ["first"]}))
    assert provider.models == ["fixture-selected"]
    assert provider.calls == []
    assert provider.text_calls == 0


@pytest.mark.unit
def test_empty_optional_evidence_keeps_the_async_text_route() -> None:
    """Valid empty evidence awaits the text operation without capability lookup."""
    provider = AsyncRecordingMediaProvider()
    assert judge(provider, ImageEvidence([], {})) is provider.response
    assert provider.text_calls == 1
    assert provider.models == []
    assert provider.calls == []


@pytest.mark.unit
def test_missing_required_evidence_never_dispatches() -> None:
    """Missing evidence stays distinct from capability and transport errors."""
    provider = AsyncRecordingMediaProvider()
    with pytest.raises(MissingEvidenceError):
        judge(provider, ImageEvidence([], {}, {"claim"}))
    assert provider.text_calls == 0
    assert provider.models == []


@pytest.mark.unit
def test_unknown_question_reference_never_reaches_the_provider() -> None:
    """Evidence bound to an unknown question ID is a request error."""
    provider = AsyncRecordingMediaProvider()
    with pytest.raises(ProviderRequestError):
        judge(provider, ImageEvidence([FIRST], {"other": ["first"]}))
    assert provider.models == []
    assert provider.calls == []


@pytest.mark.unit
def test_declared_transport_error_propagates() -> None:
    """The awaited transport error keeps its class."""
    provider = AsyncRecordingMediaProvider(fail=True)
    with pytest.raises(ProviderTransportError, match="fixture transport failed"):
        judge(provider, evidence())
    assert len(provider.calls) == 1


@pytest.mark.unit
def test_invalid_media_response_is_a_provider_error() -> None:
    """A response missing a question ID fails the media response contract."""
    partial = SystemOneResponse(
        model="fixture-resolved",
        usage=Usage(0, None),
        answers={"claim": NoulAnswer(0.9)},
    )
    provider = AsyncRecordingMediaProvider(response=partial)
    with pytest.raises(ProviderResponseError):
        judge(provider, evidence())


@pytest.mark.unit
def test_sync_media_method_raises_type_error_on_await() -> None:
    """A synchronous `system_one_media` on an async port fails on await."""
    provider = SyncMediaOnAsyncPort()
    with pytest.raises(TypeError):
        judge(provider, evidence())
    assert len(provider.calls) == 1
