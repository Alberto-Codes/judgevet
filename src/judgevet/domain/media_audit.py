"""Immutable caller-declared media provenance without input content.

Source: https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851443210.

Examples:
    ```python
    from judgevet.domain.media_audit import MediaProvenance

    value = MediaProvenance((), {}, "a" * 64, "b" * 64)
    assert value.provider_identity is None
    ```

See Also:
    - [judgevet.media_audit][]: Explicit keyed fingerprint construction.
    - [judgevet.domain.audit][]: Optional terminal record attachment.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from judgevet.domain.media import _associations, _identifier

_DIGEST_LENGTH = 64
_PAIR_LENGTH = 2


def _digest(value: object) -> None:
    """Validate a lowercase SHA-256 hex declaration without hashing.

    Args:
        value: Caller-declared fingerprint.

    Raises:
        ValueError: The declaration is not a lowercase 64-character hex string.
    """
    if (
        not isinstance(value, str)
        or len(value) != _DIGEST_LENGTH
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError("Fingerprint must be lowercase SHA-256 hex")


def _attachments(values: Sequence[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    """Snapshot ordered attachment IDs and their validated fingerprints.

    Args:
        values: Caller-owned pairs.

    Returns:
        Immutable ordered pairs.

    Raises:
        ValueError: Pair shape, ID, digest or uniqueness is invalid.
        TypeError: Attachments are not a sequence.
    """
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise TypeError("Attachments must be a sequence")
    result = []
    identifiers = set()
    for pair in values:
        if not isinstance(pair, (tuple, list)) or len(pair) != _PAIR_LENGTH:
            raise ValueError("Attachments require ID and fingerprint pairs")
        identifier, fingerprint = pair
        _identifier(identifier)
        _digest(fingerprint)
        if identifier in identifiers:
            raise ValueError("Attachment IDs must be unique")
        identifiers.add(identifier)
        result.append((identifier, fingerprint))
    return tuple(result)


@dataclass(frozen=True, slots=True)
class MediaProvenance:
    """Snapshot fingerprints and opaque caller-declared revision identifiers.

    Attributes:
        attachments (Sequence[tuple[str, str]]): Ordered immutable ID/digest pairs.
        by_question (Mapping[str, Sequence[str]]): Immutable ordered associations.
        evidence_fingerprint (str): Keyed digest of the entire evidence snapshot.
        request_fingerprint (str): Keyed digest of normalized question definitions.
        prompt_revision (str | None): Caller-declared opaque prompt revision.
        provider_identity (str | None): Caller-declared provider identity.
        preprocessing_revision (str | None): Caller-declared preprocessing revision.

    Examples:
        ```python
        value = MediaProvenance((), {}, "a" * 64, "b" * 64)
        assert value.attachments == ()
        ```
    """

    attachments: Sequence[tuple[str, str]]
    by_question: Mapping[str, Sequence[str]]
    evidence_fingerprint: str
    request_fingerprint: str
    prompt_revision: str | None = None
    provider_identity: str | None = None
    preprocessing_revision: str | None = None

    def __post_init__(self) -> None:
        """Validate fields and detach all collection aliases.

        Raises:
            ValueError: A digest, attachment or association is malformed.
            TypeError: Revision metadata is neither a string nor None.
        """
        attachments = _attachments(self.attachments)
        associations = _associations(
            self.by_question, {identifier for identifier, _ in attachments}
        )
        _digest(self.evidence_fingerprint)
        _digest(self.request_fingerprint)
        for value in (
            self.prompt_revision,
            self.provider_identity,
            self.preprocessing_revision,
        ):
            if value is not None and not isinstance(value, str):
                raise TypeError("Revision metadata must be a string or None")
        object.__setattr__(self, "attachments", attachments)
        object.__setattr__(self, "by_question", MappingProxyType(associations))
