"""Exercise the manifest launcher in an isolated uvx cache outside the checkout.

Examples:
    Run ``uv run python -m scripts.smoke_registry_release --wheel /tmp/judgevet.whl``.
    Omit ``--wheel`` to verify the real published package through the manifest.

See Also:
    - [scripts.registry_manifest][]: Validated launch contract.
    - [scripts.mcp_smoke_transport][]: Discovery and all three tool calls.
"""

import argparse
import asyncio
import json
import os
import shutil
import tempfile
import zipfile
from contextlib import chdir
from email.parser import BytesParser
from pathlib import Path

from packaging.requirements import Requirement

from scripts.mcp_smoke_transport import smoke
from scripts.registry_manifest import launch_command


def check_wheel(wheel: Path, version: str, name: str) -> None:
    """Check candidate identity, version, optional extra and ownership marker.

    Args:
        wheel: Exact built or downloaded wheel.
        version: Required manifest version.
        name: Registry server name.

    Raises:
        ValueError: Wheel metadata differs from the manifest or lacks MCP ownership.
    """
    with zipfile.ZipFile(wheel) as archive:
        (metadata,) = [
            n for n in archive.namelist() if n.endswith(".dist-info/METADATA")
        ]
        message = BytesParser().parsebytes(archive.read(metadata))
    if (
        message["Name"] != "judgevet"
        or message["Version"] != version
        or "mcp" not in message.get_all("Provides-Extra", [])
        or f"<!-- mcp-name: {name} -->" not in str(message.get_payload())
    ):
        raise ValueError("candidate metadata does not match the registry manifest")


async def check(manifest: Path, wheel: Path | None = None) -> None:
    """Launch the manifest argv with fresh installation and exercise every tool.

    Args:
        manifest: Manifest to execute.
        wheel: Optional exact candidate artifact, mapped with uv's dependency override.

    Raises:
        RuntimeError: Uvx is missing or the transport check fails.
        ValueError: Wheel metadata does not match the manifest.
    """
    data = json.loads(manifest.read_text())
    command = launch_command(data)
    uvx = shutil.which(command[0])
    if uvx is None:
        raise RuntimeError("registry smoke requires uvx")
    command[0] = uvx
    if wheel is not None:
        check_wheel(wheel, data["version"], data["name"])
    with tempfile.TemporaryDirectory(prefix="judgevet-registry-") as directory:
        workdir = Path(directory)
        env = {
            k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "UV_"))
        }
        env.update(UV_CACHE_DIR=str(workdir / "cache"), UV_ISOLATED="1")
        if wheel is not None:
            override = workdir / "override.txt"
            requested = Requirement(command[2])
            extras = (
                "[" + ",".join(sorted(requested.extras)) + "]"
                if requested.extras
                else ""
            )
            override.write_text(f"judgevet{extras} @ {wheel.resolve().as_uri()}\n")
            env["UV_OVERRIDE"] = str(override)
        with chdir(workdir):
            await smoke(command, data["version"], env, timeout=120)
    print("Registry launcher: discovery and all three tools pass")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("server.json"))
    parser.add_argument("--wheel", type=Path)
    arguments = parser.parse_args()
    asyncio.run(check(arguments.manifest.resolve(), arguments.wheel))
