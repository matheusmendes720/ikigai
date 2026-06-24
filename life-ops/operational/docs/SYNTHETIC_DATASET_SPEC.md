# SPEC: 6-Month Synthetic Dataset Generator

**Version:** 1.0
**Date:** 2026-06-22
**Range:** 2025-12-23 → 2026-06-22 (180 days)
**Systems:** operational (JSON) + vibe-ops (SQLite)

---

## 1. Global Unified Schema

### 1.1 UEID Naming Convention

Unified prefix format bridging operational's human-readable IDs and vibe-ops's cluster format:

```
{cluster}:{entity}:{id}

cluster  = oper | vibe | qhem
entity   = 2-4 letter abbreviation
id       = {type}{index}  OR  {date}  OR  {cluster_id}
```

**operational cluster (oper) — JSON persistence:**

| Entity | UEID Pattern | Example |
|--------|-------------|---------|
| SleepRecord | `oper:sle:{YYYYMMDD}` | `oper:sle:20251223` |
| Habit | `oper:hab:{slug_20}` | `oper:hab:beber_2l_de_agua` |
| HabitState | `oper:hst:{hab_slug}:{YYYYMMDD}` | `oper:hst:beber_2l_20251223` |
| QHEMetrics | `oper:qhe:{YYYYMMDD}` | `oper:qhe:20251223` |
| Routine | `oper:rou:{idx03}` | `oper:rou:001` |
| RoutineLog | `oper:rlg:{idx03}:{YYYYMMDD}` | `oper:rlg:001:20251223` |
| TimeBlock | `oper:blk:{idx03}:{YYYYMMDD}` | `oper:blk:001:20251223` |
| JournalEntry | `oper:jrn:{idx03}:{YYYYMMDD}` | `oper:jrn:001:20251223` |
| PomodoroRound | `oper:pom:{idx04}:{YYYYMMDD}` | `oper:pom:0001:20251223` |
| DayContext | `oper:ctx:{YYYYMMDD}` | `oper:ctx:20251223` |
| DailyReflection | `oper:ref:{YYYYMMDD}` | `oper:ref:20251223` |
| LunchRecord | `oper:lun:{YYYYMMDD}` | `oper:lun:20251223` |
| TransicaoRegistrada | `oper:trn:{T}:{YYYYMMDD}` | `oper:trn:T1:20251223` |
| AjusteFino | `oper:adj:{YYYYMMDD}:{idx02}` | `oper:adj:20251223:01` |
| PolicyDecision | `oper:pol:{YYYYMMDD}` | `oper:pol:20251223` |
| PolicySetpoints | `oper:set:{state}` | `oper:set:PUSH` |

**vibe-ops cluster (vibe) — SQLite persistence:**

| Entity | UEID Pattern | Example |
|--------|-------------|---------|
| TemporalWave | `vibe:wave:{NN}` | `vibe:wave:01` |
| TemporalCycle | `vibe:cycl:{NN}` | `vibe:cycl:01` |
| TemporalPhase | `vibe:phas:{NN}` | `vibe:phas:01` |
| StudyPlan | `vibe:stpl:{NN}` | `vibe:stpl:01` |
| StudyTopic | `vibe:stpc:{slug}` | `vibe:stpc:st_python_01` |
| StudyNote | `vibe:stnt:{NN}` | `vibe:stnt:01` |
| DevProject | `vibe:devp:{slug}` | `vibe:devp:proj_vibe_01` |
| DevRoadmap | `vibe:devr:{NN}` | `vibe:devr:01` |
| DevBacklog | `vibe:devb:{NN}` | `vibe:devb:01` |
| DevChangelog | `vibe:devc:{NN}` | `vibe:devc:01` |
| HabitState (vibe) | `vibe:hst:{hab_slug}:{YYYYMMDD}` | `vibe:hst:habit_01:20251223` |
| StudySession | `vibe:stss:{YYYYMMDD}:{NN}` | `vibe:stss:20251223:01` |

---

## 2. Temporal Structure

### 2.1 Phase / Cycle / Wave Mapping

