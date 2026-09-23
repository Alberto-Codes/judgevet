"""Exercise the artifact detector with missing exports and broken examples."""

import sys
from pathlib import Path

import pytest

import judgevet
from scripts.policy_artifact_check import check_surface
from scripts.smoke_policy_release import run_examples


def test_surface_accepts_original_objects() -> None:
    assert check_surface() is None


def test_surface_rejects_missing_export(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(judgevet, "SystemOnePort")
    with pytest.raises(RuntimeError, match="SystemOnePort"):
        check_surface()


def test_surface_rejects_replaced_export(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(judgevet, "SystemOnePort", object)
    with pytest.raises(RuntimeError, match="SystemOnePort"):
        check_surface()


@pytest.mark.parametrize(
    "code,expected",
    [("assert 2 + 2 == 4", 0), ("raise RuntimeError('broken example')", 1)],
)
def test_examples_execute(code: str, expected: int, tmp_path: Path) -> None:
    assert run_examples(Path(sys.executable), [code], tmp_path) == expected


def test_empty_examples_fail(tmp_path: Path) -> None:
    assert run_examples(Path(sys.executable), [], tmp_path) == 1
