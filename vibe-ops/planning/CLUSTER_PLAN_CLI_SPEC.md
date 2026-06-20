# CLUSTER PLAN — CLI Specification (Sprint 1)

> Especificação completa de comandos CLI para o Cluster PLAN.
> **AI-native**: cada comando tem `--json` flag, idempotência, e output determinístico.

---

## 1. Comandos Canônicos (Sprint 1)

### 1.1. `plan journal log --morning|--afternoon|--evening`

**Descrição:** Wizard interativo para registrar perguntas socráticas.

```bash
# Matinal
python -m life.cli plan journal log --morning [--date YYYY-MM-DD] [--json]

# Tarde
python -m life.cli plan journal log --afternoon [--date YYYY-MM-DD] [--json]

# Noite
python -m life.cli plan journal log --evening [--date YYYY-MM-DD] [--json]
```

**Args:**
- `--morning | --afternoon | --evening` (obrigatório, mutually exclusive)
- `--date YYYY-MM-DD` (opcional, default: hoje)
- `--json` (opcional, default: human-readable)

**Comportamento:**
1. Valida `--date` (não pode ser futuro, pode ser até 7d passado)
2. Valida se já existe `auto_indagacao(date, ritual_type=X)` → se sim, **atualiza** (idempotência)
3. Abre wizard com perguntas filtradas por ritual_type
4. Persiste em `auto_indagacao`
5. Calcula Q_HE + regime via `ikigai_meta_heuristics.md §1`
6. Persiste regime em `qhe_history`
7. Retorna JSON ou human-readable

**Output (--json):**
```json
{
  "date": "2026-06-05",
  "ritual_type": "morning",
  "qhe_at_moment": 0.78,
  "regime_predicted": "MAINTAIN",
  "ikigai_focus": "skill",
  "pomodoros_planned": 7,
  "updated_existing": false
}
```

**Output (human-readable):**
```
✓ Morning ritual logged for 2026-06-05
  Q_HE: 0.78 (MAINTAIN)
  IKIGAi focus: skill
  Pomodoros recommended: 7
```

**Edge cases:**
- Data futura: erro
- Data > 7d passada: erro
- Idempotência: re-execução ATUALIZA row existente (mensagem: "✓ Updated existing ritual")

### 1.2. `plan today`

**Descrição:** Mostra estado de hoje (rituais + regime + tasks).

```bash
python -m life.cli plan today [--json]
```

**Output (--json):**
```json
{
  "date": "2026-06-05",
  "regime": "MAINTAIN",
  "qhe": 0.78,
  "ikigai_focus": "skill",
  "wake_time_actual": "03:45",
  "rituals_done": {"morning": true, "afternoon": false, "evening": false},
  "pomodoros_planned": 7,
  "pomodoros_done": 3,
  "pomodoros_yield_pct": 42.8,
  "next_ritual": "afternoon",
  "wave_position": "7/15 (Mid-Wave tomorrow)"
}
```

### 1.3. `plan block start <name>`

**Descrição:** Inicia um bloco de tempo (morning/afternoon/evening).

```bash
python -m life.cli plan block start morning
python -m life.cli plan block start afternoon --ikigai skill
python -m life.cli plan block start evening --recover
```

**Args:**
- `<name>` (obrigatório: `morning | afternoon | evening | lunch | sleep`)
- `--ikigai <vector>` (opcional, default: skill)
- `--recover` (opcional, força regime RECOVER)
- `--json` (opcional)

**Comportamento:**
1. Cria `daily_routine` row (idempotente por date)
2. Registra `started_at` no `transition_ritual` (ritual_type=cold_start)
3. Retorna status

### 1.4. `plan block end`

**Descrição:** Fecha bloco atual.

```bash
python -m life.cli plan block end [--pomodoros-done N] [--json]
```

**Args:**
- `--pomodoros-done N` (opcional, registrado no `daily_routine`)
- `--json` (opcional)

**Comportamento:**
1. Fecha `transition_ritual` (ended_at, duration_minutes)
2. Atualiza `daily_routine.pomodoros_done`
3. Registra `transition_ritual` (ritual_type=warm_down ou shutdown)

### 1.5. `plan pomodoro start|--done|--interrupted`

**Descrição:** Lifecycle de pomodoro individual.

```bash
python -m life.cli plan pomodoro start [--block morning|afternoon|evening] [--json]
python -m life.cli plan pomodoro done [--task-ref <id>] [--type project|study|admin] [--energy-after 7] [--json]
python -m life.cli plan pomodoro interrupted [--count 2] [--reason "external notification"] [--json]
```

**Comportamento:**
- `start`: cria `pomodoro` row com status='running'
- `done`: fecha pomodoro, status='completed', calcula yield
- `interrupted`: fecha pomodoro, status='interrupted', registra count + reason

### 1.6. `plan ritual cold-start|--warm-down`