```
Phase 1:  2025-12-23 → 2026-06-22  (180 days, ~26 weeks)
├── Cycle 1:  2025-12-23 → 2026-02-05  (45 days)
│   ├── Wave 1:  2025-12-23 → 2026-01-06  (15 days)
│   ├── Wave 2:  2026-01-07 → 2026-01-21  (15 days)
│   └── Wave 3:  2026-01-22 → 2026-02-05  (15 days)
├── Cycle 2:  2026-02-06 → 2026-03-22  (45 days)
│   ├── Wave 4:  2026-02-06 → 2026-02-20  (15 days)
│   ├── Wave 5:  2026-02-21 → 2026-03-07  (15 days)
│   └── Wave 6:  2026-03-08 → 2026-03-22  (15 days)
├── Cycle 3:  2026-03-23 → 2026-05-06  (45 days)
│   ├── Wave 7:  2026-03-23 → 2026-04-06  (15 days)
│   ├── Wave 8:  2026-04-07 → 2026-04-21  (15 days)
│   └── Wave 9:  2026-04-22 → 2026-05-06  (15 days)
└── Cycle 4:  2026-05-07 → 2026-06-20  (45 days)
    ├── Wave 10: 2026-05-07 → 2026-05-21  (15 days)
    ├── Wave 11: 2026-05-22 → 2026-06-05  (15 days)
    └── Wave 12: 2026-06-06 → 2026-06-20  (15 days)

Remaining days: 2026-06-21 → 2026-06-22 (2 days, partial wave 13)
```

---

## 3. Scenario Coverage Matrix

### 3.1 Scenario Definitions

| Scenario | TipoDia | Sleep | Pomodoros | Hardwork | Policy | Frequency |
|----------|---------|-------|-----------|----------|--------|-----------|
| **Padrao_Ouro** | CURSO | 8h, Q=9 | 11-12 | 240 min | MAINTAIN | baseline |
| **Desvio_Leve** | CURSO | 7h, Q=6 | 8-9 | 200 min | REDUCE | ~2x/week |
| **Hardcore** | HARDCORE | 4h, Q=4 | 10-11 | 480 min | RECOVER | rare |
| **Recuperacao** | DESCANSO | 10h, Q=10 | 3-4 | 90 min | MAINTAIN | post-hardcore |
| **Lunch_Pesado** | CURSO | 8h, Q=8 | 7-8 | 210 min | REDUCE | ~1x/week |
| **Fim_de_Semana** | LIVRE | 8h, Q=9 | 8-9 | 360 min | PUSH | Sat/Sun |
| **Visita_Inesperada** | LIVRE | 7h, Q=7 | 6-7 | 300 min | MAINTAIN | rare |
| **Doente** | DESCANSCO | 10h+, Q=5 | 0-1 | 30 min | RECOVER | very rare |
| **Feriado** | LIVRE | 9h, Q=8 | 2-3 | 120 min | MAINTAIN | ~3x/phase |
| **Vigilia** | HARDCORE | 3h, Q=3 | 8-9 | 540 min | RECOVER | accidental |

### 3.2 26-Week Scenario Calendar

