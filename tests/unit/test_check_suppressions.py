"""Tests for scripts/check_suppressions.py."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from scripts.check_suppressions import (
    ALLOWED_PER_FILE_IGNORE_CODES,
    count_per_file_ignores,
    main,
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
        # Current budget: 10 codes (7 in tests/**/*.py, 3 in mcp.py)
        assert total == 10
        assert len(per_pattern) == 2
        # tests/**/*.py has 7 codes
        assert len(per_pattern["tests/**/*.py"]) == 7
        # mcp.py has 3 codes
        assert len(per_pattern["src/judgevet/adapters/inbound/mcp.py"]) == 3

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

            # Write a pyproject.toml that exceeds the budget (10 codes)
            # 11 codes total
            pyproject.write_text(
                "[tool.ruff.lint.per-file-ignores]\n"
                '"tests/**/*.py" = [\n'
                '    "S101",\n'
                '    "D100",\n'
                '    "D101",\n'
                '    "D102",\n'
                '    "D103",\n'
                '    "D104",\n'
                '    "PLR2004",\n'
                '    "E501",\n'
                '    "F401",\n'
                '    "W503",\n'
                '    "PLR0915",\n'
                "]\n"
            )

            # Test that the count exceeds the budget
            total, _ = count_per_file_ignores(pyproject)
            assert total == 11
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
