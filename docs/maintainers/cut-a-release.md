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
`server.json`. See [registry publication](mcp-registry.md). The separate `update-lockfile` job
refreshes `uv.lock` on the release branch. Never edit a version by hand.

Merging the release PR creates a draft and tag. Publishing the draft triggers
`publish.yml`. A draft permits a pause; it does not upload to PyPI.

## Authority and prerequisites

Standing authorization permits merging and publishing a release that meets
these criteria without another approval:

- Main and candidate CI are green. Required local gates pass.
- The changelog describes the release and its user-visible changes.
- `STATUS.md` reports measured tests, coverage and verified-versus-inferred
  claims. No inferred claim becomes verified without an exercising call.
- The candidate downloaded from TestPyPI passes isolated base and MCP checks.
- No unresolved release requirement affects the installation being shipped.

Hold for a human decision if the change breaks a published API, changes what
users should trust in the verified table, or needs unavailable credentials.
The published 0.2.0 files remain immutable. TestPyPI is also a real publication
to an immutable index, not a dry run.

Run the following Bash blocks in one shell from the repository root, with
Python 3.12 or newer, `gh`, `uv`, and configured `direnv`. Inherit the vendor
key through the approved environment. Never print it or put it in a command
or checked-in configuration. Do not enable shell tracing.

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
```

Inspect all seven version values, including the registry root, package and
uvx pin with `uv run python -m scripts.registry_manifest`. The existing four are: project version, root `__version__`, manifest
root entry, and the root `judgevet` package version in `uv.lock`. All must equal
`VERSION`. Review the changelog and STATUS trust table. Inspect the identified
main CI run and require completed success. Fetching does not replace local
files or discard unrelated work.

Keep the generated release PR body intact. release-please parses its version
heading and body structure after merge. Put acceptance evidence in issue or PR
comments, and put reviewed prose in the draft release notes. Replacing the body
in #130 made release-please skip the merged release and propose another version,
even though the workflow was green. Restoring the generated body and rerunning
the same workflow recovered the draft without changing source or index files.
Always verify the expected draft and tag; a green workflow alone is insufficient.

## Publish and verify the TestPyPI candidate

Verify TestPyPI before merging. This checks what the index serves before using
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
EVIDENCE_DIR=$(mktemp -d /tmp/judgevet-release.XXXXXXXX)
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
launches `judgevet-mcp`, discovers exactly three tools, and calls all three
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

Record final evidence on the active release tracker and measured results in `STATUS.md`. Update the
installation guide after the published MCP command is verified. A fresh
transport probe does not prove the current Codex session reloaded its native
tools. Leave unseen 429/529 bodies inferred.

The existing [broken-library proof](https://github.com/Alberto-Codes/judgevet/actions/runs/35686353515)
and [broken-MCP proof](https://github.com/Alberto-Codes/judgevet/actions/runs/35699666984)
show failed smoke checks prevented upload. Link them; do not recreate them for
each release.

## Credential troubleshooting

For `Resource not accessible by personal access token`, check
`RELEASE_PLEASE_TOKEN` repository scope and permissions. A fine-grained token
needs Contents, Pull requests and Issues read/write; a classic token needs
`repo`. Pull request labels use the Issues API.

Test changed credentials with a fresh workflow run. Do not infer which secret
value a previous attempt used. Keep credential values out of logs and issue
evidence. Missing artifact downloads require checking the selected run and
artifact; failed smoke checks require investigating the artifact and isolation.