```
Week 01 (Dec 23-29):  Padrao_Ouro ×5, Desvio_Leve ×1, Fim_de_Semana ×2
Week 02 (Dec 30-Jan 5):  Padrao_Ouro ×4, Fim_de_Semana ×2, Desvio_Leve ×1
Week 03 (Jan 6-12):   Padrao_Ouro ×4, Lunch_Pesado ×1, Fim_de_Semana ×2
Week 04 (Jan 13-19):  Padrao_Ouro ×3, Desvio_Leve ×2, Fim_de_Semana ×2
Week 05 (Jan 20-26):  Padrao_Ouro ×4, Fim_de_Semana ×2, Feriado ×1
Week 06 (Jan 27-Feb 2): Padrao_Ouro ×4, Hardcore ×1, Recuperacao ×1, Fim_de_Semana ×2

--- MID-PHASE CHECKPOINT (Week 7) ---

Week 07 (Feb 3-9):   Padrao_Ouro ×4, Lunch_Pesado ×1, Fim_de_Semana ×2
Week 08 (Feb 10-16): Padrao_Ouro ×3, Desvio_Leve ×2, Fim_de_Semana ×2
Week 09 (Feb 17-23): Padrao_Ouro ×4, Feriado ×1, Fim_de_Semana ×2
Week 10 (Feb 24-Mar 2): Padrao_Ouro ×3, Hardcore ×1, Recuperacao ×1, Fim_de_Semana ×2
Week 11 (Mar 3-9):   Padrao_Ouro ×4, Lunch_Pesado ×1, Fim_de_Semana ×2
Week 12 (Mar 10-16): Padrao_Ouro ×3, Desvio_Leve ×2, Fim_de_Semana ×2
Week 13 (Mar 17-23): Padrao_Ouro ×4, Fim_de_Semana ×2, Doente ×1

--- QUARTER TRANSITION (Week 14) ---

Week 14 (Mar 24-30): Padrao_Ouro ×4, Feriado ×1, Fim_de_Semana ×2
Week 15 (Mar 31-Apr 6): Padrao_Ouro ×4, Lunch_Pesado ×1, Fim_de_Semana ×2
Week 16 (Apr 7-13):  Padrao_Ouro ×3, Desvio_Leve ×2, Fim_de_Semana ×2
Week 17 (Apr 14-20): Padrao_Ouro ×4, Hardcore ×1, Recuperacao ×1, Fim_de_Semana ×2
Week 18 (Apr 21-27): Padrao_Ouro ×4, Fim_de_Semana ×2, Visita_Inesperada ×1
Week 19 (Apr 28-May 4): Padrao_Ouro ×4, Lunch_Pesado ×1, Fim_de_Semana ×2
Week 20 (May 5-11):  Padrao_Ouro ×3, Feriado ×1, Fim_de_Semana ×2

--- FINAL PHASE (Weeks 21-26) ---

Week 21 (May 12-18): Padrao_Ouro ×4, Desvio_Leve ×1, Fim_de_Semana ×2
Week 22 (May 19-25): Padrao_Ouro ×3, Hardcore ×1, Recuperacao ×1, Fim_de_Semana ×2
Week 23 (May 26-Jun 1): Padrao_Ouro ×4, Lunch_Pesado ×1, Fim_de_Semana ×2
Week 24 (Jun 2-8):   Padrao_Ouro ×4, Fim_de_Semana ×2, Doente ×1
Week 25 (Jun 9-15):  Padrao_Ouro ×4, Feriado ×1, Fim_de_Semana ×2
Week 26 (Jun 16-22):  Padrao_Ouro ×3, Desvio_Leve ×1, Vigilia ×1 (last day)
```

**Distribution Summary (180 days):**

| Scenario | Days | % |
|----------|------|---|
| Padrao_Ouro | 98 | 54.4% |
| Desvio_Leve | 18 | 10.0% |
| Fim_de_Semana | 52 | 28.9% |
| Hardcore | 4 | 2.2% |
| Recuperacao | 4 | 2.2% |
| Lunch_Pesado | 6 | 3.3% |
| Feriado | 4 | 2.2% |
| Doente | 2 | 1.1% |
| Visita_Inesperada | 1 | 0.6% |
| Vigilia | 1 | 0.6% |

---

## 4. Algorithm Simulation

### 4.1 H(t) — Habit Consolidation

```python
H(t) = 1 - exp(-λ * streak)
λ = 0.093  (DEFAULT.LAMBDA_LEARNING_DEFAULT)

# After s days of unbroken habit:
streak=1  → H=0.0887
streak=3  → H=0.2449
streak=7  → H=0.4817
streak=15 → H=0.7529
streak=30 → H=0.9372
streak=60 → H=0.9963
```

**Streak patterns per habit category (6-month simulation):**

| Habit | Start | Break points | Final streak |
|-------|-------|-------------|-------------|
| Beber 2L Agua | Day 1 | None | 180 |
| Meditar 10min | Day 1 | Days 46-48, 102-103 | 174 |
| Alongamento | Day 1 | Days 20-22, 88-90, 150-151 | 171 |
| Ler 30min | Day 8 | Days 45-52, 120-125 | 162 |
| Caminhada 20min | Day 15 | Days 60-65, 140-142 | 168 |
| Ligar Familia | Day 22 | Days 70-80, 130-140 | 158 |
| Escrever Diario | Day 1 | Days 10-12, 95-97 | 174 |
| Planejar Dia | Day 1 | None | 180 |

### 4.2 Q_HE Simulation

