# 03 — Entity Lifecycle

> The 14 entities wired into the persistent state. For each: purpose,
> key fields, computed fields, Pydantic invariants, and the UEID
> convention.

All 14 entities share three properties:

1. They are **Pydantic v2 `BaseModel` subclasses** with
   `frozen=True` (immutable) unless noted.
2. They are **leaves of the import graph** — entities only import
   from `operational.enums`, `operational.types`, and (sometimes)
   `operational.constants`. **No entity imports another entity.**
   The one exception is `JournalEntry`, which embeds `AjusteFino`
   inline (`entities/journal.py:44`).
3. They enforce `extra="forbid"` — unknown fields are rejected at
   construction time.

For the unified reference table (all 14 in one view), see
[../data/00-DATA-MODEL.md](../data/00-DATA-MODEL.md).

---

## 1. Routine

- **File:** `entities/routine.py:80`
- **Purpose:** A time-bounded daily task within a `Period` (PAV §3).
  Routines are *scheduled* in advance; they are the canonical
  structure of a typical day.
- **Key fields:**
  - `id: UEID` (e.g. `"rou_morning_wake"`)
  - `name: str` (1-100 chars, whitespace stripped)
  - `period: Period` (MANHA / TARDE / NOITE)
  - `routine_type: RoutineType` (ENTRY / CORE / TRANSITION / EXIT)
  - `start_time: time`, `end_time: time` (same-day, no overnight)
  - `days_of_week: set[Weekday]` (0=Mon ... 6=Sun; default = all 7)
  - `mandatory: bool = True`
  - `archived: bool = False`
- **Computed fields:**
  - `duration_minutes` (whole minutes; same-day only)
  - `active_on_weekend` (True iff `{5, 6} ∩ days_of_week`)
- **Invariants:**
  - `end_time > start_time` (`_validate_times`,
    `entities/routine.py:162-178`)
  - `days_of_week ⊆ {0, 1, 2, 3, 4, 5, 6}` (`_validate_days_of_week`,
    `entities/routine.py:137-160`)
- **UEID pattern:** `rou_<slug>` (no date component — routines are
  reusable across days)

---

## 2. RoutineLog

- **File:** `entities/routine.py:347`
- **Purpose:** A natural-language log of a single routine execution
  (PAV §3, §10). Captures *what* and *how* a routine was performed,
  separate from the gross entry/exit times tracked in `TimeBlock`.
- **Key fields:**
  - `id: UEID` (e.g. `"rlog_manha_2026_06_07_acordar"`)
  - `routine_id: UEID` (back-reference to `Routine`)
  - `block_id: UEID | None` (optional back-reference to `TimeBlock`)
  - `date: date`, `period: Period`, `routine_type: RoutineType`
  - `text: str` (1-2000 chars, the NL log)
  - `energia_nivel: int | None` (1-10), `foco_nivel: int | None` (1-10),
    `humor: int | None` (1-5)
- **Computed fields:**
  - `is_entry_routine` (True iff `routine_type == ENTRY`)
  - `is_exit_routine` (True iff `routine_type == EXIT`)
- **Invariants:**
  - `text` non-empty (Pydantic `min_length=1`)
  - Optional ratings bounded by `Field(ge=..., le=...)`
- **UEID pattern:** `rlog_<period>_<YYYY_MM_DD>_<slug>`

---

## 3. TimeBlock

- **File:** `entities/time_block.py:41`
- **Purpose:** A calendar-aware time interval for ad-hoc activity
  tracking (PRD-01 §2). The daily handler records "this is what I did
  between 14:00 and 14:50 on a Tuesday". Not the same as a
  `Routine` (which is scheduled in advance).
- **Key fields:**
  - `id: UEID` (e.g. `"blk_2026_06_07_1410"`)
  - `label: str` (0-100 chars; default `""`)
  - `start: datetime`, `end: datetime` (timezone-aware in prod;
    naive in tests)
  - `period: Period`
  - `routine_id: UEID | None` (optional link to a planned routine)
  - `energia_nivel: int | None` (1-10),
    `foco_nivel: int | None` (1-10)
  - `notes: str` (0-500 chars)
- **Computed fields:**
  - `duration_minutes` (whole minutes; positive because of validator)
  - `overlaps_period` (True iff the block lies inside the canonical
    PAV §3 windows: 3-5 / 8-17 / 18-21)
  - `has_routine_link` (True iff `routine_id` is set)
- **Invariants:**
  - `end > start` (`_validate_times`, `entities/time_block.py:83-100`)
