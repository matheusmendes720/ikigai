---
name: ikigai-daily
description: Run IKIGAI v2 daily reflection cycle — surfaces PAV-written state, emits pt-BR suggestions
entry_point: surface_intentions
actor: user
triggers:
  - cron: "57 8 * * *"     # 08:57 local — before workday starts
  - slash: "/ikigai-daily"
inputs:
  - vault: closing-2026/01-q3-2026/04-relatorios-diarios/{yesterday}.md
  - vault: meta/cycle_state/{date}.md
  - tool: taskdog_list_tasks(status="done", since=24h)
outputs: []
---

# ikigai-daily

Daily reflection cycle — reads PAV-written state, surfaces intentions as pt-BR suggestions.

## Invocation

```bash
# Via CLI
python -m interfaces.cli.v2 daily --date $(date +%Y-%m-%d)

# Via slash command in IKIGAI chat
/ikigai-daily
```

## Behavior

1. Read `vault/ikigai/meta/cycle_state/{date}.md` (PAV-written)
2. Read yesterday's daily report from `closing-2026/.../04-relatorios-diarios/`
3. Run prompt chain `surface_pav_intentions` → emit 3-5 pt-BR suggestions to CLI stdout (NOT to vault, NOT to taskdog)

## Example output

```
Sugestoes PAV (4):
  1. [FAKE-LLM] Considere revisar tasks com regime RECOVER ativo
  2. [FAKE-LLM] Vector passion_score baixo — ajustar habito matinal
  3. [FAKE-LLM] Q_HE em declinio — priorizar completion de tasks pendentes
  4. [FAKE-LLM] Verificar alinhamento com SONHO atual
```

## Constraints

- **Surface-only** — does not write vault; does not invoke taskdog
- **IKIGAI does NOT execute math** — observes PAV-written state only
- Downstream `v2 commit` (W3.6 territory) writes via `vault_write`