```python
Q_HE = H_avg * (E / E_max) * (1 + η * S_bonus)
η = 0.5
S_bonus = normalized average streak / max possible streak
E_max = 10.0

# Energy ratio driven by:
# - Sleep quality score (0-10)
# - Infraction count (-0.1 per infraction)
# - Hardcore/Vigilia penalty (-0.3)
# - Recuperacao/Descanso bonus (+0.1)
```

**Q_HE ranges by scenario:**

| Scenario | Q_HE range | Regime |
|----------|-----------|--------|
| Padrao_Ouro | 0.72 - 0.88 | PUSH/MAINTAIN |
| Desvio_Leve | 0.55 - 0.68 | MAINTAIN/REDUCE |
| Hardcore | 0.28 - 0.40 | RECOVER |
| Recuperacao | 0.58 - 0.68 | MAINTAIN |
| Lunch_Pesado | 0.52 - 0.64 | REDUCE |
| Fim_de_Semana | 0.65 - 0.82 | PUSH/MAINTAIN |
| Feriado | 0.60 - 0.72 | MAINTAIN |
| Doente | 0.30 - 0.45 | RECOVER |
| Visita_Inesperada | 0.55 - 0.68 | MAINTAIN |
| Vigilia | 0.20 - 0.32 | RECOVER |

### 4.3 Policy FSM Simulation

```
QHE_PUSH_THRESHOLD    = 0.85
QHE_MAINTAIN_THRESHOLD = 0.60
QHE_RECOVER_THRESHOLD  = 0.40

Transition rules (hysteresis from PRD-06):
- PUSH → MAINTAIN:  QHE < 0.80 for 2 consecutive days
- MAINTAIN → REDUCE: QHE < 0.65 for 2 consecutive days
- MAINTAIN → PUSH:  QHE >= 0.85 for 3 consecutive days
- REDUCE → RECOVER: QHE < 0.50 for 1 day OR infractions >= 3
- RECOVER → REDUCE: QHE >= 0.55 for 3 consecutive days
- Any state → RECOVER: sleep < 4h OR infractions >= 4
```

**Policy distribution (180 decisions):**

| State | Days | % |
|-------|------|---|
| PUSH | 42 | 23.3% |
| MAINTAIN | 98 | 54.4% |
| REDUCE | 28 | 15.6% |
| RECOVER | 12 | 6.7% |

### 4.4 Sleep Pattern Simulation

```python
# Circadian rhythm model
base_bedtime = time(21, 30)   # 21:30
base_wake    = time(5, 0)      # 05:00
base_hours   = 7.5

# Variance by scenario:
Padrao_Ouro:       +30min bedtime, +0min wake  = 8.0h
Desvio_Leve:       -60min bedtime, +60min wake = 6.0h
Hardcore:          -120min bedtime, +60min wake = 4.0h
Recuperacao:       +90min bedtime, +90min wake  = 10.0h
Lunch_Pesado:      +0min bedtime, +0min wake   = 7.5h (post-lunch dip)
Fim_de_Semana:     +60min bedtime, +120min wake = 8.0h
Feriado:           +60min bedtime, +60min wake  = 8.0h
Doente:            +60min bedtime, +180min wake = 10.0h+
Visita_Inesperada: +0min bedtime, +0min wake   = 7.5h
Vigilia:           -240min bedtime, +60min wake = 3.0h

# Quality score:
Q = 9 if sleep >= 8h and no interruptions
Q = 7 if sleep >= 7h and interruptions <= 1
Q = 5 if sleep >= 6h
Q = 4 if sleep >= 5h
Q = 3 if sleep < 5h
```

**Sleep architecture (daily):**

```python
deep_pct  = 0.20 + 0.003 * sleep_hours  # ~20-30% range
rem_pct   = 0.18 + 0.004 * sleep_hours  # ~18-26% range
interruptions = 0 if sleep >= 7h else random(0, 3)
```

---

## 5. Entity Generation Rules

### 5.1 operational — Daily Entity Set

Per day, generate:

**SleepRecord** (1/day)
- bedtime, wake_time derived from scenario
- quality_score = scenario Q
- deep_pct, rem_pct from sleep hours
- interruptions from scenario rules
- source = "SYNTHETIC"

**HabitState** (8 habits/day)
- completed = True for Padrao_Ouro/Fim_de_Semana/PUSH days
- completed = False with 10% probability for Desvio_Leve
- completed = False with 30% probability for HARDWARE/recover days
- streak_current increments or resets per H(t) rules
- effort_minutes from scenario (e.g., meditacao=10, caminhada=20)

