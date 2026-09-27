"""Pin the installed provider proof's isolation, receipts and oracles for #205."""

import json
import subprocess
import tarfile
import zipfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from judgevet import Question, SystemOneResponse
from judgevet.ports import SystemOnePort
from scripts import smoke_provider_release as runner
from tests.fixtures.providers import consumer_checks, provider_fixture

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def _completed(code: int, stdout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["python"], code, stdout=stdout, stderr="")


def test_consumer_env_clears_injection_and_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in (
        "PYTHONPATH",
        "PYTHONHOME",
        "JEV_API__KEY",
        "JEV_API__BASE_URL",
        "TYPESAFE_API_KEY",
        "VIRTUAL_ENV",
    ):
        monkeypatch.setenv(name, "inherited-synthetic")
    python = tmp_path / "venv" / "bin" / "python"
    env = runner.consumer_env(tmp_path, python)
    assert not [key for key in env if key.startswith(("JEV", "TYPESAFE", "PYTHONP"))]
    assert "PYTHONHOME" not in env
    assert "VIRTUAL_ENV" not in env
    assert "inherited-synthetic" not in env.values()
    assert env["HOME"] == str(tmp_path / "home")
    for name in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME"):
        assert Path(env[name]).is_relative_to(tmp_path)
    assert env["PATH"].split(":")[0] == str(python.parent)
    assert env["PYTHONNOUSERSITE"] == "1"


def test_workspace_must_be_outside_checkout(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        runner.require_outside(ROOT / "scratchpad" / "venv", ROOT)
    assert runner.require_outside(tmp_path, ROOT) is None


@pytest.mark.parametrize(
    ("code", "stdout"),
    [(1, json.dumps({"receipt": "x"})), (0, "ok\n"), (0, "")],
    ids=["failed-child", "not-json", "empty"],
)
def test_receipt_rejects_failed_or_malformed_child(code: int, stdout: str) -> None:
    with pytest.raises(RuntimeError):
        runner.parse_receipt(_completed(code, stdout), "x")


def test_receipt_rejects_wrong_kind() -> None:
    with pytest.raises(RuntimeError):
        runner.parse_receipt(_completed(0, json.dumps({"receipt": "y"})), "x")
    assert runner.parse_receipt(
        _completed(0, "log\n" + json.dumps({"receipt": "x", "n": 1})), "x"
    ) == {"receipt": "x", "n": 1}


LINUX = {
    "implementation_name": "cpython",
    "implementation_version": "3.13.13",
    "os_name": "posix",
    "platform_machine": "x86_64",
    "platform_release": "7.0",
    "platform_system": "Linux",
    "platform_version": "#1",
    "python_full_version": "3.13.13",
    "platform_python_implementation": "CPython",
    "python_version": "3.13",
    "sys_platform": "linux",
}
BLOCKED = {"errors": ["NetworkBlockedError", "NetworkBlockedError"]}


def _dists(graph: Mapping[str, list[str]]) -> dict[str, dict[str, object]]:
    return {
        name: {"version": "1.2.3", "requires": reqs} for name, reqs in graph.items()
    }


def _identity(purelib: Path, **changes: object) -> dict[str, object]:
    receipt: dict[str, object] = {
        "receipt": "provider-identity",
        "version": "1.2.3",
        "metadata_version": "1.2.3",
        "py_typed": True,
        "purelib": str(purelib),
        "origins": {"judgevet": str(purelib / "judgevet" / "__init__.py")},
        "distributions": _dists({"judgevet": ["httpx"], "httpx": [], "pip": []}),
        "environment": LINUX,
        "mcp_spec": False,
        "network": BLOCKED,
        "preimport": [],
    }
    receipt.update(changes)
    return receipt


def test_identity_accepts_isolated_receipt(tmp_path: Path) -> None:
    purelib = tmp_path / "venv" / "lib" / "site-packages"
    result = runner.validate_identity(
        _identity(purelib), "1.2.3", tmp_path / "venv", ROOT, extra=False
    )
    assert result is None


@pytest.mark.parametrize(
    "change",
    [
        {"version": "9.9.9"},
        {"metadata_version": "9.9.9"},
        {"py_typed": False},
        {"mcp_spec": True},
        {"origins": {}},
        {"origins": {"judgevet": str(ROOT / "src" / "judgevet" / "__init__.py")}},
        {"distributions": _dists({"httpx": []})},
        {"distributions": _dists({"judgevet": ["httpx"]})},
        {"network": {"errors": [None, None]}},
        {"preimport": ["judgevet"]},
    ],
    ids=[
        "version",
        "metadata",
        "py-typed",
        "mcp-in-base",
        "no-origins",
        "checkout-origin",
        "no-self",
        "missing-dependency",
        "unguarded-network",
        "imported-before-guard",
    ],
)
def test_identity_rejects_false_positive(
    tmp_path: Path, change: dict[str, object]
) -> None:
    purelib = tmp_path / "venv" / "lib" / "site-packages"
    with pytest.raises(RuntimeError):
        runner.validate_identity(
            _identity(purelib, **change), "1.2.3", tmp_path / "venv", ROOT, extra=False
        )


def test_identity_rejects_purelib_outside_environment(tmp_path: Path) -> None:
    purelib = tmp_path / "elsewhere" / "site-packages"
    with pytest.raises(RuntimeError):
        runner.validate_identity(
            _identity(purelib), "1.2.3", tmp_path / "venv", ROOT, extra=False
        )


def test_extra_identity_requires_mcp(tmp_path: Path) -> None:
    purelib = tmp_path / "venv" / "lib" / "site-packages"
    with pytest.raises(RuntimeError):
        runner.validate_identity(
            _identity(purelib), "1.2.3", tmp_path / "venv", ROOT, extra=True
        )


def _wheel(path: Path, version: str, typed: bool = True) -> Path:
    path.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"judgevet-{version}.dist-info/METADATA",
            f"Name: judgevet\nVersion: {version}\n",
        )
        if typed:
            archive.writestr("judgevet/py.typed", "")
    return path


