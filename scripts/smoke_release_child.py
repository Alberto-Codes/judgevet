"""Venv-side program for smoke_release.py.

This module runs under the venv interpreter and performs the checks that
require the built wheel:

- import guard: judgevet.__file__ must be under site-packages
- every name in __all__ resolves
- extract fenced blocks from judgevet.__doc__
- substitute the real API key from the environment
- run the sync example
- run the async example under asyncio.run

All failures are reported as named errors; the orchestrator collects them.

Attributes:
    __doc__ (str | None): This module's docstring, which carries no examples.

Examples:
    Running the self-test:

    ```python
    # uv run python scripts/smoke_release_child.py --selftest
    ```

    Running the offline checks (requires judgevet installed in venv):

    ```python
    # /path/to/venv/bin/python scripts/smoke_release_child.py
    ```

See Also:
    - [judgevet][]: The package being smoke-tested
    - [scripts.smoke_release][]: The orchestrator that invokes this child script
"""

import asyncio
import os
import re
import subprocess
import sys
import sysconfig
import tempfile
import textwrap
from pathlib import Path
from typing import Any

_NUM_PYTHON_BLOCKS = 2


def assert_in_site_packages() -> None:
    """Verify resolved imports belong to this interpreter's install directories.

    Raises:
        RuntimeError: If the imported file is not below a resolved purelib or
            platlib directory within the interpreter's environment.
    """
    module = __get_judgevet_module()
    module_file = Path(module.__file__).resolve()
    prefix = Path(sys.prefix).resolve()
    paths = sysconfig.get_paths()

    for key in ("purelib", "platlib"):
        raw = paths.get(key)
        if not isinstance(raw, str) or not raw:
            continue
        root = Path(raw)
        if not root.is_absolute():
            continue
        root = root.resolve()
        if (
            root != prefix
            and root.is_relative_to(prefix)
            and module_file.is_relative_to(root)
        ):
            return

    raise RuntimeError(
        f"judgevet imported from {module_file}, not under interpreter install directories"
    )


def assert_all_names_resolve() -> None:
    """Assert every name in judgevet.__all__ is importable from judgevet.

    Raises:
        AttributeError: If any name in __all__ cannot be imported from
            judgevet.
    """
    judgevet_module = __get_judgevet_module()
    for name in judgevet_module.__all__:
        if not hasattr(judgevet_module, name):
            raise AttributeError(
                f"judgevet.__all__ contains {name!r} which is not present"
            )


def extract_python_blocks(docstring: str | None) -> list[str]:
    """Extract all ```python blocks from a docstring.

    Args:
        docstring: The docstring to parse.

    Returns:
        A list of Python code strings, one per fenced block.

    Raises:
        ValueError: If docstring is None.
    """
    if docstring is None:
        raise ValueError("Package docstring is None")
    # The fences are indented, because the examples live inside a Google-style
    # `Examples:` section. A pattern anchored at column 0 matches nothing on
    # any real docstring, which is how this gate ran for a release without
    # ever executing an example. Allow leading whitespace on the closing
    # fence, then dedent -- an indented block is an IndentationError at exec.
    pattern = r"```python[ \t]*\n(.*?)^[ \t]*```"
    found = re.findall(pattern, docstring, re.DOTALL | re.MULTILINE)
    return [textwrap.dedent(block) for block in found]


def count_await_blocks(blocks: list[str]) -> int:
    """Count how many blocks contain the word 'await'.

    Args:
        blocks: A list of Python code strings.

    Returns:
        The count of blocks containing 'await'.
    """
    return sum(1 for b in blocks if "await" in b)


def check_placeholder_present(blocks: list[str]) -> None:
    """Assert both blocks contain the placeholder 'your-api-key'.

    Args:
        blocks: A list of Python code strings.

    Raises:
        ValueError: If any block does not contain the placeholder.
    """
    for i, block in enumerate(blocks):
        if "your-api-key" not in block:
            raise ValueError(f"Block {i} does not contain 'your-api-key' placeholder")


def substitute_key(blocks: list[str], key: str) -> list[str]:
    """Replace 'your-api-key' with the real key in each block.

    Args:
        blocks: A list of Python code strings.
        key: The real API key to substitute.

    Returns:
        A list of modified Python code strings.
    """
    return [b.replace("your-api-key", key) for b in blocks]


def run_sync_block(code: str) -> None:
    """Execute a sync example block.

    Args:
        code: The Python code to execute.

    Raises:
        Exception: Any exception raised by exec.
    """
    exec(code, {"__name__": "__main__"})


