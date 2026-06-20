# PRD: Time-Blocks + Break Calculator + Context Switch + Journal Segmenter

**Version:** 1.0.0
**Date:** 2026-06-07
**Status:** Draft → Implementation Complete

> **Standalone Memory Machine** — Especificação autônoma do subdomínio time-blocks
> e reflexão por período. Cobre: TimeBlock (entrada/saída grossa),
> BreakCalculator (descanso entre blocos), ContextSwitch (overhead PAV
> entre períodos), JournalSegmenter (relatório NL por período).
> **Sem pomodoro** — pomodoros são contrato plug-in para integração
> futura com Timewarrior (ver `core/pomodoro_machine.py`).

---

## 1. Propósito

Este subdomínio implementa a **camada numérica primária** do
time-blocks e a **camada de reflexão** do journal:

1. **TimeBlock** (entidade): registro bruto de entrada/saída.
2. **BreakCalculator** (core): calcula descanso entre blocos.
3. **ContextSwitch** (core): estima overhead PAV entre períodos.
4. **JournalSegmenter** (core): segmenta journal por período e renderiza relatório NL.

**Sem pomodoro, sem LLM, sem NLP** — apenas aritmética + funções algorítmicas.

## 2. Modelos Pydantic

### TimeBlock (entidade, em `entities/time_block.py`)

```python
class TimeBlock(BaseModel):
    id: UEID  # e.g., "tbl_manha_focus"
    label: str  # e.g., "morning focus"
    start: datetime
    end: datetime
    period: Period  # MANHA, TARDE, NOITE
    routine_id: UEID | None
    notes: str
    created_at: datetime
    # Computed
    duration_minutes: int
    overlaps_period: bool
    has_routine_link: bool
```

### JournalEntry (entidade, em `entities/journal.py`)

```python
class JournalEntry(BaseModel):
    id: UEID
    date: date
    entry_text: str  # free-form markdown
    periods_covered: set[Period]
    routines_completed: list[UEID]
    desvios: list[str]
    licoes_aprendidas: list[str]
    energia_nivel: int | None  # 1-10
    foco_nivel: int | None  # 1-10
    pomodoros_completos: int  # 0-12
    humor_morning: int | None  # 1-5
    humor_evening: int | None  # 1-5
    created_at: datetime
    updated_at: datetime | None
```

## 3. Core Logic

### 3.1. BreakCalculator

**Propósito:** Calcular descanso (wall-clock) entre `TimeBlock`s consecutivos.

**Fórmula:**
```python
break_minutes(prev, next_) = max(0, (next_.start - prev.end) / 60s)
```

**Edge cases:**
- Overlap (prev.end > next_.start): registrado como `is_overlap=True` com
  `overlap_minutes = (prev.end - next_.start) / 60s`. Tolerância: 0.5 min.
- Overlap > tolerance: `ValueError`.
- Input fora de ordem: ordenado por `start` antes do cálculo.

**Outputs:**
- `BreakInfo(from_block_id, to_block_id, break_minutes, is_overlap, overlap_minutes)`
- `BreakStatistics(total_break_minutes, mean_break_minutes, max_break_minutes, min_break_minutes, break_count, overlap_count)`

### 3.2. ContextSwitch

**Propósito:** Estimar overhead de context switch baseado em PAV §3.

**Matriz canônica (em minutos):**

| From → To | MANHÃ | TARDE | NOITE |
|:---------:|:-----:|:-----:|:-----:|
| **MANHÃ** | 5 (within) | 30 (canonical) | 60 (skip) |
| **TARDE** | 45 (backward) | 5 (within) | 20 (canonical) |
| **NOITE** | 45 (severe) | 30 (backward) | 5 (within) |

**Fórmula Net Rest:**
```python
net_rest = max(0, gross_break - context_switch_overhead(from, to))
```

**Severidade:**
- MINIMAL (within-period): 5min
- LOW (forward canonical): 20-30min
- MEDIUM (backward): 30-45min
- HIGH (skip): 60min
- SEVERE (reverse sleep): 45min

