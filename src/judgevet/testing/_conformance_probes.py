"""Observers the provider conformance kit wraps around a provider.

`ScopeRecorder` wraps a provider factory and records every context it
constructs, so the kit observes entry and exit itself instead of trusting the
provider. `TextOnlyView` hides every method except `system_one`. `MediaProbe`
counts media dispatches so the kit can show that a refusal happened before the
provider ran. `declared_evidence` builds one image whose MIME type and size
the declared capabilities admit, and `undeclared_evidence` builds one whose
MIME type they do not admit. Each kit image is a valid one-pixel PNG, JPEG or
WebP file. `signature_problem` and `provider_error_problem` describe a broken
port shape or failure contract, so the synchronous and asynchronous kits share
one message. `media_members` reports a port's media methods for both kits.
None of these import pytest.
Source: https://github.com/Alberto-Codes/judgevet/issues/241#issuecomment-5902293909.

Examples:
    ```python
    from contextlib import nullcontext

    from judgevet.media import MediaCapabilities
    from judgevet.providers import provider_scope
    from judgevet.testing import FakeSystemOnePort
    from judgevet.testing._conformance_probes import (
        ScopeRecorder,
        declared_evidence,
        undeclared_evidence,
    )

    recorder = ScopeRecorder(lambda: nullcontext(FakeSystemOnePort()))
    with provider_scope(factory=recorder) as port:
        assert callable(port.system_one)
    assert recorder.contexts[0].exits == [None]

    evidence = undeclared_evidence(MediaCapabilities({"image/png"}))
    assert evidence.images[0].media_type == "image/jpeg"

    declared = declared_evidence(MediaCapabilities({"image/webp"}))
    assert declared is not None
    assert declared.images[0].media_type == "image/webp"

    from judgevet.testing._conformance_probes import (
        provider_error_problem,
        signature_problem,
    )

    assert signature_problem(FakeSystemOnePort().system_one, "m") is None
    assert provider_error_problem(RuntimeError("boom")) is not None
    ```

See Also:
    - [judgevet.testing.conformance][]: The base class that uses these observers
    - [judgevet.providers][]: `provider_scope` and `ProviderFactory`
    - [judgevet.media][]: `judge_with_images` and its capability checks
"""

import inspect
from base64 import b64decode
from collections.abc import Mapping
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any

from judgevet.domain.media import ImageAttachment, ImageEvidence, MediaCapabilities
from judgevet.domain.questions import Question
from judgevet.domain.response import SystemOneResponse
from judgevet.ports import SystemOnePort
from judgevet.ports.media import MediaSystemOnePort
from judgevet.providers import ProviderError, ProviderFactory
from judgevet.testing._conformance_cases import (
    CONFORMANCE_QUESTIONS,
    CONFORMANCE_STATE,
)

IMAGE_ID = "conformance-image"
"""The attachment identity of every kit image."""

IMAGE_QUESTION = "conformance_noul"
"""The kit question every kit image is bound to."""

_IMAGE_BYTES = {
    "image/png": b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAACklEQVR42mP4DwABAQEAHLCMmQ"
        "AAAABJRU5ErkJggg=="
    ),
    "image/jpeg": b64decode(
        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABALDA4MChAODQ4SERATGCgaGBYWGDEjJR0oOjM9"
        "PDkzODdASFxOQERXRTc4UG1RV19iZ2hnPk1xeXBkeFxlZ2P/wAALCAABAAEBAREA/8QAHwAA"
        "AQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQR"
        "BRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RF"
        "RkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ip"
        "qrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/9oACAEB"
        "AAA/APQK/9k="
    ),
    "image/webp": b64decode("UklGRhwAAABXRUJQVlA4TA8AAAAvAAAAAAcQ/Y/+ByKi/wEA"),
}
"""One valid one-pixel image per MIME type that `judge_with_images` admits."""

MEDIA_METHODS = ("capabilities", "system_one_media")
"""The methods the media checks require as callables on a media port."""

_FALLBACK_TYPE = "image/gif"


