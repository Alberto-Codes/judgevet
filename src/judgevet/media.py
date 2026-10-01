"""Validate ordered image evidence around application-owned providers.

Source: https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851219798.

Examples:
    ```python
    from judgevet.media import ImageAttachment, ImageEvidence, MediaCapabilities

    evidence = ImageEvidence(
        [ImageAttachment("a", b"opaque", "image/png")], {"q": ["a"]}
    )
    assert evidence.by_question["q"] == ("a",)
    assert "image/png" in MediaCapabilities({"image/png"}).image_types
    ```

`async_judge_with_images` keeps the checks, their order and the errors of
`judge_with_images`, and awaits the provider instead.
Source: https://github.com/Alberto-Codes/judgevet/issues/252#issuecomment-5924224316.

Both entries forward an optional `provider_options` mapping unchanged. They
pass it only when it is set, and only to a method whose signature takes it.
Source: https://github.com/Alberto-Codes/judgevet/issues/281.

See Also:
    - [judgevet.domain.media][]: Immutable evidence values.
    - [judgevet.ports.media][]: Optional provider extension.
    - [judgevet.ports.options][]: Ports that take provider options.
"""

import inspect
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from judgevet.domain.answers import ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.media import ImageAttachment, ImageEvidence, MediaCapabilities
from judgevet.domain.provider_errors import (
    MissingEvidenceError,
    ProviderCapabilityError,
    ProviderRequestError,
    ProviderResponseError,
)
from judgevet.domain.questions import Choice, Noul, Question, Score
from judgevet.domain.response import SystemOneResponse
from judgevet.ports import AsyncSystemOnePort, SystemOnePort
from judgevet.ports.media import AsyncMediaSystemOnePort, MediaSystemOnePort

__all__ = [
    "AsyncMediaSystemOnePort",
    "ImageAttachment",
    "ImageEvidence",
    "MediaCapabilities",
    "MediaSystemOnePort",
    "MissingEvidenceError",
    "async_judge_with_images",
    "judge_with_images",
]

_MEDIA_METHODS = ("capabilities", "system_one_media")


def _description(value: object) -> bool:
    """Recognize the existing question description shapes.

    Args:
        value: Instructions or one criterion description.

    Returns:
        Whether the value has a supported description shape.
    """
    return (
        value is None
        or isinstance(value, (str, dict))
        or (isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)))
    )


def _question(value: Question | Mapping[str, Any]) -> tuple[str, frozenset[str]]:
    """Validate a definition and snapshot its response constraints.

    Question fields follow https://docs.typesafe.ai/api.

    Args:
        value: Typed or raw definition, retained unchanged for dispatch.

    Returns:
        Variant name and declared Choice labels.

    Raises:
        ProviderRequestError: A definition has an unsupported shape or field.
    """
    if isinstance(value, (Noul, Choice, Score)):
        kind = (
            "noul"
            if isinstance(value, Noul)
            else "choice"
            if isinstance(value, Choice)
            else "score"
        )
        instructions, criteria = value.instructions, value.criteria
    elif isinstance(value, Mapping):
        if set(value) - {"type", "instructions", "criteria"}:
            raise ProviderRequestError("Unknown question fields")
        kind = value.get("type")
        instructions, criteria = value.get("instructions"), value.get("criteria")
    else:
        raise ProviderRequestError("Unsupported question definition")
    if not _description(instructions):
        raise ProviderRequestError("Invalid question instructions")
    return _criteria(kind, criteria)


def _criteria(kind: object, criteria: object) -> tuple[str, frozenset[str]]:
    """Check criteria shapes while preserving existing Noul content and Choice labels.

    Args:
        kind: Declared question variant.
        criteria: Original criteria value.

    Returns:
        Variant and immutable Choice label constraints.

    Raises:
        ProviderRequestError: The variant or its criteria are malformed.
    """
    if kind == "noul":
        if criteria is not None and not isinstance(criteria, dict):
            raise ProviderRequestError("Invalid Noul criteria")
        return "noul", frozenset()
    if kind == "choice":
        if not isinstance(criteria, Mapping) or not criteria:
            raise ProviderRequestError("Choice criteria must be a nonempty mapping")
        if not all(isinstance(key, str) for key in criteria):
            raise ProviderRequestError("Choice labels must be strings")
        if not all(_description(item) for item in criteria.values()):
            raise ProviderRequestError("Invalid Choice descriptions")
        return "choice", frozenset(criteria)
    if kind == "score":
        if (
            not isinstance(criteria, Sequence)
            or isinstance(criteria, (str, bytes, bytearray))
            or not criteria
            or not all(item is not None and _description(item) for item in criteria)
        ):
            raise ProviderRequestError(
                "Score criteria must be a nonempty description sequence"
            )
        return "score", frozenset()
    raise ProviderRequestError("Unknown question variant")


def _media_methods(port: object) -> bool:
    """Report whether every media method of a port is callable.

    Args:
        port: Selected provider.

    Returns:
        Whether `capabilities` and `system_one_media` are both callable.
    """
    return all(callable(getattr(port, name, None)) for name in _MEDIA_METHODS)


