# Schema: Contrato de YAML Frontmatter v2 (Temporal + Behavioral Entities)

**Versao:** 0.2.0
**Ultima Atualizacao:** 2026-05-09
**Referencia:** `architecture/ADR-001-data-flow-topology.md`, `doc/03-data-mesh-enrichment.md`, `schema-pydantic-models-v2.md`
**Status:** Draft para implementacao

Este documento estende o contrato de Frontmatter v1 (`schema-frontmatter-contract.md`) com os novos tipos de entidade temporal (WAVE, CYCLE, PHASE) e comportamental (HABIT, STUDY_PLAN) derivados do modelo matematico de `life-ops/planner/`.

---

## 1. Regras Gerais (Inalteradas do v1)

| Regra | Descricao |
|:------|:----------|
| Todo arquivo `.md` no dominio Planning **DEVE** ter Frontmatter | Sem Frontmatter = arquivo ignorado pelo pipeline |
| O campo `entity_type` e **sempre obrigatorio** | Determina qual Pydantic Model sera usado na validacao |
| O campo `id` e **sempre obrigatorio** | Identificador unico dentro do tipo de entidade |
| O campo `status` e **sempre obrigatorio** | Determina se a entidade e processada (`active`) ou ignorada (`archived`) |

### 1.1. Convencoes de Nomenclatura (Estendidas)

| Campo | Formato | Exemplos |
|:------|:--------|:---------|
| `id` (Dream) | `S` + numero inteiro | `S1`, `S2` |
| `id` (Objective) | `O` + numero inteiro | `O1`, `O2` |
| `id` (Meta) | `M` + numero inteiro | `M1`, `M2` |
| `id` (Project) | `proj_` + snake_case | `proj_alfa_01` |
| `id` (Wave) | `W` + numero + `_` + Mmm + `_` + YYYY | `W3_Jul_2026` |
| `id` (Cycle) | `C` + numero + `_` + YYYY | `C1_2026` |
| `id` (Phase) | `P` + numero + `_` + YYYY | `P1_2026` |
| `id` (Habit) | `hab_` + snake_case | `hab_sleep`, `hab_meditation` |
| `id` (StudyPlan) | `study_` + snake_case | `study_backend_01` |
| `quarter` | `Q[1-4]_YYYY` | `Q3_2026` |
| `wave` (em Meta) | FK para WaveEntity.id | `W3_Jul_2026` |
| `tags` | Array de strings, snake_case | `["habit", "phase:train"]` |

### 1.2. Campos Opcionais Universais (Inalterados)

```yaml
created: "2026-07-15"
updated: "2026-07-20"
tags: ["tag1", "tag2"]
notes: "Contexto adicional"
```

---

## 2. Schemas por Tipo de Entidade (Novos e Atualizados)

### 2.1. Meta (`entity_type: "meta"`) — ATUALIZADO

O campo `wave` deixa de ser string livre e torna-se **FK obrigatoria** para WaveEntity.

```yaml
---
id: "M3"
title: "Sprint: API REST com Autenticacao JWT"
entity_type: "meta"
status: "active"
created: "2026-07-15"

# FK obrigatoria (atualizada)
parent_objective: "O2"              # FK -> ObjectiveEntity.id (VALIDADA)
wave: "W3_Jul_2026"                 # FK -> WaveEntity.id (NOVO - VALIDADA)

# Especificos da Meta
duration_days: 15
estimated_hours: 30
priority: "P1"
review_cycle: "weekly"

# Campo computado (gerado pelo pipeline, NAO editado manualmente):
# tw_project_key: "S1.O2.W3_Jul_2026.M3"

tags: ["api", "jwt", "sprint"]
---
```

### 2.2. Wave (`entity_type: "wave"`) — NOVO

Container temporal de 15 dias para consolidacao de habitos.

```yaml
---
# ===================================================
# CAMPOS OBRIGATORIOS
# ===================================================
id: "W3_Jul_2026"
title: "Wave 3: Consolidacao de Deep Work"
entity_type: "wave"
status: "active"                     # active | paused | completed | aborted
created: "2026-07-01"
started: "2026-07-01"
expected_end: "2026-07-15"

# ===================================================
# CAMPOS ESPECIFICOS DO WAVE
# ===================================================
wave_number: 3                        # int: sequencial dentro do ciclo
parent_cycle: "C1_2026"               # FK -> CycleEntity.id
parent_objective: "O2"                # FK -> ObjectiveEntity.id

# Metas comportamentais (habitos a consolidar nesta wave)
habit_targets:
  - habit_id: "hab_sleep"
    target_streak: 15
  - habit_id: "hab_meditation"
    target_streak: 15
  - habit_id: "hab_workout"
    target_streak: 12

# Checkpoints de revisao
mid_wave_review: "2026-07-08"         # Dia 8: ajuste de carga
wave_end_review: "2026-07-15"         # Dia 15: consolidacao

# ===================================================
# CAMPOS COMPUTADOS (pipeline, NAO editar manualmente)
# ===================================================
# c_comp: 0.92                        # Consistency score
# ic: 0.87                            # Index of Consistency

# ===================================================
# CAMPOS OPCIONAIS
# ===================================================
tags: ["wave", "deep_work", "habit_formation"]
notes: ""
---
```

