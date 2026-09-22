#!/usr/bin/env bash
# M114g — Backtest Q1 driver
#
# Runs the full backtest pipeline end-to-end:
#   1. Generate scenarios (M114a) — if not already present
#   2. Pad with synthetic gap-fillers (M114d) — if not already present
#   3. Map scenarios to role-anchors (M114e) — if not already present
#   4. Run deterministic harness through real taskdog-server (M114b)
#   5. Score with rule-based judge (M114c)
#   6. Render markdown report (M114g)
#
# Writes:
#   reports/backtest-Q1-results.json   (M114b harness output)
#   reports/backtest-Q1-judgment.json  (M114c judge output)
#   reports/backtest-Q1.md             (M114g markdown report)
#
# Usage:
#   bash scripts/backtest/run_backtest.sh           # full pipeline
#   bash scripts/backtest/run_backtest.sh --skip-gen  # skip scenario generation

set -euo pipefail

# --- Resolve repo root from script location ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Convert to native path for Windows Python (Git Bash + MSYS need cygpath).
if command -v cygpath >/dev/null 2>&1; then
    PYTHONPATH_SRC="$(cygpath -w "$REPO")"
    SCENARIOS_WIN="$(cygpath -w "$REPO/vault/drafts/q3-scenarios.with-anchors.yaml")"
    RESULTS_WIN="$(cygpath -w "$REPO/reports/backtest-Q1-results.json")"
    JUDGMENT_WIN="$(cygpath -w "$REPO/reports/backtest-Q1-judgment.json")"
    REPORT_WIN="$(cygpath -w "$REPO/reports/backtest-Q1.md")"
    DRIFT_WIN="$(cygpath -w "$REPO/reports/backtest-drift.md")"
    BASELINE_WIN="$(cygpath -w "$REPO/reports/backtest-Q1-judgment.bak.json")"
    LLM_WIN="$(cygpath -w "$REPO/reports/backtest-Q1-llm-judgment.json")"
    SCENARIOS_NAT_YAML="$(cygpath -w "$REPO/vault/drafts/q3-scenarios.yaml")"
    SCENARIOS_NAT_EXHAUSTIVE="$(cygpath -w "$REPO/vault/drafts/q3-scenarios.exhaustive.yaml")"
else
    PYTHONPATH_SRC="$REPO"
    SCENARIOS_WIN="$REPO/vault/drafts/q3-scenarios.with-anchors.yaml"
    RESULTS_WIN="$REPO/reports/backtest-Q1-results.json"
    JUDGMENT_WIN="$REPO/reports/backtest-Q1-judgment.json"
    REPORT_WIN="$REPO/reports/backtest-Q1.md"
    DRIFT_WIN="$REPO/reports/backtest-drift.md"
    BASELINE_WIN="$REPO/reports/backtest-Q1-judgment.bak.json"
    LLM_WIN="$REPO/reports/backtest-Q1-llm-judgment.json"
    SCENARIOS_NAT_YAML="$REPO/vault/drafts/q3-scenarios.yaml"
    SCENARIOS_NAT_EXHAUSTIVE="$REPO/vault/drafts/q3-scenarios.exhaustive.yaml"
fi
export PYTHONPATH="$PYTHONPATH_SRC"

cd "$REPO"

# --- Python interpreter ---
PYTHON="${PYTHON:-src/ikigai/.venv/Scripts/python.exe}"
if [[ ! -x "$PYTHON" ]]; then
    PYTHON="python"
fi

# --- Optional flag: --skip-gen (assume scenarios already exist) ---
SKIP_GEN=0
for arg in "$@"; do
    if [[ "$arg" == "--skip-gen" ]]; then
        SKIP_GEN=1
    fi
done

echo "===================================="
echo "  Backtest Q1 — full pipeline"
echo "  repo: $REPO"
echo "  python: $PYTHON"
echo "  skip-gen: $SKIP_GEN"
echo "===================================="

# --- 1. Verify taskdog-server is reachable ---
echo ""
echo "[1/5] Checking taskdog-server health..."
set +e
HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/api/v1/tasks?limit=1" 2>/dev/null | tr -d '\n\r ')
curl_status=$?
set -e
HEALTH_CODE="${HEALTH_CODE:-000}"
if [[ "$HEALTH_CODE" != "200" ]]; then
    echo "  ERROR: taskdog-server unreachable at http://127.0.0.1:8000 (got HTTP $HEALTH_CODE, curl_status=$curl_status)" >&2
    echo "  Start it with: cd taskwarrior/taskdog-server && uv run uvicorn main:app" >&2
    exit 2
