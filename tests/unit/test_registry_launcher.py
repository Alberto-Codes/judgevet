"""Exercise the manifest launcher from an isolated candidate wheel."""

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest

from scripts.smoke_registry_release import check, check_wheel
from scripts.smoke_release import build_wheel
from tests.unit import test_mcp_subprocess

api_server = test_mcp_subprocess.api_server

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep inherited credentials and gateway settings out of child tests and failures."""
    environment = {
        name: os.environ[name]
        for name in ("PATH", "HOME", "LANG")
        if name in os.environ
    }
    monkeypatch.setattr(os, "environ", environment)


@pytest.fixture(scope="module")
def candidate(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build one exact candidate for the installed launch contracts."""
    return build_wheel(tmp_path_factory.mktemp("registry-wheel"))


def test_manifest_installed_launcher(
    candidate: Path,
    api_server: tuple[str, list[dict[str, Any]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require discovery, all three tools and real requests from the isolated launcher."""
    base_url, requests = api_server
    monkeypatch.setenv("JEV_API__KEY", "registry-canary")
    monkeypatch.setenv("JEV_API__BASE_URL", base_url)
    asyncio.run(check(ROOT / "server.json", candidate))
    assert len(requests) == 3
    assert {next(iter(item["body"]["questions"])) for item in requests} == {
        "noul_question",
        "choice_question",
        "score_question",
    }
    assert all(item["auth"] == "Bearer registry-canary" for item in requests)


def test_wrong_wheel_version_rejected(candidate: Path) -> None:
    """Reject a manifest that would test a different package release."""
    with pytest.raises(ValueError, match="metadata does not match"):
        check_wheel(candidate, "0.0.0", "io.github.Alberto-Codes/judgevet")


def test_wrong_launcher_fails(candidate: Path, tmp_path: Path) -> None:
    """Prove the transport check fails when the manifest selects the CLI instead."""
    manifest = json.loads((ROOT / "server.json").read_text())
    manifest["packages"][0]["runtimeArguments"][1]["value"] = "judgevet"
    path = tmp_path / "wrong.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(RuntimeError, match="stage=initialization"):
        asyncio.run(check(path, candidate))


def test_missing_extra_fails(candidate: Path, tmp_path: Path) -> None:
    """Prove the candidate override cannot hide a missing MCP extra in the manifest."""
    manifest = json.loads((ROOT / "server.json").read_text())
    manifest["packages"][0]["runtimeArguments"][0]["value"] = "judgevet=={version}"
    path = tmp_path / "base-only.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(RuntimeError, match="stage=initialization"):
        asyncio.run(check(path, candidate))


def test_broken_candidate_cannot_fall_back_to_pypi(
    candidate: Path, tmp_path: Path
) -> None:
    """Require failure for a candidate missing its launcher, despite a working PyPI release."""
    broken = tmp_path / candidate.name
    with ZipFile(candidate) as original, ZipFile(broken, "w") as output:
        for info in original.infolist():
            if info.filename != "judgevet/adapters/inbound/mcp_entrypoint.py":
                output.writestr(info, original.read(info.filename))
    with pytest.raises(RuntimeError, match="stage=initialization"):
        asyncio.run(check(ROOT / "server.json", broken))
