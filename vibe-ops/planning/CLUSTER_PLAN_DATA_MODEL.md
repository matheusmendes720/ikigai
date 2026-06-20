# CLUSTER PLAN — Data Model (SQLite + Pydantic)

> Schema SQLite canônico + Pydantic v2 models para o Cluster PLAN.
> **Nenhuma tabela** deve ser criada fora deste schema.

---

## 1. SQLite Schema

Todas as tabelas abaixo são **adições** ao schema canônico existente
[`../src/storage/schema.sql`](../src/storage/schema.sql). Devem ser criadas via
migration `004_cluster_plan_v1.sql` (Sprint 1).

### 1.1. `auto_indagacao` (socratic journaling — NOVA, Sprint 1)

```sql
CREATE TABLE auto_indagacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    ritual_type TEXT NOT NULL CHECK (ritual_type IN ('morning', 'afternoon', 'evening', 'manual')),
    wake_time TIME,                          -- apenas morning
    sleep_classification TEXT,               -- 3-5h=green, 5-6h=yellow, 6h+=red
    q1_repeat TEXT,                          -- "O que fiz ontem que preciso repetir?"
    q2_stop TEXT,                            -- "O que fiz ontem que preciso parar de fazer?"
    q3_habit_candidate TEXT,                 -- "Que tarefa deve virar hábito?"
    q4_big_win TEXT,                         -- "Qual é a grande vitória de hoje?"
    q5_one_priority TEXT,                    -- "Se eu só pudesse fazer 1 coisa?"
    q6_ready_for_deep_work TEXT,             -- apenas afternoon
    q7_went_well TEXT,                       -- apenas evening
    q8_went_bad TEXT,                         -- apenas evening
    q9_learned TEXT,                          -- apenas evening
    q10_tension TEXT,                        -- apenas evening
    q11_tomorrow_priority TEXT,              -- apenas evening
    ikigai_focus TEXT,                       -- passion|skill|market|revenue|course
    regime_predicted TEXT CHECK (regime_predicted IN ('PUSH', 'MAINTAIN', 'REDUCE', 'RECOVER')),
    qhe_at_moment REAL,                      -- 0-1
    pomodoros_planned_morning INTEGER DEFAULT 0,
    pomodoros_planned_afternoon INTEGER DEFAULT 0,
    pomodoros_planned_evening INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, ritual_type)                -- idempotência
);

CREATE INDEX idx_auto_indagacao_date ON auto_indagacao(date);
CREATE INDEX idx_auto_indagacao_regime ON auto_indagacao(regime_predicted);
CREATE INDEX idx_auto_indagacao_ikigai ON auto_indagacao(ikigai_focus);
```

### 1.2. `daily_routine` (Pomodoro + TimeBlock tracking — NOVA, Sprint 1)

```sql
CREATE TABLE daily_routine (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    wake_time_actual TIME,
    sleep_target TIME NOT NULL,                 -- 18-21h
    regime_actual TEXT CHECK (regime_actual IN ('PUSH', 'MAINTAIN', 'REDUCE', 'RECOVER')),
    pomodoros_planned INTEGER DEFAULT 0,
    pomodoros_done INTEGER DEFAULT 0,
    pomodoros_interrupted INTEGER DEFAULT 0,
    transition_rituals_count INTEGER DEFAULT 0,
    transition_rituals_minutes INTEGER DEFAULT 0,  -- total
    ikigai_focus TEXT,
    qhe_avg REAL,                                 -- média rolling
    notes TEXT,                                   -- opcional
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_daily_routine_date ON daily_routine(date);
CREATE INDEX idx_daily_routine_regime ON daily_routine(regime_actual);
```

### 1.3. `sleep_window` (sono — NOVA, Sprint 1)

```sql
CREATE TABLE sleep_window (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    bedtime TIME,                                 -- 18-21h ideal
    wake_time TIME,                               -- 3-5h ideal
    duration_hours REAL,
    deficit_hours REAL,                           -- vs target 7-9h
    quality_score INTEGER CHECK (quality_score BETWEEN 1 AND 10),
    interruptions INTEGER DEFAULT 0,
    source TEXT DEFAULT 'manual',                 -- manual|garmin|oura|apple
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sleep_window_date ON sleep_window(date);
```

### 1.4. `transition_ritual` (overhead tracking — NOVA, Sprint 1)

```sql
CREATE TABLE transition_ritual (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    ritual_type TEXT NOT NULL CHECK (ritual_type IN ('cold_start', 'warm_down', 'context_switch', 'shutdown')),
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    duration_minutes REAL,
    completed BOOLEAN DEFAULT 0,                  -- checklist done?
    from_block TEXT,                              -- ex: 'morning'
    to_block TEXT,                                -- ex: 'afternoon'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transition_ritual_date ON transition_ritual(date);
CREATE INDEX idx_transition_ritual_type ON transition_ritual(ritual_type);
```

