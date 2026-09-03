---
name: ikigai-daily
description: Run IKIGAI v2 daily reflection cycle — surfaces PAV-written state, emits pt-BR suggestions
triggers:
  - cron: "57 8 * * *"     # 08:57 local — before workday starts
  - slash: "/ikigai-daily"
inputs:
  - vault: closing-2026/01-q3-2026/04-relatorios-diarios/{yesterday}.md
  - vault: meta/cycle_state/{date}.md
  - tool: taskdog_list_tasks(status="done", since=24h)
outputs:
  - vault_write: closing-2026/01-q3-2026/04-relatorios-diarios/{date}.md
  - taskdog_create_task: top-3 priorities
---

# ikigai-daily

Daily reflection cycle — reads PAV-written state, surfaces intentions as pt-BR suggestions.

## Invocation

```bash
# Via CLI
python -m interfaces.cli.v2 suggest --date $(date +%Y-%m-%d)

# Via slash command in IKIGAI chat
/ikigai-daily
```

## Behavior

1. Read `vault/ikigai/meta/cycle_state/{date}.md` (PAV-written)
2. Read yesterday's daily report from `closing-2026/.../04-relatorios-diarios/`
3. Run prompt chain `surface_pav_intentions` → emit 3-5 pt-BR suggestions
4. Write today's daily report via `vault_write` MCP tool (sole vault writer)
5. Create top-3 priority tasks via `taskdog_create_task` (if suggestions reference tasks)

## Example output

```
Sugestoes PAV (4):
  1. [FAKE-LLM] Considere revisar tasks com regime RECOVER ativo
  2. [FAKE-LLM] Vector passion_score baixo — ajustar habito matinal
  3. [FAKE-LLM] Q_HE em declinio — priorizar completion de tasks pendentes
  4. [FAKE-LLM] Verificar alinhamento com SONHO atual
```

## Constraints

- **vault_write is the SOLE vault writer** — no direct vault writes from skill code
- **IKIGAI does NOT execute math** — observes PAV-written state only
- All writes go through `vault_write` MCP tool or `taskdog_*` tools
- Reads from `vault/` only — never writes to vault directly
