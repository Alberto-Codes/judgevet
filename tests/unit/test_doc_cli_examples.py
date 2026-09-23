"""Acceptance checks for exact shell examples against an offline CLI service."""

import importlib
from pathlib import Path

import pytest


def invoke(tmp_path: Path, command: str, probability: float = 0.85):
    """Run the actual shell executor with complete synthetic local inputs."""
    runner = importlib.import_module("scripts.doc_cli_child")
    (tmp_path / "document.txt").write_text("Synthetic text")
    (tmp_path / "questions.json").write_text('{"clear":{"type":"noul"}}')
    (tmp_path / "policy.json").write_text(
        '{"rules":[{"question":"clear","pass":{"noul":{"min":0.8}}}]}'
    )
    return runner.execute(command, tmp_path, probability, 200)


@pytest.mark.parametrize(("probability", "status"), [(0.85, 0), (0.79, 3)])
def test_policy_example_preserves_exit_and_answer(
    tmp_path: Path, probability: float, status: int
) -> None:
    result = invoke(
        tmp_path,
        "judgevet --state-file document.txt --questions-file questions.json "
        "--policy policy.json --json",
        probability,
    )
    assert result.returncode == status
    assert '"policy"' in result.stdout
    assert not result.stderr


def test_invalid_documented_option_is_rejected(tmp_path: Path) -> None:
    result = invoke(tmp_path, "judgevet --not-a-supported-option")
    assert result.returncode == 2
    assert result.stderr


def test_exact_pipe_reaches_cli(tmp_path: Path) -> None:
    result = invoke(
        tmp_path,
        "printf 'Synthetic text' | judgevet --state-file - "
        "--questions-file questions.json --json",
    )
    assert result.returncode == 0
    assert '"clear"' in result.stdout
