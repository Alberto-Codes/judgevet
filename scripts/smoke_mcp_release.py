"""Verify the exact installed MCP wheel before publication.

Examples:
    ```python
    from scripts.smoke_mcp_release import main

    callable(main)
    ```

See Also:
    - [scripts.mcp_smoke_transport][]: Existing transport validation.
"""

import asyncio
import json
import os
import shutil
import sys
import tempfile
from contextlib import chdir
from pathlib import Path

from scripts.mcp_smoke_transport import _cleanup, smoke


async def run_command(
    command: list[str], env: dict[str, str], workdir: Path, timeout: float = 120.0
) -> str:
    """Run a setup command with a bounded lifetime and fixed diagnostics.

    Args:
        command: Absolute executable and arguments.
        env: Copied child environment.
        workdir: External working directory.
        timeout: Total spawn and communication deadline in seconds.

    Returns:
        Decoded stdout, including its trailing newline.

    Raises:
        RuntimeError: Startup, exit, decoding, timeout or cleanup fails.
    """
    process = None
    try:
        async with asyncio.timeout(timeout):
            process = await asyncio.create_subprocess_exec(
                *command,
                env=env,
                cwd=workdir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError("mcp_release: command failed")
        return stdout.decode("utf-8")
    except (OSError, ValueError):
        raise RuntimeError("mcp_release: command failed") from None
    finally:
        if process is not None:
            try:
                await _cleanup(process)
            except RuntimeError:
                raise RuntimeError("mcp_release: cleanup failed") from None


def _probe_version(output: str, venv: Path) -> str:
    """Validate the isolated import probe and return its version.

    Args:
        output: JSON from the installed interpreter import probe.
        venv: Path to the virtual environment root directory.

    Returns:
        The version string extracted from the metadata.

    Raises:
        TypeError: The object or its required fields have wrong types.
        ValueError: JSON, paths or version are invalid.
    """
    data = json.loads(output)
    if not isinstance(data, dict):
        raise TypeError("mcp_release: probe must be an object")
    file_ = data.get("file")
    prefix = data.get("prefix")
    version = data.get("version")

    if (
        not isinstance(file_, str)
        or not isinstance(prefix, str)
        or not isinstance(version, str)
    ):
        raise TypeError(
            "mcp_release: metadata fields file, prefix, and version must be strings"
        )

    if not version.strip():
        raise ValueError("mcp_release: version field must be non-empty after stripping")

    file_path = Path(file_).resolve()
    prefix_path = Path(prefix).resolve()
    venv_path = venv.resolve()

    if prefix_path != venv_path:
        raise ValueError("mcp_release: prefix path does not match venv path")

    if not file_path.is_relative_to(venv_path):
        raise ValueError("mcp_release: file path is not relative to venv path")

    if "site-packages" not in file_path.parts:
        raise ValueError(
            "mcp_release: file path must contain 'site-packages' in its path"
        )

    return version


def _checked_wheel(wheel: Path, env: dict[str, str]) -> Path:
    """Require the live credential and an existing absolute wheel path.

    Args:
        wheel: Supplied artifact path.
        env: Environment containing the credential.

    Returns:
        Resolved path to the supplied wheel.

    Raises:
        RuntimeError: The key or wheel is absent.
    """
    if not env.get("TYPESAFE_API_KEY"):
        raise RuntimeError("mcp_release: missing TYPESAFE_API_KEY")
    resolved = wheel.resolve()
    if not resolved.is_file():
        raise RuntimeError("mcp_release: wheel file not found")
    return resolved


async def check_wheel(wheel: Path, env: dict[str, str]) -> None:
    """Check wheel artifact by validating its MCP server functionality.

    Args:
        wheel: Path to the wheel file to check.
        env: Environment variables to use during verification.

    Raises:
        RuntimeError: If TYPESAFE_API_KEY is missing, wheel doesn't exist,
                     or any artifact check step fails.
    """
    try:
        wheel_resolved = _checked_wheel(wheel, env)
        child_env = {
            k: v for k, v in env.items() if k not in ("PYTHONPATH", "PYTHONHOME")
        }

        with tempfile.TemporaryDirectory(prefix="judgevet-mcp-") as directory:
            workdir = Path(directory).resolve()
            await _exercise(wheel_resolved, child_env, workdir)
    except (RuntimeError, OSError, ValueError, TypeError, KeyError, AttributeError):
        raise RuntimeError("mcp_release: artifact check failed") from None


async def _exercise(wheel: Path, env: dict[str, str], workdir: Path) -> None:
    """Exercise wheel by creating venv, installing package, and testing MCP server.

    Args:
        wheel: Absolute path to the wheel file.
        env: Environment variables for command execution.
        workdir: Working directory for operations.

    Raises:
        RuntimeError: Setup or transport fails.
        TypeError: Probe fields have invalid types.
        ValueError: Probe metadata violates isolation or version requirements.
    """
    checkout_root = Path(__file__).resolve().parent.parent
    if workdir.is_relative_to(checkout_root):
        raise RuntimeError("mcp_release: workdir inside checkout root")
    venv = workdir / "venv"
    interpreter = venv / "bin" / "python"
    executable = venv / "bin" / "judgevet-mcp"

    uv_path = shutil.which("uv")
    if uv_path is None:
        raise RuntimeError("mcp_release: uv not found")
    uv = str(Path(uv_path).absolute())

    await run_command([sys.executable, "-I", "-m", "venv", str(venv)], env, workdir)
    await run_command(
        [uv, "pip", "install", "--python", str(interpreter), f"{wheel}[mcp]"],
        env,
        workdir,
    )

    if not executable.is_file():
        raise RuntimeError("mcp_release: judgevet-mcp executable not found")

    probe_code = (
        "import json,sys,importlib.metadata,judgevet; "
        "print(json.dumps({'file':judgevet.__file__,'prefix':sys.prefix,"
        "'version':importlib.metadata.version('judgevet')}))"
    )

    output = await run_command([str(interpreter), "-I", "-c", probe_code], env, workdir)
    version = _probe_version(output, venv)

    with chdir(workdir):
        await smoke([str(executable)], version, env)


_WHEEL_ARGUMENT_COUNT = 2


def _wheel_argument(argv: list[str]) -> Path:
    """Parse the required wheel-only invocation.

    Args:
        argv: Command-line arguments.

    Returns:
        Absolute wheel path.

    Raises:
        ValueError: Arguments do not name an existing wheel.
    """
    if len(argv) != _WHEEL_ARGUMENT_COUNT or argv[0] != "--wheel":
        raise ValueError("invalid arguments")
    wheel = Path(argv[1]).absolute()
    if wheel.suffix != ".whl" or not wheel.is_file():
        raise ValueError("invalid wheel")
    return wheel


def main(argv: list[str]) -> int:
    """Validate a supplied wheel and print only its fixed verdict.

    Args:
        argv: Exactly --wheel followed by an existing wheel path.

    Returns:
        Zero on success and one on usage or artifact failure.
    """
    try:
        wheel = _wheel_argument(argv)
        asyncio.run(check_wheel(wheel, os.environ.copy()))
    except (RuntimeError, OSError, ValueError):
        print("mcp_release: FAIL")
        return 1
    print("mcp_release: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
