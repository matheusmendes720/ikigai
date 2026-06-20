# Spec: Cluster PLAN — Reports (Sprint 1)

> Especificação técnica dos **reports** gerados pelo Cluster PLAN.
> **Apenas markdown + JSON determinísticos**. Sem charts interativos,
> sem LLM, sem embeddings.

---

## 1. Visão Geral

O Cluster PLAN gera **4 tipos de reports** (Sprint 1):

| Report | Frequência | Tempo de Geração | Formato |
|---|---|---|---|
| Daily Status | Diário | < 100ms | JSON (via `plan today`) |
| Weekly Report | Semanal | < 2s | Markdown + JSON |
| Monthly Report | Mensal | < 5s | Markdown + JSON |
| Wave/Cycle/Phase Review | Quinzenal/45d/180d | < 5s | Markdown + JSON |

Todos são:
- **Determinísticos** (mesmo input → mesmo output)
- **Auditáveis** (cada métrica tem fórmula explícita)
- **Offline-first** (zero dependência de network)

---

## 2. Daily Status (US-001/002/003)

### 2.1. CLI

```bash
python -m life.cli plan today [--json]
```

### 2.2. Output (JSON)

```json
{
  "date": "2026-06-05",
  "regime": "MAINTAIN",
  "qhe": 0.78,
  "ikigai_focus": "skill",
  "wake_time_actual": "03:45",
  "rituals_done": {
    "morning": true,
    "afternoon": false,
    "evening": false
  },
  "pomodoros_planned": 7,
  "pomodoros_done": 3,
  "pomodoros_yield_pct": 42.8,
  "next_ritual": "afternoon",
  "wave_position": "7/15 (Mid-Wave tomorrow)"
}
```

### 2.3. Algoritmo

```python
def generate_daily_status(date: date) -> dict:
    # Query 1: Rotina do dia
    routine = db.query(DailyRoutine).filter(
        DailyRoutine.date == date
    ).first()

    # Query 2: Rituals done
    rituals = db.query(AutoIndagacao).filter(
        AutoIndagacao.date == date
    ).all()
    rituals_done = {
        "morning": any(r.ritual_type == "morning" for r in rituals),
        "afternoon": any(r.ritual_type == "afternoon" for r in rituals),
        "evening": any(r.ritual_type == "evening" for r in rituals)
    }

    # Query 3: Pomodoros
    pomodoros = db.query(Pomodoro).filter(
        Pomodoro.date == date
    ).all()
    done = sum(1 for p in pomodoros if p.status == "completed")
    yield_pct = (done / max(routine.pomodoros_planned if routine else 0, 1)) * 100

    # Query 4: Q_HE
    qhe_row = db.query(QHEHistory).filter(
        QHEHistory.date == date
    ).first()

    return {
        "date": str(date),
        "regime": qhe_row.regime if qhe_row else None,
        "qhe": qhe_row.qhe_score if qhe_row else None,
        "ikigai_focus": routine.ikigai_focus if routine else None,
        "wake_time_actual": str(routine.wake_time_actual) if routine and routine.wake_time_actual else None,
        "rituals_done": rituals_done,
        "pomodoros_planned": routine.pomodoros_planned if routine else 0,
        "pomodoros_done": done,
        "pomodoros_yield_pct": round(yield_pct, 1),
        "next_ritual": next_pending_ritual(rituals_done),
        "wave_position": get_wave_position(date)
    }
```

---

## 3. Weekly Report (US-004)

### 3.1. CLI

```bash
python -m life.cli plan report weekly [--date YYYY-MM-DD] [--json]
```

### 3.2. Output (Markdown)

```markdown
# Weekly Report: 2026-06-01 → 2026-06-07

## Summary
- **Pomodoros:** 28/35 (80.0% yield)
- **Regime distribution:** 🟢 PUSH=2 | 🟡 MAINTAIN=4 | 🟠 REDUCE=0 | 🔴 RECOVER=1
- **Q_HE avg:** 0.76
- **Q_HE trend:** 0.65 → 0.70 → 0.78 → 0.82 → 0.80 → 0.75 → 0.78

## Q_HE Chart (ASCII)
```
0.85 ┤                                          ╭─╮
0.80 ┤                              ╭─╮         │ ╰─╮
0.75 ┤                  ╭─╮    ╭───╯ ╰╮   ╭───╯   ╰─
0.70 ┤      ╭─╮    ╭───╯ ╰────╯      ╰───╯
0.65 ┤──────╯ ╰────╯
     └─Mon─Tue─Wed─Thu─Fri─Sat─Sun─