### 2.3. Cycle (`entity_type: "cycle"`) — NOVO

Container temporal de 45 dias para estabilizacao de performance. Alinha com HALF_QUARTER.

```yaml
---
id: "C1_2026"
title: "Cycle 1: Fundacao Q3"
entity_type: "cycle"
status: "active"
created: "2026-07-01"
started: "2026-07-01"
expected_end: "2026-08-14"

# Posicionamento temporal
cycle_number: 1                       # int: sequencial dentro da phase
parent_phase: "P1_2026"               # FK -> PhaseEntity.id
parent_objective: "O2"                # FK -> ObjectiveEntity.id

# Constantes estruturais (do time-lengths doc)
wave_count: 3
wave_duration_days: 15
total_duration_days: 45

# Checkpoints de revisao
mid_cycle_review: "2026-07-30"        # Dia 30: renormalizacao
cycle_end_review: "2026-08-14"        # Dia 45: checkpoint

# Alinhamento calendario
aligned_half_quarter: "HQ1_Q3_2026"   # Mapeia para HALF_QUARTER

tags: ["cycle", "Q3", "foundation"]
---
```

### 2.4. Phase (`entity_type: "phase"`) — NOVO

Container temporal de 180 dias para maestria de competencia. Alinha com 2 Quarters.

```yaml
---
id: "P1_2026"
title: "Phase 1: Maestria de Backend"
entity_type: "phase"
status: "active"
created: "2026-07-01"
started: "2026-07-01"
expected_end: "2026-12-27"

# Posicionamento temporal
phase_number: 1                       # int: sequencial dentro do dream
parent_dream: "S1"                    # FK -> DreamEntity.id

# Constantes estruturais
cycle_count: 4
cycle_duration_days: 45
total_duration_days: 180

# Checkpoints de revisao
mid_phase_review: "2026-09-29"        # Dia 90: revisao estrategica
phase_end_review: "2026-12-27"        # Dia 180: checkpoint de maestria

# Alinhamento calendario
aligned_quarter_start: "Q3_2026"
aligned_quarter_end: "Q4_2026"

tags: ["phase", "backend", "mastery"]
---
```

### 2.5. Habit (`entity_type: "habit"`) — NOVO

Entidade ortogonal de rotina comportamental. Alimenta o Q_HE.

```yaml
---
id: "hab_sleep"
title: "Janela de Sono 21h-3h"
entity_type: "habit"
status: "active"
created: "2026-07-01"

# Parametros comportamentais
habit_category: "physiological"       # physiological | cognitive | social | creative
resistance: 3                         # int 1-10: dificuldade inerente (R)
lambda: 0.1                           # float: taxa de aprendizado para H(t)
energy_cost: 0.2                      # float 0-1: E_req normalizado

# Ancora temporal
anchor_wave: "W3_Jul_2026"            # FK -> WaveEntity.id (wave atual)
target_streak: 15                     # int: meta para wave atual

# Pesos para Q_HE (de Points_of_premisses)
qhe_weight: 0.35                      # float: w_i na formula Q_HE

# Rastreamento
tracking_type: "binary"               # binary | duration | count
target_value: 1                       # meta diaria
unit: "completion"                    # completion | minutes | pages | reps

# Alinhamento IKIGAi
ikigai_vector: "passion"              # passion | skill | market | revenue

tags: ["habit", "sleep", "physiological", "phase:train"]
---
```

### 2.6. StudyPlan (`entity_type: "study_plan"`) — NOVO

Plano de estudo continuo (7/7). Especializacao de Project com tracking de topicos.

