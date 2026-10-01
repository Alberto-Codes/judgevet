"""Prove the doc host launcher environment shares the run's uv cache.

Each launcher test keeps its own ``HOME`` and ``UV_OVERRIDE`` but resolves
through one warmed uv cache per pytest run, so a run does not resolve the
``mcp`` tree from PyPI cold once per test. See issue #262.

Examples:
    Run the offline check:

    ```bash
    uv run pytest -q tests/unit/test_doc_host_support.py
    ```

See Also:
    - [tests.unit.doc_host_support][]: The helper under test.
    - [scripts.smoke_release][]: Names the session cache variable.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.smoke_release import SESSION_CACHE_VAR
from tests.unit.doc_host_support import environment

pytestmark = pytest.mark.unit


def test_environment_uses_the_run_cache(tmp_path: Path) -> None:
    """Point uv at the run's shared cache, not a cache under the test workdir."""
    wheel = tmp_path / "dist" / "judgevet-0.15.0-py3-none-any.whl"
    workdir = tmp_path / "work"
    workdir.mkdir()
    env = environment(workdir, wheel, "judgevet[mcp]==0.15.0")
    shared = Path(os.environ[SESSION_CACHE_VAR])
    assert env["UV_CACHE_DIR"] == str(shared)
    assert not Path(env["UV_CACHE_DIR"]).is_relative_to(workdir)
    assert env["HOME"] == str(workdir)
    assert Path(env["UV_OVERRIDE"]).parent == workdir
