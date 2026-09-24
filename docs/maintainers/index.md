---
status: draft
---

# Maintainer procedures

Status: **draft**.

These guides are for people who build and publish judgevet.
For package use, follow [installation](../how-to/install.md) or the
[typed policy guide](../how-to/use-policy-library.md).

- [Write and review technical prose](writing-guide.md).
- [Build documentation and check links](build-docs.md).
- [Verify a wheel's typing marker and isolated consumer](verify-package.md).
- [Cut and verify a release](cut-a-release.md): authorization, compatibility
  notes, index publication and credential troubleshooting.
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