### 1.5. `qhe_history` (regime + Q_HE ao longo do tempo — NOVA, Sprint 1)

```sql
CREATE TABLE qhe_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    qhe_score REAL NOT NULL,                      -- 0-1
    qhe_components_json TEXT,                     -- {sono: 0.85, med: 0.5, ...}
    regime TEXT NOT NULL CHECK (regime IN ('PUSH', 'MAINTAIN', 'REDUCE', 'RECOVER')),
    regime_changed BOOLEAN DEFAULT 0,            -- 1 se regime mudou hoje
    streak_days INTEGER,                          -- streak de hábitos âncora
    energy_score_morning INTEGER CHECK (energy_score_morning BETWEEN 1 AND 10),
    energy_score_evening INTEGER CHECK (energy_score_evening BETWEEN 1 AND 10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_qhe_history_date ON qhe_history(date);
```

### 1.6. `pomodoro` (granular — NOVA, Sprint 1)

```sql
CREATE TABLE pomodoro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    duration_minutes INTEGER DEFAULT 50,
    break_minutes INTEGER DEFAULT 10,
    status TEXT CHECK (status IN ('planned', 'running', 'completed', 'interrupted', 'skipped')),
    task_ref TEXT,                                -- FK opcional (PROJ/STUDY task_id)
    task_type TEXT CHECK (task_type IN ('project', 'study', 'admin', 'ritual')),
    block_type TEXT CHECK (block_type IN ('morning', 'afternoon', 'evening')),
    energy_before INTEGER CHECK (energy_before BETWEEN 1 AND 10),
    energy_after INTEGER CHECK (energy_after BETWEEN 1 AND 10),
    interruptions_count INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pomodoro_date ON pomodoro(date);
CREATE INDEX idx_pomodoro_status ON pomodoro(status);
CREATE INDEX idx_pomodoro_block ON pomodoro(block_type);
```

---

## 2. Pydantic Models

```python
# File: vibe-ops/src/models/cluster_plan_entities.py (NEW, Sprint 1)

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import date, time, datetime
from enum import Enum

class RitualType(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    MANUAL = "manual"

class RegimeType(str, Enum):
    PUSH = "PUSH"
    MAINTAIN = "MAINTAIN"
    REDUCE = "REDUCE"
    RECOVER = "RECOVER"

class IKIGAiFocus(str, Enum):
    PASSION = "passion"
    SKILL = "skill"
    MARKET = "market"
    REVENUE = "revenue"
    COURSE = "course"

class SleepClassification(str, Enum):
    GREEN = "green"      # 3-5h
    YELLOW = "yellow"    # 5-6h
    RED = "red"          # 6h+

class AutoIndagacao(BaseModel):
    id: Optional[int] = None
    date: date
    ritual_type: RitualType
    wake_time: Optional[time] = None
    sleep_classification: Optional[SleepClassification] = None
    q1_repeat: Optional[str] = None
    q2_stop: Optional[str] = None
    q3_habit_candidate: Optional[str] = None
    q4_big_win: Optional[str] = None
    q5_one_priority: Optional[str] = None
    q6_ready_for_deep_work: Optional[str] = None
    q7_went_well: Optional[str] = None
    q8_went_bad: Optional[str] = None
    q9_learned: Optional[str] = None
    q10_tension: Optional[str] = None
    q11_tomorrow_priority: Optional[str] = None
    ikigai_focus: Optional[IKIGAiFocus] = None
    regime_predicted: Optional[RegimeType] = None
    qhe_at_moment: Optional[float] = Field(default=None, ge=0, le=1)
    pomodoros_planned_morning: int = 0
    pomodoros_planned_afternoon: int = 0
    pomodoros_planned_evening: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DailyRoutine(BaseModel):
    id: Optional[int] = None
    date: date
    wake_time_actual: Optional[time] = None
    sleep_target: time
    regime_actual: Optional[RegimeType] = None
    pomodoros_planned: int = 0
    pomodoros_done: int = 0
    pomodoros_interrupted: int = 0
    transition_rituals_count: int = 0
    transition_rituals_minutes: int = 0
    ikigai_focus: Optional[IKIGAiFocus] = None
    qhe_avg: Optional[float] = Field(default=None, ge=0, le=1)
    notes: Optional[str] = None


class SleepWindow(BaseModel):
    id: Optional[int] = None
    date: date
    bedtime: Optional[time] = None
    wake_time: Optional[time] = None
    duration_hours: Optional[float] = None
    deficit_hours: Optional[float] = None
    quality_score: Optional[int] = Field(default=None, ge=1, le=10)
    interruptions: int = 0
    source: str = "manual"


class TransitionRitualType(str, Enum):
    COLD_START = "cold_start"
    WARM_DOWN = "warm_down"
    CONTEXT_SWITCH = "context_switch"
    SHUTDOWN = "shutdown"

class TransitionRitual(BaseModel):
    id: Optional[int] = None
    date: date
    ritual_type: TransitionRitualType
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: Optional[float] = None
    completed: bool = False
    from_block: Optional[str] = None
    to_block: Optional[str] = None
    notes: Optional[str] = None


class QHEHistory(BaseModel):
    id: Optional[int] = None
    date: date
    qhe_score: float = Field(ge=0, le=1)
    qhe_components_json: Optional[str] = None
    regime: RegimeType
    regime_changed: bool = False
    streak_days: Optional[int] = None
    energy_score_morning: Optional[int] = Field(default=None, ge=1, le=10)
    energy_score_evening: Optional[int] = Field(default=None, ge=1, le=10)


class PomodoroStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    SKIPPED = "skipped"

class PomodoroTaskType(str, Enum):
    PROJECT = "project"
    STUDY = "study"
    ADMIN = "admin"
    RITUAL = "ritual"

class BlockType(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"

class Pomodoro(BaseModel):
    id: Optional[int] = None
    date: date
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: int = 50
    break_minutes: int = 10
    status: PomodoroStatus = PomodoroStatus.PLANNED
    task_ref: Optional[str] = None
    task_type: Optional[PomodoroTaskType] = None
    block_type: Optional[BlockType] = None
    energy_before: Optional[int] = Field(default=None, ge=1, le=10)
    energy_after: Optional[int] = Field(default=None, ge=1, le=10)
    interruptions_count: int = 0
    notes: Optional[str] = None
```

