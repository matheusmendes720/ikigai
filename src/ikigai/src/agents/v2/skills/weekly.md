---
name: ikigai-weekly
description: Run IKIGAI v2 weekly review — score vectors, heuristics, regime check
entry_point: observe
actor: agent
triggers:
  - cron: "0 9 * * 1"   # Monday 09:00 local
  - slash: "/ikigai-weekly"
inputs:
  - vault: closing-2026/*/04-relatorios-diarios/*.md (last 7 days)
  - vault: meta/cycle_state/{date}.md
  - vault: meta/habit_state/{date}.md
outputs:
  - vault_write: closing-2026/*/weekly-review/{date}.md
  - taskdog_create_task: weekly priorities
---

# ikigai-weekly

Weekly review — aggregates daily reports, scores vectors, emits regime observation.

## Invocation

```bash
# Via CLI
python -m interfaces.cli.v2 cycle --dry-run

# Via slash command in IKIGAI chat
/ikigai-weekly
```

## Behavior

1. Read last 7 daily reports from `closing-2026/.../04-relatorios-diarios/`
2. Read current `cycle_state/{date}.md` and `habit_state/{date}.md`
3. Run `v2_score` — passion vector observation via `score_passion_observation` prompt chain
4. Run `v2_regime` — regime check via `heuristics_regime_observation` prompt chain
5. Write weekly review report via `vault_write` MCP tool (sole vault writer)
6. Create weekly priorities via `taskdog_create_task`

## Example output

```
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
- Weekly review is READ-ONLY on all fork adapters (no taskdog writes in review)
- All writes go through `vault_write` MCP tool
