"""Build an isolated wheel and execute/type-check exact user-doc Python blocks.

Examples:
    Run ``uv run python -m scripts.check_doc_python`` from the checkout.

See Also:
    - [judgevet][]: Installed package under test.
"""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from scripts.doc_cli_prepare import prepare_cli, prepare_continuations
from scripts.doc_example_inventory import discover, validate
from scripts.smoke_release import (
    build_wheel,
    create_venv,
    install_wheel,
    probe_import,
    run_child,
)
from scripts.smoke_release_child import check_console, extract_python_blocks


def prepare(root: Path, workdir: Path) -> list[Path]:
    """Extract classified Python programs without rewriting their text.

    Args:
        root: Documentation source root.
        workdir: Isolated execution directory.

    Returns:
        Written example files in source order.

    Raises:
        ValueError: If inventory or extraction is empty or inconsistent.
    """
    manifest = root / "scripts/doc_examples.json"
    validate(root, manifest)
    records = json.loads(manifest.read_text())
    jobs = []
    for page, blocks in discover(root).items():
        python_blocks = [block for block in blocks if block.language == "python"]
        for entry in records[page]:
            if entry["language"] == "python" and entry["kind"] != "runnable":
                raise ValueError(
                    f"{page}: Python classification needs an explicit runner"
                )
        extracted = extract_python_blocks((root / page).read_text())
        if extracted != [block.text for block in python_blocks]:
            raise ValueError(f"{page}: Python extraction differs from exact inventory")
        for block in python_blocks:
            path = workdir / f"example_{len(jobs)}.py"
            path.write_text(block.text)
            jobs.append({"file": str(path), "label": f"{page}:{block.line}"})
    if not jobs:
        raise ValueError("empty Python example inventory")
    (workdir / "python_examples.json").write_text(json.dumps(jobs))
    return [Path(job["file"]) for job in jobs]


def check(root: Path, workdir: Path) -> int:
    """Use existing artifact helpers to build, install, execute and type-check.

    Args:
        root: Documentation root, optionally a copied tree for mutation proofs.
        workdir: Fresh temporary directory outside the checkout.

    Returns:
        Zero only when every execution and typing check passes.

    Raises:
        RuntimeError: If build, installation or import isolation fails.
        ValueError: If example inventory is invalid.
    """
    paths = prepare(root, workdir)
    prepare_cli(root, workdir)
    prepare_continuations(root, workdir)
    wheel = build_wheel(workdir / "dist")
    python = create_venv(workdir)
    install_wheel(python, wheel)
    environment = {"PATH": str(python.parent)}
    probe_import(python, environment, workdir)
    (workdir / "scripts").mkdir()
    shutil.copy(Path(__file__).with_name("doc_python_child.py"), workdir)
    shutil.copy(Path(__file__).with_name("smoke_release_child.py"), workdir / "scripts")
    if run_child(python, workdir / "doc_python_child.py", environment, workdir):
        return 1
    if run_shell_checks(python, environment, workdir):
        return 1
    checker = shutil.which("ty")
    if checker is None:
        raise RuntimeError("ty is required for documentation typing checks")
    command = [checker, "check", "--project", str(workdir), "--python", str(python)]
    command.extend(map(str, paths))
    finding = check_console(command)
    if finding:
        print(finding)
        return 1
    print(f"Python documentation: {len(paths)} isolated programs type-checked")
    return 0


def run_shell_checks(python: Path, environment: dict[str, str], workdir: Path) -> int:
    """Run CLI and continuation helpers with the same isolated installation.

    Args:
        python: Installed-wheel interpreter.
        environment: Controlled child environment.
        workdir: Prepared execution directory.

    Returns:
        One if either shell workflow check fails, otherwise zero.
    """
    for name in ("smoke_release.py", "doc_cli_child.py"):
        shutil.copy(Path(__file__).with_name(name), workdir / "scripts")
    for name in (
        "doc_cli_child.py",
        "doc_continuations.py",
        "doc_tutorial_bootstrap.py",
    ):
        shutil.copy(Path(__file__).with_name(name), workdir)
    environment["PATH"] += ":/usr/bin:/bin"
    for name in ("doc_cli_child.py", "doc_continuations.py"):
        if run_child(python, workdir / name, environment, workdir):
            return 1
    return 0


def main() -> int:
    """Check current documentation with a freshly built artifact.

    Returns:
        The execution status, or one for a setup/inventory failure.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix="judgevet-doc-python-") as directory:
            return check(args.root.resolve(), Path(directory))
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Python documentation: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
