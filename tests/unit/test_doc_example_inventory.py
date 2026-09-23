"""Acceptance checks for complete documentation-example classification."""

import contextlib
import io
import json
import runpy
import sys
from pathlib import Path

import pytest


def setup_inventory(tmp_path: Path) -> Path:
    """Write one exact runnable block and its explicit classification."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("# Example\n\n```python\nassert True\n```\n")
    manifest = tmp_path / "examples.json"
    manifest.write_text(
        json.dumps(
            {
                "README.md": [
                    {
                        "language": "python",
                        "kind": "runnable",
                        "reason": "Standalone offline assertion.",
                    }
                ]
            }
        )
    )
    return manifest


def run_inventory(root: Path, manifest: Path) -> tuple[int, str]:
    """Run the module command with controlled arguments and capture diagnostics."""
    arguments = [
        "doc_example_inventory",
        "--root",
        str(root),
        "--manifest",
        str(manifest),
    ]
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(sys, "argv", arguments)
        with (
            contextlib.redirect_stdout(output := io.StringIO()),
            pytest.raises(SystemExit) as caught,
        ):
            runpy.run_module("scripts.doc_example_inventory", run_name="__main__")
    code = caught.value.code
    assert isinstance(code, int)
    return code, output.getvalue()


def test_inventory_accepts_classified_block(tmp_path: Path) -> None:
    manifest = setup_inventory(tmp_path)
    code, output = run_inventory(tmp_path, manifest)
    assert code == 0, output
    assert "1 classified block" in output


@pytest.mark.parametrize("change", ["new", "removed", "empty", "reason", "language"])
def test_inventory_rejects_drift(tmp_path: Path, change: str) -> None:
    manifest = setup_inventory(tmp_path)
    if change == "new":
        (tmp_path / "docs/new.md").write_text("~~~bash\necho example\n~~~\n")
    elif change == "removed":
        (tmp_path / "README.md").write_text("# No example\n")
    elif change == "empty":
        (tmp_path / "README.md").write_text("# No example\n")
        manifest.write_text("{}")
    else:
        data = json.loads(manifest.read_text())
        data["README.md"][0][change] = "" if change == "reason" else "bash"
        manifest.write_text(json.dumps(data))
    code, output = run_inventory(tmp_path, manifest)
    assert code == 1
    assert "inventory:" in output


def test_inventory_reports_unclosed_fence(tmp_path: Path) -> None:
    manifest = setup_inventory(tmp_path)
    (tmp_path / "README.md").write_text("```python\nassert True\n")
    code, output = run_inventory(tmp_path, manifest)
    assert code == 1
    assert "README.md:1: unclosed fence" in output
