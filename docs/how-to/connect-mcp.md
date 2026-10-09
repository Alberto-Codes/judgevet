---
status: draft
---

# Connect an MCP host

Status: **draft**. These recipes follow current host documentation. Mechanical
checks parse the exact configurations and exercise isolated launchers. They do
not prove that a host loaded them. The
[frozen evidence record](../history/status-2026-10-09.md#onboarding-release)
holds the recorded host observations.
Codex CLI and Pi returned live answers. VS Code and Claude Code reached
discovery; account access blocked their calls. Cursor and Desktop remain
unverified in-host. See that record for exact versions and limits.
Unavailable-host checks are [deferred](https://github.com/Alberto-Codes/judgevet/issues/167).

Choose [VS Code](#vs-code), [Cursor](#cursor), [Claude Code](#claude-code),
[Claude Desktop](#claude-desktop), or [Codex](#configure-codex-for-a-project).
[Pi uses the CLI](#pi-cli-access), not MCP. Tool calls need a TypeSafe key and
service access. A local Ollama server needs neither; see
[Use Ollama as a local server](use-ollama.md). Inputs go to Jev; review
[data disclosure](../../SECURITY.md#data-sent-to-the-service).

## Install the optional MCP runtime

Choose one installation method. For a persistent command, use either a Python
3.12-or-newer virtual environment with pip:

<!-- x-release-please-start-version -->
```bash
python -m pip install 'judgevet[mcp]==0.19.0'
```
<!-- x-release-please-end -->

Or install a standalone tool with uv:

<!-- x-release-please-start-version -->
```bash
uv tool install 'judgevet[mcp]==0.19.0'
```
<!-- x-release-please-end -->

Configure the host with the installed `judgevet-mcp` executable's absolute
path and an empty `args` array. This avoids GUI `PATH` differences. The MCP
extra is required for this server; the base library and CLI do not need it.

## Run the published MCP command

Alternatively, install [uv](https://docs.astral.sh/uv/getting-started/installation/)
and let the host execute the package with uvx. No prior judgevet installation
or source checkout is required:

<!-- x-release-please-start-version -->
```bash
uvx --from 'judgevet[mcp]==0.19.0' judgevet-mcp
```
<!-- x-release-please-end -->

The host recipes below use this alternative. Use the absolute path to `uvx`
if the host cannot find it. uv can provision Python 3.12 or newer. According
to [uv's tool guide](https://docs.astral.sh/uv/guides/tools/), uvx executes in an
isolated cached environment; `uv tool install` installs a persistent command.
Do not run both installation methods as sequential prerequisites.

The pin identifies the published judgevet version, not all transitive
dependencies. Replace it with a newer published version after verification.
Manual execution waits for MCP input; EOF ends it. Protocol frames use stdout
and diagnostics use stderr. Use the host to send tool calls.

## Supply a credential

For VS Code and Cursor, create a private UTF-8 environment file outside the
repository. Put `JEV_API__KEY=` followed by your key on one line. Replace the
`/absolute/path/to/judgevet.env` placeholder below with its absolute path.
Restrict file access to your user. Never commit or share its contents.

Claude Desktop uses a different file: one credential token with an optional
trailing newline, without `JEV_API__KEY=`. Replace its
`/absolute/path/to/judgevet.key` placeholder. judgevet reads this through
[`JEV_API__KEY_FILE`](../reference/configuration.md#credential-sources).
An environment file and a key file have different formats.

For Claude Code, Codex CLI and Pi, start the host from a shell with the key
exported. In Bash, read it without echoing or putting it in shell history:

```bash
read -r -s -p 'TypeSafe key: ' JEV_API__KEY
printf '\n'
export JEV_API__KEY
```

On PowerShell, use your approved secret provider to populate the process
environment before launching the CLI host. Do not paste a key into a command.
Desktop/IDE launches do not necessarily inherit a terminal's environment.
Use the file-based GUI recipes instead. Existing literal, file and command
sources retain their [precedence](../reference/configuration.md#credential-sources).

## VS Code

Run **MCP: Open User Configuration** to configure the current user profile,
or save this in `.vscode/mcp.json` for a workspace. **MCP: Add Server** also
provides a guided flow. Merge the entry with existing servers.

<!-- x-release-please-start-version -->
```json
{
  "servers": {
    "judgevet": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "judgevet[mcp]==0.19.0", "judgevet-mcp"],
      "envFile": "/absolute/path/to/judgevet.env"
    }
  }
}
```
<!-- x-release-please-end -->

Trust the workspace when prompted. Use **MCP: List Servers** to start the
server and review its trust prompt.
Open Chat's tool picker and enable judgevet's four tools. Ask the agent to
[call each tool](#verify-the-connection). Restart the server from its controls
after editing configuration; inspect its output if startup fails. If the
server still uses old settings, reload the window and start it again.
Chat calls require an available model and its account access.

This recipe uses `envFile`. VS Code also supports password input variables on
the extension-host route, but current Agent Host sessions do not receive
configurations requiring interactive inputs. Record which route you use.
See [management](https://code.visualstudio.com/docs/agent-customization/mcp-servers)
and the [configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration).
The root is `servers`, without an outer `mcp` object.

## Cursor

Save this in `.cursor/mcp.json` for the project or `~/.cursor/mcp.json` for
personal use. Merge it with other entries. Project entries take precedence
when the same name appears in both locations.

<!-- x-release-please-start-version -->
```json
{
  "mcpServers": {
    "judgevet": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "judgevet[mcp]==0.19.0", "judgevet-mcp"],
      "envFile": "/absolute/path/to/judgevet.env"
    }
  }
}
```
<!-- x-release-please-end -->

Save and restart Cursor. Inspect **Customize > MCPs**, enable the server and
its tools, then request the three calls below in Agent chat. Check **Output >
MCP Logs** for startup failures. Toggle or re-add the test entry after a fix.
Cursor supports `${env:NAME}` interpolation, but this file-based route avoids
assuming shell inheritance. See the [reference](https://prod.cursor.com/docs/mcp)
and [setup guide](https://prod.cursor.com/help/customization/mcp).
Cursor Agent CLI inspection is not evidence that the IDE loaded a server.

## Claude Code

After exporting the key, use the native project-scoped add command:

<!-- x-release-please-start-version -->
```bash
claude mcp add --transport stdio --scope project judgevet --env 'JEV_API__KEY=${JEV_API__KEY}' -- uvx --from 'judgevet[mcp]==0.19.0' judgevet-mcp
```
<!-- x-release-please-end -->

Keep `judgevet` before `--env`: that option accepts multiple values. The
single quotes preserve the variable reference, not the secret value.
The equivalent project `.mcp.json` entry is:

<!-- x-release-please-start-version -->
```json
{
  "mcpServers": {
    "judgevet": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "judgevet[mcp]==0.19.0", "judgevet-mcp"],
      "env": {"JEV_API__KEY": "${JEV_API__KEY}"}
    }
  }
}
```
<!-- x-release-please-end -->

Use `--scope user` for personal cross-project setup instead. Inspect with
`claude mcp get judgevet`; `claude mcp list` checks connection. Start Claude
from the credential-bearing shell, approve project configuration, inspect
`/mcp`, and request the three calls. Restart the session after changes.
Missing variables can remain literal with a warning: inspect connection
status before calling. An account usage limit can block calls after successful
MCP discovery. `${VAR}` is Claude Code syntax, not Cursor syntax.
See [Claude Code MCP](https://code.claude.com/docs/en/mcp).

## Claude Desktop

This is manual local-server setup, not extension installation. judgevet does
not ship a `.mcpb` bundle or claim a Desktop directory listing. Current
[Desktop guidance](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)
favors extensions with UI-managed sensitive settings; that packaging is
[deferred](https://github.com/Alberto-Codes/judgevet/issues/166).
This manual route is documented and mechanically checked, not host-tested.

Open Desktop **Settings > Developer > Edit Config**. Merge this entry into
`claude_desktop_config.json`. The official
[manual guide](https://modelcontextprotocol.io/docs/develop/connect-local-servers)
places it at `~/Library/Application Support/Claude/claude_desktop_config.json`
on macOS and `%APPDATA%\Claude\claude_desktop_config.json` on Windows.
Use the UI to locate configuration on other supported platforms.

<!-- x-release-please-start-version -->
```json
{
  "mcpServers": {
    "judgevet": {
      "command": "uvx",
      "args": ["--from", "judgevet[mcp]==0.19.0", "judgevet-mcp"],
      "env": {"JEV_API__KEY_FILE": "/absolute/path/to/judgevet.key"}
    }
  }
}
```
<!-- x-release-please-end -->

Use actual absolute paths for both the executable and key file. On Windows,
escape backslashes in JSON or use forward slashes, for example
`C:/Users/your-name/private/judgevet.key`. Do not use shell interpolation.
Fully quit Desktop and reopen it. Inspect **Connectors** for tools and
**Developer** settings for connection status/logs, then request all three calls.
Check paths and key-file permissions if it fails.
[Supported platforms](https://support.claude.com/en/articles/10065433-install-claude-desktop)
include macOS, Windows and a Linux beta with stated distribution requirements.
A browser session does not exercise this local Desktop route.

## Configure Codex for a project

Save this in `.codex/config.toml` in a trusted project, or in
`~/.codex/config.toml` for user-wide settings. Merge with existing settings.

<!-- x-release-please-start-version -->
```toml
[mcp_servers.judgevet]
command = "uvx"
args = ["--from", "judgevet[mcp]==0.19.0", "judgevet-mcp"]
env_vars = ["JEV_API__KEY"]
```
<!-- x-release-please-end -->

After exporting the key, start Codex CLI from that shell. `env_vars` forwards
the named environment variable without storing its value in TOML. Inspect
saved configuration with:

```bash
codex mcp get judgevet
```

This is not live discovery. In the fresh CLI session, use `/mcp`, confirm the
four tools, and request the calls below. Restart the configured client after
changes. Accept project trust through Codex before loading project settings.
A command-line trust override alone did not load this recipe in CLI 0.156.1.
Check trust, executable path and startup diagnostics if tools are absent.

Approve the requested tool calls in the host. Headless execution with approval
policy `never` can discover tools while rejecting every call. For authorized
automation, configure approval for each named tool explicitly; consult
[tool approval settings](https://learn.chatgpt.com/docs/config-file/config-reference).
Discovery alone does not establish that a call was approved or completed.
See [MCP setup](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) and
[configuration precedence](https://learn.chatgpt.com/docs/config-file/config-basic).

## Pi CLI access

Pi's [official guidance](https://github.com/earendil-works/pi/tree/main/packages/coding-agent#philosophy)
leaves MCP to extensions and supports CLI tools through its Bash tool.
This recipe selects the existing CLI, with no MCP extension or discovery claim.
Install base judgevet persistently as described in [installation](install.md#run-the-cli),
or use the uvx alternative below. Start Pi from the shell where you exported
the key. Ask Pi to run these exact commands through its Bash tool:

<!-- x-release-please-start-version -->
```bash
uvx --from 'judgevet==0.19.0' judgevet 'Two checks passed.' '{"noul_question":{"type":"noul","instructions":"Did the checks pass?"}}' --json
```
<!-- x-release-please-end -->

<!-- x-release-please-start-version -->
```bash
uvx --from 'judgevet==0.19.0' judgevet 'Two checks passed.' '{"choice_question":{"type":"choice","instructions":"Did the checks pass?","criteria":{"yes":"Yes","no":"No"}}}' --json
```
<!-- x-release-please-end -->

<!-- x-release-please-start-version -->
```bash
uvx --from 'judgevet==0.19.0' judgevet 'Two checks passed.' '{"score_question":{"type":"score","instructions":"Did the checks pass?","criteria":["Poor","Fair","Good","Excellent"]}}' --json
```
<!-- x-release-please-end -->

Inspect the actual tool execution and JSON answers, model and usage. A model's
claim that it ran a command is insufficient. Command-not-found errors require
checking Pi's executable path; missing credentials require restarting Pi from
the configured shell. An optional [Pi skill](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md)
can point to these commands, but no skill installation is required.

## Verify the connection

For the recipes above, discover exactly `ask_noul`, `ask_choice`, `ask_score`
and `evaluate_policy`. Call the three `ask_*` tools to verify the connection.
Send these complete argument objects to the corresponding tools:

`ask_noul`:

```json
{"state":"Two checks passed.","instruction":"Did the checks pass?"}
```

`ask_choice`:

```json
{"state":"Two checks passed.","instruction":"Did the checks pass?","criteria":{"yes":"Yes","no":"No"}}
```

`ask_score`:

```json
{"state":"Two checks passed.","instruction":"Did the checks pass?","criteria":["Poor","Fair","Good","Excellent"]}
```

| Tool | Expected structured answer |
|---|---|
| `ask_noul` | `noul` probability between 0 and 1, `model`, `usage` |
| `ask_choice` | `choice`, `confidence`, `probabilities`, `model`, `usage` |
| `ask_score` | numeric `score`, `confidence`, `probabilities`, `legend`, `default_criteria`, `model`, `usage` |
| `evaluate_policy` | `model`, `usage`, `answers`, `policy` |

The text block carries the same JSON as the structured content. A host that
shows only text shows this JSON. `default_criteria` is `false` here because
the call supplies `criteria`.

Require a successful tool answer, not a tool error. A service error returns a
tool result with `isError` true and the error text. A tripped spend cap also
returns `isError` true and says the server must restart. Restart the server
from the host before you retry. Values vary. This checks integration, not
judgment accuracy. See the [MCP reference](../reference/mcp.md)
and [adapter contract](../../src/judgevet/adapters/inbound/mcp.py).
For failures, use [host-specific diagnosis](troubleshoot.md#when-mcp-does-not-connect).

The [official registry listing](../maintainers/mcp-registry.md) is metadata
publication. It does not establish availability in VS Code's gallery,
Cursor's marketplace or Desktop's directory. Use these manual routes unless
a native install link has been separately verified.

## Optional: use direnv

If you already use direnv, it can wrap the published launcher. The project
must have a reviewed, approved `.envrc` exporting the key:

<!-- x-release-please-start-version -->
```bash
direnv exec /absolute/path/to/project uvx --from 'judgevet[mcp]==0.19.0' judgevet-mcp
```
<!-- x-release-please-end -->

This is an alternative credential mechanism, not a judgevet prerequisite.
[direnv exec](https://direnv.net/man/direnv.1.html) loads the approved environment
without relying on an interactive shell startup file.

## Optional: run MCP from a source checkout

For development only, use a checkout and its approved environment:

```bash
direnv exec /absolute/path/to/judgevet uv run --directory /absolute/path/to/judgevet --locked --extra mcp judgevet-mcp
```

You can instead supply credentials explicitly and run
`uv run --locked --extra mcp judgevet-mcp` from the checkout. Consumer host
setup uses the published package and needs neither this checkout nor direnv.


## Run an application provider

An application launcher can import `main` from
`judgevet.adapters.inbound.mcp_entrypoint` and call
`main(provider_factory=application_factory, model="application-model")`.
The factory returns a context manager yielding a `SystemOnePort`.
Configure the MCP host to execute that application launcher.
The application owns its provider dependencies and configuration.

For an already acquired provider, call `main(port=provider, model="application-model")`
and close it in the application after serving ends. Explicit selection bypasses
hosted credentials and settings. The existing `judgevet-mcp` command retains
its hosted defaults. See [provider lifetime and cancellation](../reference/mcp.md#application-selected-providers).
For a launcher on a self-hosted model, see [Use a self-hosted judgment provider](use-a-self-hosted-provider.md).
For hooks, question wording and shadow mode, see [Use judgevet in an agent harness](use-in-an-agent-harness.md).


The server also exposes `evaluate_policy`. Supply `state`, keyed `questions`
and the existing JSON `policy` object. Use the structured answer envelope and
its ordered policy report. A valid unmet policy is a successful tool response;
validation and declared provider failures are tool errors. The application
launcher selects the model. See the [policy tool contract](../reference/mcp.md#keyed-policy-tool).

For an application provider that supports images, add `evidence` to
`evaluate_policy` as JSON text. Encode image bytes as standard base64 and use
ordered attachment IDs to bind images to questions. Keep state and image bytes
separate. A minimal empty value is `{"images":[],"by_question":{}}`; this retains
text routing. Nonempty images require the media provider extension. See the
[image evidence contract](../reference/mcp.md#image-evidence) for fields,
limits and error behavior. This addition does not claim live provider
compatibility.
