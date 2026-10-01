---
name: M161-skills
description: 2 new skills (taskdog-triage + vault-intent-extract) — meta_plan pattern, propose-only, never auto-exec.
status: PENDING
owner: loop-orchestrator
created: 2026-09-29
constitution_refs:
  - composition_over_inheritance
  - tests_are_the_contract
  - reversibility_over_cleverness
  - state_on_disk_not_conversation
estimated_cost_usd: 0.50
---

# M161 — 2 skills novos: taskdog-triage + vault-intent-extract

**Status:** 🟡 PLANNED
**Date:** 2026-09-29
**Author:** loop-orchestrator + user
**Builds on:** M158 (td chat REPL), M155 (meta_plan pattern), M168 (roadmap)
**Goal:** Implementar 2 skills novos que operam automaticamente via cron,
seguindo o padrão meta_plan (NUNCA auto-exec, sempre propõe primeiro).

---

## TL;DR

| Skill | Cron | O que faz | Output |
|---|---|---|---|
| `taskdog-triage` | 09:00 diário | Detecta tasks overdue, deadline < 48h, sem descrição | Proposal com updates (priority, status, due) |
| `vault-intent-extract` | 22:00 diário | Lê `vault/daily/{date}.md`, extrai "amanhã eu faço X" | Proposal com novas tasks via review queue |

Ambos NUNCA executam. Sempre emitem Proposal e esperam `--approve`.

---

## Skill 1: `taskdog-triage`

### Cron
- Triggers: `0 9 * * *` (todo dia 09:00 local)
- Slash: `/triage`
- Manual: `td chat /skill triage`

### Inputs
- `taskdog_list(status="active")` — todas tasks não-done
- `vault/daily/{today}.md` se existir (contexto)
- `cycle_state/{today}.md` se existir (regras)

### Lógica de detecção

```python
def detect_changes(tasks: list[dict], today: date) -> list[TaskChange]:
    changes = []
    for t in tasks:
        ueid = t["ueid"]
        priority = t.get("priority")
        deadline = t.get("deadline")
        status = t.get("status")
        description = t.get("description", "")

        # 1. Deadline < 48h e status != done
        if deadline:
            try:
                dl = date.fromisoformat(deadline)
                days_until = (dl - today).days
                if 0 <= days_until <= 2 and status != "done":
                    # Sugerir bump de priority se ainda não está max
                    if priority is None or priority > 2:
                        changes.append(TaskChange(
                            action=TaskAction.UPDATE,
                            ueid=ueid,
                            fields={"priority": 1},
                            rationale=f"deadline in {days_until} days, status={status}",
                        ))
            except ValueError:
                pass

        # 2. Overdue (planned_start no passado e status == planned)
        planned_start = t.get("planned_start")
        if planned_start and status == "planned":
            try:
                ps = date.fromisoformat(planned_start)
                if ps < today:
                    changes.append(TaskChange(
                        action=TaskAction.UPDATE,
                        ueid=ueid,
                        fields={"status": "in_progress"},
                        rationale=f"planned_start {planned_start} is in the past",
                    ))
            except ValueError:
                pass

        # 3. Sem descrição (UX ruim)
        if not description or len(description.strip()) < 10:
            changes.append(TaskChange(
                action=TaskAction.UPDATE,
                ueid=ueid,
                fields={"description": f"(auto) pending review for {today.isoformat()}"},
                rationale="missing or too-short description",
            ))

    return changes
```

### Output
- `Proposal` com lista de `TaskChange`s
- Aprovação via `--approve` aplica via `review_queue.enqueue`
- Cada change passa pelo `agent_consumer.validate_*` (M148)

### Tests
- 3 tasks: 1 overdue, 1 deadline-soon, 1 no-description → 3 changes propostas
- 0 tasks → 0 changes
- Tasks already-done ignoradas
- Data inválida (deadline="invalid") não crasha

---

## Skill 2: `vault-intent-extract`

### Cron
- Triggers: `0 22 * * *` (todo dia 22:00 local)
- Slash: `/extract`
- Manual: `td chat /skill extract`

### Inputs
- `vault/daily/{today}.md` — nota do dia (criada pelo usuário)
- Se não existir: skill termina com 0 mudanças

### Lógica de extração

#### Phase 1 — Regex (rápido, determinístico)

```python
INTENT_PATTERNS = [
    (r"amanhã\s+(?:eu\s+)?(?:vou\s+|vai\s+|farei\s+|faço\s+)?(?P<task>.+?)(?:\.|;|$)",
     "tomorrow"),
    (r"próxima\s+semana\s+(?:eu\s+)?(?:vou\s+|vai\s+|farei\s+|faço\s+)?(?P<task>.+?)(?:\.|;|$)",
     "next_week"),
    (r"deadline\s+(?:é\s+)?(?P<date>\d{4}-\d{2}-\d{2})\s+(?:para\s+|pro\s+)?(?P<task>.+?)(?:\.|;|$)",
     "deadline"),
    (r"(?:TODO|FIXME|XXX)\s*:?\s*(?P<task>.+?)(?:\.|;|$)",
     "todo"),
    (r"lembrar\s+de\s+(?P<task>.+?)(?:\.|;|$)",
     "reminder"),
]
```

