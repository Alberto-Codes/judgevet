---
status: draft
---

# Install judgevet

Published judgevet 0.7.0 provides the library, CLI and `judgevet-mcp` command.
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

## Install the optional MCP runtime

In a virtual environment with pip, run:

```bash
python -m pip install 'judgevet[mcp]'
```

This installs the MCP runtime and `judgevet-mcp` command. Supply `JEV_API__KEY`
through the environment before running it. The launcher below loads it through
direnv.

## Run the published MCP command

Prerequisites: `uv` and `direnv` installed. `/absolute/path/to/project` is any
trusted project directory with an approved `.envrc` exporting `JEV_API__KEY`.
No judgevet checkout is required. Keep secrets outside checked-in
configuration, command arguments, or diagnostics.

Execute the following command to launch the MCP server:

```bash
direnv exec /absolute/path/to/project uvx --from 'judgevet[mcp]==0.7.0' judgevet-mcp
```

This command pins judgevet to version 0.7.0. To update, replace `0.7.0` with a
newer published version after verification. Note that only the judgevet package
is pinned; transitive dependencies may still resolve differently. The server
waits for client input on stdin and closes on EOF, emitting frames on stdout
and diagnostics on stderr.

## Optional: run MCP from a source checkout

For development, use a checkout containing the supported command. Install uv and direnv.
Replace `/absolute/path/to/judgevet` with that checkout's absolute path.
Its reviewed, already-authorized `.envrc` must export `JEV_API__KEY`.
Keep the credential outside checked-in files, TOML, command arguments and
printed diagnostics.

From any working directory, the launcher is:

```bash
direnv exec /absolute/path/to/judgevet uv run --directory /absolute/path/to/judgevet --locked --extra mcp judgevet-mcp
```

[direnv exec](https://direnv.net/man/direnv.1.html) loads the authorized
`.envrc` at launch. This does not depend on an interactive shell startup file.
The command serves MCP over stdio and waits for a client; it is not an
interactive question prompt. EOF ends a manual run. Protocol output uses
stdout; diagnostics use stderr.

## Configure Codex for a project

Create or edit `.codex/config.toml` in your trusted project directory. Keep
other settings unchanged. The placeholder refers to your project's approved
`.envrc`. Ensure `direnv` and `uvx` are on `PATH`, or use absolute executable
paths.

```toml
[mcp_servers.judgevet]
command = "direnv"
args = ["exec", "/absolute/path/to/project", "uvx", "--from", "judgevet[mcp]==0.7.0", "judgevet-mcp"]
```

Codex loads project settings only for trusted projects. User-wide settings
instead live in `~/.codex/config.toml`. See the official
[MCP setup](https://learn.chatgpt.com/docs/extend/mcp) and
[configuration precedence](https://learn.chatgpt.com/docs/config-file/config-basic).
Explicit CLI flags override saved configuration.

From the configured project, inspect the saved entry:

```bash
codex mcp get judgevet
```

This checks configuration, not live discovery. Start a fresh Codex CLI session,
or restart the configured desktop/IDE client. In the CLI, `/mcp` shows active
servers. Confirm the judgevet server exposes exactly `ask_noul`, `ask_choice`
and `ask_score`, then ask the agent to call each tool with a small question.

## Verify the connection

Use a state and an instruction for each call. Choice also takes a criteria map;
Score takes an ordered criteria list. Check the returned structured content:

| Tool | Expected content |
|---|---|
| `ask_noul` | `noul` probability between 0 and 1, resolved model, usage |
| `ask_choice` | selected `choice`, `confidence`, `probabilities`, model, usage |
| `ask_score` | numeric `score`, `confidence`, `probabilities`, `legend`, model, usage |

A successful call has no tool error and returns model and usage fields.
This verifies integration, not the accuracy of a judgment.

## When MCP does not connect

If the server fails to start, first check that the configured executable is on
`PATH` and that the project path exists. If using direnv, check that the
project's `.envrc` is approved. Do not print the environment or credential.
Check that a key is supplied through `JEV_API__KEY` or `TYPESAFE_API_KEY`.
Read [credential handling](../../SECURITY.md#credentials) before changing it.

If the process starts but tools are missing, inspect the host's saved server
configuration. Start a fresh host session and repeat discovery. A saved entry
is not proof of a connection. A standalone SDK check is not proof that the
host loaded the tools. Confirm all three tools in the session you intend to use.

If initialization fails with `invalid_data`, record the judgevet version,
launcher command with sensitive values removed, host version and failure stage.
Intermittent failures have been observed with the published launcher; their
cause remains unknown. Successful later runs do not establish a cache or timeout
remedy. Do not delete caches or increase timeouts on that evidence alone.
If it persists, report a minimal reproduction with synthetic data through the
[repository issue form](https://github.com/Alberto-Codes/judgevet/issues/new).

Review [diagnostic disclosure limits](../../SECURITY.md#diagnostics-and-error-content)
before sharing output. Use the private reporting path there for vulnerabilities.
If discovery succeeds but a call fails, check the key and supplied tool arguments.
Do not interpret a service or tool error as a negative judgment.
