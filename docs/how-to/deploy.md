---
status: draft
---

# Deploy in a container or serverless runtime

Status: **draft**.

Use the library inside your application, or run the CLI as a finite job.
The base package includes both. Install the optional MCP extra only when your
host launches the stdio server. judgevet does not provide an HTTP application
server, a remote MCP endpoint or a load-balancer contract.

This guide targets judgevet 0.8.0. Platform deployment, IAM permissions and
network access remain your responsibility. The container recipe is checked with
synthetic requests; it does not prove a deployment in your cloud account.

## Build a base CLI image

Create a dedicated `image` build directory containing only the Dockerfile and
one reviewed wheel. Keep runtime inputs, credentials and private configuration
outside that directory. After 0.8.0 is published, prepare the wheel:

```bash
mkdir -p image/wheels
python -m pip download --no-deps --only-binary=:all: \
  'judgevet==0.8.0' --dest image/wheels
```

Use a fresh directory so an older wheel cannot enter the image. For a release
candidate, use its verified downloaded wheel instead. Save this as
`image/Dockerfile`:

```dockerfile
FROM docker.io/library/python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY wheels/ /wheels/
RUN python -m pip install --no-cache-dir /wheels/*.whl
USER 65532:65532
ENTRYPOINT ["judgevet"]
```

