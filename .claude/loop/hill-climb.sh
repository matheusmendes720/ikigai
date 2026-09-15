#!/bin/bash
# Hill-Climb v2 — pattern-based milestone proposal (supersedes v1)
# Reads observed patterns (progress.md, roadmap.md, constitution.md, SPEC.md files)
# and proposes 3 candidates as M-CAND-* sections in roadmap.md
#
# Usage:
#   bash .claude/loop/hill-climb.sh
#   bash .claude/loop/hill-climb.sh --dry-run
#
# v2 logic (M33): replaces v1's weekly stat summary + proposal file with
# a pattern-analysis loop that proposes concrete M-CAND-* milestones.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROGRESS_FILE="$SCRIPT_DIR/progress.md"
ROADMAP_FILE="$SCRIPT_DIR/roadmap.md"
CONSTITUTION_FILE="$SCRIPT_DIR/constitution.md"
SPECS_DIR="$PROJECT_ROOT/specs"
SIGNAL_REPORT="$PROJECT_ROOT/docs/superpowers/specs/signal-discovery-2026-09-15.md"

DRY_RUN=false
if [ "${1:-}" == "--dry-run" ]; then
  DRY_RUN=true
fi

# ── Helpers ────────────────────────────────────────────────────────────────

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] hill-climb-v2: $*" >&2; }

# ── Gather data ────────────────────────────────────────────────────────────

# Last 30 progress entries (tail of progress.md after the marker line)
PROGRESS_TAIL=$(awk '/^<!-- /{found=1} found' "$PROGRESS_FILE" 2>/dev/null | tail -30)

# Cost data from all progress entries
ALL_COSTS=$(grep "cost_usd:" "$PROGRESS_FILE" 2>/dev/null | awk -F': ' '{print $NF}' | tr -d ' ')

# Recent pass/fail counts
RECENT_PASS=$(echo "$PROGRESS_TAIL" | grep -c "| PASS" 2>/dev/null || echo "0")
RECENT_FAIL=$(echo "$PROGRESS_TAIL" | grep -c "| FAIL" 2>/dev/null || echo "0")

# ── CANDIDATE 1 — Drift Coverage Gap ─────────────────────────────────────
# Find constitution principles NOT yet referenced in any SPEC's constitution_refs.

CAND1_TITLE=""
CAND1_WHAT=""
CAND1_WHY=""

if [ -f "$CONSTITUTION_FILE" ] && [ -d "$SPECS_DIR" ]; then
  # Extract principle names from constitution.md (## and ### heading lines)
  # Each heading is a principle; split comma-separated multi-principle headings
  # Use newline-separated list to avoid bash word-splitting on spaces
  DECL_PRINCIPLES=$(grep -E "^#{2,3} [A-Z0-9]" "$CONSTITUTION_FILE" 2>/dev/null | \
    sed 's/^##* *//' | \
    tr ',' '\n' | sed 's/^ *//' | grep -v '^$' | sort -u | tr '\n' '|')

  # Collect all constitution_refs from SPEC.md files (YAML multiline list: - key)
  DECLARED_PRINCIPLES=""
  for spec in "$SPECS_DIR"/M*/SPEC.md; do
    [ -f "$spec" ] || continue
    # Get lines after "constitution_refs:" that start with "  - "
    refs=$(sed -n '/^constitution_refs:/,/^[a-z]/{s/^  - //p}' "$spec" 2>/dev/null || true)
    DECLARED_PRINCIPLES="$DECLARED_PRINCIPLES
$refs"
  done
  DECLARED_PRINCIPLES=$(echo "$DECLARED_PRINCIPLES" | grep -v '^$' | sort -u)

  # Find principles in constitution not referenced in any SPEC
  UNCOVERED=""
  IFS='|' read -ra PRINCIPLES <<< "$DECL_PRINCIPLES"
  for principle in "${PRINCIPLES[@]}"; do
    FOUND=$(echo "$DECLARED_PRINCIPLES" | grep -i "^${principle}$" 2>/dev/null || true)
    if [ -z "$FOUND" ]; then
      UNCOVERED="${UNCOVERED}${UNCOVERED:+, }${principle}"
    fi
  done

  if [ -n "$UNCOVERED" ]; then
    CAND1_TITLE="Drift Coverage — unconstitutioned principle"
    CAND1_WHAT="Audit unconstitutioned principles ($UNCOVERED). Add constitution_refs to SPEC.md files that exercise these principles, or create a new milestone to cover the gap."
    CAND1_WHY="Constitution principles without SPEC coverage create drift risk — the invariant is invisible to the drift net."
  fi
fi

