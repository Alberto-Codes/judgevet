"""Parse the selected documented host templates without claiming host execution.

Schemas and credential mechanisms follow the host sources cited in
``docs/how-to/connect-mcp.md``. This checks our bounded recipe contract; it is
not a complete host schema or a replacement for host integration evidence.

Examples:
    Run ``uv run pytest -q tests/unit/test_doc_host_recipes.py``.

See Also:
    - [judgevet.adapters.inbound.credentials][]: Private key-file handling.
    - [judgevet.adapters.inbound.mcp_entrypoint][]: Launched server.
"""

import json
import tomllib
from dataclasses import dataclass


@dataclass(frozen=True)
class HostRecipe:
    """A parsed launcher and its documented credential delivery mechanism.

    Attributes:
        command: Executable and unchanged argument vector.
        credential: Environment file, private key file, or inherited variable.
        location: File placeholder or variable name, never a secret value.
    """

    command: tuple[str, ...]
    credential: str
    location: str


def _credential(host: str, server: dict) -> tuple[str, str]:
    """Require the credential mechanism selected by the cited host survey.

    Args:
        host: Selected host name.
        server: Parsed server entry.

    Returns:
        Credential mechanism and its non-secret placeholder.

    Raises:
        ValueError: A credential is missing or uses another host's syntax.
    """
    if host in {"vscode", "cursor"}:
        if server.get("envFile") == "/absolute/path/to/judgevet.env":
            return "env-file", server["envFile"]
    elif host == "desktop":
        if server.get("env") == {"JEV_API__KEY_FILE": "/absolute/path/to/judgevet.key"}:
            return "key-file", server["env"]["JEV_API__KEY_FILE"]
    elif host == "claude-code":
        if server.get("env") == {"JEV_API__KEY": "${JEV_API__KEY}"}:
            return "interpolation", "JEV_API__KEY"
    elif host == "codex" and server.get("env_vars") == ["JEV_API__KEY"]:
        return "forward", "JEV_API__KEY"
    raise ValueError("host recipe has an invalid credential mechanism")


def parse_recipe(host: str, text: str) -> HostRecipe:
    """Parse a selected host's exact template with bounded semantic checks.

    Args:
        host: One of vscode, cursor, claude-code, desktop or codex.
        text: Exact JSON or TOML configuration block.

    Returns:
        Launcher and credential reference for separate mechanical checks.

    Raises:
        ValueError: Configuration violates the documented recipe contract.
        TypeError: The server entry is not an object.
    """
    roots = {
        "vscode": "servers",
        "cursor": "mcpServers",
        "claude-code": "mcpServers",
        "desktop": "mcpServers",
        "codex": "mcp_servers",
    }
    if host not in roots:
        raise ValueError("unknown documented host")
    data = tomllib.loads(text) if host == "codex" else json.loads(text)
    if not isinstance(data, dict) or set(data) != {roots[host]}:
        raise ValueError("host recipe has an invalid root")
    servers = data[roots[host]]
    if not isinstance(servers, dict) or set(servers) != {"judgevet"}:
        raise ValueError("host recipe must configure judgevet")
    server = servers["judgevet"]
    if not isinstance(server, dict):
        raise TypeError("host recipe requires a server object")
    credential_field = {
        "vscode": "envFile",
        "cursor": "envFile",
        "claude-code": "env",
        "desktop": "env",
        "codex": "env_vars",
    }[host]
    allowed = {"command", "args", "type", credential_field}
    server_type = server.get("type", None if host in {"vscode", "cursor"} else "stdio")
    if server.keys() - allowed or server_type != "stdio":
        raise ValueError("host recipe requires a stdio launcher")
    command, args = server.get("command"), server.get("args", [])
    if not isinstance(command, str) or not command.strip():
        raise ValueError("host recipe requires an executable")
    if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
        raise ValueError("host recipe requires string arguments")
    credential, location = _credential(host, server)
    return HostRecipe((command, *args), credential, location)
