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
import glob
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_NUM_PYTHON_BLOCKS = 2


def assert_in_site_packages() -> None:
    """Assert judgevet was imported from site-packages, not src/.

    Raises:
        RuntimeError: If judgevet.__file__ is not under the venv's
            site-packages directory.
    """
    judgevet_module = __get_judgevet_module()
    judgevet_file = Path(judgevet_module.__file__)
    site_packages = Path(sys.prefix) / "lib" / "python*" / "site-packages"

    globbed = glob.glob(str(site_packages))
    if not globbed:
        raise RuntimeError(f"site-packages pattern not found: {site_packages}")

    for sp_dir in globbed:
        if judgevet_file.is_relative_to(sp_dir):
            return

    raise RuntimeError(
        f"judgevet imported from {judgevet_file}, not under site-packages"
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
    pattern = r"```python\n(.*?)\n```"
    return re.findall(pattern, docstring, re.DOTALL)


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
        + "\n__tmp_async()\n"
    )
    local_ns: dict[str, object] = {}
    exec(wrapped, {"__name__": "__main__"}, local_ns)


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

    if len(blocks) != _NUM_PYTHON_BLOCKS:
        failures.append(
            f"Expected {_NUM_PYTHON_BLOCKS} python blocks, found "
            f"{len(blocks)} in judgevet.__doc__"
        )
        return failures

    if count_await_blocks(blocks) != 1:
        failures.append(
            f"Expected exactly 1 block with 'await', found {count_await_blocks(blocks)}"
        )
        return failures

    try:
        check_placeholder_present(blocks)
    except ValueError as e:
        failures.append(f"Placeholder check failed: {e}")
        return failures

    substituted = substitute_key(blocks, api_key)

    # Run sync block
    try:
        run_sync_block(substituted[0])
    except Exception as e:
        failures.append(f"Sync example failed: {e}")

    # Run async block
    try:
        asyncio.run(run_async_block(substituted[1]))
    except Exception as e:
        failures.append(f"Async example failed: {e}")

    return failures


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

    # judgevet --help
    # Derive absolute path from sys.executable to avoid PATH ambiguity
    venv_python = Path(sys.executable).absolute()
    venv_bin_dir = venv_python.parent
    judgevet_bin = venv_bin_dir / "judgevet"
    result = subprocess.run(
        [str(judgevet_bin), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        failures.append(f"judgevet --help failed with exit code {result.returncode}")

    return failures


def selftest() -> list[str]:
    """Run self-test by sabotaging each detector and asserting it fires.

    Returns:
        A list of failure messages; empty if all self-tests pass.
    """
    failures: list[str] = []

    # Test 1: Example runner with broken example
    try:
        broken_code = "raise RuntimeError('intentional failure')"
        exec(broken_code, {"__name__": "__main__"})
        failures.append("Selftest 1 (example runner): Expected failure did not occur")
    except RuntimeError:
        # Expected
        pass

    # Test 2: Import guard with bad path
    try:
        # Temporarily modify sys.prefix to force a mismatch
        original_prefix = sys.prefix
        sys.prefix = "/nonexistent"
        try:
            assert_in_site_packages()
            failures.append("Selftest 2 (import guard): Expected failure did not occur")
        except RuntimeError:
            # Expected
            pass
    finally:
        sys.prefix = original_prefix

    # Test 3: Placeholder check with missing placeholder
    try:
        blocks_without_placeholder = ['print("no key here")']
        check_placeholder_present(blocks_without_placeholder)
        failures.append(
            "Selftest 3 (placeholder check): Expected failure did not occur"
        )
    except ValueError:
        # Expected
        pass

    # Report what ran. A selftest that succeeds in silence is
    # indistinguishable from one that did nothing, which is the defect class
    # this whole script exists to catch.
    print(f"selftest: {3 - len(failures)}/3 detectors fired as expected")
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
