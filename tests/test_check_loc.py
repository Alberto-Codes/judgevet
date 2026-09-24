"""Boundary tests for the file-size gate in `scripts/check_loc.py`.

Every fixture module is generated into `tmp_path`, so each case pins one
boundary of the real counter and the real `main`: the single 300-line
module limit, and the 50-line function report.

Examples:
    ```python
    from scripts.check_loc import count_function_lines
    ```

See Also:
    [judgevet][]
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_loc import count_code_lines, count_function_lines, main

pytestmark = pytest.mark.unit


def _module_source(code_lines: int) -> str:
    """Build a module source with exactly `code_lines` code lines.

    Args:
        code_lines: Number of assignment lines to emit.

    Returns:
        The module source text.
    """
    return "".join(f"x{i} = {i}\n" for i in range(code_lines))


def _function_source(body_lines: int) -> str:
    """Build a decorated function with exactly `body_lines` code lines.

    Args:
        body_lines: Number of assignment lines in the function body.

    Returns:
        The module source text defining `long_one`.
    """
    body = "".join(f"    a{i} = {i}\n" for i in range(body_lines))
    return (
        "import functools\n\n\n"
        "@functools.cache\n"
        "def long_one(\n    first: int,\n    second: int,\n) -> None:\n"
        f"{body}"
    )


def _write_pkg(tmp_path: Path, source: str) -> Path:
    """Write `source` as the only module of a package directory.

    Args:
        tmp_path: Directory to create the package in.
        source: Module source text.

    Returns:
        The package directory.
    """
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text(source, encoding="utf-8")
    return pkg


@pytest.mark.parametrize(
    ("lines", "exit_code"),
    [(300, 0), (301, 1), (320, 1), (321, 1)],
)
def test_module_limit(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    lines: int,
    exit_code: int,
) -> None:
    """Hold the single 300-line module limit at its exact boundary."""
    pkg = _write_pkg(tmp_path, _module_source(lines))
    assert count_code_lines(pkg / "mod.py") == lines
    assert main([str(pkg)]) == exit_code
    captured = capsys.readouterr()
    assert "WARN" not in captured.out + captured.err
    assert ("mod.py" in captured.out) is (exit_code == 1)
    assert ("FAIL" in captured.out) is (exit_code == 1)


def test_docstring_and_comment_lines_do_not_count(tmp_path: Path) -> None:
    """Add only documentation lines and see no count change."""
    plain = tmp_path / "plain.py"
    documented = tmp_path / "documented.py"
    commented = tmp_path / "commented.py"
    source = _module_source(10) + _function_source(5)
    plain.write_text(source, encoding="utf-8")
    documented.write_text(
        '"""Module.\n\nMore text.\n"""\n'
        + source.replace(
            ") -> None:\n", ') -> None:\n    """Doc.\n\n    More.\n    """\n'
        ),
        encoding="utf-8",
    )
    commented.write_text(
        "# header\n\n"
        + source.replace("    a0 = 0\n", "    # note\n    a0 = 0  # tail\n"),
        encoding="utf-8",
    )
    for path in (documented, commented):
        assert count_code_lines(path) == count_code_lines(plain)
        assert count_function_lines(path) == count_function_lines(plain)


def test_function_count_excludes_decorator_and_signature(tmp_path: Path) -> None:
    """Count only body lines of a decorated, multi-line signature."""
    path = tmp_path / "mod.py"
    path.write_text(_function_source(7), encoding="utf-8")
    assert count_function_lines(path) == [("long_one", 7)]


def test_nested_function_counts_toward_parent(tmp_path: Path) -> None:
    """Charge a nested function's lines to its enclosing function."""
    path = tmp_path / "mod.py"
    path.write_text(
        "class Box:\n"
        "    def outer(self) -> int:\n"
        "        def inner() -> int:\n"
        "            return 1\n"
        "        return inner()\n",
        encoding="utf-8",
    )
    counts = dict(count_function_lines(path))
    assert counts["Box.outer"] == 3
    assert counts["Box.outer.inner"] == 1


@pytest.mark.parametrize(("lines", "reported"), [(50, False), (51, True)])
def test_function_report_boundary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    lines: int,
    reported: bool,
) -> None:
    """Report a function past 50 code lines and still exit 0."""
    pkg = _write_pkg(tmp_path, _function_source(lines))
    assert count_function_lines(pkg / "mod.py") == [("long_one", lines)]
    assert main([str(pkg)]) == 0
    assert ("long_one" in capsys.readouterr().out) is reported
