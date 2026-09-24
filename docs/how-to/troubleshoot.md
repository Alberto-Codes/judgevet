---
status: draft
---

# Diagnose a failed task

Status: **draft**.

First identify whether installation, local input, connection or a service call
failed. Use synthetic content for a reproduction. Do not print credentials or
share unreviewed service error text. These steps assume the
[installed package](install.md) and the same interpreter/host you intend to use.

| Symptom | Safe check | Next action |
|---|---|---|
| Import or command not found | Check the interpreter and executable paths. | Install into that environment; use its Python or console command. |
| Missing key or `KeyError` | Check the required variable is present in the calling process, without printing it. | Supply the key through the approved provider. Library examples pass it explicitly. |
| Authentication failure | Check which key source takes precedence and the configured service URL. | Correct the selected credential or ask the service administrator; do not guess by dumping the environment. |
| CLI exit 2 | Compare input sources with the file guide and installed help. | Choose exactly one state source and one question source. |
| CLI input failure | Check UTF-8, nonempty content, JSON syntax and duplicate keys. | Correct the input before calling again. |
| Policy definition failure | Match each rule to a question name/type and valid bounds. | Correct and revalidate the policy. |
| Timeout or transport failure | Check service reachability and your approved proxy/CA configuration. | Restore connectivity or review timeout requirements; transport retries require explicit configuration. |
| CLI exit 3 | Read the policy report and returned answers. | Treat it as an unmet policy, not an installation failure. |

The CLI/MCP credential precedence and direct-library differences are documented
in [SECURITY](../../SECURITY.md#credentials). HTTPX proxy and certificate behavior
is described under [transport](../../SECURITY.md#transport-and-certificates).
For library categories, see [error handling](handle-errors.md).

## When MCP does not connect

If the server fails to start, first check that the configured executable is on
`PATH`; use an absolute executable path for GUI hosts. A persistent install
uses `judgevet-mcp` directly. The uvx route requires `uvx` and the MCP extra,
not a prior judgevet installation. If using optional direnv, check that the
project's `.envrc` is approved. Do not print the environment or credential.
Check the selected credential route without printing its value. Environment
files contain `JEV_API__KEY=...`; `JEV_API__KEY_FILE` points to a file containing
only the token. Check file access under the host's user account. An inherited
literal key can override a key file; consult precedence before changing it.
Read [credential handling](../../SECURITY.md#credentials) before changing it.

If the process starts but tools are missing, inspect the host's saved server
configuration. Start a fresh host session and repeat discovery. A saved entry
is not proof of a connection. A standalone SDK check is not proof that the
host loaded the tools. Confirm all three tools in the session you intend to use.

| Host | Inspect and recover |
|---|---|
| VS Code | Use MCP: List Servers and server output. Check `servers` at the root, the private `envFile` path and workspace trust. Restart the server. Interactive input configurations are not forwarded to current Agent Host sessions. |
| Cursor IDE | Inspect Customize > MCPs and Output > MCP Logs. Check `mcpServers`, `envFile` and the executable path. Save and restart Cursor. |
| Claude Code | Use `claude mcp list` and `/mcp`. A missing `${VAR}` can remain literal with a warning. Export the credential before starting a fresh session. |
| Claude Desktop | Use Developer settings/logs and Connectors. Check absolute paths and the private key file; fully quit and restart. Manual setup is not `.mcpb` installation. |
| Codex CLI | `codex mcp get judgevet` checks saved configuration; `/mcp` in a fresh session checks active tools. Check project trust and the exported variable named by `env_vars`. |
| Pi CLI route | Inspect the actual Bash tool execution, exit status and JSON. Check the uvx or persistent CLI path and restart Pi from the configured shell. There is no MCP discovery in this route. |

These controls and schemas follow the sources in the
[host recipes](connect-mcp.md). A controlled nonexistent executable in an
isolated test entry can confirm the host reports a startup failure. Restore
that test entry after the check; do not modify unrelated user servers.

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
