#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
[ -d ".venv" ] && source .venv/bin/activate || true
exec python -m src.ikigai.bin.ikigai_serve "$@"
