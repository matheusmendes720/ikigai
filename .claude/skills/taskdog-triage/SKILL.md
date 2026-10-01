---
name: taskdog-triage
description: Proactive daily scan of taskdog state — detects deadline-soon / overdue / missing-description / long-blocked / long-paused tasks and emits review-queue proposals (NEVER auto-executes). Cron 09:00, slash /triage.
version: 1.0.0
created: 2026-10-01
tier: production-ready
entry_point: agents.v2.skills.taskdog_triage.run_skill
actor: cron | user
triggers:
  - cron: "0 9 * * *"        # 09:00 local — start of workday
  - slash: "/triage"
  - slash: "/skill taskdog-triage"
inputs:
  - tool: TaskdogAdapter.list_all()  → list of task dicts
  - tool: taskdog_audit             → context for blocked/paused heuristics
outputs:
  - review_queue: data/review_queue/*.json (action: "triage_<finding>")
---

# taskdog-triage

Proactive daily scan that surfaces taskdog tasks needing attention. **Emits
proposals only — never executes changes directly.** User approves via
`--approve` and only then are changes applied via the review queue.

## What it detects

| Finding | Trigger | Proposed action |
|---------|---------|-----------------|
| `deadline_soon` | `deadline` within 48 h AND `status != "done"` | UPDATE `priority` → 1 |
| `overdue` | `planned_start < today` AND `status == "planned"` | UPDATE `status` → `in_progress` |
| `missing_description` | `description` is empty or shorter than 10 chars | UPDATE `description` → auto-flag note |
| `blocked_long` | `status == "blocked"` for > 7 days (per taskdog_audit) | UPDATE `description` with stale-flag rationale |
| `paused_long` | `status == "paused"` for > 14 days (per taskdog_audit) | UPDATE `description` with stale-flag rationale |

Each finding produces a `TaskChange` proposal with action `triage_<finding>`
(e.g. `triage_deadline_soon`).

## Algorithm (pseudocode)

```
def propose(tasks, today=None):
    today = today or date.today()
    changes = []

    for t in tasks:
        ueid = t.get("ueid")
        if not ueid: continue

        deadline = parse_iso(t.get("deadline"))
        planned_start = parse_iso(t.get("planned_start"))
        status = t.get("status", "")
        priority = t.get("priority")
        description = (t.get("description") or "").strip()

        # 1. Deadline within 48h
        if deadline and 0 <= (deadline - today).days <= 2 and status != "done":
            if priority is None or priority > 1:
                changes.append({
                    "action": "triage_deadline_soon",
                    "ueid": ueid,
                    "fields": {"priority": 1},
                    "rationale": f"deadline in {(deadline-today).days}d ({deadline})",
                })

        # 2. Overdue planned
        if planned_start and planned_start < today and status == "planned":
            changes.append({
                "action": "triage_overdue",
                "ueid": ueid,
                "fields": {"status": "in_progress"},
                "rationale": f"planned_start {planned_start} is in the past",
            })

        # 3. Missing / too-short description
        if len(description) < 10:
            changes.append({
                "action": "triage_missing_description",
                "ueid": ueid,
                "fields": {"description": f"(auto-flagged {today}: needs human description)"},
                "rationale": f"description is {len(description)} chars (min 10)",
            })

        # 4. Blocked > 7 days, 5. Paused > 14 days
        # (uses taskdog_audit to compute staleness; see detect_blocked_paused())

    return Proposal(
        skill="taskdog-triage",
        reasoning=f"scanned {len(tasks)} task(s) for {today}: ... found {len(changes)} candidate(s)",
        changes=changes,
    )
```

## Inputs and outputs

**Inputs:**
- `tasks: list[dict]` — flat dicts from `TaskdogAdapter.list_all()`. Each
  must have `ueid`, may have `status`, `priority`, `deadline`, `planned_start`,
  `description`, `blocked_since`, `paused_since`.
- `today: date | None` — defaults to `date.today()`. Override for testing.

**Outputs:**
- `Proposal` with `approval_state="pending"`. The skill NEVER calls
  `queue.enqueue` directly. The user runs `--approve` and the chat loop
  converts the proposal into `TaskChange` events for the review queue.

## Cron and slash

```bash
# Cron entry (09:00 local)
0 9 * * *  cd <repo> && uv run python -m interfaces.cli.main v2 daily --skill taskdog-triage

# Manual slash command
/triage
```

## Constraints (NON-NEGOTIABLE)

1. **NEVER auto-execute** — every change goes through the proposal → review queue pipeline.
2. **Cron preserved** — `0 9 * * *`.
3. **Idempotent** — running twice on the same day produces identical proposals.
4. **Per-task deterministic** — same `tasks` + `today` → same `changes`.
5. **Dependency-free** — the `detect_changes()` function takes plain dicts so
   it can be unit-tested without spinning up the TaskdogAdapter.

## Error handling

| Failure | Behavior |
|---------|----------|
| Task without `ueid` | Skipped silently |
| Malformed `deadline` / `planned_start` | Parsed as `None`, no detection triggered |
| `TaskdogAdapter` raises | Skill returns empty `Proposal` with `reasoning="<error>"` |
| `taskdog_audit` unavailable | `blocked_long` / `paused_long` skipped; other 3 still run |

## Tests

Tests at `src/ikigai/tests/skills/test_taskdog_triage.py`:
- `detect_changes` returns expected changes for fixture tasks
- `propose` builds a valid `Proposal` with `approval_state="pending"`
- Idempotency: running `propose(tasks, today=T)` twice → identical output
- Missing-ueid tasks are skipped
- Malformed dates parsed as None (no false positives)
- Review-queue integration: approved proposal → `TaskChange` lands in queue
- Mocked `TaskdogAdapter` failure → empty proposal, no crash

## Implementation

```python
from agents.v2.skills.taskdog_triage import (
    SKILL_NAME,           # "taskdog-triage"
    detect_changes,       # pure function on dicts
    propose,              # builds Proposal from task list
    run_skill,            # entry point for /skill taskdog-triage
)
```

See `src/ikigai/src/agents/v2/skills/taskdog_triage.py` for the canonical
implementation. Thresholds (`DEADLINE_WINDOW_DAYS = 2`, `DESCRIPTION_MIN_LEN = 10`)
are module constants — bump them deliberately, never per-call.

## Provenance

Skill shipped in M161 (Sep 2026) as a stub. Implementation fleshed out per
M162 — added `blocked_long` and `paused_long` heuristics on top of the
original 3, plus review-queue integration tests.
