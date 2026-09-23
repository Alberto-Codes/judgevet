"""Execute exact tutorial and staged-review continuation commands offline.

Examples:
    Run through the parent, which prepares the isolated environment:

    ```bash
    uv run python -m scripts.check_doc_python
    ```

See Also:
    - [judgevet.adapters.inbound.cli][]: Staged-review command contract.
"""

import json
import os
import shutil
import sys
from pathlib import Path

from scripts.doc_cli_child import execute, verify
from scripts.smoke_release import run_process


def check_staged(command: str, directory: Path) -> int:
    """Run clean, met and unmet staged changes with the documented script.

    Args:
        command: Exact shell block from the staged-review guide.
        directory: Temporary directory containing all three checkout example files.

    Returns:
        Number of verified command outcomes.

    Raises:
        ValueError: If Git setup or any documented outcome fails.
        RuntimeError: If Git is unavailable.
    """
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("Git is required for staged documentation checks")
    environment = {"PATH": os.defpath, "GIT_CONFIG_NOSYSTEM": "1"}
    if run_process([git, "init", "-q"], environment, directory).returncode:
        raise ValueError("temporary Git initialization failed")
    clean = execute(command, directory, 0.85, 200)
    if clean.returncode or clean.stdout or "No staged changes" not in clean.stderr:
        raise ValueError("clean staged-review outcome differs")
    (directory / "sample.txt").write_text("Synthetic staged content\n")
    if run_process([git, "add", "sample.txt"], environment, directory).returncode:
        raise ValueError("temporary Git staging failed")
    for probability, expected in ((0.85, 0), (0.79, 3)):
        verify(execute(command, directory, probability, 200), "policy", expected)
    return 3


def check_tutorial(
    command: str, filename: str, program: str, expected: str, directory: Path
) -> int:
    """Run the exact saved program via the exact documented shell invocation.

    Args:
        command: Shell continuation block.
        filename: Documented saved program name.
        program: Exact Python block body.
        expected: Expected stdout for the deterministic fixture.
        directory: Fresh isolated tutorial directory.

    Returns:
        One verified invocation.

    Raises:
        ValueError: If command status or output does not match the tutorial.
    """
    (directory / filename).write_text(program)
    (directory / ".venv").symlink_to(Path(sys.prefix), target_is_directory=True)
    bootstrap = directory / "bootstrap"
    bootstrap.mkdir()
    shutil.copy(
        Path(__file__).with_name("doc_tutorial_bootstrap.py"),
        bootstrap / "sitecustomize.py",
    )
    result = execute(command, directory, 0.85, 200, bootstrap=bootstrap)
    if result.returncode or result.stderr or result.stdout != expected:
        raise ValueError(f"tutorial command/output differs (exit {result.returncode})")
    return 1


def main() -> int:
    """Run prepared continuation jobs inside the installed-wheel environment.

    Returns:
        Zero if every continuation succeeds, otherwise one.
    """
    jobs = json.loads(Path("continuations.json").read_text())
    for index, job in enumerate(jobs):
        directory = Path(f"continuation_{index}").resolve()
        directory.mkdir()
        try:
            if job["kind"] == "staged":
                for name, content in job["files"].items():
                    (directory / name).write_text(content)
                check_staged(job["command"], directory)
            else:
                check_tutorial(
                    job["command"],
                    job["filename"],
                    job["program"],
                    job["expected"],
                    directory,
                )
        except (OSError, ValueError, RuntimeError) as error:
            print(f"{job['label']}: {type(error).__name__}: {error}")
            return 1
    print(f"Documentation continuations: {len(jobs)} exact commands passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
