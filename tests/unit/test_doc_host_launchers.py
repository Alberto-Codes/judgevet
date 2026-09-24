"""Exercise exact documented launchers without claiming native host integration."""

import asyncio
import json
import os
import shlex
import shutil
from contextlib import chdir
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pytest

from scripts.mcp_smoke_transport import smoke
from scripts.smoke_release import build_wheel, create_venv, run_process
from tests.unit import test_mcp_subprocess
from tests.unit.doc_host_support import (
    HOSTS,
    environment,
    exact_block,
    exact_recipe,
    launcher,
    verify_cli,
)

api_server = test_mcp_subprocess.api_server


@pytest.fixture(scope="module")
def candidate(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_wheel(tmp_path_factory.mktemp("host-recipes-wheel"))


@pytest.mark.parametrize("host", HOSTS)
def test_exact_host_launcher(
    host: str,
    candidate: Path,
    tmp_path: Path,
    api_server: tuple[str, list[dict[str, Any]]],
) -> None:
    base_url, requests = api_server
    command, env = launcher(host, exact_recipe(host), tmp_path, candidate, base_url)
    with chdir(tmp_path):
        asyncio.run(smoke(command, version("judgevet"), env, 120))
    assert len(requests) == 3
    assert all(item["auth"] == "Bearer host-canary" for item in requests)
    assert {next(iter(item["body"]["questions"])) for item in requests} == {
        "noul_question",
        "choice_question",
        "score_question",
    }


@pytest.mark.parametrize("defect", ["wrong-command", "missing-extra", "missing-key"])
def test_exact_launcher_rejects_broken_route(
    defect: str,
    candidate: Path,
    tmp_path: Path,
    api_server: tuple[str, list[dict[str, Any]]],
) -> None:
    base_url, requests = api_server
    data = json.loads(exact_recipe("desktop"))
    args = data["mcpServers"]["judgevet"]["args"]
    if defect == "wrong-command":
        args[-1] = "judgevet"
    elif defect == "missing-extra":
        args[1] = args[1].replace("[mcp]", "")
    command, env = launcher("desktop", json.dumps(data), tmp_path, candidate, base_url)
    if defect == "missing-key":
        env["JEV_API__KEY_FILE"] = str(tmp_path / "absent.key")
    with chdir(tmp_path), pytest.raises(RuntimeError, match="stage=initialization"):
        asyncio.run(smoke(command, version("judgevet"), env, 120))
    assert requests == []


@pytest.mark.parametrize(
    ("number", "kind"), [(12, "noul"), (13, "choice"), (14, "score")]
)
def test_exact_pi_cli_command(
    number: int,
    kind: str,
    candidate: Path,
    tmp_path: Path,
    api_server: tuple[str, list[dict[str, Any]]],
) -> None:
    base_url, requests = api_server
    command = shlex.split(exact_block(number, "bash"))
    executable = shutil.which(command[0])
    assert executable is not None
    command[0] = executable
    env = environment(tmp_path, candidate, command[2])
    env.update(JEV_API__KEY="host-canary", JEV_API__BASE_URL=base_url)
    result = run_process(command, env, tmp_path, timeout=120)
    assert result.returncode == 0
    verify_cli(result.stdout, kind)
    assert len(requests) == 1
    assert requests[0]["auth"] == "Bearer host-canary"


@pytest.mark.parametrize("number", [1, 2])
def test_documented_persistent_install(
    number: int,
    candidate: Path,
    tmp_path: Path,
    api_server: tuple[str, list[dict[str, Any]]],
) -> None:
    base_url, requests = api_server
    command = shlex.split(exact_block(number, "bash"))
    env = environment(tmp_path, candidate, command[-1])
    if number == 1:
        python = create_venv(tmp_path)
        command[0] = str(python)
        env.update(PIP_REQUIREMENT=env["UV_OVERRIDE"], PIP_CONFIG_FILE=os.devnull)
        executable = python.parent / "judgevet-mcp"
    else:
        uv = shutil.which(command[0])
        assert uv is not None
        command[0] = uv
        env.update(
            UV_TOOL_DIR=str(tmp_path / "tools"), UV_TOOL_BIN_DIR=str(tmp_path / "bin")
        )
        executable = tmp_path / "bin" / "judgevet-mcp"
    result = run_process(command, env, tmp_path, timeout=120)
    assert result.returncode == 0
    assert executable.is_file()
    env.update(JEV_API__KEY="host-canary", JEV_API__BASE_URL=base_url)
    with chdir(tmp_path):
        asyncio.run(smoke([str(executable)], version("judgevet"), env, 120))
    assert len(requests) == 3
    assert all(item["auth"] == "Bearer host-canary" for item in requests)