```

## Pomodoros por dia
- **Mon 06-01:** 5/5 (100%) — regime PUSH
- **Tue 06-02:** 4/5 (80%) — regime PUSH
- **Wed 06-03:** 5/5 (100%) — regime MAINTAIN
- **Thu 06-04:** 4/5 (80%) — regime MAINTAIN
- **Fri 06-05:** 3/7 (43%) — regime MAINTAIN (afternoon skipped)
- **Sat 06-06:** 4/5 (80%) — regime REDUCE (low energy)
- **Sun 06-07:** 3/3 (100%) — regime RECOVER (recovery day)

## IKIGAi Vectors Avg (Sprint 6+)
- (TBD — Sprint 6 implementa `ikigai_scorer.py` 5 vetores)

## Transitions
- Total: 32 min (alvo: ≤ 45 min/dia × 7 = 315 min)
- Avg per day: 4.6 min

## Notes
- Best day: Wed 06-03 (100% yield, MAINTAIN)
- Worst day: Fri 06-05 (43% yield, afternoon skipped)
- Top 3 aprendizados (top 3 q9_learned):
  1. "Pomodoro timing works when no notifications"
  2. "JIT refactor before next sprint saves time"
  3. "Lunch 30min is sweet spot"
```

### 3.3. Output (JSON)

```json
{
  "period": {"start": "2026-06-01", "end": "2026-06-07"},
  "summary": {
    "pomodoros_planned": 35,
    "pomodoros_done": 28,
    "pomodoros_interrupted": 0,
    "yield_pct": 80.0,
    "days_pushed": 2,
    "days_maintain": 4,
    "days_recover": 1
  },
  "ikigai_avg": {
    "passion": 0.0,
    "skill": 0.0,
    "market": 0.0,
    "revenue": 0.0
  },
  "qhe_trend": [0.65, 0.70, 0.78, 0.82, 0.80, 0.75, 0.78],
  "qhe_avg": 0.76,
  "transitions_total_minutes": 32.0,
  "best_day": "2026-06-03",
  "worst_day": "2026-06-05",
  "top_3_learnings": [
    "Pomodoro timing works when no notifications",
    "JIT refactor before next sprint saves time",
    "Lunch 30min is sweet spot"
  ]
}
```

### 3.4. Algoritmo

Ver [`spec-cluster-plan-pipelines.md §4.2`](spec-cluster-plan-pipelines.md).

---

## 4. Monthly Report (Sprint 1+)

### 4.1. CLI

```bash
python -m life.cli plan report monthly [--month 2026-06] [--json]
```

### 4.2. Output (Markdown)

```markdown
# Monthly Report: June 2026

## Top-Line
- **Total pomodoros:** 110/135 (81.5% yield)
- **Q_HE avg:** 0.74
- **Regime distribution:** 🟢 PUSH=8 (27%) | 🟡 MAINTAIN=15 (50%) | 🟠 REDUCE=5 (17%) | 🔴 RECOVER=2 (6%)

## Week-by-Week
| Week | Yield | Q_HE Avg | Top Regime | Notes |
|---|---|---|---|---|
| W1 (Jun 1-7) | 80.0% | 0.76 | MAINTAIN | Best day Wed |
| W2 (Jun 8-14) | 78.0% | 0.75 | MAINTAIN | SENAI exam week |
| W3 (Jun 15-21) | 88.0% | 0.81 | PUSH | Wave-End strong |
| W4 (Jun 22-28) | 80.0% | 0.74 | REDUCE | Mid-cycle fatigue |

## IKIGAi Vector Deltas (Sprint 6+)
- Passion: TBD
- Skill: TBD
- Market: TBD
- Revenue: TBD

## Insights
- Best week: W3 (88% yield, 0.81 Q_HE) — 2 days in PUSH
- Worst week: W4 (80% yield, 0.74 Q_HE) — fatigue from sprint density
- 2 RECOVER days suggests histerese working (caught dips early)
- Transition overhead: avg 32 min/dia (target: ≤ 45 min)

## Phase Position
- Cycle: 18/45 (40%)
- Phase: 18/180 (10%)
```

### 4.3. Output (JSON)

```json
{
  "month": "2026-06",
  "top_line": {
    "pomodoros_planned": 135,
    "pomodoros_done": 110,
    "yield_pct": 81.5,
    "qhe_avg": 0.74,
    "regime_distribution": {
      "PUSH": 8, "MAINTAIN": 15, "REDUCE": 5, "RECOVER": 2
    }
  },
  "weeks": [
    {"week": "W1", "yield_pct": 80.0, "qhe_avg": 0.76, "top_regime": "MAINTAIN", "notes": "Best day Wed"},
    ...
  ],
  "ikigai_delta": {
    "passion": null,  // Sprint 6+
    "skill": null,
    "market": null,
    "revenue": null
  },
  "cycle_position": "18/45",
  "phase_position": "18/180"
}
```

