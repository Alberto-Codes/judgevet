"""Guard, then probe or run code inside one installed judgevet environment.

The runner copies this stdlib-only file outside the checkout and starts every
runtime child through it. ``main`` installs a process-wide audit hook that
refuses internet connections and name lookups before any package under test
is imported. Importing this module installs nothing.

``identity CHECKOUT base|mcp`` prints the installed identity receipt: version,
typing marker, loaded module files, raw distribution metadata and the PEP 508
marker environment for parent-side dependency evaluation. ``run MODULE ARGS``
runs a module as ``__main__`` and, when ``PROVIDER_FIXTURE_ORIGINS`` names a
file, writes the child's loaded judgevet module files and network probe there.

Source: https://github.com/Alberto-Codes/judgevet/issues/205#issuecomment-5851983135.

Examples:
    ```python
    from scripts.provider_artifact_check import normalize

    assert normalize("Typing_Extensions") == "typing-extensions"
    ```

See Also:
    - [scripts.smoke_provider_release][]: Four-environment runner.
    - [scripts.policy_artifact_check][]: Root export and base-install check.
"""

import importlib
import importlib.metadata
import importlib.util
import json
import os
import pkgutil
import platform
import re
import runpy
import socket
import sys
import sysconfig
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ORIGINS_VARIABLE = "PROVIDER_FIXTURE_ORIGINS"
SEED = frozenset({"pip"})
INFERENCE = frozenset(
    {
        "anthropic",
        "google-genai",
        "jax",
        "litellm",
        "llama-cpp-python",
        "ollama",
        "openai",
        "tensorflow",
        "torch",
        "transformers",
        "typesafe",
        "vllm",
    }
)
_IDENTITY_ARGUMENTS = 3
_RUN_ARGUMENTS = 2
_INTERNET = (socket.AF_INET, socket.AF_INET6)
_SENDS = frozenset({"socket.connect", "socket.sendto", "socket.sendmsg"})


class NetworkBlockedError(PermissionError):
    """Raised when guarded code attempts network access."""


def _audit(event: str, args: tuple[Any, ...]) -> None:
    """Refuse internet connections, datagrams and name lookups.

    Args:
        event: Audit event name.
        args: Audit event arguments; socket events carry the socket first.

    Raises:
        NetworkBlockedError: The event would reach the network.
    """
    if event == "socket.getaddrinfo" or (
        event in _SENDS and getattr(args[0], "family", None) in _INTERNET
    ):
        raise NetworkBlockedError("network access is blocked in this process")


def package_modules() -> list[str]:
    """Name the judgevet modules currently imported.

    Returns:
        Sorted module names.
    """
    return sorted(name for name in sys.modules if name.split(".")[0] == "judgevet")


def install_network_guard() -> list[str]:
    """Install the audit hook and report package modules imported before it.

    Returns:
        judgevet modules already imported when the guard was installed.
    """
    before = package_modules()
    sys.addaudithook(_audit)
    return before


def network_probe() -> dict[str, list[str | None]]:
    """Attempt a loopback connection and a local name lookup.

    Neither attempt leaves the machine, even without the guard.

    Returns:
        Failure class names, or None for an attempt that succeeded.
    """
    errors: list[str | None] = []
    for host, port, lookup in (("127.0.0.1", 9, False), ("localhost", 9, True)):
        try:
            if lookup:
                socket.getaddrinfo(host, port)
            else:
                socket.create_connection((host, port), 1).close()
        except OSError as error:
            errors.append(type(error).__name__)
        else:
            errors.append(None)
    return {"errors": errors}


def loaded_origins() -> dict[str, str]:
    """Return files for every judgevet module currently imported.

    Returns:
        Sorted module names mapped to their files.
    """
    return {
        name: str(sys.modules[name].__file__)
        for name in package_modules()
        if getattr(sys.modules[name], "__file__", None)
    }


