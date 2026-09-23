"""Fresh artifact selection for isolated documentation and release checks."""

import subprocess
from pathlib import Path

import pytest

from scripts import smoke_release


@pytest.mark.parametrize("name", ["old.whl", "old.tar.gz", "notes.txt"])
def test_nonempty_output_is_rejected_before_build(
    tmp_path: Path, monkeypatch, name: str
) -> None:
    existing = tmp_path / name
    existing.write_text("preserve existing artifact")
    calls: list[Path] = []

    def no_output_build(directory: Path) -> subprocess.CompletedProcess[str]:
        calls.append(directory)
        return subprocess.CompletedProcess(["builder"], 0, "", "")

    monkeypatch.setattr(smoke_release, "_build_wheel_subprocess", no_output_build)
    with pytest.raises(RuntimeError, match="must be empty"):
        smoke_release.build_wheel(tmp_path)
    assert calls == []
    assert existing.read_text() == "preserve existing artifact"


def test_fresh_build_selects_only_new_wheel(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "new-output"

    def write_wheel(directory: Path) -> subprocess.CompletedProcess[str]:
        directory.mkdir()
        (directory / "candidate.whl").write_text("new artifact")
        return subprocess.CompletedProcess(["builder"], 0, "", "")

    monkeypatch.setattr(smoke_release, "_build_wheel_subprocess", write_wheel)
    selected = smoke_release.build_wheel(output)
    assert selected == output / "candidate.whl"
    assert selected.read_text() == "new artifact"
