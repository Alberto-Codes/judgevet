"""Prove the live CLI test rejects broken behavior without a live service.

Examples:
    ```python
    from tests.cli_process_support import SUCCESS

    assert SUCCESS["model"] == "jev-1.13.0"
    ```

See Also:
    - [judgevet.domain.response_parser][]: Typed answer validation.
"""

import asyncio
import copy
import importlib
import json
import os
import signal
import sys
from contextlib import suppress
from pathlib import Path
from types import ModuleType

import pytest

from judgevet.domain.errors import JevResponseError
from tests.cli_process_support import SUCCESS

pytestmark = pytest.mark.unit


def live_module() -> ModuleType:
    """Load the actual live test without running its marked function.

    Returns:
        Live test module under audit.
    """
    return importlib.import_module("tests.live.test_cli_live")


def wire_answer() -> dict:
    """Return synthetic rendered CLI output including answer names.

    Returns:
        Fresh mutable output fixture.
    """
    answer = copy.deepcopy(SUCCESS)
    for name, value in answer["answers"].items():
        value["name"] = name
    return answer


def test_accepts_valid_typed_output() -> None:
    """The oracle accepts actual CLI shape with all three typed variants."""
    answer = live_module().validate_cli_output(
        0, json.dumps(wire_answer()).encode(), b""
    )
    assert set(answer.nouls) == {"noul"}
    assert set(answer.choices) == {"choice"}
    assert set(answer.scores) == {"score"}


@pytest.mark.parametrize(
    "code,stdout,stderr",
    [
        (1, b"{}", b""),
        (0, b"{}", b"canary-error"),
        (0, b"{", b""),
        (0, b"[]", b""),
    ],
)
def test_rejects_broken_process_output(code: int, stdout: bytes, stderr: bytes) -> None:
    """Process failures and malformed output cannot masquerade as a live pass.

    Args:
        code: Synthetic process status.
        stdout: Synthetic captured output.
        stderr: Synthetic captured diagnostics.
    """
    with pytest.raises((AssertionError, json.JSONDecodeError)):
        live_module().validate_cli_output(code, stdout, stderr)


@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "variant",
        "confidence",
        "model",
        "legend",
        "name",
        "usage",
    ],
)
def test_rejects_broken_answer(defect: str) -> None:
    """The real live oracle rejects independently corrupted answer fields.

    Args:
        defect: Field corruption under test.
    """
    raw = wire_answer()
    if defect == "missing":
        del raw["answers"]["noul"]
    elif defect == "variant":
        raw["answers"]["noul"] = {**raw["answers"]["choice"], "name": "noul"}
    elif defect == "confidence":
        raw["answers"]["choice"]["confidence"] = 1.5
    elif defect == "model":
        raw["model"] = "wrong-model"
    elif defect == "legend":
        raw["answers"]["score"]["legend"]["0"] = "Wrong"
    elif defect == "name":
        raw["answers"]["noul"]["name"] = "wrong"
    else:
        raw["usage"]["input_tokens"] = True
    with pytest.raises(
        (AssertionError, ValueError, TypeError, KeyError, JevResponseError)
    ):
        live_module().validate_cli_output(0, json.dumps(raw).encode(), b"")


def test_missing_key_skips_before_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing credentials skip before the subprocess helper is reached.

    Args:
        monkeypatch: Remove every supported source of a configured key.
    """
    module = live_module()
    for name in ("JEV_API__KEY", "TYPESAFE_API_KEY", "JEV_API"):
        monkeypatch.delenv(name, raising=False)

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Spawn attempted without configured key")

    monkeypatch.setattr(sys, "executable", "/nonexistent-judgevet-live-test/python")
    monkeypatch.setattr(module, "run_capped", forbidden)
    with pytest.raises(pytest.skip.Exception, match="Missing"):
        module.test_installed_cli_mixed_live()


def test_configured_failure_is_not_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """A configured canary reaches one subprocess and fails on its status.

    Args:
        monkeypatch: Supply synthetic configuration and a failed child.
    """
    module = live_module()
    monkeypatch.setenv("JEV_API__KEY", "offline-live-canary")
    calls: list[list[str]] = []

    async def failed(argv: list[str]) -> tuple[int, bytes, bytes]:
        calls.append(argv)
        return 1, b"", b"Denied"

    monkeypatch.setattr(module, "run_capped", failed)
    with pytest.raises(AssertionError):
        module.test_installed_cli_mixed_live()
    assert len(calls) == 1
    argv = calls[0]
    assert argv[0] == str(Path(sys.executable).parent / "judgevet")
    assert argv[-3:] == ["--model", "jev-1.13.0", "--json"]
    payload = json.loads(argv[2])
    assert set(payload) == {"noul", "choice", "score"}
    assert {name: value["type"] for name, value in payload.items()} == {
        "noul": "noul",
        "choice": "choice",
        "score": "score",
    }
    assert set(payload["noul"]["criteria"]) == {"true", "false"}
    assert set(payload["choice"]["criteria"]) == {"yes", "no"}
    assert payload["score"]["criteria"] == ["Poor", "Fair", "Good", "Excellent"]
    assert "offline-live-canary" not in " ".join(argv)


def test_missing_console_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A configured live test cannot skip a missing installed executable.

    Args:
        monkeypatch: Isolate executable lookup and key configuration.
        tmp_path: Directory without a console script.
    """
    module = live_module()
    monkeypatch.setenv("JEV_API__KEY", "offline-live-canary")
    monkeypatch.setattr(sys, "executable", str(tmp_path / "python"))
    with pytest.raises((AssertionError, FileNotFoundError)):
        module.test_installed_cli_mixed_live()


def test_timeout_reaps_actual_child(tmp_path: Path) -> None:
    """A timed-out real child is killed and reaped before the helper returns.

    Args:
        tmp_path: Location for a synthetic child's PID record.
    """
    module = live_module()
    pidfile = tmp_path / "pid"
    child = (
        "import os,time,pathlib,sys;"
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()));time.sleep(30)"
    )
    try:
        with pytest.raises(TimeoutError):
            asyncio.run(
                module.run_capped([sys.executable, "-c", child, str(pidfile)], 1.0)
            )
        assert pidfile.is_file()
        with pytest.raises(ProcessLookupError):
            os.kill(int(pidfile.read_text()), 0)
    finally:
        if pidfile.is_file():
            with suppress(ProcessLookupError):
                os.kill(int(pidfile.read_text()), signal.SIGKILL)


def test_invalid_configuration_is_not_missing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid settings must fail instead of silently skipping live coverage.

    Args:
        monkeypatch: Set a synthetic key and invalid timeout.
    """
    monkeypatch.setenv("JEV_API__KEY", "offline-live-canary")
    monkeypatch.setenv("JEV_API__TIMEOUT_SECONDS", "not-a-number")
    with pytest.raises(ValueError):
        live_module().api_key_configured()
