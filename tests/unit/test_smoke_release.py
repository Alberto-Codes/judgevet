"""Tests for scripts/smoke_release.py."""

from __future__ import annotations

import hashlib
import inspect
import os
import tempfile
from pathlib import Path

import pytest

from scripts.smoke_release import (
    _CLEAR_VARS,
    _parse_argv,
    build_child_env,
    main,
)


class TestClearVars:
    """Tests for _CLEAR_VARS."""

    def test_clear_vars_contains_pythonpath(self) -> None:
        """PYTHONPATH is in the clear set."""
        assert "PYTHONPATH" in _CLEAR_VARS

    def test_clear_vars_contains_pythonhome(self) -> None:
        """PYTHONHOME is in the clear set."""
        assert "PYTHONHOME" in _CLEAR_VARS

    def test_clear_vars_only_has_two_vars(self) -> None:
        """Only PYTHONPATH and PYTHONHOME are cleared."""
        assert frozenset(["PYTHONPATH", "PYTHONHOME"]) == _CLEAR_VARS


class TestBuildChildEnv:
    """Tests for build_child_env."""

    def test_excludes_pythonpath(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """PYTHONPATH is excluded."""
        monkeypatch.setenv("PATH", "/some/path")
        monkeypatch.setenv("PYTHONPATH", "/evil/path")
        monkeypatch.setenv("OTHER", "value")
        result = build_child_env()
        assert "PYTHONPATH" not in result
        assert "PATH" in result
        assert "OTHER" in result

    def test_excludes_pythonhome(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """PYTHONHOME is excluded."""
        monkeypatch.setenv("PATH", "/some/path")
        monkeypatch.setenv("PYTHONHOME", "/evil/home")
        monkeypatch.setenv("OTHER", "value")
        result = build_child_env()
        assert "PYTHONHOME" not in result
        assert "PATH" in result
        assert "OTHER" in result

    def test_preserves_other_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Other environment variables are preserved."""
        monkeypatch.setenv("PATH", "/some/path")
        monkeypatch.setenv("HOME", "/home/user")
        monkeypatch.setenv("CUSTOM", "value")
        result = build_child_env()
        assert result.get("PATH") == "/some/path"
        assert result.get("HOME") == "/home/user"
        assert result.get("CUSTOM") == "value"


def _fingerprint(name: str) -> str:
    """Hash one environment value so no test local holds it.

    Args:
        name: The environment variable to fingerprint.

    Returns:
        A SHA-256 digest of the value, or of the absence marker.
    """
    return hashlib.sha256(repr(os.environ.get(name)).encode()).hexdigest()


class TestBuildChildEnvIsolation:
    """Prove TestBuildChildEnv leaves the process environment as it found it."""

    def test_path_and_home_survive(self) -> None:
        """PATH and HOME keep their values after every TestBuildChildEnv test."""
        before = {name: _fingerprint(name) for name in ("PATH", "HOME")}
        suite = TestBuildChildEnv()
        for name in ("test_excludes_pythonpath", "test_excludes_pythonhome"):
            _call_with_monkeypatch(getattr(suite, name))
        _call_with_monkeypatch(suite.test_preserves_other_vars)
        after = {name: _fingerprint(name) for name in ("PATH", "HOME")}
        assert after == before


def _call_with_monkeypatch(method: object) -> None:
    """Call one test method, passing a monkeypatch when it takes one.

    Args:
        method: A bound TestBuildChildEnv test method.
    """
    assert callable(method)
    with pytest.MonkeyPatch.context() as patch:
        if inspect.signature(method).parameters:
            method(patch)
        else:
            method()


class TestParseArgv:
    """Tests for _parse_argv."""

    def test_empty_argv_returns_none_and_zero(self) -> None:
        """Empty argv returns (None, 0)."""
        result = _parse_argv([])
        assert result == (None, 0)

    def test_wheel_flag_only_returns_error(self) -> None:
        """--wheel without PATH returns (None, 1)."""
        result = _parse_argv(["--wheel"])
        assert result[0] is None
        assert result[1] == 1

    def test_wheel_flag_with_path_returns_path(self) -> None:
        """--wheel PATH returns (Path, 0)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wheel_path = Path(tmpdir) / "test.whl"
            wheel_path.touch()
            result = _parse_argv(["--wheel", str(wheel_path)])
            assert result[0] == wheel_path
            assert result[1] == 0

    def test_wheel_flag_with_nonexistent_path_returns_error(self) -> None:
        """--wheel /nonexistent returns (None, 1)."""
        result = _parse_argv(["--wheel", "/nonexistent.whl"])
        assert result[0] is None
        assert result[1] == 1

    def test_invalid_argv_returns_error(self) -> None:
        """Unknown argv returns (None, 1)."""
        result = _parse_argv(["--unknown"])
        assert result[0] is None
        assert result[1] == 1


class TestSmokeReleaseIntegration:
    """Integration tests for smoke_release.py."""

    def test_smoke_release_with_wheel_flag_fails_for_invalid_wheel(self) -> None:
        """Main returns 1 for non-existent wheel."""
        result = main(["--wheel", "/nonexistent.whl"])
        assert result == 1
