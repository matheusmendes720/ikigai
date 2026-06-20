# Spec: Cluster PLAN — Inputs (Sprint 1)

> Especificação técnica dos **inputs manuais** que o operador fornece ao Cluster PLAN.
> Estes inputs alimentam as tabelas SQLite (ver [`../planning/CLUSTER_PLAN_DATA_MODEL.md`](../planning/CLUSTER_PLAN_DATA_MODEL.md))
> e o regime IKIGAi (ver [`../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md`](../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md)).

---

## 1. Visão Geral

O Cluster PLAN tem **3 tipos de inputs** manuais:

1. **Socratic journaling** — 11 perguntas distribuídas em 3 rituais (morning, afternoon, evening)
2. **Pomodoro tracking** — start/done/interrupted events
3. **Sleep window** — bedtime + wake_time + quality

Todos os inputs são:
- **Idempotentes** (UNIQUE constraints em `auto_indagacao`, `sleep_window`)
- **Offline-first** (sem dependência de network)
- **CLI-first** (wizard interativo, não formulários web)

---

## 2. Socratic Journaling

### 2.1. Schema YAML (Obsidian frontmatter)

Operador **opcionalmente** registra answers em Markdown com frontmatter:

```yaml
---
type: auto_indagacao
date: 2026-06-05
ritual: morning
q1_repeat: "code review diário + meditação"
q2_stop: "tw notifications mid-pomodoro"
q3_habit_candidate: "code review"
q4_big_win: "implementar JWT validator"
q5_one_priority: "JWT validator"
ikigai_focus: skill
regime_predicted: MAINTAIN
qhe_at_moment: 0.78
---
```

**Schema canônico:** [`schema-frontmatter-contract-v2.md`](schema-frontmatter-contract-v2.md)

### 2.2. Schema Pydantic

```python
class AutoIndagacao(BaseModel):
    date: date
    ritual_type: Literal["morning", "afternoon", "evening", "manual"]
    wake_time: Optional[time] = None
    q1_repeat: Optional[str] = Field(default=None, max_length=500)
    q2_stop: Optional[str] = Field(default=None, max_length=500)
    q3_habit_candidate: Optional[str] = Field(default=None, max_length=500)
    q4_big_win: Optional[str] = Field(default=None, max_length=500)
    q5_one_priority: Optional[str] = Field(default=None, max_length=500)
    q6_ready_for_deep_work: Optional[str] = Field(default=None, max_length=500)
    q7_went_well: Optional[str] = Field(default=None, max_length=500)
    q8_went_bad: Optional[str] = Field(default=None, max_length=500)
    q9_learned: Optional[str] = Field(default=None, max_length=500)
    q10_tension: Optional[str] = Field(default=None, max_length=500)
    q11_tomorrow_priority: Optional[str] = Field(default=None, max_length=500)
    ikigai_focus: Optional[Literal["passion", "skill", "market", "revenue", "course"]]
    regime_predicted: Optional[Literal["PUSH", "MAINTAIN", "REDUCE", "RECOVER"]]
    qhe_at_moment: Optional[float] = Field(default=None, ge=0, le=1)
    pomodoros_planned_morning: int = Field(default=0, ge=0, le=20)
    pomodoros_planned_afternoon: int = Field(default=0, ge=0, le=20)
    pomodoros_planned_evening: int = Field(default=0, ge=0, le=20)
```

### 2.3. Perguntas Socráticas (origem)

| # | Pergunta | Ritual | Origem |
|---|---|---|---|
| 1 | "O que fiz ontem que preciso repetir?" | morning | `strategics/Análise (Tático e Operacional).md §Rotina Inicial` |
| 2 | "O que fiz ontem que preciso parar de fazer?" | morning | Idem |
| 3 | "Que tarefa de ontem deve virar hábito?" | morning | Idem |
| 4 | "Qual é a grande vitória de hoje?" | morning | Idem |
| 5 | "Se eu só pudesse fazer 1 coisa, qual seria?" | morning | Idem |
| 6 | "Tô pronto para Deep Work?" | afternoon | [`../../CLUSTER_PLAN.md §2.5 Template 2`](../../CLUSTER_PLAN.md) |
| 7 | "O que correu bem hoje?" | evening | `strategics/Análise (Tático e Operacional).md §Rotina Final` |
| 8 | "O que correu mal hoje?" | evening | Idem |
| 9 | "Qual foi o maior aprendizado?" | evening | Idem |
| 10 | "O que estou levando de tensão desnecessária?" | evening | [`../../CLUSTER_PLAN.md §2.5 Template 3`](../../CLUSTER_PLAN.md) |
| 11 | "Se amanhã eu só pudesse fazer 1 coisa?" | evening | Idem |