Cada match vira candidate com due_date inferido (amanhã, +1 dia; próxima semana, +7; deadline, data explícita).

#### Phase 2 — LLM refinement (opcional, M161c)

Hoje: só regex. M161c adiciona LLM refinement dos candidates com descarte de falso-positivo.

### Output
- `Proposal` com lista de CREATE TaskChange
- Cada candidate vira task com:
  - `ueid`: gerado determinístico (`tsk:intention:{hash}:{rand}`)
  - `name`: texto do task (truncado 80 chars)
  - `priority`: default 3 (baixa)
  - `due`: data inferida (se pattern tem data)

### Tests
- Markdown com 5 patterns diferentes → 5 candidates
- Markdown vazio → 0 candidates
- Markdown sem patterns → 0 candidates
- Cada candidate tem ueid único, priority=3, due correto
- Aprovação → tasks criadas via review_queue

---

## Architecture

### File layout

```
src/ikigai/src/agents/v2/skills/
├── __init__.py
├── taskdog_triage.py        # Skill 1
└── vault_intent_extract.py  # Skill 2

src/ikigai/src/agents/v2/proposals.py  # NEW: shared Proposal type
```

### Proposal type

Reusa o que tá em `v2/state.py` se já existir, senão cria:

```python
@dataclass
class Proposal:
    skill: str
    reasoning: str
    changes: list[dict]  # each is {action, ueid, fields, rationale}
    created_at: datetime
    vault_log_path: str | None = None
    approval_state: str = "pending"  # pending | approved | rejected | applied
```

### Skill runner

```python
async def run_skill(skill_name: str, context: dict) -> Proposal:
    if skill_name == "taskdog-triage":
        return await taskdog_triage.propose(context)
    if skill_name == "vault-intent-extract":
        return await vault_intent_extract.propose(context)
    raise ValueError(f"unknown skill: {skill_name}")
```

(Async pra futuro, hoje roda sync wrapped em asyncio.to_thread se precisar.)

### Wire-up to td chat

`td chat` REPL (M158) já tem `/skill <name> <args>`. Vou:
- Adicionar `/triage` como atalho de `/skill taskdog-triage`
- Adicionar `/extract` como atalho de `/skill vault-intent-extract`
- Skills registradas como disponíveis na inicialização do REPL

### Wire-up to cron

`~/.claude/loop/cron.json` (ou similar) — vou criar entrada:
```json
{
  "taskdog-triage": "0 9 * * *",
  "vault-intent-extract": "0 22 * * *"
}
```

(M163+ vai implementar o cron runner real. M161 só cria as funções.)

---

## Out of scope (explícito)

- ❌ Auto-approval (meta_plan pattern: sempre pede `--approve`)
- ❌ LLM refinement dos candidates (M161c)
- ❌ Cron runner real (M163+)
- ❌ UI no `td tui` mostrando "1 proposta pendente" (M160 cancelado)
- ❌ Cross-session memory (M171+)

---

## LOC budget

| File | LOC | Notas |
|---|---|---|
| `proposals.py` | ~80 | Proposal dataclass + helpers |
| `taskdog_triage.py` | ~180 | detect_changes + propose |
| `vault_intent_extract.py` | ~200 | regex patterns + candidate generation |
| `taskdog_chat.py` (patch) | ~30 | atalhos /triage, /extract |
| `tests/test_m161_taskdog_triage.py` | ~120 | 4 tests |
| `tests/test_m161_vault_intent_extract.py` | ~150 | 5 tests |
| **Total** | **~760 LOC** | |

---

## Critério de done

- [ ] `proposals.py` com Proposal dataclass + 3 testes
- [ ] `taskdog_triage.py` com detect_changes + propose + 4 testes
- [ ] `vault_intent_extract.py` com 5 patterns + propose + 5 testes
- [ ] `td chat` reconhece `/triage` e `/extract`
- [ ] Cada skill roda em FAKE_LLM mode sem LLM real
- [ ] Cada skill emite Proposal, espera `--approve`
- [ ] Aprovação aplica via review_queue (M148 path intacto)
- [ ] 12 testes novos passam, zero regressão nos 55 existentes

## Riscos

| Risco | Mitigação |
|---|---|
| Regex pega falso-positivo (ex: "amanhã chover") | User revisa Proposal antes de `--approve` |
| Vault path não existe | Skill termina com 0 changes + log info |
| `vault/daily/{today}.md` schema indefinido | Spec M155 disse OPÇÃO B (`vault/daily/`); M161 assume |
| Cron runner não existe ainda | Manual via `td chat /triage` funciona AGORA |
| `taskdog_list` API muda | Wrap em adapter; testa contra stub |
