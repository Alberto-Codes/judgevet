# Contributing to judgevet

Start with an issue describing the problem, expected behavior and a reproducible
check. Keep credentials and private inputs out of public reports. Report
vulnerabilities through the private route in [SECURITY.md](SECURITY.md#report-a-vulnerability).

## How changes land

Ordinary contributions do not use pull requests. Discuss proposed work on an
issue first. Authorized maintainers commit a finished deliverable directly to
`main`, run the enabled hooks, push and verify CI for that exact commit.
Opening an issue does not grant commit or publication access.

The commit-message gate checks an author allowlist in
[pyproject.toml](pyproject.toml). Do not impersonate an allowed author, bypass
the gate or change the list merely to make your commit pass. Contributors
without repository authorization can provide reproductions and proposed changes
through the issue for maintainer review.

The existing automated release-please workflow creates release pull requests.
That exception prepares version and changelog changes under the
[release procedure](docs/maintainers/cut-a-release.md). It does not create an
ordinary pull-request workflow or authorize publication by itself.

## Set up once, keep the gates enabled

Follow the canonical [contributor setup](docs/maintainers/contributor-setup.md).
It covers prerequisites, the cold-clone sequence, test selection and recovery.
Install all three hook stages first: `pre-commit`, `pre-push` and `commit-msg`.
Ordinary setup and the default tests need no live API credentials.

Run the [complete gate stages](docs/maintainers/contributor-setup.md#run-the-gates)
before declaring work ready. Fix the cause of a failure. Never silence a gate,
weaken an architecture contract, lower coverage or skip a hook. A focused check
cannot replace the complete stages. Fixing one gate must not break another.

## Define and prove one deliverable

Record the acceptance contract on the issue before behavioral implementation.
Write its test first and record the failing command and output. Check that
it fails for the missing behavior rather than a broken fixture. Keep the test
and implementation in the same round. Preserve existing tests and provide
an independent failure proof before claiming success.

Finish one deliverable per round. Update [STATUS.md](STATUS.md) in the commit
that changes its claims, using measured tests, coverage, gate state and service
evidence. Synthetic tests do not verify live service behavior. Keep unseen
responses and untested models explicitly unverified.

Preserve unrelated workspace changes. Keep MCP dependencies in the optional
adapter and the domain free of IO. Follow the [repository rules](AGENTS.md)
for architecture, size limits, attribution and evidence requirements.

Every new module needs its docstring sections on the first pass, including
runnable `Examples:` and cross-referenced `See Also:` sections. Classes need
`Attributes:`; functions need the relevant `Args:`, `Returns:`
and `Raises:` sections. Ruff and docvet both apply. Follow the
[writing guide](docs/maintainers/writing-guide.md) and canonical glossary.

## Write factual commits

Use Conventional Commits with this closed type vocabulary:

`feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `build`, `ci`.

Use a subject such as `docs: explain contributor setup`. Reference the issue
in the message. A commit that finishes an issue uses the footer `Closes #N`;
an incomplete contribution uses `Refs #N`. GitHub closes finished issues from
the pushed commit. Do not replace that link with a manual issue closure.

Local-model attribution is factual and per commit. Use `Specified-By` only
when that model produced the issue-hosted specification. Use `Generated-By`
only when that model wrote the implementation. Keep the roles separate. Follow the exact
[attribution rules](AGENTS.md#commits); do not add an unearned trailer.
