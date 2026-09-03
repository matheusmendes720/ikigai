---
name: ikigai-monthly
description: Run IKIGAI v2 monthly review — aggregate weekly reviews, Q_HE trend analysis
triggers:
  - cron: "0 10 1 * *"   # 1st of month 10:00 local
  - slash: "/ikigai-monthly"
inputs:
  - vault: closing-2026/*/weekly-review/*.md (last 4 weeks)
  - vault: meta/cycle_state/{date}.md
  - vault: meta/habit_state/{date}.md
outputs:
  - vault_write: closing-2026/01-q3-2026/monthly-review-{date}.md
---

# ikigai-monthly

Monthly review — aggregates weekly reviews, trend analysis, strategic realignment.

## Invocation

```bash
# Via CLI
python -m interfaces.cli.v2 cycle --dry-run && \
python -m interfaces.cli.v2 score --date $(date +%Y-%m-%d)

# Via slash command in IKIGAI chat
/ikigai-monthly
```

## Behavior

1. Read last 4 weekly review reports from `closing-2026/*/weekly-review/`
2. Read current `cycle_state/{date}.md` and `habit_state/{date}.md`
3. Run `v2_score` for trend analysis — monthly passion vector
4. Run `v2_regime` — updated regime recommendation
5. Run full `v2_cycle` — 8-node graph end-to-end for monthly context
6. Write monthly review report via `vault_write` MCP tool (sole vault writer)

## Example output

```
OK Cycle dry-run complete (last_step=surface_intentions)
  commit_summary: Monthly review cycle complete

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
- Monthly review is READ-ONLY on fork adapters
- All writes go through `vault_write` MCP tool