---

## 5. Wave/Cycle/Phase Review (Sprint 2-4)

### 5.1. Wave Review (d7 + d15)

```bash
python -m life.cli plan wave review --mid [--wave-id WAVE-2026-Q2-1]
python -m life.cli plan wave review --end [--wave-id WAVE-2026-Q2-1]
```

**Output (--mid):**
```markdown
# Mid-Wave Review: WAVE-2026-Q2-1 (d7/15)

## Status
- $H_{wave}$ esperado: 48.0% (λ=0.093)
- $H_{wave}$ real: 50.5% ✅
- $C_{comp}$: 65.0% (8/12 tasks done)
- Days in regime: 🟢 PUSH=2 | 🟡 MAINTAIN=5

## Top 3 Aprendizados
1. "Refactor antes de feature reduz bug rate"
2. "Tw pomodoro time tracking é mais preciso que timew manual"
3. "Q_HE 0.78 vs 0.65 = 1 hora mais de foco"

## Ajustes Sugeridos
- [ ] Manter 7 pomodoros/dia (alcançável)
- [ ] Aumentar 1 pomodoro de manhã (Q_HE morning = 8)
- [ ] Reduzir 1 pomodoro de tarde (afternoon Q_HE = 5)
```

### 5.2. Cycle Review (d45)

```markdown
# Cycle-End Review: CYCLE-2026-Q2-1 (45/45)

## Status
- 3 WAVE reviews consolidadas
- $H_{cycle}$ real: 98.5% (target: 98.5%) ✅
- Days in regime: 🟢 PUSH=12 | 🟡 MAINTAIN=24 | 🟠 REDUCE=7 | 🔴 RECOVER=2

## HALF_QUARTER Check
- 45D ≡ 45D ✅ (alinhamento dimensional perfeito)
- OKR Q2: 47% (target: 50% no HALF_QUARTER) — leve atraso

## IKIGAi Vector Deltas
- Passion: +0.5h treino (target: 7h/semana, achieved: 8h)
- Skill: +12h study (3 topics completed)
- Market: +0 (Sprint 6 territory)
- Revenue: +0 (Sprint 6 territory)

## Próximo CYCLE
- **Tema:** Aprofundar Skill (Python async, Data engineering)
- **Top 3 objetivos:** ...
- **Riscos:** SENAI final exams em CYCLE 2
```

### 5.3. Phase Review (d180)

(ver US-008)

---

## 6. Performance Targets

| Report | Target Tempo | Medição |
|---|---|---|
| Daily Status | < 100ms | stopwatch |
| Weekly Report | < 2s | stopwatch |
| Monthly Report | < 5s | stopwatch |
| Wave Review | < 3s | stopwatch |
| Cycle Review | < 5s | stopwatch |
| Phase Review | < 10s | stopwatch |

**Constraints:**
- Sem LLM (zero chamadas)
- Sem embeddings
- Sem charts interativos (apenas ASCII em markdown)
- Offline (zero network)

---

## 7. Edge Cases

### 7.1. Semana sem dados

- Se 0 dias registrados: report mostra "Sem dados nesta semana"
- Se 1-6 dias registrados: report parcial com aviso

### 7.2. Regimes inconsistentes

- Se regime_predicted ≠ regime_actual: warning amarelo
- Conta como "regime_drift_count" para revisão

### 7.3. Pomodoros incompletos

- Pomodoros `interrupted` contam como yield negativo no cálculo
- Pomodoros `skipped` são ignorados (não contam para yield)

---

## 8. Cross-refs

- [`../planning/CLUSTER_PLAN_BRD.md`](../planning/CLUSTER_PLAN_BRD.md) — Business Requirements
- [`../planning/CLUSTER_PLAN_DATA_MODEL.md`](../planning/CLUSTER_PLAN_DATA_MODEL.md) — Schema
- [`../planning/CLUSTER_PLAN_CLI_SPEC.md`](../planning/CLUSTER_PLAN_CLI_SPEC.md) — CLI
- [`spec-cluster-plan-pipelines.md`](spec-cluster-plan-pipelines.md) — Pipelines (algoritmos)
- [`spec-cluster-plan-inputs.md`](spec-cluster-plan-inputs.md) — Inputs
- [`../../CLUSTER_PLAN.md §3.5`](../../CLUSTER_PLAN.md) — Templates de review (referência)
- [`../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md`](../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md) — Algoritmos

---

*spec-cluster-plan-reports.md — v1.0 — 2026-06-05 — Formato dos reports para Cluster PLAN*
