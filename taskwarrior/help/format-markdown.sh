#!/bin/bash
# Markdown formatter wrapper - calls Python formatter
# Formats markdown files with ANSI colors for better readability

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_FORMATTER="$SCRIPT_DIR/format-markdown.py"

if [ $# -eq 0 ]; then
    echo "Usage: format-markdown.sh <file.md>"
    exit 1
fi

if [ -f "$PYTHON_FORMATTER" ]; then
    python3 "$PYTHON_FORMATTER" "$1"
else
    echo "Error: Python formatter not found: $PYTHON_FORMATTER" >&2
    # Fallback to plain cat
    cat "$1"
    exit 1
fi
