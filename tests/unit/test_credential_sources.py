"""Prove credential precedence, bounded source reads and safe failures."""

import os
import shlex
import sys
import time
import traceback
from pathlib import Path

import pytest
from pydantic import SecretStr

from judgevet.adapters.inbound.settings import ApiSettings


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch) -> None:
    """Keep inherited credentials out of this synthetic source suite."""
    for name in os.environ:
        if name.startswith(("JEV_", "TYPESAFE_")):
            monkeypatch.delenv(name)


def command(tmp_path: Path, code: str, *args: str) -> str:
    """Return a quoted command for a caller-owned synthetic script."""
    script = tmp_path / "secret provider.py"
    script.write_text(code)
    return "!" + shlex.join([sys.executable, str(script), *args])


def test_explicit_key_skips_other_sources(tmp_path: Path) -> None:
    """An explicit argument must not read a missing file or run a command."""
    marker = tmp_path / "executed"
    source = command(
        tmp_path, "import pathlib,sys; pathlib.Path(sys.argv[1]).touch()", str(marker)
    )
    settings = ApiSettings(key=source, key_file=str(tmp_path / "missing"))
    assert settings.resolve_key("explicit") == SecretStr("explicit")
    assert settings.resolve_key("!literal") == SecretStr("!literal")
    assert not marker.exists()


def test_literal_key_skips_file(tmp_path: Path) -> None:
    """A literal configured key wins over an unreadable lower-priority file."""
    settings = ApiSettings(key="literal", key_file=str(tmp_path / "missing"))
    assert settings.resolve_key() == SecretStr("literal")


def test_file_wins_over_command(tmp_path: Path) -> None:
    """Read a mounted key and do not execute a configured fallback command."""
    key_file = tmp_path / "key"
    key_file.write_bytes(b"file-canary\r\n")
    source = command(tmp_path, "raise RuntimeError('must not run')")
    settings = ApiSettings(key=source, key_file=str(key_file))
    resolved = settings.resolve_key()
    assert resolved == SecretStr("file-canary")
    assert "file-canary" not in repr(resolved)
    assert "file-canary" not in repr(settings)


def test_selected_file_failure_does_not_fall_back(tmp_path: Path) -> None:
    """A broken selected source fails without executing a lower-priority command."""
    marker = tmp_path / "executed"
    source = command(
        tmp_path, "import pathlib,sys; pathlib.Path(sys.argv[1]).touch()", str(marker)
    )
    settings = ApiSettings(key=source, key_file=str(tmp_path / "missing"))
    with pytest.raises(ValueError):
        settings.resolve_key()
    assert not marker.exists()


def test_command_is_lazy_and_argv_is_quoted(tmp_path: Path) -> None:
    """Keep construction side-effect free and execute quoted arguments literally."""
    marker = tmp_path / "executed"
    source = command(
        tmp_path,
        "import pathlib,sys; pathlib.Path(sys.argv[1]).touch(); print(sys.argv[2])",
        str(marker),
        "value;literal",
    )
    settings = ApiSettings(key=source)
    assert not marker.exists()
    assert settings.resolve_key() == SecretStr("value;literal")
    assert marker.exists()


@pytest.mark.parametrize(
    "data", [b"", b" \n", b"a\nb", b"a\x00b", b"\xff", b"x" * 4097]
)
def test_reject_invalid_file_output(tmp_path: Path, data: bytes) -> None:
    """Reject invalid source values without exposing their content."""
    key_file = tmp_path / "key"
    key_file.write_bytes(data)
    with pytest.raises(ValueError):
        ApiSettings(key_file=str(key_file)).resolve_key()


def test_reject_nonregular_file(tmp_path: Path) -> None:
    """Reject a directory instead of attempting a credential read."""
    with pytest.raises(ValueError):
        ApiSettings(key_file=str(tmp_path)).resolve_key()


@pytest.mark.parametrize(
    "code",
    [
        "import sys; print('stdout-canary'); sys.stderr.write('stderr-canary'); sys.exit(9)",
        "import sys; sys.stdout.buffer.write(b'\\xff')",
        "print('x' * 4097)",
        "print('')",
    ],
)
def test_command_failure_is_private(tmp_path: Path, code: str, capsys) -> None:
    """Reject bad command results without disclosing command text or streams."""
    source = command(tmp_path, code)
    with pytest.raises(ValueError) as caught:
        ApiSettings(key=source).resolve_key()
    rendered = "".join(traceback.format_exception(caught.value))
    assert "stdout-canary" not in rendered
    assert "stderr-canary" not in rendered
    assert source not in str(caught.value)
    assert source not in repr(caught.value)
    assert capsys.readouterr() == ("", "")


def test_timeout_is_bounded_and_private(tmp_path: Path) -> None:
    """Stop a slow provider after the configured deadline without partial output."""
    source = command(
        tmp_path, "import time; print('partial-canary', flush=True); time.sleep(30)"
    )
    started = time.monotonic()
    with pytest.raises(ValueError, match="command") as caught:
        ApiSettings(key=source, key_command_timeout=0.1).resolve_key()
    assert time.monotonic() - started < 3
    assert "partial-canary" not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_invalid_timeout_rejected(timeout) -> None:
    """Require a finite positive execution timeout before resolving a source."""
    with pytest.raises(ValueError):
        ApiSettings(key_command_timeout=timeout)


def test_missing_source_and_empty_explicit_key() -> None:
    """Preserve absent-source and explicit-literal argument semantics."""
    assert ApiSettings().resolve_key() is None
    assert ApiSettings(key="").resolve_key() is None
    assert ApiSettings(key="literal").resolve_key("") == SecretStr("")


@pytest.mark.parametrize("source", ["file", "command"])
def test_exact_output_limit_is_accepted(tmp_path: Path, source: str) -> None:
    """Accept exactly 4096 bytes while larger source values remain rejected."""
    if source == "file":
        key_file = tmp_path / "key"
        key_file.write_text("a" * 4096)
        settings = ApiSettings(key_file=str(key_file))
    else:
        settings = ApiSettings(
            key=command(tmp_path, "import sys; sys.stdout.write('a' * 4096)")
        )
    assert settings.resolve_key() == SecretStr("a" * 4096)


def test_empty_file_path_fails_without_command_fallback(tmp_path: Path) -> None:
    """Treat an empty configured path as a selected source that fails closed."""
    marker = tmp_path / "executed"
    source = command(
        tmp_path,
        "import pathlib,sys; pathlib.Path(sys.argv[1]).touch(); print('fallback-key')",
        str(marker),
    )
    settings = ApiSettings(key=source, key_file="")
    assert settings.has_key_source
    with pytest.raises(ValueError, match="Cannot read API key file"):
        settings.resolve_key()
    assert not marker.exists()
