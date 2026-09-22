"""Prove console detection and selftest sensitivity without a key or network.

Examples:
    Run the offline regressions::

        uv run pytest -q tests/unit/test_console_smoke.py

See Also:
    - [scripts.smoke_release_child][]: Shared detector and production wiring.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from scripts import smoke_release_child as child

pytestmark = pytest.mark.unit


def test_real_success() -> None:
    """A real successful child yields no finding."""
    assert child.check_console([sys.executable, "-c", "pass"]) is None


def test_real_nonzero() -> None:
    """A real failed child yields the existing named finding."""
    assert child.check_console([sys.executable, "-c", "raise SystemExit(7)"]) == (
        "judgevet --help failed with exit code 7"
    )


def test_real_missing(tmp_path: Path) -> None:
    """An absent executable produces a finding instead of escaping."""
    assert child.check_console([str(tmp_path / "absent")]) == (
        "judgevet --help executable unavailable"
    )


def test_default_uses_installed_absolute_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Observe the argv actually sent by the production default."""
    calls: list[tuple[list[str], dict[str, object]]] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(child.subprocess, "run", run)
    assert child.check_console() is None
    assert calls == [
        (
            [str(Path(sys.executable).absolute().parent / "judgevet"), "--help"],
            {"capture_output": True, "text": True, "check": False},
        )
    ]


def test_offline_checks_invoke_shared_detector(monkeypatch: pytest.MonkeyPatch) -> None:
    """The production caller consumes the same detector selftest sabotages."""
    calls: list[list[str] | None] = []

    def detector(command: list[str] | None = None) -> str:
        calls.append(command)
        return "console-sentinel"

    monkeypatch.setattr(child, "check_console", detector)
    findings = child.run_checks_offline()
    assert calls == [None]
    assert "console-sentinel" in findings


def test_nine_healthy_cases(capsys: pytest.CaptureFixture[str]) -> None:
    """Preserve six cases and execute three new console cases."""
    assert child.main(["--selftest"]) == 0
    assert "selftest: 9/9 detectors fired as expected" in capsys.readouterr().out


def test_false_clean_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A disabled shared detector makes the executable selftest fail."""

    def disabled(_command: list[str] | None = None) -> None:
        return None

    monkeypatch.setattr(child, "check_console", disabled)
    assert child.main(["--selftest"]) == 1
    output = capsys.readouterr().out
    assert "Selftest (console nonzero exit)" in output
    assert "Selftest (console missing executable)" in output
    assert "selftest: 7/9 detectors fired as expected" in output


def test_false_dirty_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An always-failing detector cannot pass the positive subprocess case."""

    def always_fails(_command: list[str] | None = None) -> str:
        return "console-sentinel"

    monkeypatch.setattr(child, "check_console", always_fails)
    assert child.main(["--selftest"]) == 1
    assert "Selftest (console success)" in capsys.readouterr().out
