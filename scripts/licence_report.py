r"""Write a dependency licence table for one CycloneDX SBOM (#59).

The CI ``sbom`` job exports three CycloneDX 1.5 SBOMs with ``uv export
--format cyclonedx1.5 --preview-features sbom-export``: runtime, runtime
with the ``mcp`` extra, and development
(https://docs.astral.sh/uv/reference/cli/#uv-export). uv 0.11.20 writes no
licence field into them, so this script reads the licence from each
package's core metadata in the synced environment through
``importlib.metadata``.

The script reads ``name`` and ``version`` from every entry of the SBOM's
top-level ``components`` list, and the ``uv:package:marker`` property when uv
records one (the environment marker that gates the package). It matches each
name against the installed distributions after PEP 503 normalisation
(https://peps.python.org/pep-0503/#normalized-names). For each package it
reports the first of these core metadata fields that names a licence
(https://packaging.python.org/en/latest/specifications/core-metadata/):

| source | field |
|---|---|
| ``License-Expression`` | the SPDX expression (metadata 2.4) |
| ``License`` | the free-text licence field |
| ``Classifier`` | every ``License ::`` trove classifier |
| ``none`` | no field names a licence: ``UNKNOWN`` |

An empty field, or one that reads ``UNKNOWN``, names no licence. A package
listed in the SBOM but absent from the environment reports
``NOT INSTALLED`` and stays in the table: the package is absent from this
environment. The ``marker`` column shows the package's marker when the SBOM
records one, which gives the reason when there is one. The script never
guesses a licence.

The script exits 0 after it writes the report, whatever the count of
``UNKNOWN`` rows. It exits 1 on a missing or malformed SBOM and writes
nothing.

Examples:
    Export the runtime SBOM, then write its licence table:

    ```console
    $ uv export --format cyclonedx1.5 --preview-features sbom-export --locked \
        --no-dev -o runtime.cdx.json
    $ uv run python scripts/licence_report.py runtime.cdx.json --markdown runtime.md
    licence report: 22 packages, 0 UNKNOWN, 0 NOT INSTALLED -> runtime.md
    ```

See Also:
    - [scripts.check_dependencies][]: The gate on declared dependencies.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

UNKNOWN = "UNKNOWN"
NOT_INSTALLED = "NOT INSTALLED"
CLASSIFIER_PREFIX = "License :: "
COLUMNS = ("name", "version", "installed", "licence", "source", "marker")


class Metadata(Protocol):
    """The part of core metadata the report reads.

    ``email.message.Message`` and ``importlib.metadata.PackageMetadata``
    both satisfy it.
    """

    def get_all(self, name: str, failobj: None = None) -> list[str] | None:
        """Return every value of one header.

        Args:
            name: The header name.
            failobj: The value when the header is absent.

        Returns:
            The header values, or ``failobj`` when there are none.
        """
        ...


@dataclass(frozen=True)
class Installed:
    """One distribution found in the environment.

    Attributes:
        version (str): The installed version.
        metadata (Metadata): Its core metadata.
    """

    version: str
    metadata: Metadata


@dataclass(frozen=True)
class Row:
    """One package of the licence table.

    Attributes:
        name (str): The name as the SBOM spells it.
        version (str): The version the SBOM pins.
        installed (str): The installed version, empty when not installed.
        licence (str): The licence text, ``UNKNOWN`` or ``NOT INSTALLED``.
        source (str): The metadata field the licence came from, or ``none``.
        marker (str): The SBOM's environment marker, empty when absent.
    """

    name: str
    version: str
    installed: str
    licence: str
    source: str
    marker: str

    def as_dict(self) -> dict[str, str]:
        """Return the row keyed by column name.

        Returns:
            The six columns in table order.
        """
        return {column: getattr(self, column) for column in COLUMNS}


def normalise(name: str) -> str:
    """Normalise a distribution name per PEP 503.

    Args:
        name: A distribution name in any spelling.

    Returns:
        The lowercase name with each run of ``-``, ``_`` and ``.`` as ``-``.
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def _named(values: list[str] | None) -> list[str]:
    """Drop values that name no licence.

    Args:
        values: Header values, or ``None``.

    Returns:
        The stripped values that are neither empty nor ``UNKNOWN``.
    """
    stripped = (value.strip() for value in values or [])
    return [value for value in stripped if value and value != UNKNOWN]


