"""Run and type-check exact policy guide examples against an isolated wheel.

Usage: uv run python -m scripts.smoke_policy_release --wheel /absolute/file.whl
The guide's live examples require the approved TYPESAFE_API_KEY environment.
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from scripts.smoke_release import (
    build_child_env,
    create_venv,
    install_wheel,
    probe_import,
    run_child,
)
from scripts.smoke_release_child import check_console, extract_python_blocks


def run_examples(python: Path, blocks: list[str], workdir: Path) -> int:
    """Write and execute every exact documentation example outside the checkout.

    Args:
        python: Isolated interpreter.
        blocks: Extracted guide examples.
        workdir: Isolated working directory.

    Returns:
        Zero if all examples execute successfully, otherwise one.
    """
    if not blocks:
        print("Policy guide has no executable examples")
        return 1
    failures = 0
    for index, block in enumerate(blocks):
        path = workdir / f"example_{index}.py"
        path.write_text(block)
        failures += run_child(python, path, build_child_env(), workdir) != 0
    return 1 if failures else 0


def check_wheel(wheel: Path, guide: Path, workdir: Path) -> int:
    """Install a wheel and run its import, example and typing checks.

    Args:
        wheel: Exact candidate or downloaded wheel.
        guide: Policy guide containing runnable Python blocks.
        workdir: Temporary directory outside checkout.

    Returns:
        Zero only when installation, execution and typing checks pass.
    """
    python = create_venv(workdir)
    install_wheel(python, wheel)
    probe_import(python, build_child_env(), workdir)
    child = Path(__file__).with_name("policy_artifact_check.py").resolve()
    if run_child(python, child, build_child_env(), workdir):
        return 1
    blocks = extract_python_blocks(guide.read_text())
    if run_examples(python, blocks, workdir):
        return 1
    checker = shutil.which("ty")
    if checker is None:
        print("Policy artifact typing check requires ty on PATH")
        return 1
    command = [checker, "check", "--project", str(workdir), "--python", str(python)]
    command.extend(str(workdir / f"example_{index}.py") for index in range(len(blocks)))
    finding = check_console(command)
    if finding:
        print("Policy artifact typing failed")
        return 1
    print(f"Policy artifact: {len(blocks)} exact examples executed and type-checked")
    return 0


def main(argv: list[str]) -> int:
    """Check the selected wheel against the policy guide.

    Args:
        argv: Wheel path and optional guide override for independent failure proof.

    Returns:
        The isolated artifact check's exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument(
        "--guide", type=Path, default=Path("docs/how-to/use-policy-library.md")
    )
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="judgevet-policy-artifact-") as directory:
        return check_wheel(args.wheel.resolve(), args.guide.resolve(), Path(directory))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