---

## 3. Migrations

A migration Sprint 1 é: **`vibe-ops/migrations/004_cluster_plan_v1.sql`**

```sql
-- Migration 004: Cluster PLAN (socratic journaling + pomodoro tracking)
-- Date: 2026-06-05
-- Author: Matheus + AI Agent

BEGIN TRANSACTION;

-- (Cole aqui as 6 CREATE TABLE do §1)

COMMIT;
```

**Como aplicar:**

```bash
sqlite3 vibe_ops.db < migrations/004_cluster_plan_v1.sql
```

---

## 4. Indexes

Os índices são **mínimos** (apenas o necessário para queries esperadas):

- `idx_auto_indagacao_date` — query: "auto_indagacao desta semana"
- `idx_auto_indagacao_regime` — query: "dias em RECOVER este mês"
- `idx_pomodoro_date` — query: "pomodoros de hoje"
- `idx_pomodoro_status` — query: "pomodoros interrupted desta sprint"
- `idx_sleep_window_date` — query: "sono últimos 7d"
- `idx_qhe_history_date` — query: "Q_HE trend"
- `idx_daily_routine_date` — query: "rotina de hoje"

**Não criar índices redundantes** — SQLite escolhe plano de query ótimo.

---

## 5. Cross-refs

- [`../src/storage/schema.sql`](../src/storage/schema.sql) — Schema canônico (5K, SQLite)
- [`../src/schemas/pydantic_v2.py`](../src/schemas/pydantic_v2.py) — Pydantic v2 canônico
- [`../src/models/`](../src/models/) — 14 entity files existentes
- [`../migrations/001_create_dev_cluster_tables.sql`](../migrations/001_create_dev_cluster_tables.sql) — Pattern de migration
- [`../migrations/versions/001_create_dev_cluster.py`](../migrations/versions/001_create_dev_cluster.py) — Pattern Python migration
- [`../../CLUSTER_PLAN.md §2`](../../CLUSTER_PLAN.md) — Entidades PLAN (Pydantic)
- [`../../CLUSTER_PLAN.md §6.5.B`](../../CLUSTER_PLAN.md) — Schema `auto_indagacao` (origem)
- [`../../life-ops/planner/Points_of_premisses-task-habits.md §3`](../../life-ops/planner/Points_of_premisses-task-habits.md) — Q_HE formula
- [`../PRD-02-habit-tracker.md §2-3`](../PRD-02-habit-tracker.md) — Q_HE components
- [`../PRD-06-policy-governance.md §2`](../PRD-06-policy-governance.md) — Regime state machine
- [`../../life-ops/life_tatics/domain/time_blocks.py`](../../life-ops/life_tatics/domain/time_blocks.py) — TimeBlocks logic (reutilizar)
- [`../../life-ops/life_tatics/domain/screentime.py`](../../life-ops/life_tatics/domain/screentime.py) — Screentime tracking

---

*CLUSTER_PLAN_DATA_MODEL.md — v1.0 — 2026-06-05 — Schema SQLite + Pydantic models para Cluster PLAN*