```yaml
---
id: "study_backend_01"
title: "Plano de Estudo: Backend Engineering"
entity_type: "study_plan"
status: "active"
created: "2026-07-01"

# Ligacao estrategica
parent_dream: "S1"                    # FK -> DreamEntity.id
parent_objective: "O2"                # FK -> ObjectiveEntity.id

# Ancora temporal
anchor_wave: "W3_Jul_2026"            # FK -> WaveEntity.id
anchor_cycle: "C1_2026"               # FK -> CycleEntity.id

# Parametros especificos de estudo
study_cadence: "daily"                # daily | wave_based
work_ratio_override: 1.0              # 1.0 = 7/7 (sem filtro de workday)
daily_target_minutes: 120             # int: orcamento diario de estudo

# Conteudo
topics:
  - topic_id: "tp_python"
    title: "Python Data Engineering"
    status: "in_progress"
    target_hours: 40
  - topic_id: "tp_sql"
    title: "Advanced SQL"
    status: "pending"
    target_hours: 20

# CLR target (Cognitive Load Ratio)
target_clr: 0.4                       # float: study_hours / work_hours ideal

# Campo computado (pipeline):
# tw_project_key: "S1.O2.study_backend_01"

tags: ["study", "backend", "phase:learn", "study_anchor"]
---
```

---

## 3. Anti-Patterns (O Que NAO Fazer) — Estendido

| Anti-Pattern | Exemplo Ruim | Correcao |
|:------------|:-------------|:---------|
| `wave` como string livre em Meta | `wave: "Julho onda 3"` | Usar FK: `wave: "W3_Jul_2026"` |
| Habit sem `anchor_wave` | Habit orfao de temporal | Sempre vincular a wave ativa |
| Cycle com `wave_count != 3` | `wave_count: 4` | Constante estrutural = 3 |
| Phase com `cycle_count != 4` | `cycle_count: 3` | Constante estrutural = 4 |
| `lambda` fora de faixa | `lambda: 2.0` | Maximo = 1.0, minimo = 0.01 |
| `resistance` fora de faixa | `resistance: 15` | Range 1-10 |
| `qhe_weight` negativo | `qhe_weight: -0.1` | Range 0.0-1.0 |
| StudyPlan sem topics | Array vazio | Minimo 1 topico ativo |

---

## 4. Grafo de Integridade Referencial (Atualizado)

```
Phase (P1)
  |--parent_dream--> Dream (S1)
  |
  +-- Cycle (C1)        <--parent_phase--
       |--parent_objective--> Objective (O2)
       |
       +-- Wave (W3)     <--parent_cycle--
            |--parent_objective--> Objective (O2)
            |
            +-- Meta (M3)  <--wave-- [ATUALIZADO: FK, nao string]
            |    |--parent_objective--> Objective (O2)
            |    +-- Project (proj_*)
            |         +-- Task (task_*)
            |
            +-- Habit (hab_*)  <--anchor_wave--
            |
            +-- StudyPlan (study_*)  <--anchor_wave--
                 +-- StudyTopic (tp_*)
```

**Validacoes do Pipeline (Novas):**
- `FK_WAVE_NOT_FOUND`: `wave` em Meta referencia ID inexistente -> Abortar push
- `FK_CYCLE_NOT_FOUND`: `parent_cycle` em Wave referencia ID inexistente -> Abortar push
- `FK_PHASE_NOT_FOUND`: `parent_phase` em Cycle referencia ID inexistente -> Abortar push
- `WAVE_DURATION_INVALID`: `expected_end - started != 14 dias` -> Abortar push
- `HABIT_ORPHAN`: Habit sem `anchor_wave` -> Mover para triagem.md
- `STUDYPLAN_NO_TOPICS`: StudyPlan com array vazio -> Alerta, nao abortar

---

## 5. Fluxo de Validacao Estendido

```
1. PARSE    -> python-frontmatter.load(filepath)
2. ROUTE    -> entity_type -> MODEL_MAP (agora com 9 tipos)
3. VALIDATE -> Pydantic Model valida tipos e ranges
4. FK_RESOLVE -> Valida toda a cadeia: Phase->Dream, Cycle->Phase, Wave->Cycle, Meta->Wave
5. ENRICH   -> Computa tw_project_key, upstream_id, c_comp, ic
6. EMIT     -> TaskPayload para entidades injetaveis (Meta, Project, Task, Habit, StudyPlan)
              -> Planning-only entities (Dream, Objective, Wave, Cycle, Phase) vao para SQLite
```

---

> NOTA: Este schema e **extensao append-only** do v1. Todos os schemas do v1 (Dream, Objective, Project, Task) permanecem validos e inalterados. As entidades temporais sao cross-cutting: elas existem em paralelo a hierarquia estrategica, nao a substituem.