fi
echo "  taskdog-server OK (HTTP 200)"

# --- 2. Generate scenarios if needed ---
if [[ $SKIP_GEN -eq 0 ]]; then
    echo ""
    echo "[2/5] Generating scenarios..."
    EXHAUSTIVE="$REPO/vault/drafts/q3-scenarios.exhaustive.yaml"
    if [[ ! -f "$EXHAUSTIVE" ]]; then
        echo "  Running M114a (seed_q3_scenarios.py)..."
        "$PYTHON" tools/backtest/seed_q3_scenarios.py --out "$REPO/vault/drafts/q3-scenarios.yaml"
        echo "  Running M114d (taskdog_exhaustiveness.py)..."
        "$PYTHON" tools/backtest/taskdog_exhaustiveness.py \
            --scenarios "$REPO/vault/drafts/q3-scenarios.yaml" \
            --out "$REPO/vault/drafts/q3-scenarios.exhaustive.yaml"
    else
        echo "  $EXHAUSTIVE exists; skipping generation"
    fi
    echo "  Running M114e (role_anchors.py)..."
    "$PYTHON" tools/backtest/role_anchors.py \
        --scenarios "$EXHAUSTIVE" \
        --out "$REPO/vault/drafts/q3-scenarios.with-anchors.yaml"
else
    echo ""
    echo "[2/5] Skipping scenario generation (--skip-gen)"
fi

# --- 3. Run harness ---
echo ""
echo "[3/5] Running M114b backtest harness..."
"$PYTHON" tools/backtest/backtest_harness.py \
    --scenarios "$SCENARIOS_WIN" \
    --out "$RESULTS_WIN"

# --- 4. Judge ---
echo ""
echo "[4/5] Running M114c judge_llm..."
"$PYTHON" tools/backtest/judge_llm.py \
    --scenarios "$SCENARIOS_WIN" \
    --harness-results "$RESULTS_WIN" \
    --out "$JUDGMENT_WIN"

# --- 5. Render report ---
echo ""
echo "[5/6] Rendering M114g markdown report..."
"$PYTHON" tools/backtest/backtest_report.py \
    --results "$RESULTS_WIN" \
    --judgment "$JUDGMENT_WIN" \
    --out "$REPORT_WIN"

# --- 6. Drift detection (M115) ---
echo ""
echo "[6/7] Running M115 backtest_drift..."
if [[ -f "$BASELINE_WIN" ]]; then
    "$PYTHON" tools/backtest/backtest_drift.py \
        --current "$JUDGMENT_WIN" \
        --baseline "$BASELINE_WIN" \
        --out "$DRIFT_WIN"
else
    # First run — snapshot current as baseline for next time.
    "$PYTHON" tools/backtest/backtest_drift.py \
        --current "$JUDGMENT_WIN" \
        --baseline "$BASELINE_WIN" \
        --out "$DRIFT_WIN" \
        --snapshot
    echo "  (No baseline found — snapshotted current as baseline for next run)"
fi

# --- 7. LLM-judge (M116) ---
echo ""
echo "[7/7] Running M116 llm_judge..."
USE_LLM_FLAG=""
if [[ "${USE_LLM:-0}" == "1" ]]; then
    USE_LLM_FLAG="--use-llm"
    echo "  (USE_LLM=1; will call ChatAnthropic if API key available)"
else
    echo "  (stub mode; pass USE_LLM=1 to enable real LLM)"
fi
"$PYTHON" tools/backtest/llm_judge.py \
    --scenarios "$SCENARIOS_WIN" \
    --harness-results "$RESULTS_WIN" \
    --out "$LLM_WIN" \
    $USE_LLM_FLAG

echo ""
echo "===================================="
echo "  Backtest Q1 complete."
echo "  Report:   reports/backtest-Q1.md"
echo "  Drift:    reports/backtest-drift.md"
echo "  LLM-judge: reports/backtest-Q1-llm-judgment.json"
echo "===================================="
