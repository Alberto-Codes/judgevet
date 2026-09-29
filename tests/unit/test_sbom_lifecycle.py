"""Pin the CycloneDX lifecycle label on the lockfile SBOMs (#231).

``uv export --format cyclonedx1.5 --preview-features sbom-export`` with uv
0.11.20 writes ``metadata`` with ``timestamp``, ``tools`` and ``component``
and no ``lifecycles`` (https://docs.astral.sh/uv/reference/cli/#uv-export).
The export reads the declared graph in ``uv.lock``, so each file is labelled
with the CycloneDX 1.5 ``pre-build`` phase
(https://cyclonedx.org/docs/1.5/json/#metadata_lifecycles).
"""

import json
from pathlib import Path

import pytest

from scripts.sbom_lifecycle import PHASE, label, main

pytestmark = pytest.mark.unit


def uv_sbom(extra: dict[str, object] | None = None) -> dict[str, object]:
    """Build CycloneDX 1.5 JSON in the shape uv 0.11.20 exports.

    Args:
        extra: Extra ``metadata`` members to merge in.

    Returns:
        The SBOM document.
    """
    root = {"type": "library", "bom-ref": "judgevet-1@0.13.0", "name": "judgevet"}
    tools = [{"vendor": "Astral Software Inc.", "name": "uv", "version": "0.11.20"}]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {"tools": tools, "component": root, **(extra or {})},
        "components": [],
        "dependencies": [],
    }


def test_label_adds_pre_build_phase_and_keeps_metadata() -> None:
    """Add the pre-build lifecycle to an export that declares none."""
    document = uv_sbom()
    labelled = label(document)
    assert labelled["metadata"]["lifecycles"] == [{"phase": "pre-build"}]
    assert labelled["metadata"]["component"]["name"] == "judgevet"
    assert labelled["components"] == [] and PHASE == "pre-build"


def test_label_keeps_an_existing_pre_build_phase() -> None:
    """Leave a document alone when it already declares pre-build."""
    document = uv_sbom({"lifecycles": [{"phase": "pre-build"}]})
    assert label(document)["metadata"]["lifecycles"] == [{"phase": "pre-build"}]


@pytest.mark.parametrize(
    "document",
    [
        uv_sbom({"lifecycles": [{"phase": "build"}]}),
        {**uv_sbom(), "specVersion": "1.4"},
        {**uv_sbom(), "bomFormat": "SPDX"},
        {"bomFormat": "CycloneDX", "specVersion": "1.5"},
    ],
    ids=["other-phase", "spec-1.4", "not-cyclonedx", "no-metadata"],
)
def test_label_rejects_documents_it_cannot_label(document: dict[str, object]) -> None:
    """Refuse a conflicting phase, an older spec or a non-CycloneDX file."""
    with pytest.raises(ValueError):
        label(document)


def test_main_labels_each_file_in_place(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Rewrite every named file with the label and report each one."""
    paths = [tmp_path / f"sbom-{scope}.cdx.json" for scope in ("runtime", "dev")]
    for path in paths:
        path.write_text(json.dumps(uv_sbom()), encoding="utf-8")
    assert main([str(path) for path in paths]) == 0
    for path in paths:
        lifecycles = json.loads(path.read_text())["metadata"]["lifecycles"]
        assert lifecycles == [{"phase": "pre-build"}]
    assert capsys.readouterr().out.count("pre-build") == 2


def test_main_fails_and_writes_nothing_on_a_bad_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 1 and leave every file unchanged when one cannot be labelled."""
    good = tmp_path / "good.cdx.json"
    bad = tmp_path / "bad.cdx.json"
    good.write_text(json.dumps(uv_sbom()), encoding="utf-8")
    bad.write_text("not json", encoding="utf-8")
    before = good.read_text()
    assert main([str(good), str(bad), str(tmp_path / "missing.json")]) == 1
    assert good.read_text() == before and bad.read_text() == "not json"
    assert "bad.cdx.json" in capsys.readouterr().err
