"""Prove README.md pins the package version to the release-please manifest.

Examples:
    ```python
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    manifest = repo_root / ".release-please-manifest.json"
    assert manifest.exists()
    ```

See Also:
    - [judgevet][]: Package whose version must match README pins.
"""

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_readme_pins_match_manifest() -> None:
    """Require every README pin to equal the release-please manifest version."""
    repo_root = Path(__file__).resolve().parents[2]
    readme_path = repo_root / "README.md"
    manifest_path = repo_root / ".release-please-manifest.json"

    manifest_content = manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_content)
    expected_version = manifest["."]

    readme_content = readme_path.read_text(encoding="utf-8")

    pin_pattern = re.compile(r"judgevet(?:\[mcp\])?==(\d+\.\d+\.\d+(?:-[\w.]+)?)")
    pins = pin_pattern.findall(readme_content)

    assert len(pins) > 0, "README.md must contain at least one judgevet pin"

    for pin in pins:
        assert pin == expected_version, (
            f"Found pin 'judgevet=={pin}' in README.md, "
            f"but the manifest version is '{expected_version}'"
        )