The image installs the base wheel without MCP. It runs as a non-root user.
Select an approved base-image digest and dependency constraints for repeatable
production builds. This example tag follows Python's maintained image updates.
No vendor credential is needed to build it. Never pass that credential through
Dockerfile `ARG`, `ENV` or `COPY`; Docker documents their persistence in
[build-secret guidance](https://docs.docker.com/build/building/secrets/).

```bash
docker build -t judgevet-job ./image
docker run --rm judgevet-job --help
```

The build and run commands also work with `podman` in place of `docker`.
The repository's acceptance run uses rootless Podman and verifies that the base
image omits MCP. Container engine permissions and registry access are prerequisites.

## Run a job with mounted credentials

Prepare `inputs/state.txt` and `inputs/questions.json` using the
[CLI file recipe](use-cli-files.md). Set `JUDGEVET_KEY_FILE` to the absolute path
of an existing credential file outside the build directory. The runtime must
make that mount readable by container UID 65532 without exposing it to other users.
Use your platform's secret-volume ownership controls.

On SELinux hosts, dedicated input and secret copies also need container labels.
Replace their `--mount` options with `--volume "$PWD/inputs:/inputs:ro,Z"` and
`--volume "$JUDGEVET_KEY_FILE:/run/secrets/jev-key:ro,Z"`.
`Z` changes labels on those host paths; use dedicated runtime copies, not shared
system directories. See [Docker bind-mount labels](https://docs.docker.com/engine/storage/bind-mounts/#configure-the-selinux-label).

```bash
docker run --rm --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=16m \
  --cap-drop ALL --security-opt no-new-privileges \
  --mount "type=bind,src=$PWD/inputs,dst=/inputs,readonly" \
  --mount "type=bind,src=$JUDGEVET_KEY_FILE,dst=/run/secrets/jev-key,readonly" \
  -e JEV_API__KEY_FILE=/run/secrets/jev-key \
  -e JEV_API__TIMEOUT_SECONDS=10 \
  -e JEV_API__MAX_ATTEMPTS=1 \
  -e JEV_LOG__FORMAT=json \
  -e JEV_LOG__LEVEL=debug \
  judgevet-job --state-file /inputs/state.txt \
  --questions-file /inputs/questions.json --json
```

A successful job writes judgment JSON to stdout and one terminal diagnostic to
stderr. Its exit status is zero. Input, source-resolution and judgment failures
produce nonzero status; see the [CLI exit contract](../reference/cli.md).
Keep stdout separate from platform log shipping when it carries customer data.
The runtime root can remain read-only; this client does not persist resolved keys.

The file source loses to a configured literal key. Avoid setting
`JEV_API__KEY` or `TYPESAFE_API_KEY` when you intend the mounted file to win.
For a secret-manager command, omit `KEY_FILE` and configure a trusted command
through `JEV_API__KEY`. Install its executable in your image and provide its
platform identity at runtime. Set `JEV_API__KEY_COMMAND_TIMEOUT` within the
startup budget. Commands are POSIX-only, noninteractive and have bounded output.
They execute without an implicit shell. See [source precedence and limits](../reference/configuration.md#credential-sources).

## Choose the platform entry point

| Platform | Supported integration | Platform requirement |
|---|---|---|
| Cloud Run job | Run the CLI image to completion. | Jobs exit successfully or fail; they do not serve HTTP. |
| Cloud Run service | Call the library from your own HTTP application. | Your ingress server must listen on the configured `PORT` at `0.0.0.0`. |
| Lambda | Call the library from your Python handler. | Package judgevet with the handler and manage the invocation deadline. |
| ECS/Fargate | Run a CLI task or your application containing the library. | Configure task networking, runtime credentials and log collection. |

Cloud Run defines the service/job distinction in its
[container contract](https://docs.cloud.google.com/run/docs/container-contract).
Its [secret configuration](https://docs.cloud.google.com/run/docs/configuring/services/secrets)
supports environment values and mounted files. Match the selected source to
judgevet's precedence. The platform's secret permissions remain separate from
TypeSafe authentication.

For Lambda, start from the [synchronous library recipe](use-library.md).
Your handler supplies validated application state and questions. Bind
`context.aws_request_id` with `bind_request_id` around the invocation's calls.
Check `context.get_remaining_time_in_millis()` before beginning expensive work;
AWS documents both values in the [Python context interface](https://docs.aws.amazon.com/lambda/latest/dg/python-context.html).
Use a runtime-supported secret retrieval path or trusted provider executable;
judgevet does not include a cloud secret-manager SDK.

For Fargate, ECS can inject secret values through a task's `secrets` definition.
A sidecar can instead place a secret in a shared volume for `KEY_FILE`.
AWS documents both patterns and their rotation behavior in
[ECS secret delivery](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data.html).
Restrict the task identity to the needed secret. Do not put the secret into
ordinary task-definition text or image build arguments.

## Budget timeouts and retries together

Choose the platform deadline first. Reserve time for startup, credential
resolution, HTTP work, retry delays, result handling and cleanup. The example
uses a ten-second HTTP operation timeout and one attempt; these are example
settings, not a guaranteed ten-second total deadline.

The HTTP timeout covers individual operations, with a separate five-second
connect timeout. Several operations, streamed reads and retries can exceed one
timeout value. A credential command has its own deadline and cleanup budget.
Use the host application's total deadline and cancellation mechanism as well.
An async host can cancel an awaited call; cancellation cannot prove that remote
processing or billing stopped.

Cloud Run exposes separate [job task deadlines](https://docs.cloud.google.com/run/docs/configuring/task-timeout).
Lambda has a configurable [function timeout](https://docs.aws.amazon.com/lambda/latest/dg/configuration-timeout.html).
Keep the HTTP and source budgets below the remaining platform budget, including
startup overhead. Test failure and shutdown paths under your chosen platform limit.

Retries are opt-in and `MAX_ATTEMPTS` includes the first call. Platform job or
event redelivery can multiply client retries. Replaying a timed-out request can
duplicate work or billing; judgevet supplies no idempotency guarantee.
See [retry settings](../reference/configuration.md#retry-limits).

## Own connections, rotation and diagnostics

An adapter retains its HTTP connection pool, configuration and credential.
It does not reread settings between calls. A context manager per invocation
closes the client predictably. A deliberately shared warm-worker adapter can
reuse connections, but its owner must handle shutdown and credential rotation.
Rebuild it after resolving a replacement key; changing a mount alone does not
change an existing adapter. Do not retain customer state in shared globals.

AWS recommends reusing suitable clients outside the handler in its
[Lambda guidance](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html).
Choose ownership deliberately rather than treating a retained client as stateless.
Do not reuse an async adapter across separate event loops.

Configure `JEV_API__PROXY` and a mounted `JEV_API__CA_BUNDLE` when your approved
network requires them. Keep certificate verification enabled. Standard HTTPX
proxy and certificate environment variables also apply; see
[network precedence](../reference/configuration.md#proxy-and-tls-configuration).
Test egress from the deployed workload, including DNS, proxy access and CA trust.

Use the [event contract](../reference/events.md) for field extraction and caller
correlation. The platform ships stderr; the library has no logging sink.
Scoped request IDs stay in local diagnostics and do not become gateway headers.
Credentials, state and question text do not belong in identifiers.

The MCP executable remains a stdio process launched by its host. This release
does not establish remote MCP scaling, load balancing or session-affinity behavior.
Use [MCP connection guidance](connect-mcp.md) for the supported transport.
