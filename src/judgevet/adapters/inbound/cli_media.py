"""Load bounded local image manifests before provider acquisition.

Source: https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851367000.

Examples:
    ```python
    from judgevet.adapters.inbound.cli_media import load_evidence

    assert load_evidence(None, {}) is None
    ```

See Also:
    - [judgevet.media][]: Typed image dispatch.
    - [judgevet.adapters.inbound.cli_options][]: Explicit file options.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from judgevet.adapters.inbound.cli_inputs import InputFailure
from judgevet.media import ImageAttachment, ImageEvidence

MANIFEST_LIMIT = 1024 * 1024
IMAGE_LIMIT = 8 * 1024 * 1024
TOTAL_LIMIT = 32 * 1024 * 1024
IMAGE_COUNT = 16


def _read(path: Path, limit: int, category: str) -> bytes:
    """Read at most one byte beyond a declared local ceiling.

    Args:
        path: Local file path.
        limit: Maximum accepted byte length.
        category: Safe diagnostic category.

    Returns:
        Original bounded bytes.

    Raises:
        InputFailure: Reading fails or the file exceeds its ceiling.
    """
    try:
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
    except (OSError, ValueError):
        raise InputFailure(f"--evidence-file: cannot read {category}") from None
    if len(data) > limit:
        raise InputFailure(f"--evidence-file: {category} exceeds byte ceiling")
    return data


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON keys at every nesting level.

    Args:
        pairs: Decoder object members in source order.

    Returns:
        Unambiguous object members.

    Raises:
        ValueError: An object repeats a key.
    """
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate manifest key")
        result[key] = value
    return result


def _constant(value: str) -> None:
    """Reject non-finite JSON constants.

    Args:
        value: Decoder constant token.

    Raises:
        ValueError: Always, because these tokens are not JSON.
    """
    raise ValueError("Non-finite manifest constant")


def _ids(value: object) -> list[str]:
    """Validate an ordered list of unique nonempty identifiers.

    Args:
        value: Decoded identifier list.

    Returns:
        Validated identifiers in source order.

    Raises:
        ValueError: The list is malformed or repeats an identifier.
    """
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError("Invalid identifier list")
    if len(set(value)) != len(value):
        raise ValueError("Duplicate identifier")
    return value


def _image_ids(images: list[Any]) -> set[str]:
    """Validate local image declarations before reading their payloads.

    Args:
        images: Decoded ordered declarations.

    Returns:
        Unique declared attachment identifiers.

    Raises:
        ValueError: A declaration or identifier is malformed.
    """
    identifiers = []
    for entry in images:
        if not isinstance(entry, dict) or set(entry) != {"id", "path", "media_type"}:
            raise ValueError("Invalid image declaration")
        if not all(isinstance(value, str) and value for value in entry.values()):
            raise ValueError("Invalid image declaration")
        if "://" in entry["path"]:
            raise ValueError("Image path must be local")
        identifiers.append(entry["id"])
    return set(_ids(identifiers))


def _manifest(data: object, questions: Mapping[str, object]) -> dict[str, Any]:
    """Validate the complete manifest structure and references before image reads.

    Args:
        data: Strictly decoded JSON.
        questions: Question identities for reference validation.

    Returns:
        Validated manifest object.

    Raises:
        ValueError: A field or reference is invalid.
        InputFailure: A known required question has no image association.
    """
    if not isinstance(data, dict) or not {"images", "by_question"} <= data.keys():
        raise ValueError("Missing manifest fields")
    if data.keys() - {"images", "by_question", "required"}:
        raise ValueError("Unknown manifest fields")
    images, bindings = data["images"], data["by_question"]
    if not isinstance(images, list) or len(images) > IMAGE_COUNT:
        raise ValueError("Invalid image count")
    known = _image_ids(images)
    if not isinstance(bindings, dict):
        raise TypeError("Invalid question bindings")
    used: set[str] = set()
    for name, references in bindings.items():
        if not isinstance(name, str) or not name or name not in questions:
            raise ValueError("Unknown question binding")
        refs = set(_ids(references))
        if not refs <= known:
            raise ValueError("Unknown image reference")
        used.update(refs)
    if used != known:
        raise ValueError("Unreferenced images")
    required = _ids(data.get("required", []))
    if any(name not in questions for name in required):
        raise ValueError("Unknown required question")
    if any(not bindings.get(name) for name in required):
        raise InputFailure("--evidence-file: missing required image evidence")
    return data


def _check_total(total: int) -> None:
    """Enforce the cumulative ceiling with a safe size diagnostic.

    Args:
        total: Total attachment bytes read so far.

    Raises:
        InputFailure: The attachment total exceeds the local ceiling.
    """
    if total > TOTAL_LIMIT:
        raise InputFailure("--evidence-file: images exceed total byte ceiling")


def load_evidence(
    path: str | None, questions: Mapping[str, object]
) -> ImageEvidence | None:
    """Load exact ordered image bytes with safe local diagnostics.

    Preserve missing-required, read and size failure categories without identifiers.

    Args:
        path: Explicit manifest path, if supplied.
        questions: Validated question identities.

    Returns:
        Immutable evidence, or None for the existing text command.

    Raises:
        InputFailure: Manifest or local image input is invalid.
    """
    if path is None:
        return None
    try:
        manifest_path = Path(path)
        raw = _read(manifest_path, MANIFEST_LIMIT, "manifest").decode("utf-8")
        data = _manifest(
            json.loads(raw, object_pairs_hook=_object, parse_constant=_constant),
            questions,
        )
        images = []
        total = 0
        for entry in data["images"]:
            image_path = manifest_path.parent / entry["path"]
            content = _read(image_path, IMAGE_LIMIT, "image")
            total += len(content)
            _check_total(total)
            images.append(ImageAttachment(entry["id"], content, entry["media_type"]))
        return ImageEvidence(images, data["by_question"], data.get("required", []))
    except InputFailure:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise InputFailure(
            "--evidence-file: invalid image manifest or evidence"
        ) from None


def validate_hosted_evidence(path: str, questions: Mapping[str, object]) -> None:
    """Reject hosted image requests before settings or credentials are accessed.

    Args:
        path: Explicit manifest path.
        questions: Parsed question identities.

    Raises:
        InputFailure: Local evidence is invalid or hosted media is requested.
    """
    evidence = load_evidence(path, questions)
    if evidence is not None and evidence.images:
        raise InputFailure("--evidence-file: hosted provider does not support images")
