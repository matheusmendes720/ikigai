#!/usr/bin/env bash
# Lint all Python files with ruff.
set -e
cd "$(dirname "$0")/.."
uv run ruff check packages/ apps/ tests/
uv run ruff format --check packages/ apps/ tests/
