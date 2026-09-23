"""Smoke-test a built wheel in isolation.

This module orchestrates a smoke test of the judgevet package by:

1. Building the wheel (or using a pre-built one via --wheel PATH)
2. Creating a fresh venv in a temp directory
3. Installing the wheel into that venv
4. Probing the installed package to prove isolation (import judgevet;
   verify __file__ is under site-packages)
5. Running the child script (smoke_release_child.py) under the isolated venv

The parent constructs the isolation, proves it, and returns the child's exit
status. It does not parse the child's output for the child's results.

Usage:
    smoke_release.py           # build, then run the child
    smoke_release.py --wheel PATH  # test a pre-built wheel

Exit status is 0 if the child's checks passed; 1 otherwise.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Arguments for --wheel mode.
_WHEEL_FLAG = "--wheel"
_WHEEL_ARG_COUNT = 2

# Variables the parent clears to preserve venv isolation.
# PYTHONPATH would let the venv interpreter import src/ from this checkout.
# PYTHONHOME redirects the standard-library lookup and would defeat the venv
# even when it does not touch src/.
_CLEAR_VARS = frozenset(["PYTHONPATH", "PYTHONHOME"])


def _uv() -> str:
    """Resolve uv to an absolute path.

    A bare "uv" is a PATH lookup, and PATH could resolve a uv from anywhere.
    This gate exists to prove one specific artifact works, so the tools it
    runs are named exactly. Resolving once also makes the S607 suppression
    unnecessary rather than suppressed.

    Returns:
        The absolute path to the uv executable.

    Raises:
        RuntimeError: If uv is not on PATH at all.
    """
    found = shutil.which("uv")
    if found is None:
        raise RuntimeError("uv not found on PATH; it is required to build the wheel")
    return found


def _build_wheel_subprocess(out_dir: Path) -> subprocess.CompletedProcess[str]:
    """Run the uv build subprocess.

    Args:
        out_dir: The directory to write the wheel into.

    Returns:
        The completed process result.
    """
    repo_root = Path(__file__).resolve().parent.parent
    return subprocess.run(
        [_uv(), "build", "--out-dir", str(out_dir), "."],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def build_wheel(out_dir: Path) -> Path:
    """Build the wheel and return its path.

    Args:
        out_dir: The directory to write the wheel into.

    Returns:
        The absolute path to the built wheel.

    Raises:
        RuntimeError: If the build fails or yields zero or more than one wheel.
    """
    result = _build_wheel_subprocess(out_dir)

    if result.returncode != 0:
        raise RuntimeError(f"uv build failed:\n{result.stdout}\n{result.stderr}")

    wheels = glob.glob(str(out_dir / "*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(
            f"Expected exactly one wheel, found {len(wheels)}:\n" + "\n".join(wheels)
        )

    return Path(wheels[0]).absolute()


def create_venv(base_dir: Path) -> Path:
    """Create a venv and return the path to its python interpreter.

    Args:
        base_dir: The base directory for the venv (will create base_dir/venv).

    Returns:
        The absolute path to the venv's python interpreter.

    Raises:
        RuntimeError: If venv creation fails.
    """
    venv_dir = base_dir / "venv"
    result = subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(f"venv creation failed:\n{result.stdout}\n{result.stderr}")

    venv_python = venv_dir / "bin" / "python"
    return venv_python.absolute()


def install_wheel(venv_python: Path, wheel: Path, extras: tuple[str, ...] = ()) -> None:
    """Install the wheel into the venv.

    Args:
        venv_python: The path to the venv's python interpreter.
        wheel: The path to the wheel to install.
        extras: Optional extras to install for a separate adapter check.

    Raises:
        RuntimeError: If the install fails.
    """
    result = subprocess.run(
        [
            _uv(),
            "pip",
            "install",
            "--python",
            str(venv_python),
            str(wheel) + ("[" + ",".join(extras) + "]" if extras else ""),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(f"uv pip install failed:\n{result.stdout}\n{result.stderr}")


def probe_import(venv_python: Path, child_env: dict, workdir: Path) -> str:
    """Probe the installed package and prove isolation.

    Args:
        venv_python: The path to the venv's python interpreter.
        child_env: The environment dict to use for the probe.
        workdir: The working directory for the probe.

    Returns:
        The printed path from the import probe.

    Raises:
        RuntimeError: If the probe fails or the path is not isolated.
    """
    result = subprocess.run(
        [str(venv_python), "-c", "import judgevet; print(judgevet.__file__)"],
        env=child_env,
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(f"import probe failed:\n{result.stdout}\n{result.stderr}")

    printed_path = result.stdout.strip()

    # Assert the path contains a site-packages part and is under the temp venv.
    venv_dir = venv_python.parent.parent
    path_obj = Path(printed_path)

    if "site-packages" not in printed_path:
        print(
            f"smoke_release: judgevet.__file__ is not under site-packages: {printed_path}"
        )
        raise RuntimeError(
            f"judgevet imported from {printed_path}, not under site-packages"
        )

    if not path_obj.is_relative_to(venv_dir):
        print(
            f"smoke_release: judgevet.__file__ is not under the temp venv: {printed_path}"
        )
        raise RuntimeError(
            f"judgevet imported from {printed_path}, not under {venv_dir}"
        )

    return printed_path


def run_process(
    command: list[str],
    environment: dict[str, str],
    workdir: Path,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run an explicit executable and argument list with captured streams.

    Args:
        command: Executable path and arguments, without shell=True.
        environment: Explicit child environment.
        workdir: Isolated working directory.
        timeout: Optional process deadline in seconds.

    Returns:
        Completed process with its real status and output streams.
    """
    return subprocess.run(
        command,
        env=environment,
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def run_child(
    venv_python: Path, child_path: Path, child_env: dict, workdir: Path
) -> int:
    """Run the child script under the isolated venv.

    Args:
        venv_python: The path to the venv's python interpreter.
        child_path: The absolute path to the child script.
        child_env: The environment dict for the child.
        workdir: The working directory for the child.

    Returns:
        The child's exit status.
    """
    result = run_process([str(venv_python), str(child_path)], child_env, workdir)

    print(result.stdout, end="")
    print(result.stderr, end="")

    return result.returncode


def build_child_env() -> dict:
    """Build the child environment, clearing isolation variables.

    Returns:
        A copy of os.environ minus PYTHONPATH and PYTHONHOME.
    """
    return {k: v for k, v in os.environ.items() if k not in _CLEAR_VARS}


def _print_usage_and_exit() -> int:
    """Print usage information and return 1."""
    print("Usage: smoke_release.py [--wheel PATH]")
    return 1


def _parse_argv(argv: list[str]) -> tuple[Path | None, int]:
    """Parse command line arguments.

    Args:
        argv: The command line arguments.

    Returns:
        A tuple of (wheel_path, exit_code). wheel_path is None if no --wheel.
        exit_code is 0 if parsing succeeded, 1 otherwise.
    """
    if not argv:
        return None, 0

    if len(argv) == 1:
        if argv[0] == _WHEEL_FLAG:
            print(f"Usage: smoke_release.py {_WHEEL_FLAG} PATH")
            print(f"smoke_release: {_WHEEL_FLAG} requires a PATH argument")
            return None, 1
        return None, _print_usage_and_exit()

    if len(argv) == _WHEEL_ARG_COUNT and argv[0] == _WHEEL_FLAG:
        wheel_path = Path(argv[1]).absolute()
        if not wheel_path.is_file():
            print(f"smoke_release: wheel not found: {wheel_path}")
            return None, 1
        return wheel_path, 0

    return None, _print_usage_and_exit()


def _do_smoke_test(wheel_path: Path, temp_dir: str) -> int:
    """Run the smoke test with the given wheel.

    Args:
        wheel_path: The path to the wheel to test.
        temp_dir: The temp directory path.

    Returns:
        The child's exit status.
    """
    try:
        # Create the venv
        venv_python = create_venv(Path(temp_dir))
        print(f"smoke_release: venv: {venv_python}")

        # Install the wheel
        install_wheel(venv_python, wheel_path)

        # Build the child environment
        child_env = build_child_env()

        # Probe the import to prove isolation
        probe_path = probe_import(venv_python, child_env, Path(temp_dir))
        print(f"judgevet.__file__ = {probe_path}")

        # Run the child
        child_path = Path(__file__).resolve().parent / "smoke_release_child.py"
        child_returncode = run_child(venv_python, child_path, child_env, Path(temp_dir))

        # The verdict is the child's, so say the child's word for it. Printing
        # "ok" beside a non-zero exit is how a publish gate gets read as green
        # by someone scanning output rather than checking $?.
        if child_returncode == 0:
            print("smoke_release: PASS — the built artifact passed every in-venv check")
        else:
            print(
                f"smoke_release: FAIL — the child reported failures (exit "
                f"{child_returncode}); the artifact is not publishable"
            )
        return child_returncode

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main(argv: list[str]) -> int:
    """Run the smoke test.

    Args:
        argv: Command line arguments. With --wheel PATH, skip the build and
            test the wheel at PATH. Otherwise, build first.

    Returns:
        The child's exit status, or 1 on parent-side failures.
    """
    wheel_path, exit_code = _parse_argv(argv)
    if exit_code != 0:
        return exit_code

    temp_dir = tempfile.mkdtemp(prefix="judgevet-smoke-")
    print(f"smoke_release: temp dir: {temp_dir}")

    try:
        if wheel_path is None:
            # Build the wheel
            dist_dir = Path(temp_dir) / "dist"
            dist_dir.mkdir()
            wheel_path = build_wheel(dist_dir)
            print(f"smoke_release: wheel: {wheel_path}")
        else:
            print(f"smoke_release: wheel (pre-built): {wheel_path}")

        return _do_smoke_test(wheel_path, temp_dir)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