def _bounds(caps: object, evidence: ImageEvidence) -> None:
    """Enforce the declaration type and the local and provider bounds.

    Args:
        caps: The value the provider's `capabilities` returned.
        evidence: Nonempty validated attachment snapshot.

    Raises:
        ProviderCapabilityError: The declaration or request bounds are invalid.
    """
    if not isinstance(caps, MediaCapabilities):
        raise ProviderCapabilityError("Provider must declare MediaCapabilities")
    images = evidence.images
    if len(images) > min(16, caps.max_images):
        raise ProviderCapabilityError("Image count exceeds media ceiling")
    allowed = {"image/png", "image/jpeg", "image/webp"} & caps.image_types
    if any(image.media_type not in allowed for image in images):
        raise ProviderCapabilityError("Image MIME type is unsupported")
    if any(
        len(image.data) > min(8 * 1024 * 1024, caps.max_image_bytes) for image in images
    ):
        raise ProviderCapabilityError("Image bytes exceed per-image ceiling")
    if sum(len(image.data) for image in images) > min(
        32 * 1024 * 1024, caps.max_total_bytes
    ):
        raise ProviderCapabilityError("Image bytes exceed total ceiling")


def _capabilities(
    port: SystemOnePort, model: str, evidence: ImageEvidence
) -> MediaSystemOnePort:
    """Require callable media support and enforce local and provider bounds.

    Args:
        port: Selected provider.
        model: Selected model for static capability lookup.
        evidence: Nonempty validated attachment snapshot.

    Returns:
        The original provider with its media extension checked.

    Raises:
        ProviderCapabilityError: Support, declarations or request bounds are invalid.
    """
    if not isinstance(port, MediaSystemOnePort) or not _media_methods(port):
        raise ProviderCapabilityError("Provider must expose callable media methods")
    _bounds(port.capabilities(model), evidence)
    return port


def _async_capabilities(
    port: AsyncSystemOnePort, model: str, evidence: ImageEvidence
) -> AsyncMediaSystemOnePort:
    """Require callable async media support and enforce the same bounds.

    Args:
        port: Selected async provider.
        model: Selected model for static capability lookup.
        evidence: Nonempty validated attachment snapshot.

    Returns:
        The original provider with its media extension checked.

    Raises:
        ProviderCapabilityError: Support, declarations or request bounds are invalid.
    """
    if not isinstance(port, AsyncMediaSystemOnePort) or not _media_methods(port):
        raise ProviderCapabilityError("Provider must expose callable media methods")
    _bounds(port.capabilities(model), evidence)
    return port