# ── CANDIDATE 2 — Cost Anomaly ────────────────────────────────────────────
# If any recent cost > 2x baseline, propose investigate milestone.

CAND2_TITLE=""
CAND2_WHAT=""
CAND2_WHY=""

if [ -n "$ALL_COSTS" ]; then
  COST_COUNT=$(echo "$ALL_COSTS" | wc -l)
  if [ "$COST_COUNT" -gt 0 ]; then
    COST_SUM=$(echo "$ALL_COSTS" | awk '{s+=$1} END {printf "%.4f", s}')
    COST_AVG=$(echo "scale=4; $COST_SUM / $COST_COUNT" | bc 2>/dev/null || echo "0")

    # Check each recent cost against 2x baseline
    ANOMALY=""
    for cost in $ALL_COSTS; do
      THRESHOLD=$(echo "scale=4; $COST_AVG * 2" | bc 2>/dev/null || echo "0")
      IS_ABOVE=$(echo "$cost > $THRESHOLD" | bc 2>/dev/null || echo "0")
      if [ "$IS_ABOVE" = "1" ] && [ "$(echo "$COST_AVG > 0" | bc 2>/dev/null)" = "1" ]; then
        ANOMALY="$cost (baseline avg=$COST_AVG)"
        break
      fi
    done

    if [ -n "$ANOMALY" ]; then
      COST_AVG_DISPLAY=$(echo "$COST_AVG" | head -c 6)
      CAND2_TITLE="Cost Anomaly Investigation"
      CAND2_WHAT="Investigate elevated cost ($ANOMALY vs baseline avg $COST_AVG_DISPLAY). Identify the tick(s) driving the spike, determine root cause (LLM token usage, retry loop, or external API call), and add a cost guard to prevent recurrence."
      CAND2_WHY="Cost cap overruns threaten budget predictability. Early detection preserves the \$5/tick budget envelope."
    fi
  fi
fi

# ── CANDIDATE 3 — M29 Followup ────────────────────────────────────────────
# Read signal-discovery top-candidate #1 if exists and unaddressed.

CAND3_TITLE=""
CAND3_WHAT=""
CAND3_WHY=""

if [ -f "$SIGNAL_REPORT" ]; then
  # Check if M30 is already addressed (in progress or done)
  M30_STATUS=$(grep -E "^#{3,4}[[:space:]]+M30[^-]" "$ROADMAP_FILE" 2>/dev/null | \
    grep -oP '(?<=STATUS:\s)[\w-]+' | head -1 || echo "")
  if [ -n "$M30_STATUS" ] && [ "$M30_STATUS" != "PENDING" ]; then
    M31_STATUS=$(grep -E "^#{3,4}[[:space:]]+M31[^-]" "$ROADMAP_FILE" 2>/dev/null | \
      grep -oP '(?<=STATUS:\s)[\w-]+' | head -1 || echo "")
    if [ -n "$M31_STATUS" ] && [ "$M31_STATUS" != "PENDING" ]; then
      CAND3_TITLE="M29 Followup — streak-tracker reactivation (M31)"
      CAND3_WHAT="Restore streak-tracker cron (scripts/streak-tracker.sh) to active schedule. M9 shipped the infrastructure; cron is STOPPED. Reactivating completes the M9闭环."
      CAND3_WHY="Completes the M9 production-mode闭环; without streak tracking, unattended operation has no health signal."
    else
      CAND3_TITLE="M29 Followup — streak-tracker reactivation (M31)"
      CAND3_WHAT="Restore streak-tracker cron to active schedule. M9 shipped streak-tracker infrastructure; production mode 7-day unattended streak was never achieved. Reactivating completes the M9闭环."
      CAND3_WHY="Completes the M9闭环; streak-tracker provides automated loop health monitoring for unattended operation."
    fi
  else
    CAND3_TITLE="M29 Followup — cost-dashboard daemon activation (M30)"
    CAND3_WHAT="Restore cost-dashboard cron (scripts/cost-dashboard.sh) to active schedule. M7 shipped a working dashboard (\$0.5/day cap, spike detection); cron is STOPPED. Reactivating enables automated daily cost reports."
    CAND3_WHY="M7 identified cost observability as top risk; restoring the dashboard provides automated overrun detection before they accumulate."
  fi
fi

# ── Count how many candidates we have ───────────────────────────────────

CAND_COUNT=0
[ -n "$CAND1_TITLE" ] && CAND_COUNT=$((CAND_COUNT + 1))
[ -n "$CAND2_TITLE" ] && CAND_COUNT=$((CAND_COUNT + 1))
[ -n "$CAND3_TITLE" ] && CAND_COUNT=$((CAND_COUNT + 1))

