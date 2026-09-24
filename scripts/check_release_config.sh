#!/usr/bin/env bash
# Resolve only locked development tooling, then execute the configured updater.
set -euo pipefail
npm --prefix scripts/release_config ci --ignore-scripts --no-audit --no-fund --silent
npm --prefix scripts/release_config test