### 3.3. JournalSegmenter

**Propósito:** Segmentar `JournalEntry` por período + renderizar relatório NL (PT-BR).

**Algoritmo:**
1. Se `periods_covered` é não-vazio, usar apenas esses períodos.
2. Split text por marker PT-BR (`Manhã:`, `Tarde:`, `Noite:`) como
   prefixo de linha. Suporta também inglês (`morning:`, `afternoon:`,
   `evening:`).
3. Texto sem marker → MANHÃ (default).
4. Cada segmento herda `energia_nivel`, `foco_nivel`,
   `pomodoros_completos` do journal global.

**Output:**
- `JournalSegment(period, text, energia_nivel, foco_nivel, pomodoros_completos)`
- `JournalReport(date, segments, full_text)`
- `render_period_summary(segment) -> str` (uma linha)
- `render_natural_language_report(report) -> str` (markdown completo)

## 4. Interfaces (CLI — Sprint 7)

```bash
# TimeBlocks
operational block start --label "morning focus" --period MANHA
operational block stop [block_id]
operational block list [--date YYYY-MM-DD]
operational block breaks [--date YYYY-MM-DD]  # calcula break_minutes

# Journal
operational journal log --date YYYY-MM-DD --text "Manhã: ..."
operational journal show [date]
operational journal week  # relatório semanal em NL
```

## 5. Test Strategy

| Test File | Tests | Coverage |
|:----------|------:|---------:|
| `test_break_calculator.py` | 33 | 100% |
| `test_context_switch.py` | 27 | 89.6% |
| `test_journal_segmenter.py` | 17 | 97.1% |

**Property-based tests (Sprint 8):**
- net_rest_minutes = max(0, gross_break - overhead) (always non-negative)
- compute_breaks produces len(blocks) - 1 elements
- compute_break_statistics.total_break_minutes = sum of non-overlap breaks

## 6. Acceptance Criteria (110% DoD)

| # | Critério | Métrica |
|--:|:---------|:--------|
| 1 | TimeBlock com Pydantic strict | 100% validators |
| 2 | BreakCalculator idempotente | 2 runs = mesmo output |
| 3 | ContextSwitch matrix completa | 9 pares cobertos |
| 4 | JournalSegmenter suporta PT-BR + EN | 100% markers detectados |
| 5 | Cobertura mínima | ≥95% por módulo |
| 6 | Latência CRUD | <100ms |
| 7 | Zero `except:` genérico | 0 ocorrências |
| 8 | Mypy --strict | 0 errors |
| 9 | Ruff ALL rules | 0 errors |

## 7. O que NÃO está aqui (out of scope)

- **Pomodoro** — contrato plug-in em `core/pomodoro_machine.py`. Não
  usado no time-blocks pipeline.
- **LLM/NLP** — sem classificação automática de journal.
- **Taskwarrior/Timewarrior integration** — diferida para Sprint futuro.
- **Roadmap cards** — premissa para sub-block tracking, ainda
  não implementadas.

## 8. References

- **PAV** (`vibe-ops/base/Produtividade Algorítmica Visual.md`):
  - §1 — Constants (HORARIO_*, POMODORO_*) [reference only, not used here]
  - §3 — Periods (MANHÃ/TARDE/NOITE) [used for context_switch]
  - §4 — Decision tree for wake-up
  - §9 — Pomodoro state machine [reference only, not used here]
  - §10 — Dashboard + journal fields
- **PRD-05** (`vibe-ops/planning/PRD-05-metrics-health.md`):
  - DailyLog, SleepRecord, EnergyReading (consumed by other clusters)
- **Sprint 2A entities** — TimeBlock, JournalEntry
- **Sprint 3B reframing** — `core/pomodoro_machine.py` as plug-in contract
- **Sprint 4B** — PolicyEngine, Consolidator (downstream consumers)

## 9. Change Log

| Version | Date | Changes |
|:--------|:-----|:--------|
| 1.0.0 | 2026-06-07 | Initial PRD (Standalone Memory Machine) |