async def run_async_block(code: str) -> None:
    """Execute an async example block under asyncio.run.

    Args:
        code: The Python code to execute.

    Raises:
        Exception: Any exception raised by the async execution.
    """
    # Wrap in an async def and call it
    wrapped = (
        "async def __tmp_async():\n"
        + "\n".join(
            f"    {line}" if line.strip() else line for line in code.split("\n")
        )
        + "\n"
    )
    # Any, not object: exec defines __tmp_async at runtime, so its type is
    # genuinely unknown to the checker. Narrowing to object and silencing the
    # await is the same claim with a suppression attached.
    local_ns: dict[str, Any] = {}
    exec(wrapped, {"__name__": "__main__"}, local_ns)
    await local_ns["__tmp_async"]()


def _dispatch_block(code: str) -> tuple[str, str | None]:
    """Execute a code block and return (type, failure_message | None).

    Args:
        code: The Python code to execute.

    Returns:
        A tuple of (block_type, failure_message). block_type is 'sync' or
        'async'. failure_message is None on success or the exception's class
        name and message on failure.
    """
    if "await" in code:
        result = _run_async_block_safe(code)
        return ("async", result)
    else:
        result = _run_sync_block_safe(code)
        return ("sync", result)


def _run_sync_block_safe(code: str) -> str | None:
    """Run a sync block, returning None on success or an error message.

    Args:
        code: The Python code to execute.

    Returns:
        None on success, or a formatted error message on failure.
    """
    try:
        run_sync_block(code)
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    return None


def _run_async_block_safe(code: str) -> str | None:
    """Run an async block, returning None on success or an error message.

    Args:
        code: The Python code to execute.

    Returns:
        None on success, or a formatted error message on failure.
    """
    try:
        asyncio.run(run_async_block(code))
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    return None


def run_live_checks(api_key: str) -> list[str]:
    """Run the live examples and return a list of failure messages.

    Args:
        api_key: The real API key from the environment.

    Returns:
        A list of failure messages; empty if all pass.
    """
    failures: list[str] = []
    judgevet_module = __get_judgevet_module()
    docstring = judgevet_module.__doc__
    blocks = extract_python_blocks(docstring)

    # Layout checks: report but do not return early
    if len(blocks) != _NUM_PYTHON_BLOCKS:
        failures.append(
            f"Expected {_NUM_PYTHON_BLOCKS} python blocks, found "
            f"{len(blocks)} in judgevet.__doc__"
        )

    if count_await_blocks(blocks) != 1:
        failures.append(
            f"Expected exactly 1 block with 'await', found {count_await_blocks(blocks)}"
        )

    # A malformed block must not prevent valid examples from running.
    for i, block in enumerate(blocks):
        try:
            check_placeholder_present([block])
        except ValueError:
            failures.append(f"Block {i} missing key placeholder")
            continue
        block_type, failure = _dispatch_block(substitute_key([block], api_key)[0])
        if failure is not None:
            failures.append(f"{block_type} example {i} failed: {failure}")

    return failures


