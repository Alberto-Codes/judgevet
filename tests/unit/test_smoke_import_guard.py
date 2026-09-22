"""Exercise the release guard against real installation paths and symlinks.

Examples:
    Run the offline path regressions::

        uv run pytest -q tests/unit/test_smoke_import_guard.py

See Also:
    - [scripts.smoke_release_child][]: Production import guard.
"""

import sysconfig
from pathlib import Path
from types import ModuleType

import pytest

from scripts import smoke_release_child as child

pytestmark = pytest.mark.unit


def _configure(
    monkeypatch: pytest.MonkeyPatch, prefix: Path, roots: dict[str, str], file: Path
) -> None:
    """Supply interpreter metadata and an imported module location.

    Args:
        monkeypatch: Scoped patch manager.
        prefix: Interpreter environment root.
        roots: Interpreter installation directories.
        file: Imported module file.
    """
    module = ModuleType("judgevet")
    module.__file__ = str(file)
    monkeypatch.setattr(child, "__get_judgevet_module", lambda: module)
    monkeypatch.setattr(child.sys, "prefix", str(prefix))
    monkeypatch.setattr(sysconfig, "get_paths", lambda **_kwargs: roots)


def _file(path: Path) -> Path:
    """Create an importable path on the real filesystem.

    Args:
        path: File to create.

    Returns:
        The created file path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


@pytest.mark.parametrize("directory", ["lib", "lib64", "Lib"])
def test_interpreter_install_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, directory: str
) -> None:
    """Accept interpreter-provided pure or platform package paths."""
    prefix = tmp_path / "venv"
    pure = prefix / "lib/python3.14/site-packages"
    platform = prefix / directory / "python3.14/site-packages"
    file = _file(platform / "judgevet/__init__.py")
    _configure(
        monkeypatch, prefix, {"purelib": str(pure), "platlib": str(platform)}, file
    )
    child.assert_in_site_packages()


@pytest.mark.parametrize("kind", ["checkout", "foreign", "prefix", "site-prefix"])
def test_reject_unrelated_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Reject source, foreign environments and misleading path prefixes."""
    prefix = tmp_path / "venv"
    root = prefix / "lib/python3.14/site-packages"
    root.mkdir(parents=True)
    locations = {
        "checkout": tmp_path / "src/judgevet/__init__.py",
        "foreign": tmp_path
        / "foreign/lib/python3.14/site-packages/judgevet/__init__.py",
        "prefix": tmp_path
        / "venv-other/lib/python3.14/site-packages/judgevet/__init__.py",
        "site-prefix": root.parent / "site-packages-other/judgevet/__init__.py",
    }
    file = _file(locations[kind])
    _configure(monkeypatch, prefix, {"purelib": str(root), "platlib": str(root)}, file)
    with pytest.raises(RuntimeError, match="not under"):
        child.assert_in_site_packages()


def test_accept_internal_alias(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve a legitimate lib to lib64 alias before containment checks."""
    prefix = tmp_path / "venv"
    root = prefix / "lib64/python3.14/site-packages"
    file = _file(root / "judgevet/__init__.py")
    (prefix / "lib").symlink_to(prefix / "lib64", target_is_directory=True)
    alias = prefix / "lib/python3.14/site-packages"
    _configure(
        monkeypatch, prefix, {"purelib": str(alias), "platlib": str(alias)}, file
    )
    child.assert_in_site_packages()


@pytest.mark.parametrize("escape", ["package", "root"])
def test_reject_symlink_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, escape: str
) -> None:
    """Reject a lexical match whose resolved installation escapes the venv."""
    prefix = tmp_path / "venv"
    root = prefix / "lib/python3.14/site-packages"
    external = tmp_path / "external"
    _file(external / "judgevet/__init__.py")
    if escape == "root":
        root.parent.mkdir(parents=True)
        root.symlink_to(external, target_is_directory=True)
    else:
        root.mkdir(parents=True)
        (root / "judgevet").symlink_to(external / "judgevet", target_is_directory=True)
    _configure(
        monkeypatch,
        prefix,
        {"purelib": str(root), "platlib": str(root)},
        root / "judgevet/__init__.py",
    )
    with pytest.raises(RuntimeError, match="not under"):
        child.assert_in_site_packages()


@pytest.mark.parametrize("roots", [{}, {"purelib": "", "platlib": ""}])
def test_reject_missing_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, roots: dict[str, str]
) -> None:
    """Missing interpreter paths cannot grant acceptance to a legacy glob."""
    prefix = tmp_path / "venv"
    file = _file(prefix / "lib/python3.14/site-packages/judgevet/__init__.py")
    _configure(monkeypatch, prefix, roots, file)
    with pytest.raises(RuntimeError, match="not under"):
        child.assert_in_site_packages()


def test_reject_foreign_install_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even a configured installation directory must belong to the venv."""
    prefix = tmp_path / "venv"
    (prefix / "lib/python3.14/site-packages").mkdir(parents=True)
    root = tmp_path / "foreign/site-packages"
    file = _file(root / "judgevet/__init__.py")
    _configure(monkeypatch, prefix, {"purelib": str(root), "platlib": str(root)}, file)
    with pytest.raises(RuntimeError, match="not under"):
        child.assert_in_site_packages()


@pytest.mark.parametrize("kind", ["relative", "prefix"])
def test_reject_invalid_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Relative paths or the environment root cannot stand in for install roots."""
    prefix = tmp_path / "venv"
    file = _file(prefix / "lib/python3.14/site-packages/judgevet/__init__.py")
    root = "lib/python3.14/site-packages" if kind == "relative" else str(prefix)
    _configure(monkeypatch, prefix, {"purelib": root, "platlib": root}, file)
    with pytest.raises(RuntimeError, match="not under"):
        child.assert_in_site_packages()
