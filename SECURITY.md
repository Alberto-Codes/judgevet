---
status: draft
---

# Security policy

The credential, transport and diagnostic review below was performed for
judgevet 0.6.0. The 0.7.0 changes leave those paths unchanged and add local
typed policy evaluation and JSON decoding. This is an implementation review,
not a new security certification. See [installation](docs/how-to/install.md) and the
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
model as JSON. It sends the API key in a Bearer authorization header. This follows
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

## Cryptographic posture

### Transport and certificates

The default URL uses HTTPS. CLI and MCP
[settings validation](src/judgevet/adapters/inbound/settings.py) rejects remote
plaintext HTTP but permits `http://localhost` and `http://127.0.0.1` for local
testing. Loopback HTTP is unencrypted. Direct library adapter construction
does not run that validator: library callers must choose an HTTPS URL and a
trusted transport themselves.

The sync and async [HTTP adapters](src/judgevet/adapters/outbound/http.py)
delegate TLS to HTTPX. They do not override certificate verification, install
certificate pins or select cipher suites. With the default transport,
[HTTPX verifies HTTPS certificates and host identity](https://www.python-httpx.org/advanced/ssl/)
by default. It uses the certifi CA bundle rather than automatically using the
OS trust store. The reviewed lockfile resolves HTTPX 0.28.1. The adapters also
accept caller-supplied transports, whose behavior belongs to the caller.

HTTPX's default environment support remains enabled.
[`SSL_CERT_FILE` and `SSL_CERT_DIR`](https://www.python-httpx.org/environment_variables/)
can replace its default trust roots; `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`
and `NO_PROXY` affect routing. Review the launch environment as part of a
deployment. Python's [ssl module](https://docs.python.org/3/library/ssl.html)
uses OpenSSL; the available protocols and cryptographic behavior depend on
that runtime and its configuration. judgevet does not perform its own
certificate validation or supply a separate cryptographic implementation.

### Storage and memory

The request path has no persistent credential, state or answer store and no
audit sink. The [CLI](src/judgevet/adapters/inbound/cli.py) prints answers and
errors; [file inputs](src/judgevet/adapters/inbound/cli_inputs.py) read
caller-owned files. Shell redirection, MCP hosts and application log handlers
can persist that output. Python, installers and the platform can also write
caches, swap or crash dumps. judgevet supplies no encryption at rest or
retention control for those artifacts; their storage and protection belong to
the application and platform.

`SecretStr` masks display; it is not encrypted or locked memory. Unwrapped keys,
HTTP headers and serialized payloads can have multiple in-memory copies.
Python [strings are immutable](https://docs.python.org/3/library/stdtypes.html#text-sequence-type-str),
and the interpreter manages its [object heap and allocators](https://docs.python.org/3/c-api/memory.html).
Given those constraints and the adapter's plain strings, judgevet cannot
guarantee secret zeroization when objects are freed. Closing an adapter releases
network resources; it does not erase every copy of a credential.

### Egress and compliance limits

The production request path targets the configured service and has no judgevet
telemetry or phone-home endpoint. This is not a guarantee of exactly one
outbound connection: [HTTPX uses connection pools](https://www.python-httpx.org/advanced/clients/),
and DNS, proxies and caller-supplied transports affect network activity.
The default HTTPX clients do not follow redirects; the
[redirect test](tests/unit/test_http_adapter.py) checks that setting. Network
allowlists and enforcement belong to the deployment.

judgevet does not claim FIPS compliance or automatically inherit it from the
OS. It neither configures nor verifies a FIPS provider. OpenSSL documents
[explicit FIPS module configuration requirements](https://docs.openssl.org/3.0/man7/fips_module/);
a compliant deployment requires assessment of the actual cryptographic module,
runtime and configuration. Certificate pinning, a judgevet mTLS configuration,
encrypted storage and enterprise audit controls are not shipped features of
0.7.0.
