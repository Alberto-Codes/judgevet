"""Immutable evidence and static model capability declarations.

Source: https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851219798.

Examples:
    ```python
    from judgevet.domain.media import ImageAttachment, ImageEvidence

    image = ImageAttachment("scan", b"opaque", "image/png")
    evidence = ImageEvidence([image], {"claim": ["scan"]})
    assert evidence.images[0].data == b"opaque"
    ```

See Also:
    - [judgevet.media][]: Validated dispatch.
    - [judgevet.ports.media][]: Provider protocol.
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType


def _identifier(value: object) -> None:
    """Require a nonempty string declaration.

    Args:
        value: Identifier or MIME declaration.

    Raises:
        ValueError: The value is not a nonempty string.
    """
    if not isinstance(value, str) or not value:
        raise ValueError("Identifiers and MIME declarations must be nonempty strings")


@dataclass(frozen=True, slots=True)
class ImageAttachment:
    """An opaque encoded image with a caller-owned identity.

    Attributes:
        id (str): Nonempty attachment identity.
        data (bytes): Exact nonempty encoded bytes, never decoded here.
        media_type (str): Nonempty declared MIME type.

    Examples:
        ```python
        image = ImageAttachment("scan", b"opaque", "image/png")
        ```
    """

    id: str
    data: bytes
    media_type: str

    def __post_init__(self) -> None:
        """Validate declarations without interpreting bytes.

        Raises:
            ValueError: An identifier or the byte payload is invalid.
        """
        _identifier(self.id)
        _identifier(self.media_type)
        if not isinstance(self.data, bytes) or not self.data:
            raise ValueError("Image data must be nonempty bytes")


@dataclass(frozen=True, slots=True, init=False)
class ImageEvidence:
    """Snapshot ordered images and question associations.

    Attributes:
        images (tuple[ImageAttachment, ...]): Images in caller order.
        by_question (Mapping[str, tuple[str, ...]]): Immutable ordered associations.
        required (frozenset[str]): Questions requiring nonempty evidence at dispatch.

    Examples:
        ```python
        evidence = ImageEvidence([], {})
        ```
    """

    images: tuple[ImageAttachment, ...]
    by_question: Mapping[str, tuple[str, ...]]
    required: frozenset[str]

    def __init__(
        self,
        images: Sequence[ImageAttachment],
        by_question: Mapping[str, Sequence[str]],
        required: Collection[str] = (),
    ) -> None:
        """Validate structure and take defensive snapshots.

        Args:
            images: Ordered attachments, each referenced at least once.
            by_question: Ordered attachment IDs for each associated question.
            required: Questions whose evidence must be present at dispatch.

        Raises:
            ValueError: A shape, identifier, duplicate or association is invalid.
        """
        valid_images = isinstance(images, Sequence) and not isinstance(
            images, (str, bytes)
        )
        if not valid_images:
            raise ValueError("Images must be a sequence of attachments")
        snapshot = tuple(images)
        if not all(isinstance(image, ImageAttachment) for image in snapshot):
            raise ValueError("Images must contain ImageAttachment values")
        identifiers = {image.id for image in snapshot}
        if len(identifiers) != len(snapshot):
            raise ValueError("Attachment IDs must be unique")
        associations = _associations(by_question, identifiers)
        required_ids = _identifiers(required)
        object.__setattr__(self, "images", snapshot)
        object.__setattr__(self, "by_question", MappingProxyType(associations))
        object.__setattr__(self, "required", frozenset(required_ids))


def _identifiers(values: Collection[str]) -> tuple[str, ...]:
    """Snapshot a collection of string identifiers.

    Args:
        values: Caller-owned identifiers.

    Returns:
        Validated identifiers in iteration order.

    Raises:
        ValueError: The collection or an identifier is invalid.
    """
    valid_collection = isinstance(values, Collection) and not isinstance(
        values, (str, bytes)
    )
    if not valid_collection:
        raise ValueError("Identifiers must be a collection")
    result = tuple(values)
    for value in result:
        _identifier(value)
    return result


def _associations(
    bindings: Mapping[str, Sequence[str]], identifiers: set[str]
) -> dict[str, tuple[str, ...]]:
    """Validate complete, unambiguous evidence associations.

    Args:
        bindings: Caller-owned question associations.
        identifiers: Known attachment IDs.

    Returns:
        Fresh mapping to ordered immutable references.

    Raises:
        ValueError: Associations are malformed, unknown, duplicated or incomplete.
    """
    valid_mapping = isinstance(bindings, Mapping)
    if not valid_mapping:
        raise ValueError("Question associations must be a mapping")
    result = {}
    used: set[str] = set()
    for question, references in bindings.items():
        _identifier(question)
        ordered = isinstance(references, Sequence)
        if not ordered:
            raise ValueError("Question references must be ordered sequences")
        refs = _identifiers(references)
        if len(set(refs)) != len(refs) or not set(refs) <= identifiers:
            raise ValueError("Question references must be unique known attachment IDs")
        result[question] = refs
        used.update(refs)
    if used != identifiers:
        raise ValueError("Every attachment must be associated with a question")
    return result


@dataclass(frozen=True, slots=True, init=False)
class MediaCapabilities:
    """Static supported formats and ceilings for one selected model.

    Attributes:
        image_types (frozenset[str]): Declared MIME types.
        max_images (int): Positive attachment-count ceiling.
        max_image_bytes (int): Positive per-image byte ceiling.
        max_total_bytes (int): Positive total byte ceiling.

    Examples:
        ```python
        caps = MediaCapabilities({"image/png"})
        ```
    """

    image_types: frozenset[str]
    max_images: int
    max_image_bytes: int
    max_total_bytes: int

    def __init__(
        self,
        image_types: Collection[str],
        max_images: int = 16,
        max_image_bytes: int = 8 * 1024 * 1024,
        max_total_bytes: int = 32 * 1024 * 1024,
    ) -> None:
        """Snapshot declarations without acquisition or inference.

        Args:
            image_types: Supported MIME declarations.
            max_images: Provider count ceiling.
            max_image_bytes: Provider per-image byte ceiling.
            max_total_bytes: Provider total byte ceiling.

        Raises:
            ValueError: Formats or positive integer bounds are malformed.
        """
        formats = frozenset(_identifiers(image_types))
        for value in (max_images, max_image_bytes, max_total_bytes):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError("Media ceilings must be positive integers")
        object.__setattr__(self, "image_types", formats)
        object.__setattr__(self, "max_images", max_images)
        object.__setattr__(self, "max_image_bytes", max_image_bytes)
        object.__setattr__(self, "max_total_bytes", max_total_bytes)