def licence(metadata: Metadata) -> tuple[str, str]:
    """Read a licence from core metadata without guessing.

    Args:
        metadata: The package's core metadata.

    Returns:
        The licence text and the field it came from, or
        ``("UNKNOWN", "none")`` when no field names a licence.
    """
    for field in ("License-Expression", "License"):
        found = _named(metadata.get_all(field))
        if found:
            return found[0], field
    classifiers = [
        value.removeprefix(CLASSIFIER_PREFIX)
        for value in _named(metadata.get_all("Classifier"))
        if value.startswith(CLASSIFIER_PREFIX)
    ]
    if classifiers:
        return "; ".join(classifiers), "Classifier"
    return UNKNOWN, "none"


def components(text: str) -> list[tuple[str, str, str]]:
    """Read package names and versions from CycloneDX JSON.

    Args:
        text: The SBOM text.

    Returns:
        ``(name, version, marker)`` for each entry of ``components``; the
        marker is empty when the entry has none.

    Raises:
        ValueError: If the text is not JSON, has no ``components`` list, or
            an entry lacks a string name or version.
    """
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"not JSON: {error}") from error
    match document:
        case {"components": list(listed)}:
            return [_pair(entry) for entry in listed]
        case _:
            raise ValueError("no components list")


def _pair(entry: object) -> tuple[str, str, str]:
    """Read one component's name, version and marker.

    Args:
        entry: One entry of the ``components`` list.

    Returns:
        The name, version and marker, the marker empty when absent.

    Raises:
        ValueError: If the entry lacks a string name or version.
    """
    match entry:
        case {"name": str(name), "version": str(version)}:
            return name, version, _marker(entry.get("properties"))
        case _:
            raise ValueError(f"component lacks a name or version: {entry!r}")


def _marker(properties: object) -> str:
    """Find the ``uv:package:marker`` value among CycloneDX properties.

    Args:
        properties: The component's ``properties`` value, if any.

    Returns:
        The marker, or an empty string when none is recorded.
    """
    for item in properties if isinstance(properties, list) else []:
        match item:
            case {"name": "uv:package:marker", "value": str(value)}:
                return value
    return ""


def environment() -> dict[str, Installed]:
    """Index the running environment's distributions by normalised name.

    Returns:
        Each installed distribution keyed by its PEP 503 name.
    """
    return {
        normalise(dist.metadata["Name"]): Installed(dist.version, dist.metadata)
        for dist in importlib.metadata.distributions()
    }


def rows(
    listed: Iterable[tuple[str, str, str]], installed: Mapping[str, Installed]
) -> list[Row]:
    """Build one table row per SBOM component.

    Args:
        listed: ``(name, version, marker)`` triples from the SBOM.
        installed: Installed distributions keyed by normalised name.

    Returns:
        The rows in SBOM order, absent packages included.
    """
    table = []
    for name, version, marker in listed:
        found = installed.get(normalise(name))
        if found is None:
            table.append(Row(name, version, "", NOT_INSTALLED, "none", marker))
            continue
        text, source = licence(found.metadata)
        table.append(Row(name, version, found.version, text, source, marker))
    return table


def _cell(text: str) -> str:
    """Fit text into one Markdown table cell.

    Args:
        text: The raw value, possibly a multi-line licence text.

    Returns:
        The first line with ``|`` escaped, marked when lines were dropped.
    """
    lines = text.strip().splitlines() or [""]
    first = lines[0].replace("|", "\\|")
    return f"{first} …" if len(lines) > 1 else first


def markdown(table: list[Row]) -> str:
    """Render the rows as a Markdown table.

    Args:
        table: The rows to render.

    Returns:
        The Markdown text, one header and one line per row.
    """
    lines = ["| " + " | ".join(COLUMNS) + " |", "|---" * len(COLUMNS) + "|"]
    for row in table:
        cells = (_cell(value) for value in row.as_dict().values())
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Read the SBOM and write the licence table.

    Args:
        argv: Command-line arguments; ``None`` reads ``sys.argv``.

    Returns:
        0 after the report is written, 1 on a missing or malformed SBOM.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sbom", type=Path, help="CycloneDX JSON from uv export")
    parser.add_argument("--markdown", type=Path, help="Markdown table to write")
    parser.add_argument("--json", type=Path, help="JSON rows to write")
    args = parser.parse_args(argv)
    try:
        listed = components(args.sbom.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"licence_report: {args.sbom}: {error}", file=sys.stderr)
        return 1
    table = rows(listed, environment())
    outputs = {args.markdown: markdown(table)}
    outputs[args.json] = json.dumps([row.as_dict() for row in table], indent=2) + "\n"
    for path, text in outputs.items():
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    unknown = sum(row.licence == UNKNOWN for row in table)
    absent = sum(row.licence == NOT_INSTALLED for row in table)
    print(
        f"licence report: {len(table)} packages, {unknown} UNKNOWN, "
        f"{absent} NOT INSTALLED -> {args.markdown or args.json or 'nothing'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
