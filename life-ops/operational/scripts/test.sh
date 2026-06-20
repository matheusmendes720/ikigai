#!/usr/bin/env bash
# Run test suite with coverage.
set -e
cd "$(dirname "$0")/.."
poetry run pytest "$@"
