#!/usr/bin/env bash
# Run full verification (imports, constants, enums, exceptions, types, tests, typecheck, lint).
set -e
cd "$(dirname "$0")/.."
poetry run python verify_sprint.py "$@"
