---
status: draft
---

# Install judgevet

The published 0.2.0 package provides the library and CLI. The supported
`judgevet-mcp` command is available on main and awaits the
[next release](https://github.com/Alberto-Codes/judgevet/issues/116).
Installing the published MCP extra alone does not provide that command yet.

## Install the library

Use Python 3.12 or newer. In a virtual environment with pip, run:

```bash
python -m pip install judgevet
```

Alternatively, in an existing uv project, run:

```bash
uv add judgevet
```

Independent installs resolved imports from their virtual environments'
site-packages. The downloaded published 0.2.0 wheel contains
`judgevet/py.typed`. See the
[installation measurements](https://github.com/Alberto-Codes/judgevet/issues/37#issuecomment-5771877533).
The base installation does not require the MCP runtime.

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

This adds the MCP runtime. Published 0.2.0 has no `judgevet-mcp` entry point;
use the source instructions below until the next release is verified.

## Run MCP from a source checkout

Use a checkout containing the supported command. Install uv and direnv.
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

In a trusted project's `.codex/config.toml`, add the following table. Preserve
other settings. Replace both placeholder paths with the source checkout path.
The Codex process must find `direnv` and `uv` on its PATH; otherwise use their
absolute executable paths.

```toml
[mcp_servers.judgevet]
command = "direnv"
args = ["exec", "/absolute/path/to/judgevet", "uv", "run", "--directory", "/absolute/path/to/judgevet", "--locked", "--extra", "mcp", "judgevet-mcp"]
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

The [issue evidence](https://github.com/Alberto-Codes/judgevet/issues/37#issuecomment-5771877533)
records discovery and all three live calls from an isolated source-wheel
installation and the configured launcher. That unreleased wheel still has
0.2.0 metadata; it is distinct from the published 0.2.0 wheel. Those checks
exercise legacy initialization. A separate SDK or wire probe does not prove
that an already-running Codex session reloaded its native tools.
