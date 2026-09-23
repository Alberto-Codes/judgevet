"""Acceptance checks for staged-review and tutorial continuation commands."""

import importlib
import shutil
from pathlib import Path

import pytest


def test_staged_command_exercises_clean_and_policy_paths(tmp_path: Path) -> None:
    checker = importlib.import_module("scripts.doc_continuations")
    for path in Path("examples/staged-review").iterdir():
        if path.is_file():
            shutil.copy(path, tmp_path)
    assert checker.check_staged("bash ./review-staged.sh\n", tmp_path) == 3


def test_wrong_tutorial_filename_fails(tmp_path: Path) -> None:
    checker = importlib.import_module("scripts.doc_continuations")
    with pytest.raises(ValueError, match="tutorial"):
        checker.check_tutorial(
            ".venv/bin/python missing.py\n",
            "first_policy.py",
            "print('ok')\n",
            "ok\n",
            tmp_path,
        )


def test_tutorial_runs_exact_saved_program(tmp_path: Path) -> None:
    checker = importlib.import_module("scripts.doc_continuations")
    assert (
        checker.check_tutorial(
            ".venv/bin/python first_policy.py\n",
            "first_policy.py",
            "print('ok')\n",
            "ok\n",
            tmp_path,
        )
        == 1
    )
