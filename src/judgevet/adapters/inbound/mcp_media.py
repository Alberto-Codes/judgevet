"""Decode bounded embedded image evidence on the serialized MCP worker.

Source: https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851508259.

Examples:
    ```python
    from judgevet.adapters.inbound.mcp_media import decode_evidence

    assert decode_evidence('{"images":[],"by_question":{}}').images == ()
    ```

See Also:
    - [judgevet.media][]: Provider capability and response validation.
    - [judgevet.adapters.inbound.mcp_dispatch][]: Serialized worker ownership.
"""

import base64
import binascii
import json
from typing import Any

from judgevet.media import ImageAttachment, ImageEvidence
from judgevet.providers import ProviderRequestError

_MAX_IMAGES = 16
_MANIFEST_BYTES = 48 * 1024 * 1024
_IMAGE_BYTES = 8 * 1024 * 1024
_TOTAL_BYTES = 32 * 1024 * 1024
_BASE64_CHARS = 4 * ((_IMAGE_BYTES + 2) // 3)


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate keys at every embedded object level.

    Args:
        pairs: Parsed object entries in input order.

    Returns:
        An object with unique keys.

    Raises:
        ValueError: A duplicate key occurs.
    """
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate evidence key")
        result[key] = value
    return result


def _constant(value: str) -> None:
    """Reject non-finite JSON constants without echoing their content.

    Args:
        value: Parser token, never included in diagnostics.

    Raises:
        ValueError: Always, because JSON constants must be finite.
    """
    raise ValueError("Non-finite evidence constant")


def _image(item: Any) -> ImageAttachment:
    """Decode one bounded attachment without interpreting its image format.

    Args:
        item: Parsed attachment declaration.

    Returns:
        Exact decoded bytes and declared identity.

    Raises:
        ValueError: The declaration or encoding is invalid or oversized.
    """
    if not isinstance(item, dict) or set(item) != {"id", "data_base64", "media_type"}:
        raise ValueError("Invalid attachment fields")
    encoded = item["data_base64"]
    if not isinstance(encoded, str) or not encoded or len(encoded) > _BASE64_CHARS:
        raise ValueError("Invalid attachment encoding size")
    data = base64.b64decode(encoded.encode("ascii"), validate=True)
    if len(data) > _IMAGE_BYTES:
        raise ValueError("Attachment exceeds byte ceiling")
    return ImageAttachment(item["id"], data, item["media_type"])


def _manifest(text: Any) -> dict[str, Any]:
    """Parse bounded strict JSON text with the declared evidence fields.

    Args:
        text: Embedded argument, which must remain JSON text.

    Returns:
        Parsed manifest object.

    Raises:
        ValueError: Input, byte bounds or fields violate the manifest contract.
        TypeError: Required questions are not an array.
    """
    if not isinstance(text, str) or len(text) > _MANIFEST_BYTES:
        raise ValueError("Invalid evidence text size")
    if len(text.encode("utf-8")) > _MANIFEST_BYTES:
        raise ValueError("Evidence exceeds UTF-8 byte ceiling")
    value = json.loads(text, object_pairs_hook=_object, parse_constant=_constant)
    if not isinstance(value, dict) or not {"images", "by_question"} <= set(value):
        raise ValueError("Missing evidence fields")
    if set(value) - {"images", "by_question", "required"}:
        raise ValueError("Unknown evidence fields")
    if not isinstance(value["images"], list) or len(value["images"]) > _MAX_IMAGES:
        raise ValueError("Invalid evidence image count")
    if not isinstance(value.get("required", []), list):
        raise TypeError("Required questions must be an array")
    return value


def _attachments(items: list[Any]) -> list[ImageAttachment]:
    """Decode attachments while bounding cumulative allocation.

    Args:
        items: Validated manifest attachment list.

    Returns:
        Ordered decoded attachments.

    Raises:
        ValueError: Encoded content or cumulative bytes violate local limits.
    """
    images = []
    total = 0
    for item in items:
        image = _image(item)
        total += len(image.data)
        if total > _TOTAL_BYTES:
            raise ValueError("Evidence exceeds total byte ceiling")
        images.append(image)
    return images


def decode_evidence(text: Any) -> ImageEvidence:
    """Validate strict JSON and snapshot bounded decoded evidence.

    Args:
        text: Embedded JSON string supplied through the MCP tool argument.

    Returns:
        Immutable ordered image evidence.

    Raises:
        ProviderRequestError: The manifest, encoding or local limits are invalid.
    """
    try:
        value = _manifest(text)
        images = _attachments(value["images"])
        return ImageEvidence(images, value["by_question"], value.get("required", []))
    except (ValueError, TypeError, UnicodeError, binascii.Error, RecursionError) as exc:
        raise ProviderRequestError("Invalid or oversized image evidence") from exc
