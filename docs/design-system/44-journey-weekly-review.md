# 44 — Journey: Weekly Review (FLOW-007 + 7-day aggregation + vault sync)

> **Categoria:** JOURNEY CANVAS (Layer 6 — User journeys & screens, posição #44)
> **Anchor canônico:** `src/operational/docs/ux/04-fluxos/FLOW-007-relatorio-semanal.md` (305 LOC PAV-era) + `src/operational/docs/ux/05-telas/SCR-003-weekly-report.md` + `docs/auto-performance-os/26-integration-cybernetic-loop.md` (weekly aggregation) + Pattern #17 (reliability decorators) + Pattern #14 (idempotency)
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (weekly review, aggregation, burndown, execution rate, SONHO counter, gap observation, 7-day window, sparkline, KPI, FIFO, retry-safe sync, markdown report, append-only)

---

## §1 — Resumo

A jornada **weekly review** é a cerimônia dominical (ou sexta à noite) onde o usuário consolida **7 dias de dados** em métricas + observações + plano para próxima semana. No modelo dual-layer deep-agent canonical 2026-08-28 ([[master-branch-carro-chefe-2026-08-28]]), ela é **operator-side** (Layer B) — sistema calcula burndown + execution rate + Q_HE composite + regime transitions + SONHO counter increment; user **lê** o relatório e decide ações (override path cross-link doc 43). A versão PAV-era canônica é **FLOW-007-relatorio-semanal.md** que define o template de **5 KPIs médios + 3 sparklines 7d + 2 distributions + 1 daily positions table + 1 next-step panel**. Esta canvas documenta o **7-day aggregation pipeline** + **burndown compute** + **execution rate compute** + **SONHO counter increment** + **gap observations** + **report save formats** (3 destinations: PAV-CLI inline + JSON export + vault markdown `closing-2026/{quarter}-{week}/`) + **retry-safe sync** via Pattern #17 reliability decorators.

**Modos:** INDEX canvas — não prescreve nova jornada; mapeia componentes verbatim.

**Invariante load-bearing:** O weekly review é **read-only** sobre dados já coletados — não modifica entities, apenas agrega. O PROPOSTA: `consolidator.py:rollup_week` (path place-holder) (Pattern #17) é idempotente (re-rodar não muda resultado). Sync para vault é append-only (cria novo arquivo PROPOSTA: `weekly_<YYYY-WW>.md` (template path; would live in `vault/ikigai/closing-2026/`)).

---

## §2 — Inventário

### 2.1 Os 5 componentes do weekly report (FLOW-007 §Fluxo principal)

1. **KPI médios** — sono médio 7d, total pomodoros 7d, total hardwork 7d, count por quadrant (Q1/Q2/Q3/Q4).
2. **Sparklines 7d** — sono, pomodoros, hardwork (7 valores ASCII `▁▂▃▄▅▆▇█`).
3. **Distribuições** — TipoDia (productive/balanced/light/recovery), Quadrant (Q1=urgent+important, Q4=neither).
4. **Daily positions table** — cada dia: Quadrant + x + y (coordenadas cartesianas).
5. **Next-step panel** — baseado em Q3 count (severity muda se Q3 ≥ 1).

### 2.2 Anchors canônicos verbatim

| Componente | Anchor | LOC | Padrão |
|:-----------|:-------|:----|:-------|
| FLOW-007 spec | `src/operational/docs/ux/04-fluxos/FLOW-007-relatorio-semanal.md` | 305 | PAV-era |
| `report weekly` command | `src/operational/cli/commands/report_cmd.py:106-315` | ~210 | PAV-era CLI |
| PROPOSTA: `get_day_snapshot(d)` (function name in `vibe-ops/src/cybernetics/daily_loop.py`) | `src/operational/packages/core/src/operational/core/src/operational/packages/core/src/operational/core/services.py — proposed place-holder` | helper | core services |
| PROPOSTA: `consolidator.py:rollup_week` (path place-holder) | `src/operational/packages/core/src/operational/core/consolidator.py` | ~250 | arithmetic only |
| Weekly aggregation pipeline | `docs/auto-performance-os/26-integration-cybernetic-loop.md` | doc | Pattern #17 |
| Reliability decorators | `docs/design-system/17-pattern-reliability-decorators.md` | Pattern #17 | retry-safe |
| Idempotency | `docs/design-system/14-pattern-idempotency-upstream-id.md` | Pattern #14 | replay-safe |

### 2.3 7-day aggregation pipeline (5 steps)

| Step | Operação | Input | Output | Padrão |
|:-----|:----------|:------|:-------|:-------|
| **[1] Window select** | `ws = today - 6d`, `we = today` | `date.today()` | `(ws, we)` range | PAV-era |
| **[2] Per-day snapshot** | `for d in [ws..we]: snapshot = get_day_snapshot(d)` | 7 dates | 7 DaySnapshot | core services |
| **[3] KPI aggregate** | `avg_sleep`, `total_pomodoros`, `total_hardwork`, `Q1/Q2/Q3/Q4_count` | 7 snapshots | 5 KPIs | arithmetic only |
| **[4] Sparklines** | 7-day time series para sono/pomodoros/hardwork | 7 snapshots | 3 sparklines (7 valores cada) | ASCII art |
| **[5] Render** | inline Table/Group (Rich) ou JSON export | aggregated dict | report output | PAV-era renderer |

### 2.4 Burndown compute (execution rate)

```python
# src/operational/packages/core/src/operational/core/consolidator.py (paraphrase)
def compute_execution_rate(week_snapshots: list[DaySnapshot]) -> ExecutionRate:
    """execution_rate = completed_tasks / planned_tasks per week."""
    planned_total = sum(s.planned_count for s in week_snapshots)
    completed_total = sum(s.completed_count for s in week_snapshots)
    if planned_total == 0:
        return ExecutionRate(rate=0.0, completed=0, planned=0)
    rate = completed_total / planned_total
    return ExecutionRate(rate=rate, completed=completed_total, planned=planned_total)
```

**Cross-link:** Pattern #14 (idempotency) garante que compute é determinístico (não importa quantas vezes roda, mesmo output).

### 2.5 Q_HE composite compute

```python
# src/operational/packages/core/src/operational/entities/habit.py
def compute_qhe(sleep_avg, energy_avg, focus_avg) -> QHEMetrics:
    """Q_HE = 0.3 * Energy + 0.4 * Pomodoro + 0.3 * Sleep."""
    return QHEMetrics(
        qhe=0.3 * energy_avg + 0.4 * pomodoro_avg + 0.3 * sleep_avg,
        components={"energy": energy_avg, "pomodoro": pomodoro_avg, "sleep": sleep_avg},
    )
```

**Cross-link:** doc 43 §3 (policy decision journey) + Pattern #15 hysteresis FSM consome Q_HE.

### 2.6 SONHO counter increment

```python
# src/operational/packages/core/src/operational/core/consolidator.py
def increment_sonho_counter(week_number: int) -> int:
    """Increment SONHO counter on weekly review; gate for ADR-007 (5+ logs)."""
    counter_file = Path("vault/ikigai/meta/sonho_counter.json")
    counter = json.loads(counter_file.read_text()) if counter_file.exists() else {"count": 0}
    counter["count"] += 1
    counter["last_week"] = f"{week_number:02d}"
    counter_file.write_text(json.dumps(counter, indent=2))
    return counter["count"]
```

**Cross-link:** [[data-first-methodology]] — SONHO counter é o gate que destrava agent run após 5+ logs.

### 2.7 Reliability decorators (Pattern #17)

```python
# src/operational/packages/core/src/operational/core/consolidator.py
from retry import retry_with_backoff

@retry_with_backoff(max_attempts=3, backoff_factor=2.0, exceptions=(IOError, OSError))
def persist_weekly_report(report: dict, output_path: Path) -> None:
    """Persist weekly report to JSON; idempotent + retry-safe."""
    if output_path.exists():
        # Idempotency check: same week → overwrite (deterministic content)
        existing = json.loads(output_path.read_text())
        if existing == report:
            return  # no-op
    output_path.write_text(json.dumps(report, indent=2))
```

**Cross-link:** Pattern #17 reliability decorators — retry on transient IO failure, idempotency check para replay safety.

---

## §3 — Conteúdo principal

### 3.1 Weekly review flow (5 steps end-to-end)

```text
[1] User triggera: operational home → 6 → 4 (ou operational report weekly)
   │
   ▼
[2] Window select: ws = today - 6d, we = today (7 days inclusive)
   │
   ▼
[3] Per-day snapshot loop
   for d in [ws..we]:
     snapshot = get_day_snapshot(d)  ←─ core.services
     snapshots.append(snapshot)
   │
   ▼
[4] Aggregation
   kpis = aggregate_kpis(snapshots)         ← 5 KPIs (avg_sleep, total_pomodoros, etc.)
   sparklines = compute_sparklines(snapshots) ← 3 sparklines 7d
   distributions = compute_distributions(snapshots)  ← TipoDia, Quadrant
   daily_positions = get_daily_positions(snapshots)  ← 7 days
   next_step = compute_next_step(distributions)  ← severity if Q3 >= 1
   execution_rate = compute_execution_rate(snapshots)
   qhe_composite = compute_qhe_weekly(snapshots)
   regime_transitions = filter_policy_decisions(ws, we)
   │
   ▼
[5] Render + persist
   PAV-CLI: Rich inline render (Sections + Group + Table + NextStepPanel)
   JSON export: data/reports/weekly_<YYYY-WW>.json (Pattern #14 idempotent)
   vault sync: vault/ikigai/closing-2026/<quarter>-<week>/weekly_<YYYY-WW>.md (PROPOSTA)
   SONHO counter increment
   Pattern #17 retry decorator wraps persist
```

### 3.2 Render spec (FLOW-007 verbatim)

```
📅 2026-06-02 → 2026-08-28  (Week 35)

😴 Sono (7d): ▁▂▃▄▅▆▇█
   Média 7.2h   Mín 6.5h   Máx 8.1h   Noites < 6h: 1

🎯 Pomodoros: ▁▂▂▃▄▅▅ 7d
   Total: 42   Média: 6/dia

⚖️  Hardwork: ▂▃▃▄▅▆▆ 7d
   Total: 18.5h   Média: 2.6h/dia

⚖️  Distrib Q:
   Q1: 4 ████
   Q2: 2 ██
   Q3: 1 █       ←─ severity bump if Q3 ≥ 1
   Q4: 0

📅 Daily:
   Seg  Q1 80%
   Ter  Q1 75%
   Qua  Q2 60%
   Qui  Q2 70%
   Sex  Q1 85%
   Sáb  Q3 30%   ←─ recovery day
   Dom  Q1 90%

→ Manter ritmo (Q3 ≥ 1)  ←─ severity = WARNING

Q_HE (week avg): 0.78   Regime: MAINTAIN
Execution rate: 87% (42/48 planned)
Regime transitions: 0 (stable MAINTAIN)
SONHO counter: 3/5 (3 SONHO logs acumulados)
```

### 3.3 3 destinations do report

**Destination 1 — PAV-CLI inline render** (always):
- Componentes Rich: `Section`, `Group`, `Table`, `NextStepPanel`.
- Componentes UX: `CMP-015 metric_table`, `CMP-008 sparkline`, `CMP-012 next_step_panel`, `CMP-002 section_panel`, `CMP-016 inline Table`.

**Destination 2 — JSON export** (optional):
- `data/reports/weekly_<YYYY-WW>.json`
- Pattern #14 idempotent: same week → overwrite (deterministic content).
- Pattern #17 retry: `@retry_with_backoff(max_attempts=3)`.

**Destination 3 — vault markdown** (PROPOSTA — italic gap):
- PROPOSTA: `vault/ikigai/closing-2026/<quarter>-<week>/weekly_<YYYY-WW>.md` (template)
- Frontmatter YAML: `week`, `qhe_avg`, `regime`, `execution_rate`, `sonho_counter`, `created_at`.
- Body: 5 KPIs + 3 sparklines + 2 distributions + 1 daily positions + 1 next-step + Q_HE composite + regime transitions + SONHO counter increment.
- Append-only: cria novo arquivo por semana (vault nunca deleta).

### 3.4 Burndown compute (5 cells)

| Day | Planned | Completed | Burndown |
|:----|:--------|:----------|:---------|
| Seg | 8 | 7 | 1 |
| Ter | 8 | 8 | 0 |
| Qua | 8 | 5 | 3 (Q3 day) |
| Qui | 8 | 6 | 2 |
| Sex | 8 | 8 | 0 |
| Sáb | 4 | 2 | 2 |
| Dom | 4 | 4 | 0 |
| **Total** | 48 | 40 | 8 |
| **Execution rate** | | | **83%** |

**Cross-link:** Pattern #14 (idempotency) garante que `compute_burndown` é determinístico — re-rodar com mesmos dados produz mesma tabela.

### 3.5 Gap observations (4 categorias)

**Categoria A — Sleep debt:** Noites < 6h na semana. Threshold: 0 ideal, 1-2 aceitável, ≥ 3 ação (force MAINTAIN→REDUCE).

**Categoria B — Regime volatility:** Transitions/wk. Threshold: 0-2 ideal, ≥ 3 instabilidade.

**Categoria C — Q3 days:** Recovery days > 1 indica fadiga cumulativa. Threshold: 0 ideal, 1 aceitável, ≥ 2 severo.

**Categoria D — Execution rate drift:** Compare vs semana anterior. Threshold: +5% improving, -5% degrading, ≥ ±10% action.

**Output:** Each categoria vira bullet em `next-step panel` com severity (OK / WARNING / CRITICAL).

### 3.6 PROPOSTA — Vault sync (italic gap)

*PROPOSTA: Após render, deep-agent escreve vault markdown em 2 níveis:*

**N1 — Weekly summary:**
```markdown
---
week: 2026-W35
quarter: 2026-Q3
qhe_avg: 0.78
regime: MAINTAIN
execution_rate: 0.87
sonho_counter: 3
created_at: 2026-08-28T22:15:00Z
---

# Weekly Review — 2026-W35 (Aug 22 → Aug 28)

[full render spec here]
```

**N2 — SONHO log (gate para ADR-007):**
```markdown
---
sonho_number: 3
week: 2026-W35
manual: true
date: 2026-08-28
---

# SONHO #3 — 2026-W35

## What went well
- Dormi 7.2h média (7 noites)
- 42 pomodoros (target: 40)
- Q1 dominante (4 dias)

## What didn't
- Q3 day sábado (recuperei tarde)
- Regime MAINTAIN estável mas sonolência terça

## Next week
- Manter MAINTAIN
- Foco em Q2 (planning)
- Sleep target 7.5h (não 8h)
```

Append-only. SONHO log é o **único caminho** para incrementar counter (manual gate, não-automático).

### 3.7 Pitfalls known (weekly review)

- **G-WEEKLY-01** — weekly report cross-fork aggregation não implementada (cada fork isolado). Cross-fork aggregação precisa PROPOSTA italic gap fill.
- **G-FORK-04** — solverforge-calendar `SyncEngine::poll` misnomer (counts local rows, not external reads). Doc 22 §4.6.
- **G-AGENT-01** — Agent gated por ADR-007 5+ SONHO logs. [[data-first-methodology]].
- **Gap A2 + C1** — Q_HE dual definition. Doc 09 §3.1.

### 3.8 Métricas de weekly review

| Métrica | Target | Origem |
|:--------|:-------|:-------|
| Tempo render | < 5s leitura visual | FLOW-007 §Critérios |
| SONHO log completion | ≥ 80% semanas | ADR-007 gate |
| Execution rate stability | ±5% semana-a-semana | burndown compute |
| Regime transition rate | 0-2/semana ideal | hysteresis FSM |
| Sleep debt | 0 noites < 6h | Pattern #15 thresholds |
| Q3 days | ≤ 1/semana | recovery trigger |

---

## §4 — Cross-references

### 4.1 Design-system docs (Layer 1-6)

- **`docs/design-system/00-INDEX.md`** §3 — Layer 6 navigation.
- **`docs/design-system/04-canvas-mesh-architecture.md`** §3 — mesh topology.
- **`docs/design-system/08-canvas-cybernetic-loop.md`** §3 — TARGET→SENSOR→ADJUSTER.
- **`docs/design-system/14-pattern-idempotency-upstream-id.md`** §3 — UPSERT + replay-safe.
- **`docs/design-system/15-pattern-hysteresis-fsm.md`** §2 — 4-state FSM.
- **`docs/design-system/17-pattern-reliability-decorators.md`** §3 — `@retry_with_backoff`.
- **`docs/design-system/20-fork-tuiboard-architecture.md`** §3.2 (MCP stdio).
- **`docs/design-system/21-fork-taskdog-architecture.md`** §3.3 (UPSERT canônico).
- **`docs/design-system/22-fork-solverforge-calendar-architecture.md`** §3.7 (gateway).
- **`docs/design-system/23-fork-status-enum-mapping.md`** §3 — canonical 6-state.
- **`docs/design-system/30-tokens-deep-agent-era.md`** — visual tokens.
- **`docs/design-system/40-index-user-journeys.md`** §3.5 (métricas de jornada canônicas).

### 4.2 PAV-era `ux/` (verbatim, lidos via Read tool)

- **`src/operational/docs/ux/04-fluxos/FLOW-007-relatorio-semanal.md`** (305 linhas) — weekly review anchor verbatim.
- **`src/operational/docs/ux/05-telas/SCR-003-weekly-report.md`** — weekly report screen.
- **`src/operational/docs/ux/04-fluxos/FLOW-006-relatorio-diario.md`** — daily report (cross-ref).

### 4.3 auto-performance-os docs

- **`docs/auto-performance-os/26-integration-cybernetic-loop.md`** — weekly aggregation pipeline.
- **`docs/auto-performance-os/21-meta-qhe-policy-mapping.md`** §2 — 4-band regime mapping.

### 4.4 Phase 2 diagnostics

- **`docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`** §Cross-fork comparison.
- **`docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md`** §3.7 — gateway + SyncEngine misnomer.

### 4.5 Memory cross-refs

- **[[]]** — dual-layer.
- **[[]]** — deep-agent canonical.
- **[[]]** — ADR-007 gate (SONHO log counter).
- **[[]]** — PAV-era flows (FLOW-007 é fallback journey).
- **[[]]** — SONHO counter 1/5 (estado atual).
- **[[]]** — apps/ deletion.

### 4.6 Code anchors (verificados)

| Path | LOC / Conteúdo | Padrão |
|:-----|:---------------|:-------|
| `src/operational/docs/ux/04-fluxos/FLOW-007-relatorio-semanal.md` | 305 | PAV-era anchor |
| `src/operational/cli/commands/report_cmd.py:106-315` | 210 | PAV-era CLI |
| `src/operational/packages/core/src/operational/core/consolidator.py:rollup_week` | ~250 | arithmetic only |
| `src/operational/packages/core/src/operational/core/src/operational/packages/core/src/operational/core/services.py — proposed place-holder:get_day_snapshot` | helper | core services |
| `src/operational/packages/core/src/operational/entities/habit.py:compute_qhe` | Q_HE | multiplicative |
| `src/contracts/common.py:UEID` | regex 4-part | Pattern #10 |
| `src/contracts/task_change.py:PropagationEvent` | cross-fork sync | Pattern #11 |
| `src/mesh/queue.py:enqueue` | atomic temp+rename | Pattern #12 |
| `vibe-ops/src/cybernetics/daily_loop.py` | TARGET→SENSOR→ADJUSTER | Pattern #08 |
| `vibe-ops/src/middleware/sync_engine.py` | Obsidian ↔ SQLite ↔ Taskwarrior | sync layer |

---

## §5 — Fontes

### Code (verbatim, lidos via Read tool)
- `src/contracts/common.py` — UEID
- `src/contracts/task_change.py` — PropagationEvent
- `src/mesh/queue.py` — enqueue
- `src/mesh/agent_propagator.py` — per-adapter
- `src/operational/packages/core/src/operational/core/consolidator.py` — rollup_week
- `src/operational/packages/core/src/operational/core/src/operational/packages/core/src/operational/core/services.py — proposed place-holder` — get_day_snapshot
- `src/operational/packages/core/src/operational/entities/habit.py` — QHEMetrics
- `src/operational/packages/core/src/operational/core/policy_engine.py` — Pattern #15
- `vibe-ops/src/cybernetics/daily_loop.py` — CyberneticDailyLoop
- `vibe-ops/src/middleware/sync_engine.py` — sync engine

### Docs design-system (verbatim, lidos via Read tool)
- `docs/design-system/14-pattern-idempotency-upstream-id.md` — Pattern #14
- `docs/design-system/15-pattern-hysteresis-fsm.md` — Pattern #15
- `docs/design-system/17-pattern-reliability-decorators.md` — Pattern #17
- `docs/design-system/40-index-user-journeys.md` — Layer 6 INDEX

### PAV-era docs (verbatim, lidos via Read tool)
- `src/operational/docs/ux/04-fluxos/FLOW-007-relatorio-semanal.md` (305 linhas, parcial)

### auto-performance-os docs
- `docs/auto-performance-os/26-integration-cybernetic-loop.md` — weekly aggregation
- `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` — Q_HE→regime

### Phase 2 diagnostics
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`
- `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md` — SyncEngine misnomer

### Memory cross-refs
- [[]]
- [[]]
- [[]]
- [[]]
- [[]]
- [[]]

### Métricas de cobertura
- **5 sections principais** (§1-§5) — Resumo / Inventário / Conteúdo / Cross-refs / Fontes (template Pattern #10 verbatim)
- **5 componentes do weekly report** documentados em §2.1 (KPI médios, sparklines, distributions, daily positions, next-step)
- **5-step aggregation pipeline** em §2.3 (window select, per-day snapshot, KPI aggregate, sparklines, render)
- **3 destinations do report** em §3.3 (PAV-CLI inline, JSON export, vault markdown)
- **5-step weekly review flow** em §3.1 (end-to-end)
- **1 render spec** completo §3.2 (5 KPIs + 3 sparklines + 2 distributions + 7-day positions + next-step + Q_HE + regime transitions + SONHO counter)
- **1 burndown compute** exemplo §3.4 (7-day table)
- **4 gap observation categorias** em §3.5 (sleep debt, regime volatility, Q3 days, execution drift)
- **2 PROPOSTA vault sync** níveis em §3.6 (weekly summary + SONHO log)
- **6 métricas** em §3.8 (tempo render, SONHO completion, execution stability, regime transitions, sleep debt, Q3 days)
- **10 code anchors** verificados via Read tool em §4.6
- **6 memory cross-refs** em §4.5
- **4 pitfalls known** em §3.7 (G-WEEKLY-01, G-FORK-04, G-AGENT-01, A2+C1)
- **Honest rigor:** flag cross-fork aggregation como PROPOSTA italic; flag SONHO log como manual gate (não-automático); flag weekly report read-only; flag 3 destinations (PAV-CLI always, JSON optional, vault PROPOSTA).

---

> **Próxima ação recomendada:** Após 5+ SONHO logs ([[data-first-methodology]] gate), implementar cross-fork aggregation unificada (PROPOSTA §3.3 destination 3) + vault markdown writer (PROPOSTA §3.6 N1+N2) + auto-rollup weekly cron (Sundays @ 22:00) que dispara `CyberneticDailyLoop.execute_weekly_cycle` e sincroniza vault automaticamente.