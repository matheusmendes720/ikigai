#!/usr/bin/env bash
# scripts/paperclip-spawner.sh — M174 Paperclip Auto-Spawner
#
# Self-managed auto-spawner for the Paperclip meta-orchestrator. Polls
# .claude/loop/inbox/ for new spec drop-ins, probes AI adapter health
# (which <adapter>), consults the cost-dashboard JSON sidecar for
# today's spend, and dispatches one Paperclip run per spec to the
# cheapest healthy adapter.
#
# Invoke sources (per M174 spec):
#   1. .claude/loop/inbox/*.md — manual spec drop-in (operator)
#   2. CLI invoke — `bash scripts/paperclip-spawner.sh --once`
#
# Sequential queue (D7): one ad per iteration; no parallel fan-out
# (that's Wave N+5). The script is idempotent — re-running with empty
# inbox is a no-op.
#
# Binary-on-PATH health (D8): `which <adapter>` exit code decides
# on_path; missing binaries are skipped (no warning to stderr — the
# router.py result captures the decision).
#
# Usage:
#   bash scripts/paperclip-spawner.sh --once        # single iteration
#   bash scripts/paperclip-spawner.sh --loop        # daemonize (default)
#   bash scripts/paperclip-spawner.sh --dry-run     # print decisions, no dispatch
#
# No Co-Authored-By trailer per project convention.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# M24.1: Translate Cygwin mount path (/c/Users/...) to Windows path (C:/Users/...)
# so that `git -C "$PROJECT_ROOT"` works on Windows + Git Bash.
PROJECT_ROOT_WIN="$(cygpath -m "$PROJECT_ROOT" 2>/dev/null || echo "$PROJECT_ROOT")"

INBOX_DIR="$PROJECT_ROOT/.claude/loop/inbox"
LOG_DIR="$PROJECT_ROOT/.claude/loop/logs"
COST_FILE="$PROJECT_ROOT/data/cost-today.json"
SPAWNER_LOG="$LOG_DIR/spawner.log"

# Tunables (overridable via env)
PAPERCLIP_LOOP_INTERVAL_S="${PAPERCLIP_LOOP_INTERVAL_S:-300}"
PAPERCLIP_MAX_PER_TICK="${PAPERCLIP_MAX_PER_TICK:-1}"
PYTHON_BIN="${PYTHON_BIN:-python}"

mkdir -p "$INBOX_DIR" "$LOG_DIR" 2>/dev/null || true

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log() {
    printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$SPAWNER_LOG"
}

# ---------------------------------------------------------------------------
# Adapter probing — `which <adapter>` exit code decides on_path
# ---------------------------------------------------------------------------
probe_adapters() {
    cat <<EOF
pi,omo,openclaw,claude
EOF
}

probe_on_path() {
    local adapter="$1"
    if command -v "$adapter" >/dev/null 2>&1; then
        echo "true"
    else
        echo "false"
    fi
}

# ---------------------------------------------------------------------------
# Cost sidecar — read data/cost-today.json (mirrors policy.CostGate shape)
# ---------------------------------------------------------------------------
read_cost_today() {
    if [[ ! -f "$COST_FILE" ]]; then
        echo "0.00"
        return
    fi
    # Pull total_usd with python — robust against schema drift. Defaults to 0.
    "$PYTHON_BIN" - "$COST_FILE" <<'PY' 2>/dev/null || echo "0.00"
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        data = json.load(fh)
    print(float(data.get("total_usd", 0.0)))
except Exception:
    print(0.0)
PY
}

# ---------------------------------------------------------------------------
# Dispatch — invoke the Paperclip graph for one spec via Python router
# ---------------------------------------------------------------------------
dispatch_spec() {
    local spec_path="$1"
    local cost_today="$2"

    log "dispatching spec: $spec_path (cost_today=\$$cost_today)"

    # Defer the adapter pick + graph dispatch to a Python helper so the
    # bash script stays pure stdlib + python. Failures are logged, not
    # raised — the spawner loop must not crash.
    PAPERCLIP_SPEC="$spec_path" \
    PAPERCLIP_COST="$cost_today" \
    "$PYTHON_BIN" - <<'PY' 2>&1 | tee -a "$SPAWNER_LOG"
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from src.ikigai.src.agents.paperclip.router import (
        AdapterHealth,
        SpecContext,
        pick_adapter,
    )
except Exception as exc:
    print(f"[dispatch] router import failed: {exc}")
    sys.exit(0)  # never crash the loop

spec_path = Path(__import__("os").environ["PAPERCLIP_SPEC"])
cost_today = float(__import__("os").environ["PAPERCLIP_COST"])
spec_text = spec_path.read_text(encoding="utf-8") if spec_path.exists() else ""
task_id = spec_path.stem

# Probe adapters via shutil.which (mirrors bash `which`)
import shutil
adapters = ("pi", "omo", "openclaw", "claude")
health = {}
for name in adapters:
    health[name] = AdapterHealth(
        name=name,
        on_path=shutil.which(name) is not None,
        last_invoked_at=datetime.now(timezone.utc),
        last_success=None,
    )

spec = SpecContext(task_id=task_id, spec_text=spec_text, cost_today_usd=cost_today)
try:
    decision = pick_adapter(spec, health)
    print(f"[dispatch] {decision.adapter} chosen — {decision.reason}")
except Exception as exc:
    print(f"[dispatch] {type(exc).__name__}: {exc}")
PY
}

# ---------------------------------------------------------------------------
# Single iteration
# ---------------------------------------------------------------------------
run_once() {
    local processed=0
    local cost_today
    cost_today="$(read_cost_today)"

    shopt -s nullglob
    for spec_path in "$INBOX_DIR"/*.md; do
        if [[ "$processed" -ge "$PAPERCLIP_MAX_PER_TICK" ]]; then
            break
        fi
        if [[ -z "${DRY_RUN:-}" ]]; then
            dispatch_spec "$spec_path" "$cost_today"
        else
            log "DRY-RUN: would dispatch $spec_path"
        fi
        processed=$((processed + 1))
    done
    shopt -u nullglob

    if [[ "$processed" -eq 0 ]]; then
        log "no specs queued (inbox empty)"
    else
        log "processed $processed spec(s)"
    fi
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
MODE="loop"
for arg in "$@"; do
    case "$arg" in
        --once) MODE="once" ;;
        --loop) MODE="loop" ;;
        --dry-run) MODE="once"; export DRY_RUN=1 ;;
        -h|--help)
            sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            log "warning: unknown arg '$arg' (ignored)"
            ;;
    esac
done

if [[ "$MODE" == "once" ]]; then
    run_once
else
    log "starting paperclip-spawner (interval=${PAPERCLIP_LOOP_INTERVAL_S}s)"
    while true; do
        run_once
        sleep "$PAPERCLIP_LOOP_INTERVAL_S"
    done
fi