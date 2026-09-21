"""Tests for scripts/check_test_hygiene.py."""

from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path

from scripts.check_test_hygiene import main


class TestV1SwallowedFailure:
    """Tests for V1: try/except with assertions only in except handler."""

    def test_fails_when_except_has_assertion_no_orelse(self) -> None:
        """V1 flags try/except where assertions only run on exception path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_file = tmpdir_path / "test_violation.py"
            test_file.write_text(
                "def test_x():\n"
                "    try:\n"
                "        do()\n"
                "    except X:\n"
                "        assert ok()\n",
            )
            result = main([str(tmpdir_path)])
            assert result == 1

    def test_passes_when_orelse_has_pytest_fail(self) -> None:
        """V1 does not flag try/except with pytest.fail in orelse."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_file = tmpdir_path / "test_clean.py"
            test_file.write_text(
                "def test_x():\n"
                "    try:\n"
                "        do()\n"
                "    except X:\n"
                "        assert ok()\n"
                "    else:\n"
                '        pytest.fail("did not raise")\n',
            )
            result = main([str(tmpdir_path)])
            assert result == 0

    def test_passes_when_except_has_no_assertion(self) -> None:
        """V1 does not flag try/except where except has no assertion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_file = tmpdir_path / "test_clean.py"
            test_file.write_text(
                "def test_x():\n"
                "    try:\n"
                "        do()\n"
                "    except X:\n"
                "        pass\n"
                "    assert True\n",
            )
            result = main([str(tmpdir_path)])
            assert result == 0


class TestV2VacuousTest:
    """Tests for V2: test_* functions with no assertions."""

    def test_fails_when_test_has_no_assertion(self) -> None:
        """V2 flags a test_* function with no assertions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_file = tmpdir_path / "test_violation.py"
            test_file.write_text(
                "def test_bare():\n    compute()\n",
            )
            result = main([str(tmpdir_path)])
            assert result == 1

    def test_passes_when_test_has_assertion(self) -> None:
        """V2 does not flag a test_* function with an assertion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_file = tmpdir_path / "test_clean.py"
            test_file.write_text(
                "def test_has_assertion():\n    assert compute() == 42\n",
            )
            result = main([str(tmpdir_path)])
            assert result == 0

    def test_passes_when_test_delegates_to_helper_with_assertion(
        self,
    ) -> None:
        """V2 does not flag a test that delegates to a helper with assertions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_file = tmpdir_path / "test_clean.py"
            test_file.write_text(
                "def _helper(x):\n"
                "    assert x > 0\n"
                "\n"
                "def test_delegates():\n"
                "    _helper(5)\n",
            )
            result = main([str(tmpdir_path)])
            assert result == 0


class TestSecretBinding:
    """Tests for secret-binding check."""

    def test_fails_when_secret_bound_without_shielding(self) -> None:
        """Secret-binding flags get_secret_value() bound to a variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_file = tmpdir_path / "test_violation.py"
            test_file.write_text(
                "def test_leak():\n"
                "    key = settings.api.key.get_secret_value()\n"
                "    use(key)\n"
                "    assert True\n",
            )
            # Capture stdout
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                result = main([str(tmpdir_path)])
            finally:
                sys.stdout = old_stdout
            output = captured.getvalue()
            assert result == 1
            assert "secret-binding" in output
            assert ":2:" in output

    def test_passes_when_secret_passed_directly_to_call(self) -> None:
        """Secret-binding does not flag get_secret_value() inside a call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_file = tmpdir_path / "test_clean.py"
            test_file.write_text(
                "def test_clean():\n"
                "    use(settings.api.key.get_secret_value())\n"
                "    assert True\n",
            )
            result = main([str(tmpdir_path)])
            assert result == 0

    def test_passes_when_secret_in_assertion(self) -> None:
        """Secret-binding does not flag get_secret_value() in assertion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_file = tmpdir_path / "test_clean.py"
            test_file.write_text(
                "def test_clean():\n"
                '    assert settings.api.key.get_secret_value() == "k"\n',
            )
            result = main([str(tmpdir_path)])
            assert result == 0


class TestScope:
    """Tests for scope: only files pytest would collect."""

    def test_passes_when_violation_in_non_collectable_file(self) -> None:
        """V2 does not flag files pytest would not collect."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # File named probe.py (not test_*.py or *_test.py)
            test_file = tmpdir_path / "probe_violation.py"
            test_file.write_text(
                "def test_bare():\n    compute()\n",
            )
            result = main([str(tmpdir_path)])
            assert result == 0

    def test_fails_when_violation_in_collectable_file(self) -> None:
        """V2 flags files pytest would collect."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # File named test_probe.py
            test_file = tmpdir_path / "test_probe.py"
            test_file.write_text(
                "def test_bare():\n    compute()\n",
            )
            result = main([str(tmpdir_path)])
            assert result == 1


class TestRealTree:
    """Tests using the real project tree."""

    def test_real_tree_passes(self) -> None:
        """The real tree passes the hygiene check after repairs."""
        result = main(["tests"])
        assert result == 0
