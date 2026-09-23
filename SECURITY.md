---
status: draft
---

# Security policy

This page describes judgevet 0.6.0. It is an implementation review, not a
security certification. See [installation](docs/how-to/install.md) and the
[release evidence and API verification limits](STATUS.md).

## Report a vulnerability

Use GitHub's private [Report a vulnerability form](https://github.com/Alberto-Codes/judgevet/security/advisories/new).
Private vulnerability reporting is enabled for this repository and was checked
through GitHub's repository API during this documentation review. Sign in to
GitHub to submit a report. Do not put vulnerabilities, credentials or private
state in a public issue.

Include the affected version, impact and a minimal reproduction using dummy
credentials and synthetic data. Review attachments and logs before submitting.
This policy does not promise a response deadline or backports to older releases.

## Credentials

The CLI and MCP composition roots use
[Settings](src/judgevet/adapters/inbound/settings.py). They accept
`JEV_API__KEY` or the compatibility alias `TYPESAFE_API_KEY`; the former wins
when both are set. Settings can also be constructed in Python. The library's
sync and async HTTP adapters instead take an explicit `api_key` argument and
do not load credentials from the environment themselves.

Settings wraps the key in Pydantic's
[SecretStr](https://docs.pydantic.dev/latest/api/types/#pydantic.types.SecretStr),
which masks its normal string and representation output. The composition roots
unwrap it for the HTTP adapter. The adapter retains a plain Python string and
puts it in the authentication header. Masking the settings object is not a
promise that arbitrary tracebacks, debuggers or memory dumps cannot expose it.
The [settings tests](tests/unit/test_settings.py) cover masking and precedence.

judgevet does not create a credential file or a persistent key store. Supply
credentials through your process environment or application secret provider.
If you use direnv, it reads your approved `.envrc`; judgevet does not encrypt
that file. Git ignores `.envrc` in this checkout, but ignoring a file does not
protect it from local readers or copies. Keep credentials out of committed
files and command arguments.

## Data sent to the service

The [HTTP adapter](src/judgevet/adapters/outbound/http.py) sends the supplied
state, named questions (including instructions and criteria), and requested
model as JSON, with the API key in a Bearer authorization header. This follows
the [official API quick start](https://docs.typesafe.ai/introduction/quickstart).
The default service is `https://api.typesafe.ai`; the CLI and MCP accept
`JEV_API__BASE_URL` or `TYPESAFE_BASE_URL`, and library callers can supply
`base_url` directly. A configured replacement service receives the same data
and credential. Only send content you are authorized to disclose to it.

CLI file/stdin inputs become state or questions before the call. CLI policy
rules are evaluated locally; they are not added to the API payload. MCP tools
send the state and question supplied by the MCP client and return answers to
that client over stdio. The client's own storage and logging are outside
judgevet's control. judgevet does not establish the remote service's retention,
training or deletion policy.

## Diagnostics and error content

The CLI and MCP configure diagnostics on stderr. At the default level, routine
HTTP calls emit no diagnostic. `JEV_LOG__LEVEL=debug` enables an `http.call`
event containing the requested model, question count, status (or null), and
success/error outcome. It excludes state, question text, headers and exception
text. Do not put sensitive content in a model identifier: that value is logged.
`JEV_LOG__FORMAT=json` or `console` selects the renderer; automatic mode uses
JSON off a terminal. Library imports do not configure logging; applications
own their logging configuration.

MCP SDK warning/error diagnostics become a fixed `mcp.runtime` event with
severity, without the SDK's message or traceback. This protects **diagnostic
stderr**, not MCP JSON-RPC error content on stdout. CLI error envelopes and
library exceptions are also separate from these diagnostic events. They can
contain service-supplied message text. The adapter discards validation `input`
fields and malformed detail structures; it does not scrub arbitrary strings
returned by a service. Exception chains can retain HTTP requests and answers.
Review protocol errors, CLI errors and tracebacks before sharing them.

The [logging adapter](src/judgevet/adapters/inbound/logs.py) masks configured
secret field names and PEM-looking strings and omits traceback frame locals.
It is not a general secret detector. Applications can configure other handlers,
and arbitrary exception messages or strings under other field names may expose
data. The [HTTP stream tests](tests/unit/test_logging_streams.py) and
[MCP stream tests](tests/unit/test_logging_mcp.py) prove the bounded diagnostic
behavior with synthetic canaries; they do not prove universal redaction.
