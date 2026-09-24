"""Pin ty's checked roots in pyproject.toml.

Examples:
    ```python
    import tomllib
    from pathlib import Path

    data = tomllib.loads(Path("pyproject.toml").read_text())
    assert data["tool"]["ty"]["src"]["include"] == ["src", "tests", "scripts"]
    ```

See Also:
    [judgevet][]
"""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_ty_include_pins_all_roots() -> None:
    """Require ty to check src, tests and scripts by explicit include."""
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert data["tool"]["ty"]["src"]["include"] == ["src", "tests", "scripts"]