def media_members(port: object) -> tuple[list[str], bool]:
    """Report which media methods a port exposes and whether all are callable.

    Args:
        port: The provider port.

    Returns:
        The exposed media attribute names, and whether every media method is
        present and callable.
    """
    exposed = [name for name in MEDIA_METHODS if hasattr(port, name)]
    complete = all(callable(getattr(port, name, None)) for name in MEDIA_METHODS)
    return exposed, complete


def signature_problem(method: object, model: str) -> str | None:
    """Describe why a `system_one` method does not take the port's arguments.

    `SystemOnePort` and `AsyncSystemOnePort` are not runtime-checkable
    protocols, so the kit checks the method and its signature directly.

    Args:
        method: The port's `system_one` attribute, or None when it is absent.
        model: The selected model.

    Returns:
        A failure message when the method is not callable or does not accept
        (state, questions, model) positionally and by keyword, or None.
    """
    if not callable(method):
        return "The port has no callable system_one method."
    signature = inspect.signature(method)
    try:
        signature.bind(CONFORMANCE_STATE, CONFORMANCE_QUESTIONS, model)
        signature.bind(
            state=CONFORMANCE_STATE, questions=CONFORMANCE_QUESTIONS, model=model
        )
    except TypeError as error:
        return (
            f"system_one{signature} does not accept (state, questions, model) "
            f"positionally and by keyword: {error}"
        )
    return None


def provider_error_problem(error: BaseException) -> str | None:
    """Describe a failing port's exception that is not a `ProviderError`.

    Args:
        error: The exception the failing port raised.

    Returns:
        A failure message naming the `ProviderError` contract, or None when
        the exception is a `ProviderError` subclass.
    """
    if isinstance(error, ProviderError):
        return None
    return (
        f"The failing port raised {type(error).__name__}; map backend "
        "failures to a judgevet.providers.ProviderError subclass."
    )


class BodyError(Exception):
    """The exception the kit raises inside a provider scope body.

    Attributes:
        args (tuple): Standard exception arguments containing a message.

    Examples:
        ```python
        error = BodyError("raised inside the provider scope")
        assert str(error) == "raised inside the provider scope"
        ```
    """


