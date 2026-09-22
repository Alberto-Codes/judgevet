"""Tests for scripts/check_dependencies.py."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from scripts.check_dependencies import (
    ALLOWED_RUNTIME_DEPENDENCIES,
    _extract_name,
    _normalize,
    check_dependencies,
    main,
    parse_runtime_names,
)


class TestNormalize:
    """Tests for the _normalize function."""

    def test_simple_name(self) -> None:
        """A simple name is lowercased."""
        assert _normalize("httpx") == "httpx"

    def test_underscore_to_dash(self) -> None:
        """Underscores become dashes."""
        assert _normalize("pydantic_settings") == "pydantic-settings"

    def test_dot_to_dash(self) -> None:
        """Dots become dashes."""
        assert _normalize("foo.bar") == "foo-bar"

    def test_mixed_separators(self) -> None:
        """Mixed separators are normalized."""
        assert _normalize("Foo_Bar.Baz") == "foo-bar-baz"

    def test_runs_collapsed(self) -> None:
        """Runs of separators become a single dash."""
        assert _normalize("foo__bar---baz...qux") == "foo-bar-baz-qux"


class TestExtractName:
    """Tests for the _extract_name function."""

    def test_simple_name(self) -> None:
        """A simple name is normalized."""
        assert _extract_name("httpx") == "httpx"

    def test_with_extras(self) -> None:
        """Extras are stripped."""
        assert _extract_name("httpx[http2]") == "httpx"

    def test_with_specifier(self) -> None:
        """Specifiers are stripped."""
        assert _extract_name("httpx>=0.28") == "httpx"

    def test_with_complex_specifier(self) -> None:
        """Complex specifiers are stripped."""
        assert _extract_name("httpx>=0.28,<1.0") == "httpx"

    def test_with_marker(self) -> None:
        """Markers are stripped."""
        assert _extract_name('httpx; python_version < "3.12"') == "httpx"

    def test_with_all_modifiers(self) -> None:
        """Extras, specifiers, and markers are all stripped."""
        assert (
            _extract_name('httpx[http2]>=0.28,<1.0; python_version < "3.12"') == "httpx"
        )

    def test_pydantic_settings_normalized(self) -> None:
        """Package names are normalized."""
        assert _extract_name("Pydantic_Settings>=2.4") == "pydantic-settings"


class TestParseRuntimeNames:
    """Tests for the parse_runtime_names function."""

    def test_empty_file_returns_empty_set(self) -> None:
        """An empty pyproject.toml has no dependencies."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("")
            f.flush()
            names = parse_runtime_names(Path(f.name))
        assert names == set()

    def test_missing_project_section_returns_empty_set(self) -> None:
        """A file without [project] section has no dependencies."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[build-system]\nrequires = ["setuptools"]\n')
            f.flush()
            names = parse_runtime_names(Path(f.name))
        assert names == set()

    def test_missing_dependencies_returns_empty_set(self) -> None:
        """A file without dependencies has an empty set."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[project]\nname = "test"\n')
            f.flush()
            names = parse_runtime_names(Path(f.name))
        assert names == set()

    def test_single_dependency(self) -> None:
        """A single dependency is parsed and normalized."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[project]\ndependencies = ["httpx>=0.28"]\n')
            f.flush()
            names = parse_runtime_names(Path(f.name))
        assert names == {"httpx"}

    def test_multiple_dependencies(self) -> None:
        """Multiple dependencies are parsed and normalized."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                "[project]\ndependencies = [\n"
                '    "httpx>=0.28",\n'
                '    "pydantic-settings>=2.4",\n'
                '    "structlog>=24.1",\n'
                '    "typer>=0.12",\n'
                "]\n"
            )
            f.flush()
            names = parse_runtime_names(Path(f.name))
        assert names == {"httpx", "pydantic-settings", "structlog", "typer"}

    def test_complex_dependency(self) -> None:
        """A dependency with extras, specifiers, and markers is parsed."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            # A complex but valid TOML dependency string
            f.write(
                """[project]
