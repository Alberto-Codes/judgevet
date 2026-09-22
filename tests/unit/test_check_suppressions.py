"""Tests for scripts/check_suppressions.py."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from scripts.check_suppressions import (
    ALLOWED_PER_FILE_IGNORE_CODES,
    count_per_file_ignores,
    main,
    scan,
)


class TestCountPerFileIgnores:
    """Tests for the count_per_file_ignores function."""

    def test_empty_file_returns_zero(self) -> None:
        """An empty pyproject.toml has no per-file-ignores codes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("")
            f.flush()
            total, per_pattern = count_per_file_ignores(Path(f.name))
        assert total == 0
        assert per_pattern == {}

    def test_missing_tool_section_returns_zero(self) -> None:
        """A file without [tool] section has no per-file-ignores codes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[project]\nname = "test"\n')
            f.flush()
            total, per_pattern = count_per_file_ignores(Path(f.name))
        assert total == 0
        assert per_pattern == {}

    def test_missing_ruff_section_returns_zero(self) -> None:
        """A file without [tool.ruff] section has no per-file-ignores codes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[tool]\nother = "value"\n')
            f.flush()
            total, per_pattern = count_per_file_ignores(Path(f.name))
        assert total == 0
        assert per_pattern == {}

    def test_missing_lint_section_returns_zero(self) -> None:
        """A file without [tool.ruff.lint] section has no per-file-ignores codes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("[tool.ruff]\nline-length = 88\n")
            f.flush()
            total, per_pattern = count_per_file_ignores(Path(f.name))
        assert total == 0
        assert per_pattern == {}

    def test_missing_per_file_ignores_section_returns_zero(self) -> None:
        """A file without per-file-ignores has zero codes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[tool.ruff.lint]\nignore = ["E501"]\n')
            f.flush()
            total, per_pattern = count_per_file_ignores(Path(f.name))
        assert total == 0
        assert per_pattern == {}

    def test_single_entry_with_single_code(self) -> None:
        """A single entry with one code counts as 1."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[tool.ruff.lint.per-file-ignores]\n"test.py" = ["E501"]\n')
            f.flush()
            total, per_pattern = count_per_file_ignores(Path(f.name))
        assert total == 1
        assert per_pattern == {"test.py": ["E501"]}

    def test_single_entry_with_multiple_codes(self) -> None:
        """A single entry with multiple codes counts all of them."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                '[tool.ruff.lint.per-file-ignores]\n"test.py" = ["E501", "F401", "W503"]\n'
            )
            f.flush()
            total, per_pattern = count_per_file_ignores(Path(f.name))
        assert total == 3
        assert per_pattern == {"test.py": ["E501", "F401", "W503"]}

    def test_multiple_entries(self) -> None:
        """Multiple entries are summed correctly."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                "[tool.ruff.lint.per-file-ignores]\n"
                '"test1.py" = ["E501", "F401"]\n'
                '"test2.py" = ["W503"]\n'
            )
            f.flush()
            total, per_pattern = count_per_file_ignores(Path(f.name))
        assert total == 3
        assert per_pattern == {"test1.py": ["E501", "F401"], "test2.py": ["W503"]}

    def test_current_pyproject_toml_budget(self) -> None:
        """The actual pyproject.toml has the expected budget."""
        total, per_pattern = count_per_file_ignores(Path("pyproject.toml"))
        # Current budget: 18 codes
        # - 7 in tests/**/*.py (S101, D100, D101, D102, D103, D104, PLR2004)
        # - 1 in conftest.py (PLC0415 - import inside function; module level trips E402)
        # - 3 in mcp.py (PLC0415, C901, PLR0915)
        # - 1 in test_secret_guard.py (S603 - subprocess for the end-to-end proof)
        # - 4 in smoke_release_child.py (S102 exec, BLE001 arbitrary example
        #   failures, S603 subprocess, PLC0415 lazy import so --selftest runs
        #   where judgevet is NOT installed)
        # - 1 in check_commit_msg.py (S603 - git is invoked by absolute path with a list argv)
        # - 1 in smoke_release.py (S603 - uv and python by absolute path, list argv)
        assert total == 18
        assert len(per_pattern) == 7
        # tests/**/*.py has 7 codes
        assert len(per_pattern["tests/**/*.py"]) == 7
        # conftest.py has 1 code
        assert len(per_pattern["tests/conftest.py"]) == 1
        # mcp.py has 3 codes
        assert len(per_pattern["src/judgevet/adapters/inbound/mcp.py"]) == 3
        # test_secret_guard.py has 1 code (S105 and PLW1510 were avoidable)
        assert len(per_pattern["tests/unit/test_secret_guard.py"]) == 1
        # smoke_release_child.py has 4 codes
        assert len(per_pattern["scripts/smoke_release_child.py"]) == 4
        # check_commit_msg.py has 1 code
        assert len(per_pattern["scripts/check_commit_msg.py"]) == 1
        # smoke_release.py has 1 code
        assert len(per_pattern["scripts/smoke_release.py"]) == 1

    def test_adding_code_to_existing_entry_increases_count(self) -> None:
        """Adding a code to an existing entry increases the total count (issue #79)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[tool.ruff.lint.per-file-ignores]\n"src/example.py" = ["E501"]\n')
            f.flush()
            total_before, per_pattern_before = count_per_file_ignores(Path(f.name))

        assert total_before == 1
        assert per_pattern_before == {"src/example.py": ["E501"]}

        # Now add a code to the existing entry
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                '[tool.ruff.lint.per-file-ignores]\n"src/example.py" = ["E501", "F401"]\n'
            )
            f.flush()
            total_after, per_pattern_after = count_per_file_ignores(Path(f.name))

        assert total_after == 2
        assert per_pattern_after == {"src/example.py": ["E501", "F401"]}

        # The key assertion: count increased when adding a code to existing entry
        assert total_after > total_before

    def test_main_fails_when_budget_exceeded(self) -> None:
        """Test that main() returns 1 when per-file-ignores exceeds the budget."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pyproject = tmpdir_path / "pyproject.toml"

            # Build a fixture that exceeds the budget by exactly one,
            # derived rather than hardcoded. A literal list of codes has to
            # be edited every time the budget moves, and when it is not, this
            # test fails with `assert N > N` — which says the budget changed,
            # not that the gate broke. Deriving it keeps the test about the
            # gate.
            over = ALLOWED_PER_FILE_IGNORE_CODES + 1
            codes = "".join(f'    "CODE{i:03d}",\n' for i in range(over))
            pyproject.write_text(
                "[tool.ruff.lint.per-file-ignores]\n"
                '"tests/**/*.py" = [\n' + codes + "]\n"
            )

            # Test that the count exceeds the budget
            total, _ = count_per_file_ignores(pyproject)
            assert total == ALLOWED_PER_FILE_IGNORE_CODES + 1
            assert total > ALLOWED_PER_FILE_IGNORE_CODES

            # Copy this pyproject.toml to the project root temporarily and test main()
            original_pyproject = Path("pyproject.toml")
            backup = tmpdir_path / "pyproject.toml.bak"
            if original_pyproject.exists():
                shutil.move(str(original_pyproject), str(backup))

            try:
                shutil.copy(pyproject, "pyproject.toml")
                result = main([])
                assert result == 1
            finally:
                if backup.exists():
                    shutil.move(str(backup), str(original_pyproject))


class TestScan:
    """Tests for the scan function."""

    def test_planted_suppression_in_code_line_is_flagged(self) -> None:
        """A # noqa comment on a code line is flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            script_dir = tmpdir_path / "scripts"
            script_dir.mkdir()
            probe_file = script_dir / "_probe_tmp.py"
            probe_file.write_text("import os  # noqa: E501\n")

            findings, files_scanned = scan([script_dir])

            assert files_scanned == 1
            assert len(findings) == 1
            assert "_probe_tmp.py" in findings[0]
            assert "import os" in findings[0]
            assert findings[0].endswith("import os  # noqa: E501")

    def test_suppression_in_docstring_is_not_flagged(self) -> None:
        """A # noqa text in a docstring is not flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            script_dir = tmpdir_path / "scripts"
            script_dir.mkdir()
            probe_file = script_dir / "_probe_tmp.py"
            probe_file.write_text(
                '"""This docstring names # noqa and # type: ignore[assignment]."""\n'
            )

            findings, files_scanned = scan([script_dir])

            assert files_scanned == 1
            assert len(findings) == 0

    def test_suppression_in_string_literal_is_not_flagged(self) -> None:
        """A # noqa text in a string literal is not flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            script_dir = tmpdir_path / "scripts"
            script_dir.mkdir()
            probe_file = script_dir / "_probe_tmp.py"
            probe_file.write_text('S = "this mentions # noqa: E501 in prose"\n')

            findings, files_scanned = scan([script_dir])

            assert files_scanned == 1
            assert len(findings) == 0

    def test_standalone_comment_suppression_is_flagged(self) -> None:
        """A # noqa on its own comment line above a statement is flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            script_dir = tmpdir_path / "scripts"
            script_dir.mkdir()
            probe_file = script_dir / "_probe_tmp.py"
            probe_file.write_text("# noqa: E501\nimport os\n")

            findings, files_scanned = scan([script_dir])

            assert files_scanned == 1
            assert len(findings) == 1
            assert findings[0].endswith("# noqa: E501")

    def test_unparseable_file_falls_back_to_line_scan(self) -> None:
        """An unparseable file falls back to line-based scan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            script_dir = tmpdir_path / "scripts"
            script_dir.mkdir()
            probe_file = script_dir / "_probe_tmp.py"
            probe_file.write_text("def broken(:\n    pass  # noqa: E501\n")

            findings, files_scanned = scan([script_dir])

            assert files_scanned == 1
            assert len(findings) == 1
            assert "_probe_tmp.py" in findings[0]
            assert "pass" in findings[0]

    def test_main_on_clean_dir_returns_zero(self) -> None:
        """main() returns 0 over a file it actually read.

        The directory holds a real module with no suppression, so a pass
        here means the scanner read it and found nothing. An empty
        directory would return 0 whether or not the scanner works.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            script_dir = Path(tmpdir)
            (script_dir / "_probe_tmp.py").write_text("import os\n\nprint(os)\n")
            findings, files_scanned = scan([script_dir])
            assert files_scanned == 1
            assert findings == []
            assert main([tmpdir]) == 0