def _sdist(path: Path, version: str) -> Path:
    info = path.parent / "PKG-INFO"
    info.write_text(f"Name: judgevet\nVersion: {version}\n")
    with tarfile.open(path, "w:gz") as archive:
        archive.add(info, arcname=f"judgevet-{version}/PKG-INFO")
    return path


def test_artifact_versions_must_agree(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "judgevet-1.2.3-py3-none-any.whl", "1.2.3")
    sdist = _sdist(tmp_path / "judgevet-1.2.3.tar.gz", "1.2.3")
    assert runner.artifact_version(wheel, sdist, wheel) == "1.2.3"
    other = _wheel(tmp_path / "judgevet-1.2.4-py3-none-any.whl", "1.2.4")
    with pytest.raises(RuntimeError):
        runner.artifact_version(wheel, sdist, other)
    untyped = _wheel(tmp_path / "u" / "judgevet-1.2.3-py3-none-any.whl", "1.2.3", False)
    with pytest.raises(RuntimeError):
        runner.artifact_version(wheel, sdist, untyped)


def test_digest_is_sha256(tmp_path: Path) -> None:
    path = tmp_path / "artifact"
    path.write_bytes(b"abc")
    assert runner.sha256(path) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_fixture_library_observations_match_oracle() -> None:
    observed = consumer_checks.library_checks()
    assert runner.mismatches(observed, runner.EXPECTED_LIBRARY) == []


def test_consumer_receipt_rejects_bare_success() -> None:
    receipt = {
        "receipt": "provider-consumer",
        "checks": dict.fromkeys(runner.expected_checks(extra=True), "ok"),
        "origins": {"judgevet": "/x"},
    }
    with pytest.raises(RuntimeError):
        runner.validate_consumer(receipt, extra=True)


def test_consumer_receipt_rejects_missing_mcp_checks() -> None:
    receipt = {
        "receipt": "provider-consumer",
        "checks": runner.expected_checks(extra=False),
        "origins": {"judgevet": "/x"},
    }
    assert runner.validate_consumer(receipt, extra=False) is None
    with pytest.raises(RuntimeError):
        runner.validate_consumer(receipt, extra=True)


