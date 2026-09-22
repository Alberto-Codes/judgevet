"""Tests for scripts/check_dependencies.py."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from scripts.check_dependencies import (
    ALLOWED_RUNTIME_DEPENDENCIES,
    _check_extras,
    _extract_name,
    _find_package_in_lock,
    _get_available_extras,
    _get_requested_extras,
    _normalize,
    _parse_lock_file,
    _parse_pyproject_dependencies,
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


class TestParseLockFile:
    """Tests for the _parse_lock_file function."""

    def test_missing_lock_file_returns_none(self) -> None:
        """A directory without a lock file returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pyproject = tmpdir_path / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test"\n')
            result = _parse_lock_file(pyproject)
        assert result is None

    def test_existing_lock_file_returns_parsed_data(self, tmp_path: Path) -> None:
        """An existing lock file is parsed and returned as a dict."""
        # Create a minimal lock file
        lock_file = tmp_path / "uv.lock"
        lock_file.write_text(
            """version = 1
revision = 1
requires-python = ">=3.12"

[[package]]
name = "httpx"
version = "0.28.0"
"""
        )
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"\n')
        result = _parse_lock_file(pyproject)
        assert result is not None
        assert isinstance(result, dict)
        assert result["version"] == 1
        assert result["revision"] == 1


class TestFindPackageInLock:
    """Tests for the _find_package_in_lock function."""

    def test_found_package(self) -> None:
        """A package in the lock is returned."""
        lock_data = {
            "package": [
                {"name": "httpx", "version": "0.28.0"},
                {"name": "pydantic", "version": "2.4.0"},
            ]
        }
        result = _find_package_in_lock(lock_data, "httpx")
        assert result == {"name": "httpx", "version": "0.28.0"}

    def test_not_found_package(self) -> None:
        """A package not in the lock returns None."""
        lock_data = {
            "package": [
                {"name": "httpx", "version": "0.28.0"},
            ]
        }
        result = _find_package_in_lock(lock_data, "nonexistent")
        assert result is None

    def test_empty_lock(self) -> None:
        """An empty lock returns None for any package."""
        lock_data: dict = {}
        result = _find_package_in_lock(lock_data, "httpx")
        assert result is None


class TestGetRequestedExtras:
    """Tests for the _get_requested_extras function."""

    def test_with_extras(self) -> None:
        """Requested extras are extracted."""
        requirement = {
            "name": "pyjwt",
            "version": "2.14.0",
            "extras": ["crypto"],
        }
        result = _get_requested_extras(requirement)
        assert result == ["crypto"]

    def test_with_multiple_extras(self) -> None:
        """Multiple extras are extracted."""
        requirement = {
            "name": "pyjwt",
            "version": "2.14.0",
            "extras": ["crypto", "auth"],
        }
        result = _get_requested_extras(requirement)
        assert result == ["crypto", "auth"]

    def test_without_extras(self) -> None:
        """A requirement without extras returns an empty list."""
        requirement = {
            "name": "httpx",
            "version": "0.28.0",
        }
        result = _get_requested_extras(requirement)
        assert result == []


class TestGetAvailableExtras:
    """Tests for the _get_available_extras function."""

    def test_with_extras(self) -> None:
        """Available extras are extracted."""
        package_entry = {
            "name": "pyjwt",
            "version": "2.14.0",
            "optional-dependencies": {
                "crypto": [{"name": "cryptography"}],
                "auth": [{"name": "pyjwt-auth"}],
            },
        }
        result = _get_available_extras(package_entry)
        assert result == {"crypto", "auth"}

    def test_without_optional_dependencies(self) -> None:
        """A package without optional-dependencies returns an empty set."""
        package_entry = {
            "name": "httpx",
            "version": "0.28.0",
        }
        result = _get_available_extras(package_entry)
        assert result == set()

    def test_empty_optional_dependencies(self) -> None:
        """An empty optional-dependencies dict returns an empty set."""
        package_entry = {
            "name": "httpx",
            "version": "0.28.0",
            "optional-dependencies": {},
        }
        result = _get_available_extras(package_entry)
        assert result == set()


