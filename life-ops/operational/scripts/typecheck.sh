#!/usr/bin/env bash
# Type check all Python files with mypy --strict.
set -e
cd "$(dirname "$0")/.."
poetry run mypy src/operational/ --strict
