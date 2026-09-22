"""Tests for scripts/smoke_release.py."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

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

    def test_excludes_pythonpath(self) -> None:
        """PYTHONPATH is excluded."""
        env = {"PATH": "/some/path", "PYTHONPATH": "/evil/path", "OTHER": "value"}
        os.environ.update(env)
        try:
            result = build_child_env()
            assert "PYTHONPATH" not in result
            assert "PATH" in result
            assert "OTHER" in result
        finally:
            # Restore original env
            for k in env:
                if k in os.environ:
                    del os.environ[k]

    def test_excludes_pythonhome(self) -> None:
        """PYTHONHOME is excluded."""
        env = {"PATH": "/some/path", "PYTHONHOME": "/evil/home", "OTHER": "value"}
        os.environ.update(env)
        try:
            result = build_child_env()
            assert "PYTHONHOME" not in result
            assert "PATH" in result
            assert "OTHER" in result
        finally:
            # Restore original env
            for k in env:
                if k in os.environ:
                    del os.environ[k]

    def test_preserves_other_vars(self) -> None:
        """Other environment variables are preserved."""
        env = {"PATH": "/some/path", "HOME": "/home/user", "CUSTOM": "value"}
        os.environ.update(env)
        try:
            result = build_child_env()
            assert result.get("PATH") == "/some/path"
            assert result.get("HOME") == "/home/user"
            assert result.get("CUSTOM") == "value"
        finally:
            # Restore original env
            for k in env:
                if k in os.environ:
                    del os.environ[k]


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
