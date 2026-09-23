"""Exercise command cleanup, source diagnostics and platform boundaries."""

import os
import select
import signal
from contextlib import suppress
from pathlib import Path

import pytest
from pydantic import SecretStr

from judgevet.adapters.inbound import credential_command
from judgevet.adapters.inbound.settings import ApiSettings
from tests.unit.test_credential_sources import command


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch) -> None:
    """Prevent ambient literal keys from overriding the source under test."""
    for name in os.environ:
        if name.startswith(("JEV_", "TYPESAFE_")):
            monkeypatch.delenv(name)


@pytest.mark.parametrize(
    "source", ["!", "!unterminated'", "!/nonexistent/private-command-canary"]
)
def test_bad_command_has_safe_context(source: str) -> None:
    """Drop parser and spawn exceptions that can carry command arguments."""
    with pytest.raises(ValueError, match="could not start") as caught:
        ApiSettings(key=source).resolve_key()
    assert caught.value.__context__ is None
    assert source not in str(caught.value)


def test_stdout_limit_and_frame_locals_are_private(tmp_path: Path) -> None:
    """Keep partial output wrapped even when command execution times out."""
    source = command(
        tmp_path,
        "import time; print('credential-frame-canary', flush=True); time.sleep(30)",
    )
    with pytest.raises(ValueError, match="timed out") as caught:
        ApiSettings(key=source, key_command_timeout=0.1).resolve_key()
    frame = caught.value.__traceback__
    inspected = 0
    while frame is not None:
        if "/src/judgevet/" in frame.tb_frame.f_code.co_filename:
            assert "credential-frame-canary" not in repr(frame.tb_frame.f_locals)
            inspected += 1
        frame = frame.tb_next
    assert inspected >= 3


def test_no_implicit_shell(tmp_path: Path) -> None:
    """Shell syntax must remain argv and must not run a second program."""
    marker = tmp_path / "executed"
    source = command(tmp_path, "print('literal-key')") + f" ; touch {marker}"
    assert ApiSettings(key=source).resolve_key() == SecretStr("literal-key")
    assert not marker.exists()


def test_command_success_discards_stderr(tmp_path: Path, capsys) -> None:
    """Successful providers cannot write diagnostics into the caller streams."""
    source = command(
        tmp_path, "import sys; print('literal-key'); sys.stderr.write('stderr-canary')"
    )
    assert ApiSettings(key=source).resolve_key() == SecretStr("literal-key")
    assert capsys.readouterr() == ("", "")


def test_unsupported_commands_fail_closed(monkeypatch) -> None:
    """Leave literal sources usable when process-group commands are unavailable."""
    monkeypatch.setattr(credential_command, "COMMANDS_SUPPORTED", False)
    assert ApiSettings(key="literal").resolve_key() == SecretStr("literal")
    with pytest.raises(ValueError, match="require POSIX"):
        ApiSettings(key="!unused").resolve_key()


def test_fifo_rejected_without_waiting(tmp_path: Path) -> None:
    """Do not block opening a pipe presented as a mounted credential file."""
    fifo = tmp_path / "key"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="Cannot read"):
        ApiSettings(key_file=str(fifo)).resolve_key()


_DESCENDANT_SCRIPT = """import os,pathlib,sys,time
ready_r,ready_w=os.pipe()
pid=os.fork()
if pid == 0:
 os.close(ready_r)
 descriptor=os.open(sys.argv[2],os.O_WRONLY)
 os.write(descriptor,b'x')
 os.write(ready_w,b'x')
 os.close(1)
 time.sleep(30)
else:
 os.close(ready_w)
 os.read(ready_r,1)
 pathlib.Path(sys.argv[1]).write_text(str(pid))
 print('literal-key',flush=True)
 if sys.argv[3] == 'wait':
  time.sleep(30)
"""


@pytest.mark.parametrize("parent_waits", [False, True])
def test_process_group_cleanup(tmp_path: Path, parent_waits: bool) -> None:
    """Observe a descendant's pipe close after success or a deadline failure."""
    child_file = tmp_path / "child"
    fifo = tmp_path / "watch"
    os.mkfifo(fifo)
    descriptor = os.open(fifo, os.O_RDONLY | os.O_NONBLOCK)
    settings = ApiSettings(
        key=command(
            tmp_path,
            _DESCENDANT_SCRIPT,
            str(child_file),
            str(fifo),
            "wait" if parent_waits else "exit",
        ),
        key_command_timeout=1,
    )
    try:
        if parent_waits:
            with pytest.raises(ValueError, match="timed out"):
                settings.resolve_key()
        else:
            assert settings.resolve_key() == SecretStr("literal-key")
        assert os.read(descriptor, 1) == b"x"
        assert select.select([descriptor], [], [], 1)[0] == [descriptor]
        assert os.read(descriptor, 1) == b""
    finally:
        os.close(descriptor)
        if child_file.exists():
            with suppress(ProcessLookupError):
                os.kill(int(child_file.read_text()), signal.SIGKILL)


def test_command_stdin_is_not_inherited(tmp_path: Path) -> None:
    """Keep credential providers from consuming CLI or MCP input streams."""
    source = command(
        tmp_path,
        "import sys; print('empty' if sys.stdin.read() == '' else 'unexpected')",
    )
    assert ApiSettings(key=source).resolve_key() == SecretStr("empty")


def test_mounted_symlink_is_supported(tmp_path: Path) -> None:
    """Follow the regular-file symlinks used by mounted secret volumes."""
    target = tmp_path / "contents"
    target.write_text("mounted-key\n")
    link = tmp_path / "mounted"
    link.symlink_to(target)
    assert ApiSettings(key_file=str(link)).resolve_key() == SecretStr("mounted-key")
