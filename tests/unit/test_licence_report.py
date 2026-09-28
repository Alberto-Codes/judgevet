"""Pin the licence report built from a CycloneDX SBOM and installed metadata (#59).

The SBOM fixtures follow the shape ``uv export --format cyclonedx1.5
--preview-features sbom-export`` wrote with uv 0.11.20: a top-level
``components`` list whose entries carry ``name``, ``version`` and ``purl``
(https://docs.astral.sh/uv/reference/cli/#uv-export).
"""

import json
from email.message import Message
from pathlib import Path

import pytest

from scripts.licence_report import (
    NOT_INSTALLED,
    UNKNOWN,
    Installed,
    components,
    licence,
    main,
    normalise,
    rows,
)

pytestmark = pytest.mark.unit


def sbom(entries: list[tuple[str, str]]) -> str:
    """Build CycloneDX 1.5 JSON in the shape uv 0.11.20 exports.

    Args:
        entries: ``(name, version)`` pairs for the components list.

    Returns:
        The JSON text.
    """
    listed = [
        {
            "type": "library",
            "bom-ref": f"{name}-{index}@{version}",
            "name": name,
            "version": version,
            "purl": f"pkg:pypi/{name}@{version}",
        }
        for index, (name, version) in enumerate(entries, start=2)
    ]
    root = {"type": "library", "bom-ref": "judgevet-1@0.13.0", "name": "judgevet"}
    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {"component": root},
        "components": listed,
        "dependencies": [],
    }
    return json.dumps(document)


def metadata(fields: dict[str, str | list[str]] | None = None) -> Message:
    """Build core metadata with the given headers.

    Args:
        fields: Header values keyed by name; a list adds the header once
            per item.

    Returns:
        The metadata message.
    """
    message = Message()
    for key, value in (fields or {}).items():
        for item in value if isinstance(value, list) else [value]:
            message[key] = item
    return message


MIT_CLASSIFIER = "License :: OSI Approved :: MIT License"


def test_licence_prefers_license_expression() -> None:
    """Report License-Expression over License and classifiers."""
    meta = metadata(
        {
            "License-Expression": "MIT OR Apache-2.0",
            "License": "MIT",
            "Classifier": [MIT_CLASSIFIER],
        }
    )
    assert licence(meta) == ("MIT OR Apache-2.0", "License-Expression")


def test_licence_falls_back_to_license_field() -> None:
    """Report License when no License-Expression exists."""
    meta = metadata({"License": "BSD-3-Clause", "Classifier": [MIT_CLASSIFIER]})
    assert licence(meta) == ("BSD-3-Clause", "License")


def test_licence_falls_back_to_classifiers() -> None:
    """Report every licence classifier when neither field exists."""
    meta = metadata(
        {
            "Classifier": [
                "Programming Language :: Python",
                MIT_CLASSIFIER,
                "License :: OSI Approved :: Apache Software License",
            ]
        }
    )
    assert licence(meta) == (
        "OSI Approved :: MIT License; OSI Approved :: Apache Software License",
        "Classifier",
    )


@pytest.mark.parametrize("value", ["", "  ", "UNKNOWN"])
def test_licence_reports_unknown_without_metadata(value: str) -> None:
    """Report UNKNOWN, never a guess, when no field names a licence."""
    meta = metadata(
        {"License": value, "Classifier": ["Programming Language :: Python"]}
    )
    assert licence(meta) == (UNKNOWN, "none")


def test_normalise_follows_pep_503() -> None:
    """Fold case and runs of ``-``, ``_`` and ``.`` to one ``-``."""
    assert normalise("Pydantic_Settings") == "pydantic-settings"
    assert normalise("zope.interface") == "zope-interface"
    assert normalise("a-_.B") == "a-b"


def test_rows_match_normalised_names_and_keep_absent_packages() -> None:
    """Match across spellings and list an absent package as NOT INSTALLED."""
    installed = {
        "pydantic-settings": Installed(
            "2.9.1", metadata({"License-Expression": "MIT"})
        ),
        "zope-interface": Installed("7.0", metadata()),
    }
    listed = [
        ("Pydantic.Settings", "2.9.1", ""),
        ("zope_interface", "7.0", ""),
        ("ghost-package", "1.0", ""),
    ]
    assert [row.as_dict() for row in rows(listed, installed)] == [
        {
            "name": "Pydantic.Settings",
            "version": "2.9.1",
            "installed": "2.9.1",
            "licence": "MIT",
            "source": "License-Expression",
            "marker": "",
        },
        {
            "name": "zope_interface",
            "version": "7.0",
            "installed": "7.0",
            "licence": UNKNOWN,
            "source": "none",
            "marker": "",
        },
        {
            "name": "ghost-package",
            "version": "1.0",
            "installed": "",
            "licence": NOT_INSTALLED,
            "source": "none",
            "marker": "",
        },
    ]