class RecordedContext(AbstractContextManager[SystemOnePort]):
    """Delegate to one provider context and record its entry and exit.

    Attributes:
        inner (AbstractContextManager[SystemOnePort]): The provider's context.
        enters (int): How many times entry ran.
        exits (list[BaseException | None]): The exception each exit received,
            or None for a clean exit.

    Examples:
        ```python
        from contextlib import nullcontext

        from judgevet.testing import FakeSystemOnePort

        recorded = RecordedContext(nullcontext(FakeSystemOnePort()))
        with recorded:
            pass
        assert (recorded.enters, recorded.exits) == (1, [None])
        ```
    """

    def __init__(self, inner: AbstractContextManager[SystemOnePort]) -> None:
        """Wrap one provider context.

        Args:
            inner: The context the provider factory returned.
        """
        self.inner = inner
        self.enters = 0
        self.exits: list[BaseException | None] = []

    def __enter__(self) -> SystemOnePort:
        """Count the entry and enter the provider context.

        Returns:
            The port the provider context yields.
        """
        self.enters += 1
        return self.inner.__enter__()

    def __exit__(
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
        return self.inner.__exit__(exc_type, exc, traceback)


class ScopeRecorder:
    """Wrap a provider factory and record every context it constructs.

    Attributes:
        factory (ProviderFactory): The provider's own factory.
        contexts (list[RecordedContext]): One recorder per factory call.

    Examples:
        ```python
        from contextlib import nullcontext

        from judgevet.testing import FakeSystemOnePort

        recorder = ScopeRecorder(lambda: nullcontext(FakeSystemOnePort()))
        with recorder():
            pass
        assert len(recorder.contexts) == 1
        ```
    """

    def __init__(self, factory: ProviderFactory) -> None:
        """Store the provider factory.

        Args:
            factory: The provider's own factory.
        """
        self.factory = factory
        self.contexts: list[RecordedContext] = []

    def __call__(self) -> RecordedContext:
        """Construct one provider context and start recording it.

        Returns:
            A recorder that delegates to the new provider context.
        """
        recorded = RecordedContext(self.factory())
        self.contexts.append(recorded)
        return recorded


class TextOnlyView:
    """Expose only the text judgment method of a port.

    Attributes:
        port (SystemOnePort): The wrapped port.
        calls (int): How many judgments reached the port.

    Examples:
        ```python
        from judgevet.ports.media import MediaSystemOnePort
        from judgevet.testing import FakeSystemOnePort

        view = TextOnlyView(FakeSystemOnePort())
        assert not isinstance(view, MediaSystemOnePort)
        ```
    """

    def __init__(self, port: SystemOnePort) -> None:
        """Wrap a port.

        Args:
            port: The port whose text method stays visible.
        """
        self.port = port
        self.calls = 0

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Count the call and delegate it to the wrapped port.

        Args:
            state: The content to judge.
            questions: Question names mapped to question definitions.
            model: The selected model.

        Returns:
            The wrapped port's response.
        """
        self.calls += 1
        return self.port.system_one(state, questions, model)


class MediaProbe(TextOnlyView):
    """Delegate every media method and count media dispatches.

    Attributes:
        port (MediaSystemOnePort): The wrapped media port.
        calls (int): How many text judgments reached the port.
        media_calls (int): How many media judgments reached the port.

    Examples:
        ```python
        from judgevet.media import MediaCapabilities
        from judgevet.testing import FakeSystemOnePort


        class Media(FakeSystemOnePort):
            def capabilities(self, model):
                return MediaCapabilities({"image/png"})

            def system_one_media(self, state, questions, model, *, evidence):
                return self.system_one(state, questions, model)


        probe = MediaProbe(Media())
        assert probe.media_calls == 0
        ```
    """

    def __init__(self, port: MediaSystemOnePort) -> None:
        """Wrap a media port.

        Args:
            port: The media port to observe.
        """
        super().__init__(port)
        self.port: MediaSystemOnePort = port
        self.media_calls = 0

    def capabilities(self, model: str) -> MediaCapabilities:
        """Return the wrapped port's declaration unchanged.

        Args:
            model: The selected model.

        Returns:
            The wrapped port's capabilities.
        """
        return self.port.capabilities(model)

    def system_one_media(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        evidence: ImageEvidence,
    ) -> SystemOneResponse:
        """Count the media dispatch and delegate it to the wrapped port.

        Args:
            state: The content to judge.
            questions: Question names mapped to question definitions.
            model: The selected model.
            evidence: The ordered image evidence.

        Returns:
            The wrapped port's response.
        """
        self.media_calls += 1
        return self.port.system_one_media(state, questions, model, evidence=evidence)


def image_evidence(media_type: str) -> ImageEvidence:
    """Build one kit image of a MIME type, bound to the kit Noul question.

    Args:
        media_type: The MIME type the attachment declares.

    Returns:
        Evidence with one small synthetic attachment.
    """
    data = _IMAGE_BYTES.get(media_type, b"GIF89aconformance")
    attachment = ImageAttachment(IMAGE_ID, data, media_type)
    return ImageEvidence([attachment], {IMAGE_QUESTION: [IMAGE_ID]})


def declared_evidence(capabilities: MediaCapabilities) -> ImageEvidence | None:
    """Build one kit image that the declared capabilities admit.

    The first image type judgevet supports that the declaration names, and
    whose kit image fits the declared byte ceilings, is used.

    Args:
        capabilities: The provider's declaration for the selected model.

    Returns:
        Evidence that `judge_with_images` dispatches for this declaration, or
        None when the declaration admits no kit image.
    """
    limit = min(capabilities.max_image_bytes, capabilities.max_total_bytes)
    for kind, data in _IMAGE_BYTES.items():
        if kind in capabilities.image_types and len(data) <= limit:
            return image_evidence(kind)
    return None


def undeclared_evidence(capabilities: MediaCapabilities) -> ImageEvidence:
    """Build one kit image whose MIME type the capabilities do not admit.

    The first image type judgevet supports that the declaration omits is used.
    When the declaration names all of them, an unsupported type is used.

    Args:
        capabilities: The provider's declaration for the selected model.

    Returns:
        Evidence that `judge_with_images` must refuse for this declaration.
    """
    omitted = [kind for kind in _IMAGE_BYTES if kind not in capabilities.image_types]
    return image_evidence(omitted[0] if omitted else _FALLBACK_TYPE)
