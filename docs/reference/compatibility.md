---
status: draft
---

# Supported imports and compatibility

judgevet ships one distribution, one version and one release-please component.
The library, CLI, MCP server and optional dependencies have separate compatibility
assessments within that release. The 0.7.0 release implements the accepted
[#67 API decision](https://github.com/Alberto-Codes/judgevet/issues/67#issuecomment-5786388416)
and [#66 compatibility decision](https://github.com/Alberto-Codes/judgevet/issues/66#issuecomment-5786398764).

## Library imports

The root `__all__` declares these supported names:

| Purpose | Imports from `judgevet` |
|---|---|
| Explicit adapters | `HTTPSystemOneAdapter`, `AsyncHTTPSystemOneAdapter` |
| Structural ports | `SystemOnePort`, `AsyncSystemOnePort` |
| Questions | `Question`, `Noul`, `Choice`, `Score` |
| Answers and metadata | `Answer`, `NoulAnswer`, `ChoiceAnswer`, `ScoreAnswer`, `SystemOneResponse`, `Usage` |
| Service errors | `JevError`, `JevAuthError`, `JevRequestError`, `JevResponseError`, `JevServiceError`, `JevRateLimitError` |
| Version | `__version__` |

Re-exports retain the original objects. Existing domain, port and adapter deep
imports remain valid. There are no wrapper classes or implicit adapter owners.
The [API reference](api.md) documents service fields and observed versus inferred
errors. Not every possible Python or HTTP exception is a `JevError`; existing
raw redirect errors, for example, retain their prior behavior.

`judgevet.policy` supports `NoulRule`, `ChoiceRule`, `ScoreRule`, `Rule`, `Policy`,
`ValidatedPolicy`, `RuleReport`, `PolicyReport`, `validate_policy`,
`evaluate_policy`, `PolicyError`, `PolicyDefinitionError`, and `PolicyAnswerError`.
`judgevet.policy_json` supports `parse_policy`. These modules are new in the
0.7.0 release and absent from 0.6.0. The implementation helpers are internal;
use the facades for new policy callers.

The [typed policy guide](../how-to/use-policy-library.md) gives runnable examples,
constructor invariants, strict answer checks, immutable snapshots, error handling
and explicit sync/async lifecycle ownership. Public policy errors are local
`ValueError` subclasses, separate from the Jev service-error hierarchy.

## 0.7.0 compatibility assessment

| Surface | Assessment | Migration |
|---|---|---|
| Library | Additive root exports, pure policy API and separate JSON facade | No existing import migration. Use typed rules and immutable reports for new policy callers. |
| CLI | Grammar, diagnostics, ordered output and exit meanings 0/1/2/3 retained | None. Private CLI policy wrappers keep their historical return shapes and answer checks. |
| MCP | Same three tools, schemas and structured content | None. No policy tool is added. |
| Dependencies | Same mandatory dependencies and optional `mcp` extra | None. Base installs still omit MCP and include `py.typed`. |

Strict public policy evaluation and the legacy CLI wrapper intentionally differ
for malformed answers. Public evaluation always checks selected confidence and
snapshotted choice/score constraints; the legacy checks remain as before. This
is a new API contract, not a migration of existing CLI semantics.

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

## Verification limits

Policy tests are synthetic local acceptance evidence. They do not establish model
quality or new service behavior. Live 429/529 bodies remain unseen; resolved
models other than `jev-1.13.0` remain untested. The historical intermittent MCP
launcher failure remains unexplained. A successful fresh launcher does not prove
that an existing agent session reloaded its native tools.
