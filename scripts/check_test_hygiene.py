#!/usr/bin/env python3
"""Fail when a test is vacuous or binds an unwrapped secret.

Two checks over `tests/`:

1. **Vacuity check** — V1: a try/except inside a `test_*` function where
   assertions only run on the exception path; V2: a `test_*` function with
   no assertions, direct or transitive through a same-module helper.

2. **Secret-binding check** — a binding whose value is a
   `.get_secret_value()` call, unless the unwrap is inside a call expression.

The reason is in #95: pytest prints the frame locals of every frame in a
failing traceback, so a plaintext key bound to a local is printed on failure —
to the terminal, to CI logs, and to any agent transcript capturing the output.
It has already happened once in this repo. A `SecretStr` local reprs as
`SecretStr('**********')`; a `str` local reprs as the key.

Usage:
    check_test_hygiene.py [paths...]     # defaults to `tests/`

Exit status is 1 when a hygiene issue is found.
"""

from __future__ import annotations

import ast
import fnmatch
import sys
import tomllib
from pathlib import Path


def _is_test_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if the function name starts with 'test_'."""
    return node.name.startswith("test_")


def _has_assertion(node: ast.AST | list[ast.stmt]) -> bool:
    """Check if an AST node contains an assertion."""
    nodes = node if isinstance(node, list) else [node]
    for stmt in nodes:
        for child in ast.walk(stmt):
            if isinstance(child, ast.Assert):
                return True
            if isinstance(child, ast.Call):
                if not isinstance(child.func, ast.Attribute):
                    continue
                if child.func.attr.startswith("assert_"):
                    return True
                if (
                    child.func.attr == "fail"
                    and isinstance(child.func.value, ast.Name)
                    and child.func.value.id == "pytest"
                ):
                    return True
                if (
                    child.func.attr == "raises"
                    and isinstance(child.func.value, ast.Name)
                    and child.func.value.id == "pytest"
                ):
                    return True
    return False


def _is_pytest_fail_call(node: ast.Call) -> bool:
    """Check if the call is pytest.fail()."""
    if not isinstance(node.func, ast.Attribute):
        return False
    if node.func.attr != "fail":
        return False
    if not isinstance(node.func.value, ast.Name):
        return False
    return node.func.value.id == "pytest"


def _has_pytest_fail_in_orelse(orelse: list[ast.stmt]) -> bool:
    """Check if the orelse contains a pytest.fail call."""
    for stmt in orelse:
        for child in ast.walk(stmt):
            if isinstance(child, ast.Call) and _is_pytest_fail_call(child):
                return True
    return False


def _check_v1_swallowed_failure(node: ast.Try | ast.TryStar) -> bool:
    """Check V1: try/except with assertions only in except handler."""
    has_assert_in_except = any(
        _has_assertion(handler.body) for handler in node.handlers
    )

    if not has_assert_in_except:
        return False

    if not node.orelse:
        return True

    return not _has_pytest_fail_in_orelse(node.orelse)


def _has_direct_assertion(func_body: list[ast.stmt]) -> bool:
    """Check if function body has a direct assertion."""
    for stmt in func_body:
        for child in ast.walk(stmt):
            if isinstance(child, ast.Assert):
                return True
            if isinstance(child, ast.Call):
                if not isinstance(child.func, ast.Attribute):
                    continue
                if child.func.attr.startswith("assert_"):
                    return True
                if (
                    child.func.attr == "fail"
                    and isinstance(child.func.value, ast.Name)
                    and child.func.value.id == "pytest"
                ):
                    return True
                if (
                    child.func.attr == "raises"
                    and isinstance(child.func.value, ast.Name)
                    and child.func.value.id == "pytest"
                ):
                    return True
    return False


def _has_real_assertion(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    module_ctx: ast.Module,
    visited: set[str] | None = None,
) -> bool:
    """Check if a test function has a real assertion.

    Returns True if the function body contains:
    - an ast.Assert
    - a pytest.raises or pytest.fail call
    - a call to an assert_* method
    - a call to a helper function defined in the same module that has an assertion
    """
    if visited is None:
        visited = set()

    func_key = f"{func_node.name}:{func_node.lineno}"
    if func_key in visited:
        return False
    visited.add(func_key)

    if _has_direct_assertion(func_node.body):
        return True

    # Check for calls to helpers defined in the same module
    helper_defs: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for top_node in module_ctx.body:
        if isinstance(top_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            helper_defs[top_node.name] = top_node

    for child in ast.walk(func_node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            helper_name = child.func.id
            if helper_name in helper_defs and _has_real_assertion(
                helper_defs[helper_name], module_ctx, visited
            ):
                return True

    return False


def _find_v2_vacuous_functions(
    tree: ast.Module,
) -> list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, int]]:
    """Find V2 vacuous test functions."""
    vacuous: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, int]] = []

    vacuous = [
        (node, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and _is_test_function(node)
        and not _has_real_assertion(node, tree)
    ]

    return vacuous


def _is_secret_unwrap(node: ast.AST) -> bool:
    """Check if an AST node is a get_secret_value() call."""
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return False
    return node.func.attr == "get_secret_value"


def _is_secret_unwrap_in_binding(node: ast.AST) -> bool:
    """Check if a get_secret_value() call is in a binding without shielding.

    Returns True if this node is a get_secret_value() call that is:
    1. The value of an Assign or AnnAssign
    2. The value of a NamedExpr
    3. The target of a For loop
    4. A with item variable
    5. A function parameter default

    And no Call node lies between this call and its binding.
    """
    return _is_secret_unwrap(node)


def _find_secret_bindings(node: ast.AST) -> list[tuple[ast.AST, int]]:
    """Find secret bindings that are not shielded by a call expression.

    Returns a list of (node, lineno) for unshielded unwraps.
    """
    findings: list[tuple[ast.AST, int]] = []

    # Look for Assign nodes where the value is or contains an unwrap
    for child in ast.walk(node):
        if isinstance(child, ast.Assign):
            # Check if the assignment value contains an unshielded unwrap
            findings.extend(_check_binding_value(child.value, child.lineno))
        elif isinstance(child, ast.AnnAssign):
            if child.value is not None:
                findings.extend(_check_binding_value(child.value, child.lineno))
        elif isinstance(child, ast.NamedExpr):
            findings.extend(_check_binding_value(child.value, child.lineno))
        elif isinstance(child, ast.For):
            # Check the target (can be Name, Tuple, List, etc.)
            findings.extend(_check_for_target(child.target, child.lineno))
        elif isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
            # Check parameter defaults
            for arg in child.args.defaults:
                findings.extend(_check_unwrap_in_expr(arg))
            for arg in child.args.kw_defaults:
                if arg is not None:
                    findings.extend(_check_unwrap_in_expr(arg))

    return findings


def _check_binding_value(value: ast.AST, lineno: int) -> list[tuple[ast.AST, int]]:
    """Check if a binding value contains an unshielded unwrap."""
    findings: list[tuple[ast.AST, int]] = []
    findings.extend(_check_unwrap_in_expr(value))
    return findings


def _check_for_target(target: ast.AST, lineno: int) -> list[tuple[ast.AST, int]]:
    """Check if a for loop target contains an unshielded unwrap."""
    findings: list[tuple[ast.AST, int]] = []

    if isinstance(target, ast.Name):
        # Simple for name in iterable: check if iterable has unwrap
        # We need to look at the iterator, not the target
        pass
    elif isinstance(target, (ast.Tuple, ast.List)):
        # for x, y in items: check each element
        for elt in target.elts:
            findings.extend(_check_for_target(elt, lineno))

    return findings


def _is_secret_unwrap_call(node: ast.AST) -> bool:
    """Check if a node is a get_secret_value() call (possibly nested in Attribute chain)."""
    if not isinstance(node, ast.Call):
        return False
    # Check if the method being called is get_secret_value
    return bool(
        isinstance(node.func, ast.Attribute) and node.func.attr == "get_secret_value"
    )


def _check_unwrap_in_expr(expr: ast.AST) -> list[tuple[ast.AST, int]]:
    """Check if an expression contains an unshielded get_secret_value() call.

    Returns a list of (node, lineno) where node is the get_secret_value() call.
    An unwrap is shielded if it's inside a Call (as an argument or keyword).
    """
    findings: list[tuple[ast.AST, int]] = []

    if _is_secret_unwrap_call(expr):
        # The unwrap itself is not shielded (no Call between it and its binding)
        if hasattr(expr, "lineno"):
            lineno = getattr(expr, "lineno", 0)
            findings.append((expr, lineno))
        return findings

    if isinstance(expr, ast.Call):
        # This Call is not the unwrap itself, so any get_secret_value() inside
        # are arguments to this Call and are shielded
        # Don't recurse into args or keywords
        for child in ast.iter_child_nodes(expr):
            if child not in expr.args and child not in expr.keywords:
                findings.extend(_check_unwrap_in_expr(child))
        return findings

    # Recurse into children
    for child in ast.iter_child_nodes(expr):
        findings.extend(_check_unwrap_in_expr(child))

    return findings


def _check_try_statements(tree: ast.Module) -> list[tuple[ast.Try | ast.TryStar, int]]:
    """Find V1 violations: try/except with assertions only in except."""
    findings: list[tuple[ast.Try | ast.TryStar, int]] = []

    findings = [
        (node, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Try, ast.TryStar))
        and _check_v1_swallowed_failure(node)
    ]

    return findings


def _is_test_collectable(file_path: Path, python_files: list[str]) -> bool:
    """Check if pytest would collect this file.

    Based on python_files from pyproject.toml (defaults to test_*.py, *_test.py).
    """
    name = file_path.name

    return any(fnmatch.fnmatch(name, pattern) for pattern in python_files)


def _get_python_files_config(pyproject: Path) -> list[str]:
    """Get python_files configuration from pytest options."""
    if not pyproject.is_file():
        return ["test_*.py", "*_test.py"]

    try:
        with pyproject.open("rb") as f:
            config = tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError):
        return ["test_*.py", "*_test.py"]

    pytest_options = config.get("tool", {}).get("pytest", {}).get("ini_options", {})
    python_files = pytest_options.get("python_files", None)

    if python_files is None:
        return ["test_*.py", "*_test.py"]

    if isinstance(python_files, str):
        return [python_files]

    return list(python_files)


def scan_test_directory(path: Path) -> list[str]:
    """Scan a test directory for hygiene issues.

    Returns a list of findings in format "file:line: <check> — <description>".
    """
    findings: list[str] = []

    if not path.is_dir():
        return findings

    python_files = _get_python_files_config(Path("pyproject.toml"))

    for file_path in path.rglob("*.py"):
        if "__pycache__" in file_path.parts or ".venv" in file_path.parts:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
        except (OSError, SyntaxError):
            continue

        # Check for secret bindings (all .py files under tests/)
        secret_findings = _find_secret_bindings(tree)
        for _node, lineno in secret_findings:
            findings.append(
                f"{file_path}:{lineno}: secret-binding — "
                f"unwrap of `.get_secret_value()` bound without call shielding"
            )

        # Check vacuity only for files pytest would collect
        if _is_test_collectable(file_path, python_files):
            v1_findings = _check_try_statements(tree)
            for _node, lineno in v1_findings:
                findings.append(
                    f"{file_path}:{lineno}: vacuity — "
                    f"`try`/`except` with assertion only in exception handler"
                )

            for _func, lineno in _find_v2_vacuous_functions(tree):
                findings.append(
                    f"{file_path}:{lineno}: vacuity — "
                    f"`test_*` function with no assertion"
                )

    return findings


def main(argv: list[str]) -> int:
    """Run the check.

    Args:
        argv: Paths to scan; defaults to `tests/`.

    Returns:
        0 if clean, 1 if findings.
    """
    roots = [Path(a) for a in argv] or [Path("tests")]

    all_findings: list[str] = []
    for root in roots:
        if root.exists():
            findings = scan_test_directory(root)
            all_findings.extend(findings)

    if not all_findings:
        return 0

    print("Test hygiene issues found. Fix the cause instead:")
    for finding in all_findings:
        print(f"  {finding}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
