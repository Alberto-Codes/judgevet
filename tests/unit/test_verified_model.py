"""Pin ``judgevet.VERIFIED_MODEL`` to the model ``STATUS.md`` names.

The constant is the one model the live suite has exercised. ``STATUS.md``
names that model in its "What is verified, and what is not" table, in the
row that begins ``| resolved models other than``. The constant and the table
must agree, so this suite reads the model from the table rather than
repeating it.

The environment variable ``JUDGEVET_STATUS_MD`` points the parse test at
another copy of the file. It exists so a failure proof can run against an
edited copy without changing the tracked ``STATUS.md``.

Examples:
    ```bash
    uv run pytest tests/unit/test_verified_model.py -q
    JUDGEVET_STATUS_MD=/path/to/copy.md uv run pytest tests/unit/test_verified_model.py -q
    ```

See Also:
    - [judgevet][]: the package root that defines ``VERIFIED_MODEL``
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

import judgevet
from judgevet import VERIFIED_MODEL

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ROW = re.compile(r"^\| resolved models other than `([^`]+)`", re.MULTILINE)


def _status_path() -> Path:
    """Return the ``STATUS.md`` path the parse test reads.

    Returns:
        The path from ``JUDGEVET_STATUS_MD`` when set, else the repository
        root ``STATUS.md``.
    """
    override = os.environ.get("JUDGEVET_STATUS_MD")
    return Path(override) if override else _REPO_ROOT / "STATUS.md"


def _status_model(text: str) -> str:
    """Extract the verified model name from the STATUS table text.

    Args:
        text: The full contents of ``STATUS.md``.

    Returns:
        The backticked model name in the ``resolved models other than`` row.

    Raises:
        AssertionError: If the row is missing.
    """
    match = _ROW.search(text)
    if match is None:
        msg = "STATUS.md has no '| resolved models other than `...`' row"
        raise AssertionError(msg)
    return match.group(1)


@pytest.mark.unit
def test_verified_model_matches_status_table() -> None:
    """``VERIFIED_MODEL`` equals the model the STATUS verified table names."""
    text = _status_path().read_text(encoding="utf-8")
    assert _status_model(text) == VERIFIED_MODEL


@pytest.mark.unit
def test_verified_model_is_exported() -> None:
    """``VERIFIED_MODEL`` is listed in the package root ``__all__``."""
    assert "VERIFIED_MODEL" in judgevet.__all__