- **UEID pattern:** `blk_<YYYY_MM_DD>_<HHMM>`

---

## 4. JournalEntry

- **File:** `entities/journal.py:90`
- **Purpose:** The raw daily narrative (PAV §10). Captures the
  periods covered, routines completed, deviations, lessons learned,
  energy/focus levels, completed pomodoros, and self-reported mood.
- **Key fields:**
  - `id: UEID` (e.g. `"day_2026_06_07"`)
  - `date: date`
  - `entry_text: str` (0-5000 chars)
  - `periods_covered: set[Period]`
  - `routines_completed: list[UEID]` (unique, validated)
  - `desvios: list[str]` (each ≤ 200 chars), `licoes_aprendidas: list[str]` (each ≤ 500)
  - `ajustes_finos: list[AjusteFino]` (inline embedded; the one
    place an entity holds another entity)
  - `energia_nivel: int | None` (1-10), `foco_nivel: int | None`,
    `humor_morning: int | None`, `humor_evening: int | None`
  - `pomodoros_completos: int` (0-12)
  - `created_at: datetime`, `updated_at: datetime | None` (auto-managed)
- **Computed fields:** none.
- **Invariants:**
  - `routines_completed` is unique (no duplicate UEIDs,
    `_validate_unique_routines`, `entities/journal.py:177-194`)
  - `updated_at` auto-refreshed on every assignment
    (`_auto_set_updated_at`, `entities/journal.py:196-213`)
  - `entry_text` ≤ 5000 chars (PAV §10)
- **Mutable:** **Yes** (`frozen=False` + `validate_assignment=True`).
  The `updated_at` auto-management requires it.
- **UEID pattern:** `day_YYYY_MM_DD`

---

## 5. Habit

- **File:** `entities/habit.py:88`
- **Purpose:** The static definition of a habit (PRD-02 §2, PAV §6).
  Carries the resistance (R), the learning rate (λ), and the relative
  weight (w_i) used by the QHE aggregator.
- **Key fields:**
  - `id: UEID` (e.g. `"hab_sleep_8h"`)
  - `name: str` (1-100 chars, non-blank)
  - `category: HabitCategory` (PHYSIOLOGICAL / COGNITIVE / SOCIAL /
    CREATIVE / RITUAL)
  - `resistance: float` (0.0-10.0, R in `E_req = R(1-H)`)
  - `lambda_learning: float` (0.0-1.0, λ in `H(t) = 1 - e^{-λs}`).
    Default: `DEFAULT.LAMBDA_LEARNING_DEFAULT` = 0.093 (ADR-003).
  - `weight_in_qhe: float` (0.0-1.0, the QHE weight)
  - `frequency: Literal["DAILY", "WEEKLY", "WAVE"]` (default `"DAILY"`)
  - `target_streak: int | None` (≥ 0)
- **Computed fields:** none.
- **Invariants:**
  - `name` non-blank after stripping (`_validate_name_not_blank`,
    `entities/habit.py:152-174`)
  - `resistance` / `lambda_learning` / `weight_in_qhe` all bounded
- **Factory:** `Habit.from_pav_defaults(name, category, resistance,
  weight_in_qhe, **overrides)` — pre-fills id, lambda, created_at,
  archived (`entities/habit.py:176-226`).
- **UEID pattern:** `hab_<slug>`

---

## 6. SleepRecord

- **File:** `entities/metric.py:101`
- **Purpose:** A single night's sleep record (PRD-05 §2.1). Bedtime,
  wake time, self-reported quality, and optional deep/rem percentages
  and interruption count.
- **Key fields:**
  - `id: UEID` (e.g. `"slp_2026_06_07"`)
  - `date: date` (the "sleep belongs to" date — typically the wake
    date)
  - `bedtime: time`, `wake_time: time`
  - `quality_score: int` (1-10)
  - `deep_sleep_pct: float | None` (0-100), `rem_sleep_pct: float | None`
  - `interruptions: int` (≥ 0)
  - `source: Literal["MANUAL", "GARMIN", "OURA", "APPLE_HEALTH"]`
    (default `"MANUAL"`)
  - `notes: str` (0-500)
- **Computed fields:**
  - `duration_hours` (handles midnight crossing — if `wake < bed`,
    adds 1 day to the wake datetime, then divides by 3600).
- **Invariants:**
  - `quality_score ∈ [1, 10]`
  - `interruptions ≥ 0`
  - `source` in the four allowed values
- **UEID pattern:** `slp_YYYY_MM_DD`

---

## 7. PomodoroRound

