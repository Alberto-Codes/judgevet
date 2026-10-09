---
status: draft
---

# Cut a release

Status: **draft**.

For release maintainers. These procedures publish immutable artifacts.
For package use, start with [installation](../how-to/install.md).

## Release communication

Use Conventional Commit scopes `api`, `cli`, `mcp`, and `deps` to identify affected
surfaces. Generated changelog sections stay grouped by commit type. Add a short
four-surface compatibility table to reviewed release notes; do not rewrite
release-please's machine-parsed PR body or maintain a second changelog.

A documented surface break uses `!` and a `BREAKING CHANGE:` footer describing
the affected callers and migration. Before 1.0, the configured release workflow
bumps the minor version for a break; after 1.0, a break requires a major version.
See [SemVer](https://semver.org/) and [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).
One wheel does not have independently released library/CLI/MCP versions.


release-please manages the version and changelog. Its Python strategy updates
`pyproject.toml`; `extra-files` updates `src/judgevet/__init__.py`. It also
updates `.release-please-manifest.json` and all three version values in
`server.json`. It updates package pins in the [host recipes](../how-to/connect-mcp.md)
through bounded release markers. Host version observations stay unchanged.
See [registry publication](mcp-registry.md). The separate `update-lockfile` job
refreshes `uv.lock` on the release branch. Never edit a version by hand.

The workflow runs the locked release-please engine through
`scripts/release_config/runner.cjs`. Its registered default changelog renderer
changes the prepared commit template's issue label to `references`. Commit
subjects, links and factual `Closes`/`Refs` trailers remain unchanged. This uses
[release-please's extension API](https://github.com/googleapis/release-please/blob/v17.3.0/docs/customizing.md).
GitHub applies closing keywords in commits independently of generated notes;
see [linking issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue).
The runner delegates release and PR creation to fresh engine manifests and
preserves the outputs used by the lockfile job. Historical notes are not rewritten.

Merging the release PR creates a draft and tag. Publishing the draft triggers
`publish.yml`. A draft permits a pause; it does not upload to PyPI.

Release evidence lives in the GitHub Release notes, the release assets and the
PyPI attestations. No post-release commit records it in a file. The
verification commands below check that evidence. The
[verification ledger](../reference/verification-ledger.md) changes only when a
call changes a service claim.

## Authority and prerequisites

Standing authorization permits merging and publishing a release that meets
these criteria without another approval:

- Main and release PR CI are green. Required local gates pass.
- The changelog describes the release and its user-visible changes.
- The gate run reports measured tests and coverage. The
  [verification ledger](../reference/verification-ledger.md) separates verified
  from inferred claims. No inferred claim becomes verified without an exercising call.
- On the optional TestPyPI route, the downloaded candidate passes isolated
  base and MCP checks.
- No unresolved release requirement affects the installation being shipped.

Hold for a human decision if the change breaks a published API, changes what
users should trust in the verified table, or needs unavailable credentials.
Published PyPI files remain immutable. TestPyPI is also a real publication
to an immutable index, not a dry run.

Run the following Bash blocks in one shell from the repository root, with
Python 3.12 or newer, `gh`, `uv`, and configured `direnv`. Inherit the vendor
key through the approved environment. Never print it or put it in a command
or checked-in configuration. Do not enable shell tracing.

## Practised release path

Releases 0.10.2 through 0.16.0 followed this path without a TestPyPI round.
Their GitHub Releases record each one. The steps are:

1. [Freeze the candidate](#freeze-the-candidate): read the release PR head,
   versions, changelog and main CI.
2. [Merge the release PR](#merge-the-accepted-candidate) with
   `--match-head-commit` set to the frozen head.
3. Verify that the tag points at the merge commit.
4. Publish the draft release with reviewed notes. This triggers `publish.yml`.
5. [Verify the PyPI digests and the attestations](#verify-digests-attestations-and-registry).
6. [Log in to the registry](#verify-digests-attestations-and-registry) with `mcp-publisher login github -token "$(gh auth token)"`.
   The device flow is unused. See [registry publication](mcp-registry.md).
7. [Publish the `server.json` file](#verify-digests-attestations-and-registry) from the release commit, not from the checkout.

The publish workflow runs the wheel and MCP smoke steps before upload.
On this path no separate index-wheel check runs.

## Freeze the candidate

Choose the release-please PR and version from its reviewed diff. Read each
operator input before continuing; run IDs below must identify the intended
workflow and commit, not merely the newest run.

```bash
set -euo pipefail
shopt -s nullglob
read -r -p 'Release PR number: ' PR
read -r -p 'Intended version: ' VERSION
RELEASE_BRANCH=$(gh pr view "$PR" --json headRefName --jq .headRefName)
HEAD_SHA=$(gh pr view "$PR" --json headRefOid --jq .headRefOid)
BASE_SHA=$(gh pr view "$PR" --json baseRefOid --jq .baseRefOid)
gh pr checks "$PR"
git fetch origin "$RELEASE_BRANCH" main
git cat-file -e "$HEAD_SHA^{commit}"
for file in pyproject.toml src/judgevet/__init__.py .release-please-manifest.json uv.lock; do
  git show "$HEAD_SHA:$file"
done
git show "$HEAD_SHA:CHANGELOG.md"
gh run list --workflow ci.yml --commit "$BASE_SHA"
EVIDENCE_DIR=$(mktemp -d /tmp/judgevet-release.XXXXXXXX)
```

Inspect all seven version values, including the registry root, package and
uvx pin with `uv run python -m scripts.registry_manifest`. The existing four are: project version, root `__version__`, manifest
root entry, and the root `judgevet` package version in `uv.lock`. All must equal
`VERSION`. Review the changelog and the verification ledger. Inspect the identified
main CI run and require completed success. Fetching does not replace local
files or discard unrelated work.

Keep the generated release PR body intact. release-please parses its version
heading and body structure after merge. Put acceptance evidence in issue or PR
comments, and put reviewed prose in the draft release notes. Replacing the body
in #130 made release-please skip the merged release and propose another version,
even though the workflow was green. Restoring the generated body and rerunning
the same workflow recovered the draft without changing source or index files.
Always verify the expected draft and tag; a green workflow alone is insufficient.

## Optional: publish and verify a TestPyPI candidate

This round is optional. Releases 0.10.2 through 0.16.0 skipped it.
When you use it, verify TestPyPI before merging. This checks what the index serves before using
standing production-release authority. The workflow's `version` input is
**descriptive, not enforced**. The checkout determines the actual version.

```bash
gh workflow run test-publish.yml --ref "$RELEASE_BRANCH" -f "version=$VERSION"
gh run list --workflow test-publish.yml --branch "$RELEASE_BRANCH" \
  --json databaseId,headSha,createdAt,status,url
read -r -p 'TestPyPI run ID for this dispatch: ' TEST_RUN
test "$(gh run view "$TEST_RUN" --json headSha --jq .headSha)" = "$HEAD_SHA"
gh run watch "$TEST_RUN" --exit-status
test "$(gh run view "$TEST_RUN" --json conclusion --jq .conclusion)" = success
gh run view "$TEST_RUN" --verbose
```

Confirm both smoke steps succeeded before upload. Both publishing workflows
build distributions once and download their `dist` artifact in the publishing
job. They require exactly one wheel and pass its path to the base and MCP smoke
runners before OIDC upload. Each smoke step receives the key separately.
Ordinary CI makes no live call.

Download only judgevet from TestPyPI. Dependencies for the isolated installs
come from normal PyPI through the existing runners.

```bash
TEST_ARTIFACT="$EVIDENCE_DIR/test-artifact"
TEST_INDEX="$EVIDENCE_DIR/test-index"
gh run download "$TEST_RUN" --name dist --dir "$TEST_ARTIFACT"
uvx --from pip pip download --index-url https://test.pypi.org/simple/ \
  --no-deps --only-binary=:all: "judgevet==$VERSION" --dest "$TEST_INDEX"
test_artifacts=("$TEST_ARTIFACT"/*.whl)
test_downloads=("$TEST_INDEX"/*.whl)
(( ${#test_artifacts[@]} == 1 ))
(( ${#test_downloads[@]} == 1 ))
TEST_WHEEL=${test_downloads[0]}
cmp "${test_artifacts[0]}" "$TEST_WHEEL"
sha256sum "${test_artifacts[0]}" "$TEST_WHEEL"
direnv exec . python3 scripts/smoke_release.py --wheel "$TEST_WHEEL"
direnv exec . uv run python -m scripts.smoke_policy_release --wheel "$TEST_WHEEL"
direnv exec . python3 -m scripts.smoke_mcp_release --wheel "$TEST_WHEEL"
direnv exec . uv run python -m scripts.smoke_registry_release --wheel "$TEST_WHEEL"
```

The policy runner additionally verifies supported import identities, base absence
of MCP, `py.typed`, and execution/static typing of every exact Python block in
the policy guide. It requires the development `ty` executable on PATH.

The runners create separate virtual environments outside the checkout and
install the exact wheel. The base check executes library examples and CLI
help. The MCP check installs `[mcp]`, checks installed path and metadata,
launches `judgevet-mcp`, discovers exactly four tools, and calls the three `ask_*` tools
against the live service. A local source build is not index verification.

Verify live judgment through the installed CLI as well. Define this helper
from the checkout root and keep it for the production check. It installs the
exact wheel and pytest in a separate environment. Python isolated mode ignores
checkout-related Python environment variables; the import assertion verifies
the package location before pytest loads the live test.

```bash
check_cli_wheel() {
  local cli_wheel="$1" cli_env repo_root
  repo_root=$(pwd)
  cli_env=$(mktemp -d /tmp/judgevet-cli-release.XXXXXXXX)
  uv venv "$cli_env"
  uv pip install --python "$cli_env/bin/python" "$cli_wheel" 'pytest==9.1.1'
  direnv exec "$repo_root" bash -e -c '
    cd "$1"
    "$1/bin/python" -I -c "import pathlib,sysconfig,judgevet; p=pathlib.Path(judgevet.__file__).resolve(); root=pathlib.Path(sysconfig.get_paths()[\"purelib\"]).resolve(); assert p.is_relative_to(root); print(\"Installed package location verified\")"
    "$1/bin/python" -I -m pytest -q -o addopts= --import-mode=importlib \
      -m live "$2/tests/live/test_cli_live.py"
  ' bash "$cli_env" "$repo_root"
}
check_cli_wheel "$TEST_WHEEL"
```

Require one passed test, not a skip. The test makes one mixed Noul/Choice/Score
request through the console and validates typed output, process status and
streams. Default tests remain offline. A missing key skips this opt-in test,
but a release cannot treat that skip as successful live verification.

Record commands, candidate SHA, run URL, hashes, live results and limits on
the active release tracker. Preserve
these downloads through production verification.

## Merge the accepted candidate

Stop if the candidate or main changed. Re-evaluate changed source or artifacts;
changed published bytes need a fresh version through release-please. Do not
blindly retry a reserved version, overwrite index files, or disable upload
hash checks.

```bash
test "$(gh pr view "$PR" --json headRefOid --jq .headRefOid)" = "$HEAD_SHA"
test "$(gh pr view "$PR" --json baseRefOid --jq .baseRefOid)" = "$BASE_SHA"
gh pr checks "$PR"
gh pr merge "$PR" --merge --match-head-commit "$HEAD_SHA"
RELEASE_SHA=$(gh pr view "$PR" --json mergeCommit --jq .mergeCommit.oid)
git fetch origin main
git diff --exit-code "$HEAD_SHA" "$RELEASE_SHA" --
gh run list --commit "$RELEASE_SHA"
```

Inspect the release commit's CI and release-please runs; require completed
success before publishing. The tree comparison must be empty. Verify the
expected draft, tag, and version. Release-please must have created the tag at
`RELEASE_SHA`; a mismatched tag is a stop condition.

```bash
TAG="v$VERSION"
gh release view "$TAG" --json tagName,isDraft,targetCommitish,url
git fetch origin "refs/tags/$TAG:refs/tags/$TAG"
test "$(git rev-parse "$TAG^{commit}")" = "$RELEASE_SHA"
read -r -p 'Path to reviewed release notes: ' NOTES_FILE
gh release edit "$TAG" --notes-file "$NOTES_FILE"
gh release edit "$TAG" --draft=false
```

The generated changelog describes changes. Release notes explain what the
release is for. Publishing the draft is the production trigger; do not bypass
the workflow with a local upload.

## Verify production publication

Production rebuilds from the release commit. Do not assume its bytes match the
accepted candidate before comparing the actual artifacts.
This fuller check runs the index wheel through the smoke runners.
The `TEST_WHEEL` comparison applies only after the optional TestPyPI round.

```bash
gh run list --workflow publish.yml --commit "$RELEASE_SHA" \
  --json databaseId,headSha,createdAt,status,url
read -r -p 'Production publish run ID: ' PROD_RUN
test "$(gh run view "$PROD_RUN" --json headSha --jq .headSha)" = "$RELEASE_SHA"
gh run watch "$PROD_RUN" --exit-status
test "$(gh run view "$PROD_RUN" --json conclusion --jq .conclusion)" = success
gh run view "$PROD_RUN" --verbose
PROD_ARTIFACT="$EVIDENCE_DIR/prod-artifact"
PROD_INDEX="$EVIDENCE_DIR/prod-index"
gh run download "$PROD_RUN" --name dist --dir "$PROD_ARTIFACT"
uvx --from pip pip download --index-url https://pypi.org/simple/ \
  --no-deps --only-binary=:all: "judgevet==$VERSION" --dest "$PROD_INDEX"
prod_artifacts=("$PROD_ARTIFACT"/*.whl)
prod_downloads=("$PROD_INDEX"/*.whl)
(( ${#prod_artifacts[@]} == 1 ))
(( ${#prod_downloads[@]} == 1 ))
PROD_WHEEL=${prod_downloads[0]}
cmp "${prod_artifacts[0]}" "$PROD_WHEEL"
cmp "$TEST_WHEEL" "$PROD_WHEEL"
sha256sum "${prod_artifacts[0]}" "$TEST_WHEEL" "$PROD_WHEEL"
direnv exec . python3 scripts/smoke_release.py --wheel "$PROD_WHEEL"
direnv exec . uv run python -m scripts.smoke_policy_release --wheel "$PROD_WHEEL"
direnv exec . python3 -m scripts.smoke_mcp_release --wheel "$PROD_WHEEL"
direnv exec . uv run python -m scripts.smoke_registry_release --wheel "$PROD_WHEEL"
direnv exec . uv run python -m scripts.smoke_registry_release
check_cli_wheel "$PROD_WHEEL"
```

Confirm the production base/MCP steps and upload succeeded. A hash mismatch
requires investigation; it does not authorize replacement of immutable files.
Do not call the release verified until actual PyPI checks pass.

Record final evidence on the active release tracker and in the GitHub Release
notes. Update the installation guide after the published MCP command is verified. A fresh
transport probe does not prove the current Codex session reloaded its native
tools. Leave unseen 429/529 bodies inferred.

The existing [broken-library proof](https://github.com/Alberto-Codes/judgevet/actions/runs/35686353515)
and [broken-MCP proof](https://github.com/Alberto-Codes/judgevet/actions/runs/35699666984)
show failed smoke checks prevented upload. Link them; do not recreate them for
each release.

## Verify digests, attestations and registry

Run the block below from the checkout root after the merge section defines
`TAG` and `RELEASE_SHA` and the publish workflow succeeds.

```bash
gh release download "$TAG" --dir "$EVIDENCE_DIR/assets"
curl -fsS "https://pypi.org/pypi/judgevet/$VERSION/json" \
  | jq -r '.urls[] | "\(.digests.sha256)  \(.filename)"'
sha256sum "$EVIDENCE_DIR"/assets/*.whl "$EVIDENCE_DIR"/assets/*.tar.gz
(
  cd "$EVIDENCE_DIR/assets"
  for dist in *.whl *.tar.gz; do
    gh attestation verify "$dist" \
      --bundle "judgevet-$VERSION.provenance.sigstore.json" \
      --repo Alberto-Codes/judgevet
  done
  for wheel in *.whl; do
    gh attestation verify "$wheel" --bundle "$wheel.sbom.sigstore.json" \
      --predicate-type https://cyclonedx.org/bom --repo Alberto-Codes/judgevet
  done
)
mkdir -p "$EVIDENCE_DIR/registry"
git show "$RELEASE_SHA:server.json" > "$EVIDENCE_DIR/registry/server.json"
(
  cd "$EVIDENCE_DIR/registry"
  mcp-publisher login github -token "$(gh auth token)"
  mcp-publisher publish
)
```

Each PyPI digest must equal the SHA-256 of the matching release asset.
Every `gh attestation verify` command must exit 0.
See the [PyPI JSON API](https://docs.pypi.org/api/json/) and
[gh attestation verify](https://cli.github.com/manual/gh_attestation_verify).
`mcp-publisher publish` reads `server.json` from the current directory.
See the [publisher instructions](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx).
A stale checkout publishes an old version, which the registry refuses as a duplicate.

## Credential troubleshooting

For `Resource not accessible by personal access token`, check
`RELEASE_PLEASE_TOKEN` repository scope and permissions. A fine-grained token
needs Contents, Pull requests and Issues read/write; a classic token needs
`repo`. Pull request labels use the Issues API.

Test changed credentials with a fresh workflow run. Do not infer which secret
value a previous attempt used. Keep credential values out of logs and issue
evidence. Missing artifact downloads require checking the selected run and
artifact; failed smoke checks require investigating the artifact and isolation.
