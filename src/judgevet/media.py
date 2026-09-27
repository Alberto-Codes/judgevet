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

See Also:
    - [judgevet.domain.media][]: Immutable evidence values.
    - [judgevet.ports.media][]: Optional provider extension.
"""

from collections.abc import Mapping, Sequence
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
from judgevet.ports import SystemOnePort
from judgevet.ports.media import MediaSystemOnePort

__all__ = [
    "ImageAttachment",
    "ImageEvidence",
    "MediaCapabilities",
    "MediaSystemOnePort",
    "MissingEvidenceError",
    "judge_with_images",
]


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
    if not isinstance(port, MediaSystemOnePort) or not all(
        callable(getattr(port, name, None))
        for name in ("capabilities", "system_one_media")
    ):
        raise ProviderCapabilityError("Provider must expose callable media methods")
    caps = port.capabilities(model)
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
    return port


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
) -> SystemOneResponse:
    """Validate evidence before dispatch and preserve the original typed result.

    Empty optional evidence uses the existing text operation unchanged. Media
    responses preserve resolved model identity and unknown or zero usage. An
    insufficient-evidence Choice is ordinary success only when the caller
    explicitly declares that option. Numbers carry no inferred calibration.

    Args:
        port: Explicitly selected borrowed provider.
        state: Original caller state, never converted to text.
        questions: Typed or raw question definitions, including mixed mappings.
        model: Caller-selected model label.
        evidence: Immutable attachments and question associations.

    Returns:
        The original response after media contract validation.

    Raises:
        ProviderRequestError: Question definitions or evidence references are invalid.
        MissingEvidenceError: A required question has no evidence.
        ProviderCapabilityError: The selected model cannot accept the evidence.
        ProviderResponseError: A media response violates the question contract.
        ProviderError: A declared provider failure propagates unchanged.
    """
    if not isinstance(evidence, ImageEvidence) or not isinstance(questions, Mapping):
        raise ProviderRequestError(
            "Evidence and questions must use the declared shapes"
        )
    if (set(evidence.by_question) | evidence.required) - questions.keys():
        raise ProviderRequestError("Evidence references unknown question IDs")
    if any(not evidence.by_question.get(name) for name in evidence.required):
        raise MissingEvidenceError("Required question has no image evidence")
    if not evidence.images:
        return port.system_one(state, questions, model)
    if not all(isinstance(name, str) and name for name in questions):
        raise ProviderRequestError("Question IDs must be nonempty strings")
    constraints = {name: _question(question) for name, question in questions.items()}
    media_port = _capabilities(port, model, evidence)
    response = media_port.system_one_media(state, questions, model, evidence=evidence)
    _response(response, constraints)
    return response