class TestParsePyprojectDependencies:
    """Tests for the _parse_pyproject_dependencies function."""

    def test_runtime_dependencies_only(self, tmp_path: Path) -> None:
        """Runtime dependencies are parsed."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\ndependencies = [\n"
            '    "httpx>=0.28",\n'
            '    "pydantic-settings>=2.4",\n'
            "]\n"
        )
        result = _parse_pyproject_dependencies(pyproject)
        assert result == [
            ("httpx", [], "requires-dist"),
            ("pydantic-settings", [], "requires-dist"),
        ]

    def test_with_extras(self, tmp_path: Path) -> None:
        """Dependencies with extras are parsed."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\ndependencies = [\n"
            '    "pyjwt[crypto]>=2.0",\n'
            '    "httpx>=0.28",\n'
            "]\n"
        )
        result = _parse_pyproject_dependencies(pyproject)
        assert result == [
            ("pyjwt", ["crypto"], "requires-dist"),
            ("httpx", [], "requires-dist"),
        ]

    def test_dev_dependencies(self, tmp_path: Path) -> None:
        """Dev dependencies are parsed with their group."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\ndependencies = ["httpx>=0.28"]\n'
            "[dependency-groups]\n"
            'dev = ["pytest>=7.0", "pyjwt[auth]>=2.0"]\n'
        )
        result = _parse_pyproject_dependencies(pyproject)
        assert result == [
            ("httpx", [], "requires-dist"),
            ("pytest", [], "requires-dev.dev"),
            ("pyjwt", ["auth"], "requires-dev.dev"),
        ]

    def test_current_pyproject_toml(self) -> None:
        """The real pyproject.toml parses correctly."""
        result = _parse_pyproject_dependencies(Path("pyproject.toml"))
        # Check that we get some dependencies
        assert len(result) > 0
        # All should have the expected format
        for pkg_name, extras, source in result:
            assert isinstance(pkg_name, str)
            assert isinstance(extras, list)
            assert source in ("requires-dist", "requires-dev.dev")


class TestCheckExtras:
    """Tests for the _check_extras function."""

    def test_invalid_extra_detected(self, tmp_path: Path) -> None:
        """A nonexistent extra is flagged as invalid."""
        # Create a manifest with a bad extra
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\ndependencies = [\n    "pyjwt[definitelynotanextra]>=2.0",\n]\n'
        )
        # Create a real lock file
        lock_file = tmp_path / "uv.lock"
        lock_file.write_text(
            """version = 1
revision = 1
requires-python = ">=3.12"

[[package]]
name = "pyjwt"
version = "2.14.0"

[package.optional-dependencies]
crypto = [
    { name = "cryptography" },
]
"""
        )
        invalid_extras, stale_locks = _check_extras(pyproject)
        assert invalid_extras == [("pyjwt", "definitelynotanextra", "requires-dist")]
        assert stale_locks == []

    def test_valid_extra_not_flagged(self, tmp_path: Path) -> None:
        """A valid extra is not flagged."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\ndependencies = [\n    "pyjwt[crypto]>=2.0",\n]\n'
        )
        # Create a real lock file with the extra
        lock_file = tmp_path / "uv.lock"
        lock_file.write_text(
            """version = 1
revision = 1
requires-python = ">=3.12"

[[package]]
name = "pyjwt"
version = "2.14.0"

[package.optional-dependencies]
crypto = [
    { name = "cryptography" },
]
"""
        )
        invalid_extras, stale_locks = _check_extras(pyproject)
        assert invalid_extras == []
        assert stale_locks == []

    def test_dev_group_extra_checked(self, tmp_path: Path) -> None:
        """A dev-group extra is checked and names its table."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\ndependencies = ["httpx>=0.28"]\n'
            "[dependency-groups]\n"
            'dev = ["pyjwt[definitelynotanextra]>=2.0"]\n'
        )
        # Create a real lock file
        lock_file = tmp_path / "uv.lock"
        lock_file.write_text(
            """version = 1