def test_components_reads_uv_sbom_shape() -> None:
    """Read name and version from every component, skipping the root."""
    text = sbom([("httpx", "0.28.1"), ("typer", "0.16.0")])
    assert components(text) == [("httpx", "0.28.1", ""), ("typer", "0.16.0", "")]


def test_main_writes_markdown_and_json_from_the_environment(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Look real packages up and report a missing one without dropping it."""
    source = tmp_path / "sbom.json"
    source.write_text(sbom([("Typer", "0.0.0"), ("no-such-dist-judgevet", "1.0")]))
    table = tmp_path / "out" / "licences.md"
    data = tmp_path / "out" / "licences.json"
    assert main([str(source), "--markdown", str(table), "--json", str(data)]) == 0
    written = json.loads(data.read_text())
    assert [row["licence"] for row in written] == ["MIT", NOT_INSTALLED]
    assert written[0]["source"] == "License-Expression"
    text = table.read_text()
    assert "| Typer | 0.0.0 |" in text
    assert f"| no-such-dist-judgevet | 1.0 |  | {NOT_INSTALLED} | none |  |" in text
    assert "2 packages, 0 UNKNOWN, 1 NOT INSTALLED" in capsys.readouterr().out


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        json.dumps({"bomFormat": "CycloneDX"}),
        json.dumps({"components": {"name": "httpx"}}),
        json.dumps({"components": [{"name": "httpx"}]}),
        json.dumps({"components": [{"name": 3, "version": "1"}]}),
    ],
)
def test_main_rejects_malformed_sbom(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str
) -> None:
    """Exit 1 on unreadable input and write no report."""
    source = tmp_path / "sbom.json"
    source.write_text(text)
    table = tmp_path / "licences.md"
    data = tmp_path / "licences.json"
    assert main([str(source), "--markdown", str(table), "--json", str(data)]) == 1
    assert "licence_report:" in capsys.readouterr().err
    assert not table.exists()
    assert not data.exists()


def test_main_rejects_missing_sbom(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 1 when the SBOM file does not exist."""
    table = tmp_path / "licences.md"
    absent = tmp_path / "absent.json"
    assert main([str(absent), "--markdown", str(table)]) == 1
    assert "licence_report:" in capsys.readouterr().err
    assert not table.exists()


MARKER = "uv:package:marker"


def test_components_reads_uv_marker_property() -> None:
    """Read the ``uv:package:marker`` property, empty when absent."""
    document = json.loads(sbom([("pywin32", "312"), ("httpx", "0.28.1")]))
    document["components"][0]["properties"] = [
        {"name": "uv:package:is_project_root", "value": "false"},
        {"name": MARKER, "value": "sys_platform == 'win32'"},
    ]
    assert components(json.dumps(document)) == [
        ("pywin32", "312", "sys_platform == 'win32'"),
        ("httpx", "0.28.1", ""),
    ]


def test_main_reports_the_marker_column(tmp_path: Path) -> None:
    """Show each component's marker in both outputs, empty when absent."""
    document = json.loads(sbom([("no-such-dist-judgevet", "1.0"), ("typer", "0")]))
    document["components"][0]["properties"] = [
        {"name": MARKER, "value": "sys_platform == 'win32'"}
    ]
    source = tmp_path / "sbom.json"
    source.write_text(json.dumps(document))
    table = tmp_path / "licences.md"
    data = tmp_path / "licences.json"
    assert main([str(source), "--markdown", str(table), "--json", str(data)]) == 0
    written = json.loads(data.read_text())
    assert [row["marker"] for row in written] == ["sys_platform == 'win32'", ""]
    lines = table.read_text().splitlines()
    assert lines[0] == "| name | version | installed | licence | source | marker |"
    assert lines[2] == (
        f"| no-such-dist-judgevet | 1.0 |  | {NOT_INSTALLED} | none "
        "| sys_platform == 'win32' |"
    )
