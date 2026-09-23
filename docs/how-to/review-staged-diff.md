---
status: draft
---

# Review staged diffs

Status: **draft**.

This document describes the `review-staged.sh` example, an opt-in probabilistic
judgment workflow for reviewing staged Git changes.

## Installation

Install judgevet:

```bash
uv tool install judgevet
```

Run `uv tool update-shell` if needed for PATH.

## Approved credentials

Load `JEV_API__KEY` through your approved `direnv` environment. The example
inherits the CLI configuration. Never print credentials or put them in the files.

## Usage

Copy all three example files (`review-staged.sh`, `questions.json`, `policy.json`) to your repository.
Invoke the script path from the repository under review:

```bash
./review-staged.sh
```

No positional arguments are accepted.

## Input

The script captures only `git diff --cached` output into a private temporary
file. The staged change is the only input sent to the judgment service.

Unstaged changes, untracked files, and working-tree modifications are excluded.

## Policy

The versioned policy requires Noul probability at least 0.8 for the `approve`
question. This is an illustrative threshold, not a quality guarantee.

See [Using policy](use-cli-policy.md) for the exact schema and examples.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | No staged changes, or judgment passed policy |
| 1 | Producer failure (git diff error) or input/operational error |
| 2 | Usage error (unexpected arguments) |
| 3 | Valid judgment failed explicit policy (only with `--policy`) |

## Output

- **Success (pass/unmet)**: JSON answer envelope on stdout, empty stderr
- **Clean (no staged changes)**: Empty stdout, short notice on stderr
- **Auth/input/producer failure**: Exit 1, empty stdout, diagnostic on stderr
- **Policy unmet**: Exit 3, answer JSON on stdout, empty stderr

The CLI forwards answer `policy` as an object with `rules` array and `result` string.

## Notes

- This is an opt-in probabilistic judgment, not a deterministic quality guarantee
- No mandatory gate installation is required
- The script respects Git's exit codes: 0=no changes, 1=changes, other=failure
- Temporary files are cleaned up on exit via trap