**Descrição:** Rituais de transição (separados de block start/end).

```bash
python -m life.cli plan ritual cold-start [--duration 5] [--checklist "fechar TW,abrir Obsidian"] [--json]
python -m life.cli plan ritual warm-down [--duration 10] [--json]
```

**Comportamento:**
- Persiste em `transition_ritual`
- Valida duration ≤ 5min (cold-start) ou ≤ 15min (warm-down)
- Se duração exceder: warning + flag para review

### 1.7. `plan sleep log`

**Descrição:** Registra janela de sono.

```bash
python -m life.cli plan sleep log --bedtime 20:30 --wake 03:45 --quality 8 [--interruptions 1] [--json]
```

**Comportamento:**
1. Valida: bedtime 18-21h, wake 3-5h (verde), 5-6h (amarelo), 6h+ (vermelho)
2. Calcula duration_hours + deficit_hours
3. Persiste em `sleep_window` (UNIQUE date)

### 1.8. `plan regime [--recover|--traverse|--show]`

**Descrição:** Gerencia regime (ver US-009, US-010).

```bash
python -m life.cli plan regime --show [--json]
python -m life.cli plan regime --recover [--auto] [--json]   # ativa RECOVER
python -m life.cli plan regime --traverse [--json]           # ativa TRAVERSE CHAOS
```

### 1.9. `plan report weekly|--monthly`

**Descrição:** Relatórios determinísticos.

```bash
python -m life.cli plan report weekly [--date YYYY-MM-DD] [--json]
python -m life.cli plan report monthly [--month YYYY-MM] [--json]
```

**Output (weekly, --json):**
```json
{
  "period": {"start": "2026-06-01", "end": "2026-06-07"},
  "summary": {
    "pomodoros_planned": 35,
    "pomodoros_done": 28,
    "yield_pct": 80.0,
    "days_pushed": 2,
    "days_maintain": 4,
    "days_recover": 1
  },
  "ikigai_avg": {
    "passion": 75.0,
    "skill": 78.0,
    "market": 65.0,
    "revenue": 71.0
  },
  "qhe_trend": [0.65, 0.70, 0.78, 0.82, 0.80, 0.75, 0.78],
  "transitions_total_minutes": 32
}
```

### 1.10. `plan wave review --mid|--end`

**Descrição:** Revisão de WAVE (US-005, US-006).

```bash
python -m life.cli plan wave review --mid [--wave-id WAVE-2026-Q2-1] [--json]
python -m life.cli plan wave review --end [--wave-id WAVE-2026-Q2-1] [--json]
```

### 1.11. `plan cycle review --end`

**Descrição:** Revisão de CYCLE (US-007).

```bash
python -m life.cli plan cycle review --end [--cycle-id CYCLE-2026-Q2-1] [--json]
```

### 1.12. `plan phase review --end`

**Descrição:** Revisão de PHASE (US-008).

```bash
python -m life.cli plan phase review --end [--phase-id PHASE-2026-H1] [--json]
```

### 1.13. `plan status [--qhe]`

**Descrição:** Status atual resumido.

```bash
python -m life.cli plan status [--qhe] [--json]
```

---

## 2. Convenções Globais

1. **Todo comando aceita `--json`** para output machine-readable
2. **Datas em ISO 8601** (`YYYY-MM-DD`)
3. **Horas em 24h** (`HH:MM`)
4. **Tempo em minutos** (inteiro) ou segundos (float)
5. **Cores**: 🟢 verde (3-5h), 🟡 amarelo (5-6h), 🔴 vermelho (6h+)
6. **Idempotência**: re-execução não cria duplicatas (UNIQUE constraints)
7. **Sem LLM**: zero chamadas a modelos generativos
8. **Offline**: zero dependência de network

---

## 3. Cross-refs

- [`CLUSTER_PLAN_BRD.md`](CLUSTER_PLAN_BRD.md) — Business Requirements
- [`CLUSTER_PLAN_DATA_MODEL.md`](CLUSTER_PLAN_DATA_MODEL.md) — Schema + Pydantic
- [`CLUSTER_PLAN_USER_STORIES.md`](CLUSTER_PLAN_USER_STORIES.md) — User stories
- [`../../CLUSTER_PLAN.md §7`](../../CLUSTER_PLAN.md) — CLI canônico anterior
- [`../../life-ops/life_tatics/cli.py`](../../life-ops/life_tatics/cli.py) — Typer base
- [`../../life-ops/life_tatics/Planning_notes.md`](../../life-ops/life_tatics/Planning_notes.md) — Constantes
- [`../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md`](../../life-ops/planner/ikigai_planning/ikigai_meta_heuristics.md) — Algoritmos

---

*CLUSTER_PLAN_CLI_SPEC.md — v1.0 — 2026-06-05 — CLI spec completa para Cluster PLAN*