def normalize(name: str) -> str:
    """Normalize a distribution name as PEP 503 does.

    Args:
        name: Declared or installed distribution name.

    Returns:
        Lowercase name with runs of separators replaced by one hyphen.
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def marker_environment() -> dict[str, str]:
    """Return this interpreter's PEP 508 marker environment.

    The values match ``packaging.markers.default_environment`` without
    importing packaging into the tested environment.

    Returns:
        Marker variable names mapped to values.
    """
    info = sys.implementation.version
    version = f"{info.major}.{info.minor}.{info.micro}"
    if info.releaselevel != "final":
        version += info.releaselevel[0] + str(info.serial)
    return {
        "implementation_name": sys.implementation.name,
        "implementation_version": version,
        "os_name": os.name,
        "platform_machine": platform.machine(),
        "platform_release": platform.release(),
        "platform_system": platform.system(),
        "platform_version": platform.version(),
        "python_full_version": platform.python_version(),
        "platform_python_implementation": platform.python_implementation(),
        "python_version": ".".join(platform.python_version_tuple()[:2]),
        "sys_platform": sys.platform,
    }


def inventory() -> dict[str, dict[str, Any]]:
    """Map installed distributions to their version and raw requirements.

    Returns:
        Normalized names mapped to ``version`` and ``Requires-Dist`` strings.
    """
    return {
        normalize(dist.metadata["Name"]): {
            "version": dist.version,
            "requires": list(dist.requires or []),
        }
        for dist in importlib.metadata.distributions()
    }


def check_origins(origins: Mapping[str, str], purelib: Path, checkout: Path) -> None:
    """Require the package root and every loaded module from this environment.

    Args:
        origins: Module names mapped to their loaded files.
        purelib: The environment's site-packages directory.
        checkout: Repository checkout that must not supply any module.

    Raises:
        RuntimeError: No root module was recorded, or one loaded from elsewhere.
    """
    if "judgevet" not in origins:
        raise RuntimeError("No judgevet package origin was recorded")
    for origin in origins.values():
        path = Path(origin).resolve()
        if not path.is_relative_to(purelib.resolve()):
            raise RuntimeError("A judgevet module is outside site-packages")
        if path.is_relative_to(checkout.resolve()):
            raise RuntimeError("A judgevet module was loaded from the checkout")


def _import_all(extra: bool) -> Any:
    """Import every packaged module the selected install supports.

    Args:
        extra: Whether MCP adapter modules are importable.

    Returns:
        The imported judgevet package.
    """
    package = importlib.import_module("judgevet")
    for info in pkgutil.walk_packages(package.__path__, "judgevet."):
        if not extra and "mcp" in info.name.rsplit(".", 1)[-1]:
            continue
        importlib.import_module(info.name)
    return package


def identity(preimport: list[str], *, extra: bool) -> dict[str, object]:
    """Build the identity receipt after the network guard is installed.

    Args:
        preimport: judgevet modules imported before the guard.
        extra: Whether the environment installed the ``mcp`` extra.

    Returns:
        JSON-serializable identity receipt.
    """
    package = _import_all(extra)
    return {
        "receipt": "provider-identity",
        "version": package.__version__,
        "metadata_version": importlib.metadata.version("judgevet"),
        "py_typed": Path(package.__file__).with_name("py.typed").is_file(),
        "purelib": str(Path(sysconfig.get_paths()["purelib"]).resolve()),
        "origins": loaded_origins(),
        "distributions": inventory(),
        "environment": marker_environment(),
        "mcp_spec": importlib.util.find_spec("mcp") is not None,
        "network": network_probe(),
        "preimport": preimport,
    }


def run(module: str, arguments: Sequence[str], preimport: list[str]) -> int:
    """Run a module as ``__main__`` and record its loaded package files.

    Args:
        module: Importable module name, resolved from the working directory.
        arguments: Arguments the module sees in ``sys.argv[1:]``.
        preimport: judgevet modules imported before the guard.

    Returns:
        The module's exit status.
    """
    sys.path.insert(0, os.getcwd())
    sys.argv = [module, *arguments]
    code = 0
    try:
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    except SystemExit as exit_:
        code = (
            exit_.code if isinstance(exit_.code, int) else int(exit_.code is not None)
        )
    finally:
        side = os.environ.get(ORIGINS_VARIABLE)
        if side:
            receipt = {"origins": loaded_origins(), "network": network_probe()}
            receipt["preimport"] = preimport
            Path(side).write_text(json.dumps(receipt))
    return code


def main(argv: Sequence[str]) -> int:
    """Guard the process, then dispatch ``identity`` or ``run``.

    Args:
        argv: Command followed by its arguments.

    Returns:
        Zero after printing an identity receipt, or the run module's status.

    Raises:
        SystemExit: The arguments are malformed.
    """
    preimport = install_network_guard()
    if len(argv) >= _RUN_ARGUMENTS and argv[0] == "run":
        return run(argv[1], argv[2:], preimport)
    if (
        len(argv) == _IDENTITY_ARGUMENTS
        and argv[0] == "identity"
        and argv[2] in {"base", "mcp"}
    ):
        print(json.dumps(identity(preimport, extra=argv[2] == "mcp")))
        return 0
    raise SystemExit("usage: provider_artifact_check.py identity CHECKOUT base|mcp")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
