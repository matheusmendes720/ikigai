#!/usr/bin/env bash
# Lint all Python files with ruff.
set -e
cd "$(dirname "$0")/.."
poetry run ruff check src/ tests/
poetry run ruff format --check src/ tests/