def check_console(command: list[str] | None = None) -> str | None:
    """Run console check for judgevet executable.

    Args:
        command: Command list to execute. If None, uses default judgevet --help.

    Returns:
        None if command exits with 0; error string otherwise.
    """
    if command is None:
        command = [str(Path(sys.executable).absolute().parent / "judgevet"), "--help"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return "judgevet --help executable unavailable"
    if result.returncode == 0:
        return None
    return f"judgevet --help failed with exit code {result.returncode}"


def _selftest_console_cases() -> list[tuple[str, str | None]]:
    """Generate console detector selftest cases.

    Returns:
        Case labels paired with selftest failures, or None when a case passes.
    """
    cases = []

    # Nonzero exit case
    finding = check_console([sys.executable, "-c", "raise SystemExit(7)"])
    cases.append(
        (
            "console nonzero exit",
            None if finding is not None else "Expected console failure did not occur",
        )
    )

    # Missing executable case
    with tempfile.TemporaryDirectory() as tmpdir:
        missing_path = str(Path(tmpdir) / "nonexistent_executable_xyz123")
        finding = check_console([missing_path, "--help"])
        cases.append(
            (
                "console missing executable",
                None
                if finding is not None
                else "Expected console failure did not occur",
            )
        )

    # Success case
    finding = check_console([sys.executable, "-c", "pass"])
    cases.append(("console success", finding))

    return cases


def run_checks_offline() -> list[str]:
    """Run all checks that do not require an API key.

    Returns:
        A list of failure messages.
    """
    failures: list[str] = []

    # Import guard
    try:
        assert_in_site_packages()
    except RuntimeError as e:
        failures.append(f"Import guard failed: {e}")

    # All names resolve
    try:
        assert_all_names_resolve()
    except AttributeError as e:
        failures.append(f"__all__ check failed: {e}")

    finding = check_console()
    if finding is not None:
        failures.append(finding)

    return failures


def _selftest_sync_example_runner() -> str | None:
    """Run self-test case for sync example runner.

    Returns:
        Failure message if the detector did not fire, None otherwise.
    """
    broken_code = "raise RuntimeError('intentional failure')"
    try:
        run_sync_block(broken_code)
    except RuntimeError:
        return None
    return "Expected failure did not occur"


async def _selftest_async_example_runner() -> str | None:
    """Run self-test case for async example runner.

    Returns:
        Failure message if the detector did not fire, None otherwise.
    """
    try:
        await run_async_block("raise RuntimeError('intentional failure')")
    except RuntimeError:
        return None
    return "Expected failure did not occur"


def _selftest_import_guard() -> str | None:
    """Run self-test case for import guard.

    Returns:
        Failure message if the detector did not fire, None otherwise.
    """
    original_prefix = sys.prefix
    try:
        sys.prefix = "/nonexistent"
        try:
            assert_in_site_packages()
        except RuntimeError:
            return None
    finally:
        sys.prefix = original_prefix
    return "Expected failure did not occur"


def _selftest_placeholder_check() -> str | None:
    """Run self-test case for placeholder check.

    Returns:
        Failure message if the detector did not fire, None otherwise.
    """
    blocks_without_placeholder = ['print("no key here")']
    try:
        check_placeholder_present(blocks_without_placeholder)
    except ValueError:
        return None
    return "Expected failure did not occur"


def _selftest_assert_all_names_resolve() -> str | None:
    """Run self-test case for assert_all_names_resolve.

    Returns:
        Failure message if the detector did not fire, None otherwise.
    """
    real_getter = __get_judgevet_module

    class FakeModule:
        __all__ = ("__selftest_missing_name__",)

    def fake_getter() -> FakeModule:
        return FakeModule()

    try:
        globals()["__get_judgevet_module"] = fake_getter
        assert_all_names_resolve()
    except AttributeError:
        return None
    finally:
        globals()["__get_judgevet_module"] = real_getter
    return "Expected failure did not occur"


def _selftest_count_await_blocks() -> str | None:
    """Run self-test case for count_await_blocks.

    Returns:
        Failure message if the detector did not fire, None otherwise.
    """
    blocks_with_await = ["await foo()"]
    result = count_await_blocks(blocks_with_await)
    if result != 1:
        return f"Expected 1, got {result}"
    return None


def selftest() -> list[str]:
    """Run every selftest case and report which detectors fired.

    Each case calls the detector named in its own label with input that must
    trip it. A case that reports no failure means its detector did not fire,
    which is the failure. The total is derived from the case list, never
    written down.

    Returns:
        A list of failure messages; empty if every detector fired.
    """
    cases: list[tuple[str, str | None]] = []
    cases.append(("sync example runner", _selftest_sync_example_runner()))
    cases.append(("import guard", _selftest_import_guard()))
    cases.append(("placeholder check", _selftest_placeholder_check()))
    cases.append(
        ("async example runner", asyncio.run(_selftest_async_example_runner()))
    )
    cases.append(("all names resolve", _selftest_assert_all_names_resolve()))
    cases.append(("await block count", _selftest_count_await_blocks()))
    cases.extend(_selftest_console_cases())

    failures = [f"Selftest ({label}): {msg}" for label, msg in cases if msg is not None]
    print(
        f"selftest: {len(cases) - len(failures)}/{len(cases)} detectors fired as expected"
    )
    for f in failures:
        print(f"  FAILED: {f}")

    return failures


def __get_judgevet_module() -> Any:
    """Import and return the judgevet module from the venv.

    This helper ensures judgevet is imported from the venv's site-packages
    rather than the parent environment, even if this script is run in a
    parent environment context.

    Returns:
        The judgevet module object.
    """
    import judgevet

    return judgevet


def main(argv: list[str]) -> int:
    """Run the in-venv checks, or the selftest.

    Without an entry point the module defined these functions and exited 0,
    so `--selftest` reported success while running nothing — the same shape
    of vacuity this script exists to detect.

    Args:
        argv: Arguments after the program name. `--selftest` runs the
            detector sabotage suite; anything else runs the real checks.

    Returns:
        0 when every check passed, 1 otherwise.
    """
    if "--selftest" in argv:
        return 1 if selftest() else 0

    key = os.environ.get("TYPESAFE_API_KEY")
    failures = run_checks_offline()
    if key:
        failures.extend(run_live_checks(key))
    else:
        failures.append(
            "TYPESAFE_API_KEY is not set, so the documented examples were "
            "never run. This is a failure, not a skip: a smoke test that "
            "silently skips at a publish gate reports green for an "
            "artifact nobody exercised."
        )

    for f in failures:
        print(f"  FAILED: {f}")
    print(f"smoke: {'ok' if not failures else f'{len(failures)} failure(s)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
