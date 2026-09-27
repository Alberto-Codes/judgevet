"""Build explicit keyed media provenance without retaining request content.

Equal inputs under one key leak equality. Callers own key custody and rotation.
Revision metadata describes caller declarations, not verified preprocessing.
Source: https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851443210.

Examples:
    ```python
    from judgevet import Noul
    from judgevet.media import ImageEvidence
    from judgevet.media_audit import media_provenance

    value = media_provenance(
        ImageEvidence([], {}), {"q": Noul()}, fingerprint_key=b"example-only-key"
    )
    assert value.attachments == ()
    ```

See Also:
    - [judgevet.domain.media_audit][]: Immutable provenance value.
    - [judgevet.domain.audit][]: Existing terminal record.
    - [judgevet.media][]: Evidence and provider validation.
"""

import hashlib
import hmac
import json
from collections.abc import Iterable, Mapping
from typing import Any

from judgevet.domain.media_audit import MediaProvenance
from judgevet.domain.questions import Choice, Noul, Question, Score
from judgevet.media import ImageEvidence, _question
from judgevet.providers import ProviderRequestError

__all__ = ["MediaProvenance", "media_provenance"]


def _hash(key: bytes, label: bytes, parts: Iterable[bytes]) -> str:
    """Hash versioned length-framed parts without retaining their content.

    Args:
        key: Caller-owned nonempty key.
        label: Fixed versioned domain separator.
        parts: Exact ordered variable-length byte parts.

    Returns:
        Lowercase HMAC-SHA-256 hexadecimal digest.
    """
    digest = hmac.new(key, label, hashlib.sha256)
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()


def _json_keys(value: object) -> None:
    """Reject implicit conversion of non-string JSON object keys.

    Args:
        value: Nested question snapshot value.

    Raises:
        TypeError: An object key is not a string.
    """
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("JSON object keys must be strings")
        for item in value.values():
            _json_keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _json_keys(item)


def _json(value: object) -> bytes:
    """Encode compact sorted-key JSON without disclosing invalid content.

    Args:
        value: JSON-compatible snapshot.

    Returns:
        UTF-8 representation preserving sequence order.

    Raises:
        TypeError: A value cannot be serialized as JSON.
        ValueError: A value is non-finite, cyclic or invalid Unicode.
    """
    try:
        _json_keys(value)
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except TypeError:
        raise TypeError("Question snapshot must contain JSON values") from None
    except (ValueError, RecursionError):
        raise ValueError("Question snapshot is not finite valid JSON") from None


def _questions(questions: Mapping[str, Question | Mapping[str, Any]]) -> bytes:
    """Normalize typed and raw definitions without dropping supported content.

    Args:
        questions: Original question mapping.

    Returns:
        Canonical encoded question snapshot.

    Raises:
        TypeError: Questions or their content cannot form a JSON mapping.
        ValueError: A definition, ID or snapshot is invalid.
    """
    if not isinstance(questions, Mapping):
        raise TypeError("Questions must be a mapping")
    normalized = {}
    for name, question in questions.items():
        if not isinstance(name, str) or not name:
            raise ValueError("Question IDs must be nonempty strings")
        try:
            kind, _ = _question(question)
        except ProviderRequestError:
            raise ValueError("Invalid question definition") from None
        if isinstance(question, (Noul, Choice, Score)):
            instructions, criteria = question.instructions, question.criteria
        else:
            instructions, criteria = (
                question.get("instructions"),
                question.get("criteria"),
            )
        normalized[name] = {
            "type": kind,
            "instructions": instructions,
            "criteria": criteria,
        }
    return _json(normalized)


def media_provenance(
    evidence: ImageEvidence,
    questions: Mapping[str, Question | Mapping[str, Any]],
    *,
    fingerprint_key: bytes,
    prompt_revision: str | None = None,
    provider_identity: str | None = None,
    preprocessing_revision: str | None = None,
) -> MediaProvenance:
    """Fingerprint evidence and questions for an existing caller-owned audit record.

    This helper emits no record, observes no retries and estimates no usage.
    State fingerprints remain separate. Use opaque IDs and revision identifiers.

    Args:
        evidence: Immutable ordered evidence snapshot.
        questions: Typed or raw question definitions with original instructions.
        fingerprint_key: Explicit caller-owned nonempty bytes key.
        prompt_revision: Optional caller-declared prompt revision.
        provider_identity: Optional caller-declared provider identity.
        preprocessing_revision: Optional caller-declared preprocessing revision.

    Returns:
        Immutable metadata and keyed fingerprints without raw request content.

    Raises:
        TypeError: Evidence, key, metadata or JSON content has an invalid type.
        ValueError: Key is empty or definitions, Unicode or JSON values are invalid.
    """
    if not isinstance(fingerprint_key, bytes) or not isinstance(
        evidence, ImageEvidence
    ):
        raise TypeError("Evidence and fingerprint key must use declared types")
    if not fingerprint_key:
        raise ValueError("Fingerprint key must be nonempty")
    request = _questions(questions)
    try:
        parts = [
            (image.id.encode("utf-8"), image.media_type.encode("utf-8"), image.data)
            for image in evidence.images
        ]
    except UnicodeError:
        raise ValueError("Evidence identifiers must be valid UTF-8") from None
    attachments = tuple(
        (image.id, _hash(fingerprint_key, b"judgevet-media-attachment-v1\0", values))
        for image, values in zip(evidence.images, parts, strict=True)
    )
    snapshot = [part for values in parts for part in values]
    snapshot.extend(
        (_json(dict(evidence.by_question)), _json(sorted(evidence.required)))
    )
    return MediaProvenance(
        attachments,
        evidence.by_question,
        _hash(fingerprint_key, b"judgevet-media-evidence-v1\0", snapshot),
        _hash(fingerprint_key, b"judgevet-media-request-v1\0", [request]),
        prompt_revision,
        provider_identity,
        preprocessing_revision,
    )