dependencies = [
    "httpx[http2]>=0.28,<1.0",
    "Pydantic_Settings>=2.4; python_version >= '3.12'",
]
"""
            )
            f.flush()
            names = parse_runtime_names(Path(f.name))
        assert names == {"httpx", "pydantic-settings"}

    def test_current_pyproject_toml(self) -> None:
        """The real pyproject.toml parses to the expected set."""
        names = parse_runtime_names(Path("pyproject.toml"))
        assert names == {"httpx", "pydantic-settings", "structlog", "typer"}


class TestCheckDependencies:
    """Tests for the check_dependencies function."""

    def test_exact_match_returns_empty(self) -> None:
        """An exact match returns (empty, empty)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[project]\ndependencies = ["httpx>=0.28"]\n')
            f.flush()
            unpinned, missing = check_dependencies(Path(f.name), {"httpx"})
        assert unpinned == []
        assert missing == []

    def test_unpinned_dependency(self) -> None:
        """A dependency not in the allowed set is in unpinned."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                '[project]\ndependencies = ["pytest-asyncio>=1.0", "httpx>=0.28"]\n'
            )
            f.flush()
            unpinned, missing = check_dependencies(Path(f.name), {"httpx"})
        assert unpinned == ["pytest-asyncio"]
        assert missing == []

    def test_missing_dependency(self) -> None:
        """A missing dependency is in missing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[project]\ndependencies = ["httpx>=0.28"]\n')
            f.flush()
            unpinned, missing = check_dependencies(Path(f.name), {"httpx", "typer"})
        assert unpinned == []
        assert missing == ["typer"]

    def test_both_unpinned_and_missing(self) -> None:
        """Both unpinned and missing are reported."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[project]\ndependencies = ["pytest-asyncio>=1.0", "rich>=13"]\n')
            f.flush()
            unpinned, missing = check_dependencies(Path(f.name), {"httpx", "typer"})
        assert unpinned == ["pytest-asyncio", "rich"]
        assert missing == ["httpx", "typer"]

    def test_normalization_holds(self) -> None:
        """Normalization is applied before comparison."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            # Use a name that normalizes to pydantic-settings but with different casing
            f.write(
                '[project]\ndependencies = ["Pydantic_Settings>=2.4", "httpx>=0.28"]\n'
            )
            f.flush()
            unpinned, missing = check_dependencies(
                Path(f.name), {"httpx", "pydantic-settings"}
            )
        assert unpinned == []
        assert missing == []

    def test_legitimate_addition_passes_with_updated_pin(self) -> None:
        """A legitimate addition passes when the pin is updated."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            # Add rich to the existing dependencies
            f.write("[project]\ndependencies = [\n")
            f.write('    "httpx>=0.28",\n')
            f.write('    "pydantic-settings>=2.4",\n')
            f.write('    "structlog>=24.1",\n')
            f.write('    "typer>=0.12",\n')
            f.write('    "rich>=13",\n')
            f.write("]\n")
            f.flush()
            unpinned, missing = check_dependencies(
                Path(f.name),
                ALLOWED_RUNTIME_DEPENDENCIES | {"rich"},
            )
        assert unpinned == []
        assert missing == []


class TestMain:
    """Tests for the main function."""

    def test_clean_file_returns_zero(self) -> None:
        """main() returns 0 when the dependency set matches the pin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pyproject = tmpdir_path / "pyproject.toml"
            pyproject.write_text(
                "[project]\ndependencies = [\n"
                '    "httpx>=0.28",\n'
                '    "pydantic-settings>=2.4",\n'
                '    "structlog>=24.1",\n'
                '    "typer>=0.12",\n'
                "]\n"
            )

            result = main([str(pyproject)])

            assert result == 0

    def test_clean_file_prints_summary(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """main() prints a summary line on clean."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pyproject = tmpdir_path / "pyproject.toml"
            pyproject.write_text(
                "[project]\ndependencies = [\n"
                '    "httpx>=0.28",\n'
                '    "pydantic-settings>=2.4",\n'
                '    "structlog>=24.1",\n'
                '    "typer>=0.12",\n'
                "]\n"
            )

            result = main([str(pyproject)])

            assert result == 0
            captured = capsys.readouterr()
            assert "check_dependencies: clean" in captured.out

    def test_planted_test_package_fails(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A planted test-only package fails the gate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pyproject = tmpdir_path / "pyproject.toml"
            pyproject.write_text(
                "[project]\ndependencies = [\n"
                '    "httpx>=0.28",\n'
                '    "pytest-asyncio[dev]>=1.4.0",\n'
                "]\n"
            )

            result = main([str(pyproject)])

            assert result == 1
            captured = capsys.readouterr()
            assert "pytest-asyncio" in captured.out

    def test_planted_test_package_names_it(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A planted test-only package is named in the output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pyproject = tmpdir_path / "pyproject.toml"
            pyproject.write_text(
                "[project]\ndependencies = [\n"
                '    "httpx>=0.28",\n'
                '    "pytest-asyncio[dev]>=1.4.0",\n'
                "]\n"
            )

            result = main([str(pyproject)])

            assert result == 1
            captured = capsys.readouterr()
            assert "pytest-asyncio" in captured.out

    def test_removal_fails(self) -> None:
        """A removal from the pinned set fails the gate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pyproject = tmpdir_path / "pyproject.toml"
            pyproject.write_text(
                "[project]\ndependencies = [\n"
                '    "httpx>=0.28",\n'
                '    "pydantic-settings>=2.4",\n'
                '    "structlog>=24.1",\n'
                "]\n"
            )

            result = main([str(pyproject)])

            assert result == 1

    def test_removal_names_missing_package(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A missing package is named in the output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pyproject = tmpdir_path / "pyproject.toml"
            pyproject.write_text(
                "[project]\ndependencies = [\n"
                '    "httpx>=0.28",\n'
                '    "pydantic-settings>=2.4",\n'
                '    "structlog>=24.1",\n'
                "]\n"
            )

            result = main([str(pyproject)])

            assert result == 1
            captured = capsys.readouterr()
            assert "typer" in captured.out

    def test_legitimate_addition_fails_until_pin_updated(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A legitimate addition fails until the pin is updated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pyproject = tmpdir_path / "pyproject.toml"
            pyproject.write_text(
                '[project]\ndependencies = [\n    "httpx>=0.28",\n    "rich>=13",\n]\n'
            )

            result = main([str(pyproject)])

            assert result == 1
            captured = capsys.readouterr()
            assert "rich" in captured.out
            assert "ALLOWED_RUNTIME_DEPENDENCIES" in captured.out
            assert "scripts/check_dependencies.py" in captured.out

    def test_missing_file_returns_nonzero(self) -> None:
        """A missing file returns 1."""
        result = main(["/nonexistent/pyproject.toml"])
        assert result == 1

    def test_default_path(self, capsys: pytest.CaptureFixture[str]) -> None:
        """main() uses pyproject.toml by default."""
        # This will succeed because we're running from the repo root
        result = main([])
        assert result == 0
        # And it should have checked the real file
        captured = capsys.readouterr()
        assert "4 runtime dependencies" in captured.out
