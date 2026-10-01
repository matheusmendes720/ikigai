#!/usr/bin/env bash
# reflect.sh — M-TBD Recursive Reflection cron wrapper
#
# Runs the reflection pipeline once and writes a markdown report to
# vault/ikigai/reflections/<YYYY-MM-DD>.md. Reads from the decision log
# populated by td CLI mutations (see _record_decision in taskdog_cli.py).
#
# Pattern follows .claude/loop/scripts/daemon-watchdog.sh: pure bash, set -euo
# pipefail, no LLM in the loop (ADR-013), idempotent.
#
# Usage:
#   bash .claude/loop/scripts/reflect.sh [--dry-run] [--lookback-days N]
#
# Environment:
#   REFLECT_LOOKBACK_DAYS — default 14
#
# Exit codes:
#   0 — wrote reflection (or dry-run succeeded)
#   1 — failure (no decision log, missing python, etc.)
#
# No Co-Authored-By trailer per project convention.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Defaults (override via flags or env)
LOOKBACK_DAYS="${REFLECT_LOOKBACK_DAYS:-14}"
DRY_RUN="false"
OUT_PATH=""

# --- arg parsing ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    --lookback-days)
      LOOKBACK_DAYS="$2"
      shift 2
      ;;
    --out)
      OUT_PATH="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: bash reflect.sh [--dry-run] [--lookback-days N] [--out PATH]"
      exit 0
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

cd "$PROJECT_ROOT"

# Prefer the active venv if present; fall back to system python.
PYTHON_BIN="${PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
  if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
  else
    PYTHON_BIN="$(command -v python || command -v python3 || true)"
  fi
fi

if [ -z "$PYTHON_BIN" ]; then
  echo "error: no python interpreter found" >&2
  exit 1
fi

# --- preflight: decision log directory must exist ---
DECISIONS_DIR="$PROJECT_ROOT/vault/ikigai/decisions"
REFLECTIONS_DIR="$PROJECT_ROOT/vault/ikigai/reflections"
if [ ! -d "$DECISIONS_DIR" ] && [ "$DRY_RUN" != "true" ]; then
  echo "warning: no decision log at $DECISIONS_DIR — nothing to reflect on" >&2
fi
mkdir -p "$REFLECTIONS_DIR"

# --- invoke reflection ---
CMD=("$PYTHON_BIN" -m src.agents.reflection.recursive --lookback-days "$LOOKBACK_DAYS")
if [ -n "$OUT_PATH" ]; then
  CMD+=(--out "$OUT_PATH")
fi
if [ "$DRY_RUN" = "true" ]; then
  CMD+=(--json)
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] reflect: starting (lookback=${LOOKBACK_DAYS}d, dry_run=${DRY_RUN})"
"${CMD[@]}"
rc=$?
if [ $rc -ne 0 ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] reflect: FAILED (rc=$rc)" >&2
  exit $rc
fi
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] reflect: ok"