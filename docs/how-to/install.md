---
status: draft
---

# Install judgevet

Published judgevet 0.3.0 provides the library, CLI and `judgevet-mcp` command.
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

The published 0.3.0 wheel includes `judgevet/py.typed`. Independent base
installs resolve under their virtual environments' site-packages without the
MCP runtime. See the [published artifact proof](https://github.com/Alberto-Codes/judgevet/issues/116#issuecomment-5773724671).

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
direnv exec /absolute/path/to/project uvx --from 'judgevet[mcp]==0.3.0' judgevet-mcp
```

This command pins judgevet to version 0.3.0. To update, replace `0.3.0` with a
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
args = ["exec", "/absolute/path/to/project", "uvx", "--from", "judgevet[mcp]==0.3.0", "judgevet-mcp"]
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

In the Python MCP SDK, initialization returns `server_info`; tool answers use
`structured_content` and `is_error`. Their JSON wire aliases are `serverInfo`,
`structuredContent` and `isError`. See the verified
[SDK compatibility notes](https://github.com/Alberto-Codes/judgevet/issues/114#issuecomment-5771829178).
A successful call has no tool error and returns model and usage fields.
This verifies integration, not the accuracy of a judgment.

The [published artifact proof](https://github.com/Alberto-Codes/judgevet/issues/116#issuecomment-5773724671)
records byte equality and live base/MCP checks on the actual PyPI download.
The [published launcher proof](https://github.com/Alberto-Codes/judgevet/issues/119#issuecomment-5773781232)
records discovery and all three live calls from a temporary working directory
with an empty uv cache. These checks exercise legacy initialization. A separate
SDK or wire probe does not prove that an already-running Codex session reloaded
its native tools.
