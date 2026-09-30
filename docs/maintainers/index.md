---
status: draft
---

# Maintainer procedures

Status: **draft**.

These guides are for people who build and publish judgevet.
For package use, follow [installation](../how-to/install.md) or the
[typed policy guide](../how-to/use-policy-library.md).

- [Contribution policy](https://github.com/Alberto-Codes/judgevet/blob/main/CONTRIBUTING.md): issue-led work and authorized commits.
- [Set up a contributor checkout](contributor-setup.md) without API credentials.
- [Write and review technical prose](writing-guide.md).
- [Build documentation and check links](build-docs.md).
- [Verify a wheel's typing marker and isolated consumer](verify-package.md).
- [Cut and verify a release](cut-a-release.md): authorization, compatibility
  notes, index publication and credential troubleshooting.
- [Validate and publish the MCP registry listing](mcp-registry.md).
- [Delegate a bounded change](delegate-work.md) to pi or a Claude sub agent.
- [Repository contribution rules](../../AGENTS.md): enabled gates, commits
  and evidence requirements.
- [Current evidence ledger](../../STATUS.md): release, gates and service limits.

Release and credential history remains in Git and linked issue evidence.
Those records are provenance, not prerequisites for user tasks.

## Audit the current lockfile

Run `uv audit --locked --preview-features audit-command` before publication.
The pre-push hook and required CI audit job run the same command. CI pins the
verified uv version to 0.11.20. The audit includes all extras and dependency
groups, including MCP and development tools. It does not install the project.
See the [uv audit reference](https://docs.astral.sh/uv/reference/cli/#uv-audit).

`--locked` rejects a missing or stale lockfile instead of rewriting it. Reported
vulnerabilities, adverse project statuses and service failures block success.
Resolve findings and rerun the audit; do not add exclusions or ignore flags.
Audit uses public vulnerability-service metadata. A clean result describes
known reports at the time of the check, not an absence of all vulnerabilities.

The [audit-command preview](https://docs.astral.sh/uv/concepts/preview/)
is experimental. Recheck supported flags and failure behavior when upgrading
uv. Commit-stage checks do not contact the audit service; the network audit
runs at push and in its own CI job.

The CI `sbom` job uploads a `supply-chain` artifact for dependency reviews. The
job and the release workflow share one composite action,
`.github/actions/supply-chain`. It exports CycloneDX 1.5 SBOMs for runtime,
runtime with MCP and development dependencies with the `sbom-export` preview of
[uv export](https://docs.astral.sh/uv/reference/cli/#uv-export).
The export reads the dependency graph that `uv.lock` declares. Each SBOM is
therefore a *source* SBOM, not a *build* SBOM of the wheel, in the
[CISA SBOM types](https://www.cisa.gov/sites/default/files/2024-10/SBOM%20Framing%20Software%20Component%20Transparency%202024.pdf).
`scripts/sbom_lifecycle.py` records that scope in each file as the CycloneDX
[lifecycle phase](https://cyclonedx.org/docs/1.5/json/#metadata_lifecycles)
`pre-build`.
`scripts/licence_report.py` builds a licence table per scope from installed
package metadata. A package without licence metadata reads `UNKNOWN`. A
package absent from the runner's environment reads `NOT INSTALLED`. The
`marker` column shows the environment marker uv records for a package, which
gives the reason for an absence when there is one. The action also saves the
audit as JSON. Its provenance file records the commit, uv version, `uv.lock`
SHA-256, the SBOM scope and the outcome of each step. A failed or skipped step
sets `complete: no`, so an artifact from a failed run shows that it is
incomplete.

Publishing a release runs `publish.yml`. Its `attest` job runs the same action
on the released commit, with the wheel and sdist that go to PyPI. It adds their
SHA-256 to the provenance file as bare hex, like the `uv.lock` hash. It signs a
build provenance attestation for the wheel and sdist, and an SBOM attestation
that binds the runtime SBOM to the wheel. The runtime SBOM lists what installing the wheel pulls in. See
[artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations).
The `release-files` job then attaches these files to the GitHub release:

- the wheel and the sdist, the same files that go to PyPI;
- `judgevet-<version>.provenance.sigstore.json`, the build provenance
  bundle. One attestation covers both the wheel and the sdist;
- `<wheel>.sbom.sigstore.json`, the SBOM attestation bundle for the wheel;
- every supply-chain file.

Each bundle is the Sigstore bundle from the `bundle-path` output of
[actions/attest](https://github.com/actions/attest/blob/v4.2.2/action.yml).
The `.sigstore.json` suffix is one that the OpenSSF Scorecard
[Signed-Releases](https://github.com/ossf/scorecard/blob/main/docs/checks.md#signed-releases)
check counts as a signature.
The PyPI `publish` job runs only after the attestations succeed. It does not
wait for `release-files`, so a failed release upload does not block PyPI.

To verify a downloaded wheel, run
`gh attestation verify <wheel> --repo Alberto-Codes/judgevet`. Add
`--predicate-type https://cyclonedx.org/bom` to verify the SBOM attestation.
The same command verifies the sdist's build provenance. See
[gh attestation verify](https://cli.github.com/manual/gh_attestation_verify).

To verify offline against the release bundles, pass a bundle with `--bundle`:

```bash
gh attestation verify judgevet-<version>-py3-none-any.whl \
  --bundle judgevet-<version>.provenance.sigstore.json \
  --repo Alberto-Codes/judgevet
gh attestation verify judgevet-<version>-py3-none-any.whl \
  --bundle judgevet-<version>-py3-none-any.whl.sbom.sigstore.json \
  --predicate-type https://cyclonedx.org/bom \
  --repo Alberto-Codes/judgevet
```

## Check configuration and workflows

The first commit and push hook runs `uv lock --check` when project or lockfile
metadata changes. It reports stale metadata before another hook can refresh it.
CI retains the same check before dependency synchronization.

The YAML hook runs strict yamllint with its default rules on all tracked YAML
files. It checks hidden configuration and workflows, including duplicate keys.
The workflow hook runs upstream actionlint v1.7.12. This Go tool has a separate
upstream pin because the Python lockfile cannot install it.

Run `uv run pre-commit run yamllint --all-files` and
`uv run pre-commit run actionlint --all-files` to check the complete tracked scope.
CI runs these same commands. See the [yamllint documentation](https://yamllint.readthedocs.io/en/stable/)
and [actionlint hook instructions](https://github.com/rhysd/actionlint/blob/v1.7.12/docs/usage.md#pre-commit).
These checks validate configuration; they do not exercise deployed workflows.