**QHEMetrics** (1/day)
- habit_avg = mean(H_i) for all 8 habits on that day
- consistency = completed_count / 8
- streak_bonus = mean(streak_i) / max_streak_observed
- energy_ratio = sleep_hours / 9.0 (capped at 1.0)
- qhe computed from formula
- regime_predicted from thresholds

**Routine** (static, ~20 routines defined once)
- 8 morning entry routines
- 6 core work routines (per period)
- 6 transition routines
- 4 exit routines
- Reused across all 180 days

**RoutineLog** (~6-10 per day)
- energia_nivel derived from journal energia
- foco_nivel derived from journal foco
- text = scenario description

**TimeBlock** (3-5 per day)
- Period MANHA: 04:00-08:00 (deep work)
- Period TARDE: 08:30-12:00, 13:00-17:00 (core work)
- Period NOITE: 18:00-20:30 (shutdown)
- Duration from hardwork_min / pomodoro_count

**JournalEntry** (1 morning + 1 evening per day = 2/day)
- entry_text from scenario template + daily variation
- energia_nivel from scenario
- foco_nivel from scenario
- humor_morning, humor_evening
- desvios list (empty for Padrao_Ouro, 1-3 for others)
- licoes_aprendidas list

**PomodoroRound** (n per day, n from scenario)
- round_number 1..n
- state = COMPLETE (90%), INTERRUPTED (10% Desvio_Leve)
- started_at, completed_at spaced 50min apart + breaks

**DayContext** (1/day)
- tipo_dia from scenario
- hardwork_orcado_min, hardwork_realizado_min from scenario
- pomodoros_meta, pomodoros_realizados from scenario
- tem_curso, tem_deadline flags

**DailyReflection** (1/day)
- parar_de_fazer, repetir, sempre_fazer from scenario templates
- big_win from scenario
- deu_certo, deu_errado from scenario
- maior_aprendizado from scenario
- ajustes_para_amanha from scenario

**LunchRecord** (1/day)
- eat_min = 5 (normal) or 10-15 (Lunch_Pesado)
- rest_min = 30 (normal) or 45-90 (Lunch_Pesado)
- pesado = True for Lunch_Pesado scenario

**TransicaoRegistrada** (T1-T9 per day = 9/day)
- completed = scenario.transicoes_complete >= T_number
- duracao_min from scenario

**AjusteFino** (0-2 per day)
- Generated on REDUCE/RECOVER days
- period from REDUCE pattern, minutos from severity

**PolicyDecision** (1/day)
- state from FSM simulation
- setpoints from PolicySetpoints.from_pav_defaults(state)
- rationale from scenario + FSM context
- qhe_input from QHEMetrics
- infraction_count from desvios count

---

## 6. Data Contracts

### 6.1 CSV Schema (Import/Export)

**File:** `synthetic_180d.csv`
**Format:** UTF-8 BOM, CRLF line endings
**Header:** `entity_type,id,date,cluster,...`

#### Core columns (all entity types):
```
entity_type,id,date,cluster
```

#### SleepRecord:
```
entity_type,id,date,cluster,bedtime,wake_time,quality_score,deep_sleep_pct,rem_sleep_pct,interruptions,notes,source
```

#### HabitState:
```
entity_type,id,date,cluster,habit_id,completed,streak_current,streak_broken_count,effort_minutes,habit_level,energy_required
```

#### QHEMetrics:
```
entity_type,id,date,cluster,habit_avg,consistency,streak_bonus,energy_ratio,qhe,regime_predicted
```

#### Routine:
```
entity_type,id,date,cluster,name,period,start_time,end_time,routine_type,description,mandatory
```

#### RoutineLog:
```
entity_type,id,date,cluster,routine_id,period,routine_type,text,energia_nivel,focus_nivel,humor
```

#### TimeBlock:
```
entity_type,id,date,cluster,start,end,period,label
```

#### JournalEntry:
```
entity_type,id,date,cluster,entry_text,energia_nivel,focus_nivel,humor_morning,humor_evening,pomodoros_completos,periods_covered,desvios,licoes_aprendidas
```

#### PomodoroRound:
```
entity_type,id,date,cluster,round_number,state,started_at,completed_at,paused_duration_seconds
```