def _options(
    method: Callable[..., object],
    provider_options: Mapping[str, object] | None,
    args: tuple[object, ...],
    kwargs: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    """Return the keyword arguments that forward set options to a method.

    The check binds the dispatch arguments to the method's signature, as the
    conformance kit does in `signature_problem`.

    Args:
        method: The provider method chosen for dispatch.
        provider_options: The caller's mapping, or None when unset.
        args: The positional values the dispatch passes.
        kwargs: The keyword values the dispatch passes besides the options.

    Returns:
        An empty dict when options are unset, else the `provider_options` keyword.

    Raises:
        ProviderCapabilityError: The method's signature cannot take the options.
    """
    if provider_options is None:
        return {}
    try:
        inspect.signature(method).bind(
            *args, **kwargs, provider_options=provider_options
        )
    except (TypeError, ValueError) as error:
        raise ProviderCapabilityError(
            "Provider method does not accept provider_options"
        ) from error
    return {"provider_options": provider_options}


def _admit(
    questions: Mapping[str, Question | Mapping[str, Any]], evidence: ImageEvidence
) -> None:
    """Check evidence and question shapes and required evidence before dispatch.

    Args:
        questions: Typed or raw question definitions.
        evidence: Immutable attachments and question associations.

    Raises:
        ProviderRequestError: Evidence or questions use undeclared shapes, or
            evidence references unknown question IDs.
        MissingEvidenceError: A required question has no evidence.
    """
    if not isinstance(evidence, ImageEvidence) or not isinstance(questions, Mapping):
        raise ProviderRequestError(
            "Evidence and questions must use the declared shapes"
        )
    if (set(evidence.by_question) | evidence.required) - questions.keys():
        raise ProviderRequestError("Evidence references unknown question IDs")
    if any(not evidence.by_question.get(name) for name in evidence.required):
        raise MissingEvidenceError("Required question has no image evidence")


def _constraints(
    questions: Mapping[str, Question | Mapping[str, Any]],
) -> dict[str, tuple[str, frozenset[str]]]:
    """Validate question IDs and definitions for a media dispatch.

    Args:
        questions: Typed or raw question definitions.

    Returns:
        Snapshotted question variants and Choice options by question ID.

    Raises:
        ProviderRequestError: A question ID or definition is invalid.
    """
    if not all(isinstance(name, str) and name for name in questions):
        raise ProviderRequestError("Question IDs must be nonempty strings")
    return {name: _question(question) for name, question in questions.items()}


def _response(
    response: SystemOneResponse, constraints: Mapping[str, tuple[str, frozenset[str]]]
) -> None:
    """Check response identities and variants against caller definitions.

    Args:
        response: Original provider result.
        constraints: Snapshotted question variants and Choice options.

    Raises:
        ProviderResponseError: The provider violates the media response contract.
    """
    if not isinstance(response, SystemOneResponse) or not isinstance(
        response.answers, Mapping
    ):
        raise ProviderResponseError("Provider must return a typed response")
    if set(response.answers) != set(constraints):
        raise ProviderResponseError("Response answer IDs must match question IDs")
    variants = {"noul": NoulAnswer, "choice": ChoiceAnswer, "score": ScoreAnswer}
    for name, (kind, labels) in constraints.items():
        answer = response.answers[name]
        if not isinstance(answer, variants[kind]):
            raise ProviderResponseError(
                "Response answer variant does not match question"
            )
        if isinstance(answer, ChoiceAnswer) and (
            answer.choice not in labels or not set(answer.probabilities) <= labels
        ):
            raise ProviderResponseError("Response Choice labels were not declared")


def judge_with_images(
    port: SystemOnePort,
    state: str | dict[str, Any] | list[Any],
    questions: Mapping[str, Question | Mapping[str, Any]],
    model: str,
    *,
    evidence: ImageEvidence,
    provider_options: Mapping[str, object] | None = None,
) -> SystemOneResponse:
    """Validate evidence before dispatch and preserve the original typed result.

    Empty optional evidence uses the existing text operation unchanged. Media
    responses preserve resolved model identity and unknown or zero usage. An
    insufficient-evidence Choice is ordinary success only when the caller
    explicitly declares that option. Numbers carry no inferred calibration.
    `async_judge_with_images` shares these checks through private helpers.

    Args:
        port: Explicitly selected borrowed provider.
        state: Original caller state, never converted to text.
        questions: Typed or raw question definitions, including mixed mappings.
        model: Caller-selected model label.
        evidence: Immutable attachments and question associations.
        provider_options: Provider-defined settings forwarded unchanged when set.

    Returns:
        The original response after media contract validation.

    Raises:
        ProviderRequestError: Question definitions or evidence references are invalid.
        MissingEvidenceError: A required question has no evidence.
        ProviderCapabilityError: The selected model cannot accept the evidence,
            or the chosen provider method cannot take `provider_options`.
        ProviderResponseError: A media response violates the question contract.
        ProviderError: A declared provider failure propagates unchanged.
    """
    _admit(questions, evidence)
    args = (state, questions, model)
    if not evidence.images:
        extra = _options(port.system_one, provider_options, args, {})
        return port.system_one(state, questions, model, **extra)
    constraints = _constraints(questions)
    media_port = _capabilities(port, model, evidence)
    extra = _options(
        media_port.system_one_media, provider_options, args, {"evidence": evidence}
    )
    response = media_port.system_one_media(
        state, questions, model, evidence=evidence, **extra
    )
    _response(response, constraints)
    return response


async def async_judge_with_images(
    port: AsyncSystemOnePort,
    state: str | dict[str, Any] | list[Any],
    questions: Mapping[str, Question | Mapping[str, Any]],
    model: str,
    *,
    evidence: ImageEvidence,
    provider_options: Mapping[str, object] | None = None,
) -> SystemOneResponse:
    """Validate evidence before an awaited dispatch and preserve the typed result.

    The checks, their order and their errors match `judge_with_images`. Empty
    optional evidence awaits the existing async text operation unchanged. The
    function adds no runtime awaitability check. A port whose
    `system_one_media` is synchronous raises `TypeError` when its result is
    awaited.

    Args:
        port: Explicitly selected borrowed async provider.
        state: Original caller state, never converted to text.
        questions: Typed or raw question definitions, including mixed mappings.
        model: Caller-selected model label.
        evidence: Immutable attachments and question associations.
        provider_options: Provider-defined settings forwarded unchanged when set.

    Returns:
        The original response after media contract validation.

    Raises:
        ProviderRequestError: Question definitions or evidence references are invalid.
        MissingEvidenceError: A required question has no evidence.
        ProviderCapabilityError: The selected model cannot accept the evidence,
            or the chosen provider method cannot take `provider_options`.
        ProviderResponseError: A media response violates the question contract.
        ProviderError: A declared provider failure propagates unchanged.
    """
    _admit(questions, evidence)
    args = (state, questions, model)
    if not evidence.images:
        extra = _options(port.system_one, provider_options, args, {})
        return await port.system_one(state, questions, model, **extra)
    constraints = _constraints(questions)
    media_port = _async_capabilities(port, model, evidence)
    extra = _options(
        media_port.system_one_media, provider_options, args, {"evidence": evidence}
    )
    response = await media_port.system_one_media(
        state, questions, model, evidence=evidence, **extra
    )
    _response(response, constraints)
    return response