log "CAND1: ${CAND1_TITLE:-skipped}"
log "CAND2: ${CAND2_TITLE:-skipped}"
log "CAND3: ${CAND3_TITLE:-skipped}"
log "Total candidates: $CAND_COUNT"

if [ "$CAND_COUNT" -eq 0 ]; then
  log "No candidates found. Exiting."
  exit 0
fi

# ── Build candidates section ───────────────────────────────────────────────

CAND_SECTIONS=""

add_cand() {
  local num=$1
  local title=$2
  local what=$3
  local why=$4
  CAND_SECTIONS="${CAND_SECTIONS}

### M-CAND-${num} — ${title} (STATUS: PROPOSED)
- **What:** ${what}
- **Why:** ${why}
- **Acceptance:**
  - [ ] Proposed milestone section added to roadmap.md
  - [ ] SPEC.md created with What/Why/Acceptance filled in
  - [ ] Drift net 65/65 PASS preserved
  - [ ] Human confirms before promotion to IN-PROGRESS
"
}

CAND_NUM=1
[ -n "$CAND1_TITLE" ] && add_cand "$CAND_NUM" "$CAND1_TITLE" "$CAND1_WHAT" "$CAND1_WHY" && CAND_NUM=$((CAND_NUM + 1))
[ -n "$CAND2_TITLE" ] && add_cand "$CAND_NUM" "$CAND2_TITLE" "$CAND2_WHAT" "$CAND2_WHY" && CAND_NUM=$((CAND_NUM + 1))
[ -n "$CAND3_TITLE" ] && add_cand "$CAND_NUM" "$CAND3_TITLE" "$CAND3_WHAT" "$CAND3_WHY"

# ── Dry-run output ───────────────────────────────────────────────────────

if $DRY_RUN; then
  echo "HILL-CLIMB v2 — Dry Run"
  echo "Candidates that would be added to roadmap.md:"
  echo "$CAND_SECTIONS"
  exit 0
fi

# ── Append candidates to roadmap.md (before ## Backlog section) ─────────────

BACKLOG_LINE=$(grep -n "^## Backlog" "$ROADMAP_FILE" 2>/dev/null | head -1 | cut -d: -f1 || echo "0")
if [ "$BACKLOG_LINE" = "0" ] || [ -z "$BACKLOG_LINE" ]; then
  # No Backlog section — append at end
  printf '%s\n\n' "$CAND_SECTIONS" >> "$ROADMAP_FILE"
else
  # Insert before Backlog section (HEAD = lines 1 to BACKLOG_LINE-1, TAIL = BACKLOG_LINE to end)
  HEAD_LINES=$(head -$((BACKLOG_LINE - 1)) "$ROADMAP_FILE")
  TAIL_LINES=$(tail -n +$BACKLOG_LINE "$ROADMAP_FILE")
  {
    printf '%s\n' "$HEAD_LINES"
    printf '%s\n' "$CAND_SECTIONS"
    printf '\n'
    printf '%s\n' "$TAIL_LINES"
  } > "$ROADMAP_FILE"
fi

log "Candidates written to $ROADMAP_FILE"

# ── Log to progress.md ───────────────────────────────────────────────────

CAND_LIST=""
CAND_NUM=1
[ -n "$CAND1_TITLE" ] && CAND_LIST="${CAND_LIST}M-CAND-${CAND_NUM}, " && CAND_NUM=$((CAND_NUM + 1))
[ -n "$CAND2_TITLE" ] && CAND_LIST="${CAND_LIST}M-CAND-${CAND_NUM}, " && CAND_NUM=$((CAND_NUM + 1))
[ -n "$CAND3_TITLE" ] && CAND_LIST="${CAND_LIST}M-CAND-${CAND_NUM}, " && CAND_NUM=$((CAND_NUM + 1))
CAND_LIST=$(echo "$CAND_LIST" | sed 's/, $//')

PROGRESS_ENTRY="
## $(date -u +%Y-%m-%dT%H:%M:%SZ) | hill-climb-v2 | PASS
- commit: —
- cost_usd: 0
- duration_min: 0
- model: opus
- attempt: 1/1
- notes: hill-climb-v2 proposed ${CAND_LIST} (${CAND_COUNT} candidates). Review and promote.
- next_action: review_and_promote"

echo "$PROGRESS_ENTRY" >> "$PROGRESS_FILE"
log "Progress entry appended to $PROGRESS_FILE"

echo ""
echo "HILL-CLIMB v2 — Complete"
echo "Proposed $CAND_COUNT candidate(s): $CAND_LIST"
echo "Review candidates in $ROADMAP_FILE"
echo "and promote selected ones to IN_PROGRESS manually."