- **File:** `entities/pomodoro.py:184`
- **Purpose:** A single round of the pomodoro state machine (PAV §9).
  Each round has its own start / completion timestamps and pause
  accounting.
- **Key fields:**
  - `id: UEID` (e.g. `"pmor_session_001_round_1"`)
  - `round_number: int` (1-20)
  - `state: PomodoroState` (IDLE / WORK / BREAK / LONG_BREAK /
    PAUSED / SKIPPED / COMPLETE)
  - `started_at: datetime | None`, `completed_at: datetime | None`
  - `paused_duration_seconds: int` (≥ 0)
- **Computed fields:**
  - `actual_duration_minutes` (`(completed - started) - paused / 60`).
    Returns `0.0` if either timestamp is None.
  - `is_focus_round` (True iff state ∈ {WORK, COMPLETE})
  - `is_break_round` (True iff state ∈ {BREAK, LONG_BREAK})
- **Invariants:**
  - `completed_at >= started_at` when both are set
    (`_validate_timestamps`, `entities/pomodoro.py:219-240`)
  - `round_number ∈ [1, 20]`
- **UEID pattern:** `pmor_<session>_<N>`

> For the full session, see `PomodoroSession`
> (`entities/pomodoro.py:290`). It is not wired into the 14 live
> repos — only `PomodoroRound` is. The session can be reconstructed
> from the list of rounds sharing a `config_id`.

---

## 8. PolicyDecision

- **File:** `entities/policy.py:271`
- **Purpose:** A policy decision for a specific date (PRD-06). The
  output of the `PolicyEngine`: the chosen `PolicyState`, severity,
  active `PolicySetpoints`, and the inputs that drove the decision.
- **Key fields:**
  - `id: UEID` (e.g. `"pol_a1b2c3d4e5f6"`)
  - `date: date`
  - `state: PolicyState` (PUSH / MAINTAIN / REDUCE / RECOVER)
  - `severity: Literal["INFO", "WARNING", "CRITICAL"]` (default `"INFO"`)
  - `rationale: str` (0-500)
  - `setpoints: PolicySetpoints` (must match `state`)
  - `days_in_state: int` (≥ 0)
  - `previous_state: PolicyState | None`
  - `qhe_input: float | None` (0.0-1.0), `energy_input: EnergyLevel | None`
  - `infraction_count: int` (≥ 0)
  - `applied: bool` (default `False`), `applied_at: datetime | None`
- **Computed fields:** none.
- **Invariants:**
  - `setpoints.state == self.state` (`_validate_setpoints_match_state`,
    `entities/policy.py:340-362`)
  - `applied_at` auto-filled when `applied` flips to True
    (`_validate_applied_at`, `entities/policy.py:364-381`)
- **Mutable:** **Yes** — `applied` is flipped in a second step after
  the decision is constructed.
- **UEID pattern:** `pol_<12 hex>`

---

## 9. PolicySetpoints

- **File:** `entities/policy.py:95`
- **Purpose:** Operational regime parameters for a given
  `PolicyState` (PRD-06 §3). The envelope the daily handler must
  respect: hard ceiling on focused hours, cap on pomodoros, sleep
  target, Q_HE target, break length, allowed phases.
- **Key fields:**
  - `id: UEID` (e.g. `"set_a1b2c3d4e5f6"`)
  - `state: PolicyState`
  - `hardwork_budget_hours: float` (0.0-16.0)
  - `max_pomodoros_per_day: int` (0-12)
  - `sleep_target_hours: float` (4.0-10.0)
  - `qhe_target: float` (0.0-1.0)
  - `break_minutes: int` (1-30)
  - `allowed_phases: list[Literal["DEEP_WORK", "SHALLOW_WORK", "RECOVERY"]]`
  - `description: str` (0-200)
- **Computed fields:** none.
- **Invariants:**
  - `allowed_phases` is non-empty
    (`_validate_phases`, `entities/policy.py:149-169`)
- **Factory:** `PolicySetpoints.from_pav_defaults(state, **overrides)`
  — the canonical setpoint table for all four states
  (`entities/policy.py:171-263`):
  - PUSH: 8h, 10 pomodoros, sleep 7h, Q_HE 0.85
  - MAINTAIN: 6h, 8, sleep 8h, Q_HE 0.75
  - REDUCE: 4h, 5, sleep 8h, Q_HE 0.65
  - RECOVER: 2h, 2, sleep 9h, Q_HE 0.50
- **UEID pattern:** `set_<12 hex>`

---

## 10. AjusteFino

