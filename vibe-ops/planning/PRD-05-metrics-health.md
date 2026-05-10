# PRD-05: Metrics & Health Engine
**Versão:** 1.0.0 | **Status:** Draft | **Data:** 2026-05-10

> **Standalone Memory Machine** — Especificação autônoma do subgrafo de métricas e saúde. Cobre: DailyLog → SleepRecord → EnergyReading → DailyConsolidation. Alimenta o PolicyEngine com sinais fisiológicos e de performance.

---

## 1. Propósito

O subgrafo de **Metrics & Health** é o sistema de telemetria do organismo humano dentro do Data-Mesh. Ele:

- Captura dados diários de sono, energia e humor
- Consolida métricas em agregados diários/semanais
- Emite sinais para o PolicyEngine ajustar cargas de trabalho
- Alimenta o cálculo de QHE (Quality Habit Effectiveness) no HabitTracker
- Provê contexto fisiológico para o TemporalEngine escalar fases

---

## 2. Modelos Pydantic

### SleepRecord
```python
class SleepRecord(BaseModel):
    id: UUID
    date: date
    bedtime: time                    # hora de dormir
    wake_time: time                  # hora de acordar
    duration_hours: float            # calculado
    quality_score: int = Field(ge=1, le=10)
    deep_sleep_pct: Optional[float]  # % sono profundo
    rem_sleep_pct: Optional[float]
    interruptions: int = 0
    notes: Optional[str]
    source: SleepSource              # MANUAL|GARMIN|OURA|APPLE_HEALTH

class SleepSource(str, Enum):
    MANUAL = "manual"
    GARMIN = "garmin"
    OURA = "oura"
    APPLE_HEALTH = "apple_health"
```

### EnergyReading
```python
class EnergyReading(BaseModel):
    id: UUID
    date: date
    timestamp: datetime
    level: EnergyLevel               # H|M|L
    context: str                     # "morning"|"afternoon"|"evening"
    mood: Optional[MoodScore]        # 1-5
    focus: Optional[int]             # 1-10
    stress: Optional[int]            # 1-10
    notes: Optional[str]

class MoodScore(int):
    # 1=muito ruim, 2=ruim, 3=neutro, 4=bom, 5=excelente
    pass
```

### DailyLog (entrada diária consolidada)
```python
class DailyLog(BaseModel):
    id: UUID
    date: date
    # Sleep
    sleep: Optional[SleepRecord]
    # Energy readings ao longo do dia
    energy_readings: list[EnergyReading] = []
    avg_energy: Optional[float]      # média das leituras
    peak_energy_time: Optional[str]  # "morning"|"afternoon"|"evening"
    # Produção
    tasks_completed: int = 0
    tasks_created: int = 0
    time_tracked_hours: float = 0.0
    focus_sessions: int = 0
    # Hábitos
    habits_done: int = 0
    habits_total: int = 0
    habit_compliance_pct: float = 0.0
    # Estudos
    study_minutes: int = 0
    pomodoros: int = 0
    # Saúde
    exercise_done: bool = False
    exercise_minutes: int = 0
    water_glasses: int = 0
    meals_logged: int = 0
    # Notas
    notes: Optional[str]
    mood_morning: Optional[int]
    mood_evening: Optional[int]
    # Score composto
    daily_score: Optional[float]     # calculado pelo engine
    created_at: datetime
    updated_at: datetime
```

### DailyConsolidation (agregado calculado)
```python
class DailyConsolidation(BaseModel):
    date: date
    # Scores compostos
    energy_score: float              # 0-100 (baseado nas leituras)
    productivity_score: float        # 0-100
    health_score: float              # 0-100
    overall_score: float             # média ponderada
    # Derivados
    sleep_debt_hours: float          # acumulado da semana
    productivity_trend: float        # vs média 7 dias
    energy_trend: float
    # Alertas gerados
    alerts: list[MetricAlert] = []
    # Recomendações
    recommendations: list[str] = []

class MetricAlert(BaseModel):
    level: AlertLevel                # INFO|WARNING|CRITICAL
    metric: str
    message: str
    value: float
    threshold: float
```

