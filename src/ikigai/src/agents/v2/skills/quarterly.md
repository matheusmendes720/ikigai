---
name: ikigai-quarterly
description: Run IKIGAI v2 quarterly review — strategic realignment, wave planning, Q_HE trend
triggers:
  - cron: "0 11 1 1,4,7,10 *"   # 1st of Jan/Apr/Jul/Oct at 11:00 local
  - slash: "/ikigai-quarterly"
inputs:
  - vault: closing-2026/*/monthly-review/*.md (last 3 months)
  - vault: closing-2026/*/weekly-review/*.md (last 13 weeks)
  - vault: meta/cycle_state/{date}.md
  - vault: meta/habit_state/{date}.md
outputs:
  - vault_write: closing-2026/Q{quarter}-YYYY/quarterly-review-{date}.md
  - taskdog_create_task: quarterly OKRs
---

# ikigai-quarterly

Quarterly review — strategic realignment, wave planning, Q_HE composite trend analysis.

## Invocation

```bash
# Via CLI — run full cycle then score and regime
python -m interfaces.cli.v2 cycle --dry-run && \
python -m interfaces.cli.v2 score --date $(date +%Y-%m-%d) && \
python -m interfaces.cli.v2 regime --date $(date +%Y-%m-%d)

# Via slash command in IKIGAI chat
/ikigai-quarterly
```

## Behavior

1. Read last 3 monthly review reports from `closing-2026/*/monthly-review/`
2. Read last 13 weekly review reports from `closing-2026/*/weekly-review/`
3. Read current `cycle_state/{date}.md` and `habit_state/{date}.md`
4. Run `v2_cycle` — full 8-node graph for quarterly context
5. Run `v2_score` — quarterly passion vector
6. Run `v2_regime` — regime recommendation for next quarter
7. Write quarterly review report via `vault_write` MCP tool (sole vault writer)
8. Create quarterly OKR tasks via `taskdog_create_task`

## Example output

```
OK Cycle dry-run complete (last_step=surface_intentions)
  commit_summary: Quarterly review cycle complete

[PAV passion observation for 2026-09-03]
  passion_score: 70
  rationale: [FAKE-LLM stub for test]

[PAV regime observation for 2026-09-03]
  regime: MAINTAIN
  rationale: [FAKE-LLM stub for test]
```

## Constraints

- **vault_write is the SOLE vault writer** — no direct vault writes
- **IKIGAI does NOT execute math** — observes PAV-written state only
- Quarterly review is READ-ONLY on fork adapters
- All writes go through `vault_write` MCP tool
- Reads from `vault/` only — never writes to vault directly