---

## 3. Pomodoro Tracking

### 3.1. Schema YAML

```yaml
---
type: pomodoro
date: 2026-06-05
started_at: "2026-06-05T14:00:00"
ended_at: "2026-06-05T14:50:00"
duration_minutes: 50
break_minutes: 10
status: completed
task_ref: "task:T-123"  # FK opcional (PROJ/STUDY)
task_type: project
block_type: afternoon
energy_before: 8
energy_after: 7
interruptions_count: 0
notes: "JWT validator implementado + testado"
---
```

### 3.2. Schema Pydantic

```python
class Pomodoro(BaseModel):
    date: date
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: int = Field(default=50, ge=1, le=300)
    break_minutes: int = Field(default=10, ge=0, le=60)
    status: Literal["planned", "running", "completed", "interrupted", "skipped"]
    task_ref: Optional[str] = None  # FK opcional
    task_type: Optional[Literal["project", "study", "admin", "ritual"]]
    block_type: Optional[Literal["morning", "afternoon", "evening"]]
    energy_before: Optional[int] = Field(default=None, ge=1, le=10)
    energy_after: Optional[int] = Field(default=None, ge=1, le=10)
    interruptions_count: int = Field(default=0, ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)
```

---

## 4. Sleep Window

### 4.1. Schema YAML

```yaml
---
type: sleep_window
date: 2026-06-05
bedtime: "20:30"
wake_time: "03:45"
duration_hours: 7.25
deficit_hours: -0.25  # vs target 7.5h
quality_score: 8
interruptions: 0
source: manual
---
```

### 4.2. Schema Pydantic

```python
class SleepWindow(BaseModel):
    date: date
    bedtime: Optional[time] = None
    wake_time: Optional[time] = None
    duration_hours: Optional[float] = Field(default=None, ge=0, le=14)
    deficit_hours: Optional[float] = None
    quality_score: Optional[int] = Field(default=None, ge=1, le=10)
    interruptions: int = Field(default=0, ge=0)
    source: Literal["manual", "garmin", "oura", "apple_health"] = "manual"

    @property
    def sleep_classification(self) -> Literal["green", "yellow", "red"]:
        if not self.wake_time:
            return "red"
        h = self.wake_time.hour
        if 3 <= h < 5:
            return "green"
        elif 5 <= h < 6:
            return "yellow"
        return "red"
```

---

## 5. Edge Cases

### 5.1. Idempotência

- `auto_indagacao`: UNIQUE(date, ritual_type) — re-execução ATUALIZA
- `sleep_window`: UNIQUE(date) — re-execução ATUALIZA
- `pomodoro`: cada chamada CRIA novo row (event sourcing)

### 5.2. Validações

- Data futura: erro (`plan journal log --morning --date 2099-01-01`)
- Data > 7d passada: erro (limite de edição retroativa)
- Bedtime fora 18-21h: warning amarelo (não bloqueia)
- Wake time fora 3-5h: warning amarelo (não bloqueia)
- Pomodoro > 240 min: warning (anti-pattern)

### 5.3. Estado Inconsistente

- Pomodoro `completed` sem `ended_at`: erro (CLI deve preencher)
- Auto_indagacao `morning` sem q1-q5: warning (campos opcionais)
- SleepWindow `quality_score = 1` (mínimo): warning amarelo

---

## 6. Cross-refs

- [`../planning/CLUSTER_PLAN_DATA_MODEL.md`](../planning/CLUSTER_PLAN_DATA_MODEL.md) — Schema SQLite
- [`../planning/CLUSTER_PLAN_USER_STORIES.md`](../planning/CLUSTER_PLAN_USER_STORIES.md) — User stories
- [`../planning/CLUSTER_PLAN_CLI_SPEC.md`](../planning/CLUSTER_PLAN_CLI_SPEC.md) — CLI
- [`schema-frontmatter-contract-v2.md`](schema-frontmatter-contract-v2.md) — Frontmatter v2
- [`schema-pydantic-models-v2.md`](schema-pydantic-models-v2.md) — Pydantic v2
- [`../../CLUSTER_PLAN.md §2.5`](../../CLUSTER_PLAN.md) — Templates inline
- [`../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md`](../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md) — Algoritmos regime

---

*spec-cluster-plan-inputs.md — v1.0 — 2026-06-05 — Spec dos inputs manuais para Cluster PLAN*