def test_media_omission_fails_oracle(monkeypatch: pytest.MonkeyPatch) -> None:
    def omit(
        port: SystemOnePort,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        **_: object,
    ) -> SystemOneResponse:
        return port.system_one(state, questions, model)

    monkeypatch.setattr(consumer_checks, "judge_with_images", omit)
    failed = runner.mismatches(
        consumer_checks.library_checks(), runner.EXPECTED_LIBRARY
    )
    assert "library_media" in failed
    assert "library_provenance" not in failed


def test_ignored_selection_fails_oracle(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def ignore_selection(
        *, port: object = None, factory: object = None
    ) -> Iterator[SystemOnePort]:
        yield provider_fixture.RecordingProvider("default")

    monkeypatch.setattr(consumer_checks, "provider_scope", ignore_selection)
    failed = runner.mismatches(
        consumer_checks.library_checks(), runner.EXPECTED_LIBRARY
    )
    assert {"library_text", "library_owned", "library_call_failure"} <= set(failed)


def test_failed_consumer_child_fails_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
        receipt = {"receipt": "provider-consumer", "checks": {}, "origins": {}}
        return _completed(1, json.dumps(receipt))

    monkeypatch.setattr(runner, "run_process", fail)
    with pytest.raises(RuntimeError):
        runner.run_consumer(tmp_path / "python", tmp_path, {}, extra=False)


def test_main_reports_failure_status(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def broken(_: Path) -> Path:
        raise RuntimeError("synthetic build failure")

    monkeypatch.setattr(runner, "build_wheel", broken)
    assert runner.main([]) == 1
    assert "FAIL" in capsys.readouterr().out


_JUDGEVET = ["httpx>=0.27", "typer", 'mcp>=2.2; extra == "mcp"']
_COMPOUND = '(extra == "mcp" or extra == "all") and python_version >= "3.12"'


@pytest.mark.parametrize(
    ("graph", "extra"),
    [
        ({"judgevet": ["httpx>=0.27", "typer"], "typer": []}, False),
        ({"judgevet": _JUDGEVET, "httpx": [], "typer": [], "pywin32": []}, False),
        (
            {
                "judgevet": [*_JUDGEVET, 'pywin32; sys_platform == "win32"'],
                "httpx": [],
                "typer": [],
                "pywin32": [],
            },
            False,
        ),
        (
            {
                "judgevet": [*_JUDGEVET, 'tomli; python_version < "3.11"'],
                "httpx": [],
                "typer": [],
                "tomli": [],
            },
            False,
        ),
        (
            {
                "judgevet": [*_JUDGEVET, 'legacy; extra != "mcp"'],
                "httpx": [],
                "typer": [],
                "mcp": [],
                "legacy": [],
            },
            True,
        ),
        ({"judgevet": _JUDGEVET, "httpx": [], "typer": []}, True),
        (
            {
                "judgevet": [*_JUDGEVET, f"compound; {_COMPOUND}"],
                "httpx": [],
                "typer": [],
                "mcp": [],
            },
            True,
        ),
    ],
    ids=[
        "missing-applicable",
        "undeclared",
        "windows-only-on-linux",
        "old-python-only",
        "negated-extra",
        "missing-mcp",
        "missing-compound",
    ],
)
def test_inventory_evaluates_markers_and_missing_nodes(
    graph: dict[str, list[str]], extra: bool
) -> None:
    with pytest.raises(RuntimeError):
        runner.check_inventory(graph, LINUX, extra=extra)


def test_inventory_accepts_marker_closures() -> None:
    requires = [
        *_JUDGEVET,
        'pywin32; sys_platform == "win32"',
        'legacy; extra != "mcp"',
        f"compound; {_COMPOUND}",
    ]
    base = {
        "judgevet": requires,
        "httpx": ['anyio; python_version >= "3.8"', "absent; os_name == 'nt'"],
        "anyio": [],
        "typer": [],
        "legacy": [],
        "pip": [],
    }
    assert runner.check_inventory(base, LINUX, extra=False) is None
    extra = {name: value for name, value in base.items() if name != "legacy"} | {
        "mcp": ["PyJWT[crypto]>=2"],
        "pyjwt": ['cryptography; extra == "crypto"'],
        "cryptography": [],
        "compound": [],
    }
    assert runner.check_inventory(extra, LINUX, extra=True) is None
    without = extra | {"mcp": ["PyJWT>=2"]}
    with pytest.raises(RuntimeError, match=r"undeclared=\['cryptography'\]"):
        runner.check_inventory(without, LINUX, extra=True)


def _consumer(purelib: Path, extra: bool) -> dict[str, Any]:
    origin = {"judgevet": str(purelib / "judgevet" / "__init__.py")}
    children = {
        label: {"origins": dict(origin), "network": dict(BLOCKED), "preimport": []}
        for label in runner.expected_children(extra=extra)
    }
    return {"origins": origin, "children": children}


def test_child_origins_accept_every_isolated_child(tmp_path: Path) -> None:
    purelib = tmp_path / "venv" / "lib" / "site-packages"
    for extra in (False, True):
        consumer = _consumer(purelib, extra)
        assert runner.validate_children(consumer, purelib, ROOT, extra=extra) is None
    assert {"cli_text_borrowed", "mcp_owned", "mcp_sdk_owned"} <= set(
        runner.expected_children(extra=True)
    )
    assert "mcp_absent" in runner.expected_children(extra=False)


@pytest.mark.parametrize(
    "fault",
    [
        "checkout",
        "missing",
        "network",
        "empty",
        "preimport_missing",
        "preimport_loaded",
    ],
)
def test_child_origins_reject_substitution(tmp_path: Path, fault: str) -> None:
    purelib = tmp_path / "venv" / "lib" / "site-packages"
    consumer = _consumer(purelib, True)
    child = consumer["children"]["cli_media_owned"]
    if fault == "checkout":
        child["origins"]["judgevet.media"] = str(ROOT / "src" / "judgevet" / "media.py")
    elif fault == "missing":
        del consumer["children"]["mcp_sdk_text_only"]
    elif fault == "network":
        child["network"] = {"errors": [None, "NetworkBlockedError"]}
    elif fault == "preimport_missing":
        del child["preimport"]
    elif fault == "preimport_loaded":
        child["preimport"] = ["judgevet"]
    else:
        child["origins"] = {}
    with pytest.raises(RuntimeError):
        runner.validate_children(consumer, purelib, ROOT, extra=True)


def test_environment_receipt_prints_origin_maps(tmp_path: Path) -> None:
    purelib = tmp_path / "venv" / "lib" / "site-packages"
    identity = _identity(purelib)
    consumer = _consumer(purelib, False)
    printed = runner.environment_receipt(
        "source", "base", "ab" * 32, identity, consumer
    )
    assert printed["purelib"] == str(purelib)
    assert printed["identity_origins"] == identity["origins"]
    assert printed["consumer_origins"] == consumer["origins"]
    assert printed["child_origins"] == {
        label: child["origins"] for label, child in consumer["children"].items()
    }
    assert str(purelib / "judgevet" / "__init__.py") in json.dumps(printed)


def test_sdk_client_checks_are_expected() -> None:
    checks = runner.expected_checks(extra=True)
    owned, text_only = checks["mcp_sdk_owned"], checks["mcp_sdk_text_only"]
    assert owned["calls"] == checks["mcp_owned"]["calls"]
    assert owned["events"] == checks["mcp_owned"]["events"]
    assert owned["media"] == checks["mcp_owned"]["media"]
    assert text_only["media"]["error"] is True
    assert "mcp_sdk_owned" not in runner.expected_checks(extra=False)


def test_children_run_through_network_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commands: list[list[str]] = []

    def record(command: list[str], *_: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return _completed(1, "")

    monkeypatch.setattr(runner, "run_process", record)
    with pytest.raises(RuntimeError):
        runner.run_consumer(tmp_path / "python", tmp_path, {}, extra=False)
    assert commands[0][1:3] == ["provider_artifact_check.py", "run"]
    assert commands[0][3] == "tests.fixtures.providers.consumer_checks"
