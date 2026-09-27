"""Pin the in-environment probe, network bootstrap and origin rules for #205."""

import json
import os
import sys
from pathlib import Path

import pytest
from packaging.markers import default_environment

from scripts import provider_artifact_check as check
from scripts.smoke_release import run_process

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scripts" / "provider_artifact_check.py"
BLOCKED = ["NetworkBlockedError", "NetworkBlockedError"]


def _env(**extra: str) -> dict[str, str]:
    base = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH"}}
    return base | extra


def test_marker_environment_matches_packaging() -> None:
    assert check.marker_environment() == dict(default_environment())


def test_inventory_reports_requirements_and_versions() -> None:
    graph = check.inventory()
    assert graph["judgevet"]["requires"]
    assert isinstance(graph["httpx"]["version"], str)


def test_importing_helpers_installs_no_guard_or_package(tmp_path: Path) -> None:
    program = (
        "import sys, socket\n"
        "import scripts.provider_artifact_check\n"
        "loaded = sorted(m for m in sys.modules if m.split('.')[0] == 'judgevet')\n"
        "import tests.fixtures.providers.provider_fixture\n"
        "import tests.fixtures.providers.cli_app\n"
        "import tests.fixtures.providers.mcp_app\n"
        "import tests.fixtures.providers.consumer_checks\n"
        "socket.getaddrinfo('localhost', 9)\n"
        "print(loaded)\n"
    )
    result = run_process([sys.executable, "-c", program], _env(), ROOT, 60)
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip() == "[]"


def _module(tmp_path: Path, body: str) -> None:
    (tmp_path / "probe_module.py").write_text(body)


def test_bootstrap_blocks_network_before_package_import(tmp_path: Path) -> None:
    _module(
        tmp_path,
        "import json, socket, sys\n"
        "loaded = [m for m in sys.modules if m.split('.')[0] == 'judgevet']\n"
        "errors = []\n"
        "for attempt in (lambda: socket.create_connection(('127.0.0.1', 9), 1),\n"
        "                lambda: socket.getaddrinfo('localhost', 9)):\n"
        "    try:\n"
        "        attempt()\n"
        "        errors.append(None)\n"
        "    except OSError as error:\n"
        "        errors.append(type(error).__name__)\n"
        "print(json.dumps({'loaded': loaded, 'errors': errors, 'argv': sys.argv[1:]}))\n",
    )
    command = [sys.executable, str(PROBE), "run", "probe_module", "a", "b"]
    result = run_process(command, _env(), tmp_path, 60)
    assert result.returncode == 0, result.stderr[-2000:]
    assert json.loads(result.stdout) == {
        "loaded": [],
        "errors": BLOCKED,
        "argv": ["a", "b"],
    }


def test_bootstrap_writes_child_origin_receipt(tmp_path: Path) -> None:
    _module(tmp_path, "import judgevet.media\nraise SystemExit(3)\n")
    side = tmp_path / "origins.json"
    command = [sys.executable, str(PROBE), "run", "probe_module"]
    result = run_process(
        command, _env(**{check.ORIGINS_VARIABLE: str(side)}), tmp_path, 60
    )
    assert result.returncode == 3
    receipt = json.loads(side.read_text())
    assert receipt["network"] == {"errors": BLOCKED}
    assert receipt["origins"]["judgevet.media"].endswith("judgevet/media.py")
    assert "judgevet" in receipt["origins"]


def test_identity_process_is_guarded(tmp_path: Path) -> None:
    command = [sys.executable, str(PROBE), "identity", str(tmp_path), "base"]
    result = run_process(command, _env(), tmp_path, 120)
    assert result.returncode == 0, result.stderr[-2000:]
    receipt = json.loads(result.stdout.strip().splitlines()[-1])
    assert receipt["network"] == {"errors": BLOCKED}
    assert receipt["preimport"] == []
    assert receipt["environment"] == dict(default_environment())
    assert receipt["distributions"]["judgevet"]["version"] == receipt["version"]


def test_origins_accept_installed_modules(tmp_path: Path) -> None:
    purelib = tmp_path / "venv" / "lib" / "site-packages"
    origins = {"judgevet": str(purelib / "judgevet" / "__init__.py")}
    assert check.check_origins(origins, purelib, tmp_path / "checkout") is None


@pytest.mark.parametrize("where", ["outside", "checkout", "empty", "no-root"])
def test_origins_reject_nonisolated_modules(tmp_path: Path, where: str) -> None:
    purelib = tmp_path / "venv" / "lib" / "site-packages"
    checkout = tmp_path / "checkout"
    origins = {
        "outside": {"judgevet": str(tmp_path / "other" / "judgevet.py")},
        "checkout": {"judgevet": str(checkout / "src" / "judgevet" / "__init__.py")},
        "empty": {},
        "no-root": {"judgevet.media": str(purelib / "judgevet" / "media.py")},
    }[where]
    if where == "checkout":
        purelib = checkout
    with pytest.raises(RuntimeError):
        check.check_origins(origins, purelib, checkout)