#### DayContext:
```
entity_type,id,date,cluster,tipo_dia,hardwork_orcado_min,hardwork_realizado_min,pomodoros_meta,pomodoros_realizados,tem_curso,tem_deadline,observacoes
```

#### DailyReflection:
```
entity_type,id,date,cluster,parar_de_fazer,repetir,sempre_fazer,big_win,deu_certo,deu_errado,maior_aprendizado,ajustes_para_amanha,estado_geral
```

#### LunchRecord:
```
entity_type,id,date,cluster,eat_min,rest_min,pesado,notas
```

#### TransicaoRegistrada:
```
entity_type,id,date,cluster,codigo,ritual,duracao_min,completed,notas
```

#### AjusteFino:
```
entity_type,id,date,cluster,period,minutos,reason
```

#### PolicyDecision:
```
entity_type,id,date,cluster,state,severity,rationale,days_in_state,previous_state,qhe_input,infraction_count
```

### 6.2 JSON Schema (Validation)

Each entity exported as individual JSON files in `synthetic_180d/json/{entity_type}/`

### 6.3 SQLite Dump (vibe-ops)

```sql
-- Generated via vibe-ops schema.sql + extended synthetic tables
-- File: synthetic_180d.db
```

---

## 7. Output Files

### 7.1 Directory Layout

```
life-ops/operational/data/synthetic/
├── SYNTHETIC_180D_SPEC.md          ← this document
├── synthetic_180d.csv               ← master CSV (all entities)
├── synthetic_180d.db               ← SQLite dump (vibe-ops tables)
├── synthetic_180d_manifest.json    ← generation metadata + UEID index
│
├── json/                            ← per-entity JSON files
│   ├── sleep_record/
│   │   └── {date}.json
│   ├── habit_state/
│   │   └── {date}.json
│   ├── qhe_metrics/
│   │   └── {date}.json
│   ├── routine/
│   ├── routine_log/
│   ├── time_block/
│   ├── journal_entry/
│   ├── pomodoro_round/
│   ├── day_context/
│   ├── daily_reflection/
│   ├── lunch_record/
│   ├── transicao/
│   ├── ajuste_fino/
│   ├── policy_decision/
│   └── policy_setpoints/
│
├── vibe_ops/                        ← vibe-ops SQLite dump
│   ├── temporal_wave.csv
│   ├── temporal_cycle.csv
│   ├── temporal_phase.csv
│   ├── study_plan.csv
│   ├── study_topic.csv
│   ├── dev_project.csv
│   ├── habit.csv
│   └── habit_state.csv
│
└── reports/                         ← generated narrative reports
    ├── weekly_01.md
    ├── weekly_02.md
    ├── ...
    └── weekly_26.md
```

### 7.2 Manifest Schema

```json
{
  "version": "1.0",
  "date_range": {"start": "2025-12-23", "end": "2026-06-22"},
  "total_days": 180,
  "generator": "synthetic_gen v1.0",
  "seed": "6-month PAV simulation",
  "entities": {
    "sleep_record": {"count": 180, "file": "json/sleep_record/"},
    "habit_state": {"count": 1440, "file": "json/habit_state/"},
    "qhe_metrics": {"count": 180, "file": "json/qhe_metrics/"},
    "routine": {"count": 22, "file": "json/routine/"},
    "routine_log": {"count": 1260, "file": "json/routine_log/"},
    "time_block": {"count": 720, "file": "json/time_block/"},
    "journal_entry": {"count": 360, "file": "json/journal_entry/"},
    "pomodoro_round": {"count": 1620, "file": "json/pomodoro_round/"},
    "day_context": {"count": 180, "file": "json/day_context/"},
    "daily_reflection": {"count": 180, "file": "json/daily_reflection/"},
    "lunch_record": {"count": 180, "file": "json/lunch_record/"},
    "transicao": {"count": 1620, "file": "json/transicao/"},
    "ajuste_fino": {"count": 60, "file": "json/ajuste_fino/"},
    "policy_decision": {"count": 180, "file": "json/policy_decision/"}
  },
  "scenarios": {
    "Padrao_Ouro": 98,
    "Desvio_Leve": 18,
    "Fim_de_Semana": 52,
    "Hardcore": 4,
    "Recuperacao": 4,
    "Lunch_Pesado": 6,
    "Feriado": 4,
    "Doente": 2,
    "Visita_Inesperada": 1,
    "Vigilia": 1
  },
  "policy_distribution": {
    "PUSH": 42,
    "MAINTAIN": 98,
    "REDUCE": 28,
    "RECOVER": 12
  },
  "ueid_index": {
    "oper:sle:20251223": {"file": "json/sleep_record/20251223.json"},
    "oper:hab:beber_2l_de_agua": {"file": "json/habit/beber_2l_de_agua.json"}
  }
}
```

