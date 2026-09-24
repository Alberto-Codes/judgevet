---
status: draft
---

# Install judgevet

Status: **draft**.

Published judgevet 0.10.0 provides the library, CLI and `judgevet-mcp` command.
The MCP runtime is optional.

## Install the library

Use Python 3.12 or newer. In a virtual environment with pip, run:

```bash
python -m pip install judgevet
```

Alternatively, in an existing uv project, run:

```bash
uv add judgevet
```

The package includes `judgevet/py.typed` for type checkers. The base installation
does not install the MCP runtime. See [supported imports](../reference/compatibility.md).

## Run the CLI

With uv installed, run this from any directory:

```bash
uvx judgevet --help
```

The base library installation above also installs `judgevet` in that virtual
environment. For a persistent standalone command with uv, run:

```bash
uv tool install judgevet
```

If `judgevet` is not on `PATH`, run `uv tool update-shell` and start a new shell.
Confirm `judgevet --help` works before following the CLI task guides.

## Install the optional MCP runtime

Follow [Connect an MCP host](connect-mcp.md#install-the-optional-mcp-runtime)
for the optional extra, host configuration and tool discovery.

## Run the published MCP command

The [pinned launcher](connect-mcp.md#run-the-published-mcp-command) runs without
a judgevet checkout.

## Optional: run MCP from a source checkout

Use the [development launcher](connect-mcp.md#optional-run-mcp-from-a-source-checkout).

## Choose a host

Follow the recipe for [VS Code](connect-mcp.md#vs-code),
[Cursor](connect-mcp.md#cursor), [Claude Code](connect-mcp.md#claude-code),
[Claude Desktop](connect-mcp.md#claude-desktop), or
[Codex](connect-mcp.md#configure-codex-for-a-project).
[Pi uses CLI access](connect-mcp.md#pi-cli-access). Host setup needs neither
direnv nor a source checkout.

## Configure Codex for a project

Follow the [Codex recipe](connect-mcp.md#configure-codex-for-a-project).

## Verify the connection

[Discover tools and make a call](connect-mcp.md#verify-the-connection) in your host.

## When MCP does not connect

Use the [safe startup/discovery checks](troubleshoot.md#when-mcp-does-not-connect).

For a first Python call, follow the [first-judgment tutorial](../tutorials/first-judgment.md).
For existing applications, use the [sync](use-library.md) or
[async](use-async-library.md) recipe. Install/import failures are covered by
[troubleshooting](troubleshoot.md).
