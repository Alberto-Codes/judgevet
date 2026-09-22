#!/bin/bash
# Review staged diff using judgevet with versioned questions and policy
# This is an opt-in probabilistic judgment, not a deterministic quality guarantee.
# Install judgevet: uv tool install judgevet
# Inherit JEV_API__KEY through the approved environment.

set -euo pipefail

# Resolve script directory independent of cwd
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

QUESTIONS_FILE="${SCRIPT_DIR}/questions.json"
POLICY_FILE="${SCRIPT_DIR}/policy.json"

# Validate arguments
if [[ $# -gt 0 ]]; then
    echo "Usage: review-staged.sh" >&2
    echo "No arguments accepted" >&2
    exit 2
fi

# Create private temporary file for diff
TEMP_FILE=$(mktemp)
trap 'rm -f "${TEMP_FILE}"' EXIT

# Capture git diff output
GIT_EXIT_CODE=0
git diff --cached --no-ext-diff --no-textconv --binary --exit-code > "${TEMP_FILE}" 2>/dev/null || GIT_EXIT_CODE=$?

# Clean/no staged change: exit 0 with notice
if [[ $GIT_EXIT_CODE -eq 0 ]]; then
    echo "No staged changes to review" >&2
    exit 0
fi

# Producer failure: exit 1 with diagnostic
if [[ $GIT_EXIT_CODE -ne 1 ]]; then
    echo "Producer failure: git diff exited with code ${GIT_EXIT_CODE}" >&2
    exit 1
fi

# Run judgevet with staged diff on stdin via --state-file -
judgevet --state-file - \
    --questions-file "${QUESTIONS_FILE}" \
    --policy "${POLICY_FILE}" \
    --json < "${TEMP_FILE}"
EXIT_CODE=$?

# Forward CLI exit code
exit ${EXIT_CODE}