revision = 1
requires-python = ">=3.12"

[[package]]
name = "httpx"
version = "0.28.0"

[[package]]
name = "pyjwt"
version = "2.14.0"

[package.optional-dependencies]
crypto = [
    { name = "cryptography" },
]
"""
        )
        invalid_extras, stale_locks = _check_extras(pyproject)
        assert invalid_extras == [("pyjwt", "definitelynotanextra", "requires-dev.dev")]
        assert stale_locks == []

    def test_stale_lock_absent_from_lock(self, tmp_path: Path) -> None:
        """A requirement absent from the lock is a stale lock, not an invalid extra."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\ndependencies = [\n    "pyjwt[crypto]>=2.0",\n]\n'
        )
        # Create a lock without pyjwt at all
        lock_file = tmp_path / "uv.lock"
        lock_file.write_text(
            """version = 1
revision = 1
requires-python = ">=3.12"

[[package]]
name = "httpx"
version = "0.28.0"
"""
        )
        invalid_extras, stale_locks = _check_extras(pyproject)
        assert invalid_extras == []
        assert stale_locks == ["pyjwt"]

    def test_current_repo_clean(self) -> None:
        """This repo's own manifest is clean."""
        invalid_extras, stale_locks = _check_extras(Path("pyproject.toml"))
        assert invalid_extras == []
        assert stale_locks == []

    def test_fixture_format_matches_what_uv_actually_writes(self) -> None:
        """The hand-written lock fixtures encode uv's real structure.

        Every failing-path test in this class writes its own `uv.lock` by
        hand, so those tests assert against a model of the format rather
        than against uv. If uv renamed the key or nested it differently they
        would all still pass while the gate silently stopped detecting
        anything.

        This reads the repository's own `uv.lock`, which uv wrote, and
        pins the one structure the fixtures depend on: `pyjwt` is locked
        with a real `crypto` extra because something in the tree requests
        `pyjwt[crypto]`. If this fails, the fixtures above are lying and
        the parser needs rechecking against the real format -- not this
        assertion relaxing.
        """
        lock_data = _parse_lock_file(Path("pyproject.toml"))
        assert lock_data is not None
        entry = _find_package_in_lock(lock_data, "pyjwt")
        assert entry is not None, "pyjwt is no longer in uv.lock; pick another anchor"
        assert _get_available_extras(entry) == {"crypto"}

    def test_no_lock_file(self, tmp_path: Path) -> None:
        """No lock file at all returns empty lists."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\ndependencies = [\n    "pyjwt[crypto]>=2.0",\n]\n'
        )
        # Don't create a lock file
        invalid_extras, stale_locks = _check_extras(pyproject)
        assert invalid_extras == []
        assert stale_locks == []


class TestCheckExtrasPureFunctions:
    """Tests for pure functions using in-memory data structures."""

    def test_find_package_in_lock_with_extras(self) -> None:
        """Find package with optional-dependencies."""
        lock_data = {
            "package": [
                {
                    "name": "pyjwt",
                    "version": "2.14.0",
                    "optional-dependencies": {
                        "crypto": [{"name": "cryptography"}],
                    },
                },
            ]
        }
        result = _find_package_in_lock(lock_data, "pyjwt")
        assert result is not None
        assert result["name"] == "pyjwt"
        assert "optional-dependencies" in result

    def test_parse_pyproject_with_dev_extras(self, tmp_path: Path) -> None:
        """Parse dev dependencies with extras."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\ndependencies = ["httpx>=0.28"]\n'
            "[dependency-groups]\n"
            'test = ["pytest[dist]", "pyjwt[crypto]>=2.0"]\n'
        )
        result = _parse_pyproject_dependencies(pyproject)
        # Find the test dependencies
        test_deps = [r for r in result if r[2].startswith("requires-dev.")]
        assert len(test_deps) == 2
        # Check they have correct extras
        assert ("pytest", ["dist"], "requires-dev.test") in test_deps
        assert ("pyjwt", ["crypto"], "requires-dev.test") in test_deps