- **File:** `entities/ajuste_fino.py:36`
- **Purpose:** A signed minute adjustment between time blocks
  (PAV §2). Captures small deviations from the canonical schedule
  that aren't full desvios: "extended 5min break because tired",
  "reduced S3 to 2 rounds because of low energy".
- **Key fields:**
  - `id: UEID` (e.g. `"aju_manha_extra_break"`)
  - `date: date`
  - `period: Period`
  - `minutos: int` (-1440 to +1440; positive = added, negative = removed)
  - `reason: str` (1-500 chars, non-blank)
  - `block_id_before: UEID | None`, `block_id_after: UEID | None`
- **Computed fields:** none.
- **Invariants:**
  - `minutos` bounded by 24h in either direction
  - `reason` non-blank after stripping
    (`_validate_reason_not_empty`, `entities/ajuste_fino.py:65-70`)
- **UEID pattern:** `aju_<period>_<slug>`

---

## 11. DayContext

- **File:** `entities/v3.py:45`
- **Purpose:** Daily context — classifies the day, holds the
  orçado/realizado hardwork budget, and pomodoros meta (PAV V3 §2).
- **Key fields:**
  - `id: UEID` (e.g. `"ctx_2026_06_07"`)
  - `date: date`
  - `tipo_dia: TipoDia` (CURSO / LIVRE / HARDCORE / DESCANSO;
    default `CURSO`)
  - `hardwork_orcado_min: int` (0-1440; default 240 = 4h)
  - `hardwork_realizado_min: int` (0-1440; default 0)
  - `pomodoros_meta: int` (0-24; default 0)
  - `pomodoros_realizados: int` (0-24; default 0)
  - `tem_curso: bool`, `tem_deadline: bool`
  - `observacoes: str` (0-500)
- **Computed fields:**
  - `desvio_min` (realizado - orçado; positive = estourou)
  - `produtividade_pct` (min(100, realizado/orçado × 100))
- **Invariants:** All fields bounded by Pydantic `Field(ge, le)`.
- **UEID pattern:** `ctx_YYYY_MM_DD`

---

## 12. DailyReflection

- **File:** `entities/v3.py:104`
- **Purpose:** OKRs V3 — both the morning entry ritual (parar /
  repetir / sempre_fazer / big_win) and the evening exit ritual
  (deu_certo / deu_errado / maior_aprendizado / ajustes_para_amanha).
- **Key fields:**
  - `id: UEID` (e.g. `"ref_2026_06_07"`)
  - `date: date`
  - `parar_de_fazer: list[str]` (each ≤ 200)
  - `repetir: list[str]`, `sempre_fazer: list[str]`
  - `big_win: str` (0-300)
  - `deu_certo: list[str]`, `deu_errado: list[str]`
  - `maior_aprendizado: str` (0-500)
  - `ajustes_para_amanha: list[str]`
  - `estado_geral: EstadoPsicomatico` (default `REGULAR`)
- **Computed fields:** none.
- **Invariants:** String length caps via `Field(max_length=...)`.
- **UEID pattern:** `ref_YYYY_MM_DD`

---

## 13. LunchRecord

- **File:** `entities/v3.py:164`
- **Purpose:** Registro de almoço — eat minutes + rest minutes + pesado
  flag (PAV V3 §2). Lunch is a critical boundary: eat should be
  short (5 min ideal), rest 30 min ideal, pesado correlates with
  cochilo beyond budget.
- **Key fields:**
  - `id: UEID` (e.g. `"lun_2026_06_07"`)
  - `date: date`
  - `eat_min: int` (0-120; default 5)
  - `rest_min: int` (0-180; default 30)
  - `pesado: bool` (default False)
  - `notas: str` (0-300)
- **Computed fields:**
  - `duracao_total` (`eat_min + rest_min`)
  - `within_budget` (True iff `eat_min <= 5` and `rest_min <= 30`)
- **Invariants:** `eat_min` and `rest_min` bounded by Pydantic.
- **UEID pattern:** `lun_YYYY_MM_DD`

---

## 14. TransicaoRegistrada

- **File:** `entities/v3.py:220`
- **Purpose:** Registro de uma transição entre períodos/rotinas
  (PAV V3 §6). The 9 canonical transitions T1-T9 mark the day
  boundaries:

  ```
  T1 = Sono → Workout     T4 = Lunch → Meditação
  T2 = Workout → Curso    T5 = Curso → Lunch
  T3 = Curso → Hardwork   T6 = Hardwork → Noite
  T7 = Noite → Dormir     T8 = Dormir → Sono Prep
  T9 = Dormir → Acordar (ciclo)
  ```
