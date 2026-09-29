r"""Label lockfile CycloneDX SBOMs with the pre-build lifecycle phase (#231).

The supply-chain action exports three CycloneDX 1.5 SBOMs with ``uv export
--format cyclonedx1.5 --preview-features sbom-export``
(https://docs.astral.sh/uv/reference/cli/#uv-export). The export reads the
dependency graph that ``uv.lock`` declares. It does not inspect a built
wheel. The files are therefore *source* SBOMs in the CISA SBOM types, not
*build* SBOMs
(https://www.cisa.gov/sites/default/files/2024-10/SBOM%20Framing%20Software%20Component%20Transparency%202024.pdf).

uv 0.11.20 writes no ``metadata.lifecycles``. This script adds
``[{"phase": "pre-build"}]``, the CycloneDX 1.5 phase for data taken before
a build (https://cyclonedx.org/docs/1.5/json/#metadata_lifecycles). A file
that already declares only ``pre-build`` is rewritten unchanged. The script
refuses a file that declares another phase, a CycloneDX version older than
1.5, which has no ``lifecycles`` field, or a document that is not CycloneDX.

The script rewrites each file in place with two-space JSON indentation. It
checks every file before it writes any. It exits 0 after it labels them all.
It exits 1 on a missing or unlabellable file and writes nothing.

Examples:
    Export the runtime SBOM, then label it:

    ```console
    $ uv export --format cyclonedx1.5 --preview-features sbom-export --locked \
        --no-dev -o runtime.cdx.json
    $ uv run python scripts/sbom_lifecycle.py runtime.cdx.json
    sbom lifecycle: runtime.cdx.json -> pre-build
    ```

See Also:
    - [scripts.licence_report][]: The licence table read from the same SBOMs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PHASE = "pre-build"
MINIMUM_SPEC = (1, 5)


def _spec(text: str) -> tuple[int, ...]:
    """Parse a CycloneDX ``specVersion``.

    Args:
        text: The version, such as ``1.5``.

    Returns:
        The version as a tuple of integers.

    Raises:
        ValueError: If a part is not an integer.
    """
    try:
        return tuple(int(part) for part in text.split("."))
    except ValueError as error:
        raise ValueError(f"unreadable specVersion {text!r}") from error


def _phases(lifecycles: object) -> set[object]:
    """Collect the phases a ``lifecycles`` value declares.

    Args:
        lifecycles: The ``metadata.lifecycles`` value.

    Returns:
        Each entry's ``phase``, or its ``name`` for a custom lifecycle.

    Raises:
        ValueError: If the value is not a list of objects.
    """
    match lifecycles:
        case list(entries) if all(isinstance(entry, dict) for entry in entries):
            return {entry.get("phase", entry.get("name")) for entry in entries}
        case _:
            raise ValueError(f"lifecycles is not a list of objects: {lifecycles!r}")


def label(document: object) -> dict[str, Any]:
    """Return a copy of the SBOM that declares the pre-build phase.

    Args:
        document: The parsed CycloneDX JSON.

    Returns:
        The document with ``metadata.lifecycles`` set to
        ``[{"phase": "pre-build"}]``.

    Raises:
        ValueError: If the document is not CycloneDX 1.5 or later with a
            ``metadata`` object, or declares a phase other than
            ``pre-build``.
    """
    match document:
        case dict(
            {
                "bomFormat": "CycloneDX",
                "specVersion": str(spec),
                "metadata": dict(metadata),
            }
        ) as whole:
            pass
        case _:
            raise ValueError("not a CycloneDX document with a metadata object")
    if _spec(spec) < MINIMUM_SPEC:
        raise ValueError(f"specVersion {spec} predates metadata.lifecycles (1.5)")
    if "lifecycles" in metadata and _phases(metadata["lifecycles"]) != {PHASE}:
        raise ValueError(f"declares lifecycles {metadata['lifecycles']!r}")
    labelled = {**metadata, "lifecycles": [{"phase": PHASE}]}
    return {**whole, "metadata": labelled}


def main(argv: list[str] | None = None) -> int:
    """Label every named SBOM, or none of them.

    Args:
        argv: Command-line arguments; ``None`` reads ``sys.argv``.

    Returns:
        0 after every file is labelled, 1 when any file cannot be.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sboms", type=Path, nargs="+", help="CycloneDX JSON")
    args = parser.parse_args(argv)
    labelled: dict[Path, dict[str, Any]] = {}
    failed = False
    for path in args.sboms:
        try:
            labelled[path] = label(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as error:
            print(f"sbom_lifecycle: {path}: {error}", file=sys.stderr)
            failed = True
    if failed:
        return 1
    for path, document in labelled.items():
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        print(f"sbom lifecycle: {path} -> {PHASE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
