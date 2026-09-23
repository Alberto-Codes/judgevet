---
status: draft
---

# Review staged diffs

Status: **draft**.

This document describes the `review-staged.sh` example, an opt-in probabilistic
judgment workflow for reviewing staged Git changes.

## Installation

Prerequisites: Git, Bash, uv and an approved credential environment. This guide
uses files from a judgevet source checkout; the wheel does not install the
example script. Obtain the three linked files below from the same revision.
Run the script from the Git repository you intend to review.

Install judgevet:

```bash
uv tool install judgevet
```

Run `uv tool update-shell` if needed for PATH.

## Approved credentials

Load `JEV_API__KEY` through your approved `direnv` environment. The example
inherits the CLI configuration. Never print credentials or put them in the files.

## Usage

Copy all three example files to one directory in your repository:
[review-staged.sh](../../examples/staged-review/review-staged.sh),
[questions.json](../../examples/staged-review/questions.json) and
[policy.json](../../examples/staged-review/policy.json).
Review the questions, policy and staged content before transmitting it to Jev.
The script finds its companion files beside itself, not in the current directory.
Invoke the script path from the repository under review:

```bash
bash ./review-staged.sh
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

For exit 1, inspect the diagnostic privately and check Git, input and credential
setup. For exit 3, inspect the answers and policy comparisons before changing
the staged work or your acceptance rule. See [troubleshooting](troubleshoot.md)
and [diagnostic limits](../../SECURITY.md#diagnostics-and-error-content).
