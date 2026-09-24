---
status: draft
---

# Publish the MCP registry listing

Status: **draft**. Manifest validation, submission and an accepted listing are
separate events. Follow [the release procedure](cut-a-release.md) before submitting
metadata for a new published package.

## Manifest contract

The root [server.json](../../server.json) follows the official
[2025-12-11 schema](https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json).
The regression fixture is a verbatim download with SHA-256
`3fba09590c99f61735d234822279f4223fab9e300c0a81e81c91ab62a4114de0`.
Compare it with the official schema during release review. An offline check
against this fixture does not prove that the registry still uses that schema.

The package identifier is `judgevet`. The manifest installs `judgevet[mcp]`
and selects the existing `judgevet-mcp` executable. It prompts for a secret
`JEV_API__KEY` for ordinary direct TypeSafe use. It stores no credential.
Existing credential-command and gateway settings remain supported outside this
minimal configuration. Tool inputs leave the host for the configured service;
review [data disclosure](../../SECURITY.md#data-sent-to-the-service).

The tested [VS Code converter](https://github.com/microsoft/vscode/blob/ad77169b64ccc8c9b2401b67f29d99efd487e3c0/src/vs/platform/mcp/common/mcpManagementService.ts)
places runtime arguments before `identifier@version`. For version `VERSION`,
the resulting command is `uvx --from 'judgevet[mcp]==VERSION' judgevet-mcp judgevet@VERSION`.
The existing MCP entrypoint ignores the trailing package identity argument.
The manifest uses a fixed variable to keep the explicit package pin synchronized.
This is a tested consumer convention, not proof that every registry client
constructs the same command. Hosts can use the explicit pinned launcher in
[the connection guide](../how-to/connect-mcp.md) when their converter differs.
Do not rename the package identifier to the executable or add extras to it:
the registry uses that identifier to fetch PyPI metadata.

release-please updates the manifest's root version, package version and runtime
variable through three JSONPath extra-file entries. The
[release configuration checks](../../scripts/release_config/versions.cjs) execute
the actual release-please 17.3.0 updater resolved by the configured v4 action.
When upgrading that action, review its resolved dependency and update the locked
check tooling together. Node and npm are development gate prerequisites; they
are not library or CLI dependencies. Install hooks as described in AGENTS.md.

## Validate before submission

Run `uv run python -m scripts.registry_manifest` to check the schema and fixed
launch contract. It checks seven version values: project, root Python export,
release-please manifest, uv.lock, registry version, package version and uvx pin.
Run `bash scripts/check_release_config.sh` to execute the actual configured
updater for minor, major and prerelease targets. Commit, push and CI run both.

Run `direnv exec . uv run python -m scripts.smoke_registry_release --wheel /absolute/candidate.whl`
with the approved environment. The runner checks wheel metadata and ownership. It uses a fresh uvx cache
outside the checkout. A uv dependency override maps the requested package to
that exact wheel. The override preserves only the
extras requested by the manifest. It does not add MCP when the manifest omits it.
The resulting argv discovers and calls all three tools. This candidate mapping
is not evidence of index publication.

After publication, omit `--wheel` to resolve the actual PyPI package through the
same manifest argv. Keep the independent downloaded-artifact checks and hashes
from the release procedure. A version pin does not lock transitive dependencies.
Default tests use synthetic loopback answers. Explicit release smoke calls use
the service and preserve the existing live-evidence limits.

Send the exact manifest to the production validation endpoint:

```bash
curl --fail-with-body -H 'Content-Type: application/json' \
  --data-binary @server.json \
  https://registry.modelcontextprotocol.io/v0.1/validate
```

Require `valid: true` and inspect every issue. This endpoint does not establish
package ownership, authentication or acceptance of a publication. See the
[official registry API](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/official-registry-api.md).

## Submit and confirm separately

The [PyPI ownership requirements](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/package-types.mdx)
require `mcp-name: io.github.Alberto-Codes/judgevet` in the published version's
package description. README supplies it as an HTML comment. Verify the marker
in the actual index metadata. TestPyPI is not a supported registry package source.
Do not submit against historical 0.9.0: its published description lacks the marker.

Use the official [publisher instructions](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx).
Authenticate for `io.github.Alberto-Codes/*` and publish the accepted manifest.
GitHub Actions OIDC is supported; a local GitHub login is not registry login.
Keep tokens out of commands printed in evidence and out of repository files.
Record the submission command, exact manifest commit, package version and
publisher response on the release tracker. If authentication or namespace
ownership fails, report the external blocker without claiming a listing.

Finally query the [registry API](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.Alberto-Codes%2Fjudgevet).
Require the exact name and version with active registry metadata and matching
package/launcher fields. Record that response separately from submission.
Registry metadata acceptance does not prove every host installed or reloaded
the server. Do not promote modern protocol paths, other models, unseen error
bodies or gateway deployments through these checks.
