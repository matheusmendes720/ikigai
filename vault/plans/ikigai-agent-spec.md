---
name: ikigai-agent-spec
description: IKIGAI — Agente de Planejamento Estratégico (cérebro do sistema)
type: spec
---

# IKIGAI — Agente de Planejamento Estratégico

## Posicionamento

IKIGAI é o **cérebro** — o agente de planejamento estratégico que:
- Mantém estado completo via checkpointers stateful (SqliteSaver)
- Lê o vault indexado por YAML (SONHOS, objetivos, projetos)
- Executa o ciclo de planejamento: observe → score → heurísticas → balance → decompose → planeje → reflita → commit
- **Backpropagation**: feedback das interfaces alimenta o próximo ciclo
- Recomenda tarefas, prazos, horários
- Orquestra interfaces (Gantt, Kanban, Calendar)

**PAV é o sensor** — alimenta IKIGAI com QHEMetrics, HabitState, PolicyDecision.

```
┌──────────────────────────────────────────────────────────────┐
│  IKIGAI (cérebro — sole writer to vault/)                     │
│                                                                  │
│ vault/ ←──── feedback loop (execution rate, burndown)         │
│    │                                                              │
│    ├── QHEMetrics ←────── PAV (sensor)                         │
│    ├── HabitState                                               │
│    ├── PolicyDecision                                          │
│    └── VaultEvent (planned vs actual)                          │
│                                                                  │
│  interfaces/ ←── planejamento rico (tasks com descrições)      │
│                                                                  │
│  Ciclo: observe → score → heurísticas → balance               │
│          → decompose → plan → reflect → commit                 │
└──────────────────────────────────────────────────────────────┘
```

## Ciclo de Planejamento (8 nós LangGraph)

```
observe (lê vault + PAV feedback)
  → score_vectors (5-vector scores)
    → heuristics (H1-H6 signals)
      → balance (workload vs capacity)
        → decompose (UEID hierarchy)
          → plan (gera Tasks ricas)
            → reflect (retrospective log)
              → commit (escreve vault + interfaces)
```

### Nó: observe
- Lê SONHOS, objetivos, projetos do vault
- Lê QHEMetrics + PolicyDecision de PAV
- Lê VaultEvent (planned vs actual) de interfaces

### Nó: score_vectors
- passion, skill, market, revenue, course
- Usa weights da fase atual (FUNDAÇÃO/BUSCA/HACKATHON/RECUPERACAO/OVERCLOCK)

### Nó: heuristics (H1-H6)
```
H1: Regime consistency (desvio do Q_HE esperado)
H2: Phase convergence (weights convergindo para targets?)
H3: Passion decay (drift do vetor passion?)
H4: Velocity gap (progresso vs velocidade planejada)
H5: Strategic friction (blockers acumulando?)
H6: Recovery signals (RECOVER produzindo benefícios esperados?)
```

### Nó: balance
- Workload estimate vs Capacity estimate
- Verdict: OK | OVERLOADED | UNDERLOADED

### Nó: decompose
- UEID hierarchy walk: dream → objectives → projects → deliverables

### Nó: plan
- Gera `Task` objects (do contracts) com descrições ricas
- Classifica por horizon: today/tomorrow/this_week/onda/sprint
- Estima effort_minutes, dependencies

### Nó: reflect
- Retrospective log: o que funcionou/não funcionou
- Atualiza phase_weights se H2 detectar convergência

### Nó: commit
- Escreve Tasks no vault/ (via VaultEvent)
- Sincroniza interfaces (via MCP Gateway)
- Persiste checkpoint (SqliteSaver)

## Ferramentas IKIGAI (18 tools)

```python
# IKIGAI core (8)
ikigai_score        # 5-vector + meta-vector
ikigai_regime      # regime + Q_HE + days_in_regime
ikigai_phase       # phase + iteration + weight distribution
ikigai_corrections # H1-H6 signals
ikigai_decompose   # UEID hierarchy walk
ikigai_plan_cycle  # executa ciclo completo
ikigai_sync_vault  # escreve checkpoint para vault markdown
ikigai_checkpoint  # list/get checkpoint threads

# Solverforge Calendar (3)
solverforge_list_events
solverforge_create_event

# Tuiboard Kanban (5)
tuiboard_list_boards
tuiboard_get_tasks
tuiboard_update_task
tuiboard_create_task

# Taskdog (4)
taskdog_list_tasks
taskdog_create_task
taskdog_complete_task
taskdog_get_task
```