### WeeklyAggregate
```python
class WeeklyAggregate(BaseModel):
    week_start: date                 # Monday
    week_end: date                   # Sunday
    days: list[DailyConsolidation]
    # Médias
    avg_sleep_hours: float
    avg_sleep_quality: float
    avg_energy_score: float
    avg_productivity: float
    total_tasks_done: int
    total_study_minutes: int
    total_exercise_days: int
    # Hábitos
    habit_compliance_avg: float
    # Streaks
    best_streak_habit: Optional[str]
    # Score da semana
    week_score: float
    week_label: WeekLabel            # EXCELLENT|GOOD|AVERAGE|POOR|RECOVERY

class WeekLabel(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"
    RECOVERY = "recovery"
```

---

## 3. Frontmatter Schema (Daily Log em Markdown)

```yaml
---
type: daily_log
date: "2026-05-10"
sleep:
  bedtime: "23:30"
  wake_time: "06:45"
  quality: 8
  interruptions: 1
energy:
  morning: H
  afternoon: M
  evening: L
  mood: 4
tasks_completed: 7
time_tracked_hours: 5.5
habits_done: 6
habits_total: 8
study_minutes: 90
pomodoros: 6
exercise: true
exercise_minutes: 45
water_glasses: 8
notes: "Dia produtivo. Foco em sprint de auth."
---
```

---

## 4. Algoritmos de Score

### Energy Score Diário
```
energy_map = {H: 100, M: 60, L: 30}
energy_score = média(energy_map[r.level] for r in readings)
penalidade_sono = max(0, (8 - sleep.duration_hours) * 10)
energy_score_final = max(0, energy_score - penalidade_sono)
```

### Productivity Score
```
base = (tasks_completed / max(tasks_created, 1)) * 60
time_bonus = min(time_tracked_hours / 8, 1) * 25
focus_bonus = min(pomodoros / 8, 1) * 15
productivity_score = base + time_bonus + focus_bonus
```

### Health Score
```
sleep_score = sleep.quality_score * 10
exercise_score = 25 if exercise_done else 0
water_score = min(water_glasses / 8, 1) * 15
health_score = (sleep_score * 0.5) + exercise_score + water_score
```

### Overall Daily Score
```
overall = energy * 0.3 + productivity * 0.4 + health * 0.3
```

---

## 5. Thresholds de Alerta (PolicyEngine Feed)

| Métrica | WARNING | CRITICAL | Ação Sugerida |
|:---|:---|:---|:---|
| `sleep_debt_hours` | > 4h | > 8h | Ativar RECOVER wave |
| `avg_energy_score` (7d) | < 50 | < 30 | Reduzir carga de trabalho |
| `habit_compliance_pct` | < 60% | < 40% | Revisar hábitos ativos |
| `productivity_score` | < 40 | < 25 | Verificar bloqueios |
| `sleep.quality_score` | < 5 | < 3 | Alert crítico de saúde |

---

## 6. Eventos Data-Mesh

| Evento Emitido | Trigger | Dados |
|:---|:---|:---|
| `metric.daily_consolidated` | fim do dia | DailyConsolidation |
| `metric.energy_low` | energy_score < 40 | level, date |
| `metric.sleep_debt` | sleep_debt > 4h | debt_hours, trend |
| `metric.week_reviewed` | domingo | WeeklyAggregate |

| Evento Consumido | Origem | Ação |
|:---|:---|:---|
| `habit.completed` | HabitTracker | incrementa habits_done |
| `task.completed` | ProjectEngine | incrementa tasks_completed |
| `timew.entry.closed` | Timewarrior | soma time_tracked_hours |

---

## 7. CLI Interface

```bash
# Log diário rápido
vibe-ops daily log --date today --sleep-quality 8 --energy-morning H

# Consolidar métricas do dia
vibe-ops daily consolidate --date today

# Relatório semanal
vibe-ops metrics weekly --week 2026-W19

# Dashboard de saúde
vibe-ops health dashboard

# Alertas pendentes
vibe-ops metrics alerts --unresolved
```

---

## 8. Módulos

| Arquivo | Responsabilidade |
|:---|:---|
| `src/models/metric_entities.py` | Modelos Pydantic (expandir) |
| `src/pipeline/harness_metrics.py` | Pipeline de consolidação (existente) |
| `src/pipeline/daily_consolidator.py` | Score engine diário (novo) |
| `src/pipeline/weekly_aggregator.py` | Agregação semanal (novo) |

---

*PRD-05 — Metrics & Health Engine | vibe-ops v1.0.0 | 2026-05-10*