- **Key fields:**
  - `id: UEID` (e.g. `"trn_T1_2026_06_07"`)
  - `date: date`
  - `codigo: str` (regex `^T[1-9]$`)
  - `ritual: RitualType` (HYDRATION / MEDITATION / SHUTDOWN / ...)
  - `duracao_min: int` (0-60; default 15)
  - `completed: bool` (default False)
  - `notas: str` (0-300)
- **Computed fields:** none.
- **Invariants:**
  - `codigo` matches `^T[1-9]$` (Pydantic regex)
  - `duracao_min ∈ [0, 60]`
- **UEID pattern:** `trn_<codigo>_<YYYY_MM_DD>`

---

## Cross-cutting: imports and the "leaves" rule

Every entity above imports only from:

- `operational.enums` — for enum types
- `operational.types` — for `UEID` (and `Annotated` aliases)
- `operational.constants` — for `DEFAULT` (e.g. `LAMBDA_LEARNING_DEFAULT`)
- Pydantic / stdlib only

**No entity imports another entity**, with the single exception of
`JournalEntry` (`entities/journal.py:44`):

```python
from operational.entities.ajuste_fino import AjusteFino
```

This is an **inline embedding** — `AjusteFino` is stored as a list
field on `JournalEntry.ajustes_finos` (`entities/journal.py:149-156`),
not as a back-reference. The cross-entity reference does not create a
circular import (AjusteFino imports only from `enums` and `types`).

This rule is what allows the package to bootstrap in any order: you
can import `JournalEntry` without pulling in `Routine`, `TimeBlock`,
`PolicyDecision`, etc. Tests rely on this for fast per-module
fixtures.

## Cross-cutting: UEID patterns at a glance

| Pattern | Entity | Example |
|---|---|---|
| `rou_<slug>` | Routine | `rou_morning_wake` |
| `rlog_<period>_<date>_<slug>` | RoutineLog | `rlog_manha_2026_06_07_acordar` |
| `rit_<slug>` | Ritual | `rit_hydration_am` |
| `trn_<from>_<to>` | Transition | `trn_manha_tarde` |
| `blk_<date>_<HHMM>` | TimeBlock | `blk_2026_06_07_1410` |
| `day_YYYY_MM_DD` | JournalEntry | `day_2026_06_07` |
| `ind_<slug>` | AutoIndagacao | `ind_morning_2026_06_07` |
| `hab_<slug>` | Habit | `hab_sleep_8h` |
| `hst_<habit>_<yyyymmdd>` | HabitState | `hst_hab_sleep_8h_20260607` |
| `qhe_<yyyymmdd>` | QHEMetrics | `qhe_20260607` |
| `slp_YYYY_MM_DD` | SleepRecord | `slp_2026_06_07` |
| `erg_<yyyymmdd>_<HHMM>` | EnergyReading | `erg_20260607_1430` |
| `pmo_<12 hex>` | PomodoroConfig | `pmo_a1b2c3d4e5f6` |
| `pmor_<session>_<N>` | PomodoroRound | `pmor_pms_001_round_1` |
| `pms_<date>_<period>` | PomodoroSession | `pms_2026_06_07_morning` |
| `set_<12 hex>` | PolicySetpoints | `set_a1b2c3d4e5f6` |
| `pol_<12 hex>` | PolicyDecision | `pol_a1b2c3d4e5f6` |
| `rec_<12 hex>` | DecisionRecord | `rec_a1b2c3d4e5f6` |
| `aju_<period>_<slug>` | AjusteFino | `aju_manha_extra_break` |
| `ctx_YYYY_MM_DD` | DayContext | `ctx_2026_06_07` |
| `ref_YYYY_MM_DD` | DailyReflection | `ref_2026_06_07` |
| `lun_YYYY_MM_DD` | LunchRecord | `lun_2026_06_07` |
| `trn_T<1-9>_<YYYY_MM_DD>` | TransicaoRegistrada | `trn_T1_2026_06_07` |

The `<12 hex>` suffix is `uuid4().hex[:12]` — a random 12-char
hex token, deterministic-enough for unit tests but not
cryptographically unique.

The `<slug>` token is 1+ lowercase alphanumerics or underscores.
The full UEID pattern is enforced at the type-system level:
`operational.types.UEID: TypeAlias = Annotated[str, Field(pattern=r"^[a-z]{3,5}_[a-z0-9_]+$")]`
(`types.py:74-80`).