## Vault como Source of Truth

Vault é YAML-indexed e append-only.

```
vault/
├── ikigai/
│   ├── closing-2026/
│   │   ├── 01-q3-2026/
│   │   │   ├── 00-sonho/         ← SONHOS (547d)
│   │   │   ├── 01-plano-trimestral/  ← Objetivos (90d)
│   │   │   ├── 02-onda-N/           ← Projetos (15d)
│   │   │   └── 03-revisoes-semanais/ ← Reviews
│   │   └── 02-q4-2026/
│   └── meta/
│       ├── ikigai_state/        ← cycle logs
│       └── perspective-log/      ← decisões de design
```

## Feedback Loop (Backpropagation)

```
interfaces (user marks done)
  → VaultEvent.done (planned_date vs actual_date)
    → Burndown + ExecutionRate computados
      → IKIGAI observa gap
        → próxima iteração: ajusta workload/capacity
          → recomenda novos prazos/tarefas
```

## UEID Format

```
ikigai:<entity_type>:<slug>:<8-hex-uuid>:<8-hex-content-hash>

entity_type: dream | objective | project | deliverable | profile | cycle
```

## 5 Vectors + Meta-Vector

| Vector | Score | Weight (BUSCA default) |
|--------|-------|------------------------|
| passion | 0.0-1.0 | 0.15 |
| skill | 0.0-1.0 | 0.25 |
| market | 0.0-1.0 | 0.25 |
| revenue | 0.0-1.0 | 0.20 |
| course | 0.0-1.0 | 0.15 |

**Meta-vector**: 60/40 blend geometric/harmonic mean (até SONHO ≥ 5 logs).

## 5 Phases

| Phase | Emoji | passion | skill | market | revenue | course |
|-------|-------|---------|-------|--------|---------|--------|
| FUNDAÇÃO | 🏗️ | 0.35 | 0.30 | 0.15 | 0.10 | 0.10 |
| BUSCA | 🔍 | 0.25 | 0.25 | 0.25 | 0.15 | 0.10 |
| HACKATHON | ⚡ | 0.20 | 0.15 | 0.20 | 0.30 | 0.15 |
| RECUPERACAO | 🔧 | 0.30 | 0.30 | 0.15 | 0.10 | 0.15 |
| OVERCLOCK | 🔥 | 0.25 | 0.15 | 0.15 | 0.30 | 0.15 |

## 4 Regimes (com hysteresis)

| Regime | Emoji | Q_HE | Hard Work | Pomodoros | Sleep |
|--------|-------|------|-----------|-----------|-------|
| PUSH | 🚀 | ≥ 0.85 | 8h | 10 | 7h |
| MAINTAIN | 🔧 | 0.65-0.85 | 6h | 8 | 8h |
| REDUCE | 📉 | 0.45-0.65 | 4h | 5 | 8h |
| RECOVER | 🛌 | < 0.45 | 2h | 2 | 9h |

**Hysteresis**: downgrade mais rápido que upgrade (down em 2 dias, up em 3).

## Interface com PAV

IKIGAI **PULL** de PAV no início de cada ciclo:

```python
# ikigai_plan_cycle.py
def _pull_pav_data(date):
    qhe = pav_get_qhe_score(date)      # → QHEScore
    policy = pav_get_policy_decision(date)  # → PolicyDecision
    habits = pav_list_habits(date)     # → list[HabitState]
    return qhe, policy, habits
```

## IKIGAI ↔ Interfaces (write path)

IKIGAI escreve para interfaces via `sync_vault` → MCP Gateway → interfaces.

Interfaces **nunca escrevem no vault**. Elas escrevem em `data/feedback/` (ExecutionRate, Burndown snapshots).

## Status

- [x] Arquitetura de dois agentes documentada
- [x] Ciclo de planejamento de 8 nós
- [x] 18 tools (8 IKIGAI + 3 solverforge + 5 tuiboard + 4 taskdog)
- [x] Vault hierarchy (SONHO → ONDA → Sprint)
- [x] UEID format
- [x] 5 vectors + 5 phases + 4 regimes
- [ ] IKIGAI ↔ PAV pull integration (leitura de journal.db)
- [ ] IKIGAI → interfaces write (sync_vault completo)
- [ ] LangGraph checkpointer idempotência verificada
