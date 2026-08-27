#!/usr/bin/env bash
# Type check all Python files with mypy --strict.
set -e
cd "$(dirname "$0")/.."
uv run mypy packages/core/src/operational/ apps/cli/src/operational/ apps/tui/src/operational/ --strict