---

## 8. Implementation Approach

### 8.1 Generator Architecture

```
synthetic_gen.py           ← CLI entry (typer)
├── SyntheticEngine         ← main simulation loop
│   ├── _simulate_day(date, scenario) → dict of entities
│   ├── _simulate_habit_state(habit, date, streak) → HabitState
│   ├── _simulate_qhe(habits, sleep) → QHEMetrics
│   ├── _simulate_policy(qhe, prev_state) → PolicyDecision
│   └── _simulate_streak(habit_id, date) → int
├── ScenarioCalendar        ← 26-week scenario assignment
│   └── _assign_scenarios(start, end) → list[ScenarioDay]
├── UeidRegistry            ← UEID generation + deduplication
│   └── make_ueid(cluster, entity, id_fragment) → str
├── CsvExporter             ← writes synthetic_180d.csv
├── JsonExporter            ← writes json/{entity}/ directory
├── VibeOpsExporter         ← writes vibe_ops/*.csv
└── ReportGenerator          ← writes reports/weekly_*.md
```

### 8.2 CLI Commands

```bash
# Generate full 180-day dataset
poetry run pav synthetic generate

# Generate specific subdataset
poetry run pav synthetic generate --days 30
poetry run pav synthetic generate --start 2026-01-01 --end 2026-03-22

# Validate existing dataset
poetry run pav synthetic validate --dataset synthetic_180d

# Export to CSV
poetry run pav synthetic export-csv --output data/synthetic_180d.csv

# Export to vibe-ops SQLite
poetry run pav synthetic export-db --output data/synthetic_180d.db

# Preview day N
poetry run pav synthetic preview --day 45
```

### 8.3 Key Generation Parameters

```python
LAMBDA_LEARNING = 0.093
ETA_STREAK_BONUS = 0.5
QHE_PUSH_THRESHOLD = 0.85
QHE_RECOVER_THRESHOLD = 0.40
HYSTERESIS_UP = 3   # days sustained to promote
HYSTERESIS_DOWN = 2 # days sustained to demote
SLEEP_TARGET_HOURS = 7.5
POMODORO_DURATION_MIN = 50
BREAK_DURATION_MIN = 10
```

### 8.4 Seeded Randomness

All random choices use a fixed seed (`SEED = 42`) for reproducibility. Scenario assignment uses deterministic scheduling first, then random variation within scenario bounds.

---

## 9. File Naming Conventions

| File | Pattern | Example |
|------|---------|---------|
| JSON entity | `{date}.json` | `20251223.json` |
| Weekly report | `weekly_{NN}.md` | `weekly_01.md` |
| vibe-ops CSV | `{entity}.csv` | `temporal_wave.csv` |
| UEID prefix | `oper:{ent}:` | `oper:sle:` |

---

## 10. Validation Checklist

- [ ] All 180 days have exactly 1 SleepRecord
- [ ] All 180 days have exactly 1 DayContext
- [ ] All 180 days have exactly 1 DailyReflection
- [ ] All 180 days have exactly 1 LunchRecord
- [ ] All 180 days have exactly 1 PolicyDecision
- [ ] All 180 days have exactly 9 TransicaoRegistrada (T1-T9)
- [ ] All 8 habits have 180 HabitState entries
- [ ] All 180 days have 2 JournalEntry (AM + PM)
- [ ] UEID prefixes are correct: `oper:` for operational, `vibe:` for vibe-ops
- [ ] QHE values are within [0, 1]
- [ ] H(t) values are within [0, 1]
- [ ] Policy FSM transitions respect hysteresis rules
- [ ] Scenario distribution matches the matrix
- [ ] CSV can be round-tripped through csv_loader.py
- [ ] JSON files validate against Pydantic models
