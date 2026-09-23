---
status: draft
---

# Supported imports and compatibility

Status: **draft**.

judgevet ships one distribution and one version. The library, CLI, MCP server
and optional dependencies have separate compatibility assessments within that
release. One wheel does not have independently released library/CLI/MCP versions.

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

The [policy reference](policy.md) defines the complete local contract.
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

## Verification limits

Policy tests are synthetic local acceptance evidence. They do not establish model
quality or new service behavior. Live 429/529 bodies remain unseen; resolved
models other than `jev-1.13.0` remain untested. Intermittent MCP
initialization failures have no established cause or remedy. Follow the
[connection checks](../how-to/install.md#when-mcp-does-not-connect). A successful
fresh launcher does not prove that an existing agent session reloaded its tools.
