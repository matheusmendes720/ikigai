# 33 — Status Matrix Unified (6 Operational × 4 Regime = 24 Cells)

> **Categoria:** TOKENS (Layer 5 — Tokens & components, posição #33 — NEW canonical, consolidação)
> **Anchor canônico:** `src/operational/docs/ux/01-inventario/02-matriz-estados.md` (origem) + Pattern #15 hysteresis FSM + fork docs 20/21/22 + doc 23 status mapping
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (status, regime, FSM, hysteresis, PENDING, ACTIVE, DONE, BLOCKED, CANCELLED, ARCHIVED, PUSH, MAINTAIN, REDUCE, RECOVER, terminal escape, ANSI, fork adapter, cross-fork, idempotent, UEID, KPI, QHE)
> **Status:** Gap-fill de critical kind + consolidação (unifica 6×4 = 24 cells de estado × regime)

---

## §1 — Resumo

Este documento preenche o **gap #5** consolidado do design system ao unificar a **matriz 6×4 = 24 cells** que cruza **status operacional canônico** (Pattern #23 fork status cycle: `PENDING / ACTIVE / DONE / BLOCKED / CANCELLED / ARCHIVED`) com **regime de policy** (Pattern #15 hysteresis FSM: `PUSH / MAINTAIN / REDUCE / RECOVER`). O problema que esta matriz resolve é triplo: **(1)** status operacional (DONE, BLOCKED, etc.) é **ortogonal** a regime (PUSH, MAINTAIN, etc.) — uma task pode estar DONE em qualquer regime, e regime pode mudar independente de status. **(2)** Sem matriz unificada, cada fork (tuiboard, taskdog, solverforge-calendar) precisa adivinhar regras cross-fork: "se task está BLOCKED em regime REDUCE, eu preservo block? eu cancelo? eu forço done?" — divergência silenciosa entre forks. **(3)** Agente Deep precisa de regras determinísticas para propagação (`PropagationEvent(ueid, action, ...)` carrega status change, mas qual ação aplicar depende da cell matriz). A solução proposta é **uma única tabela 6×4** com 24 cells, cada uma com: **(a)** action rule (create/preserve/cancel/log/celebrate), **(b)** terminal escape code (ANSI color para renderização), **(c)** fork adapter sync trigger (qual adapter propaga mudança). A tabela é **estática** (não muda com SONHO logs) porque cruza dois contratos Pydantic canônicos (`TaskStatus` em `task.py` + `RegimeState` em `common.py:150-156`); o que vai evoluir com empirical data são os **thresholds internos** de QHE que disparam transições de regime, **não** a estrutura da matriz.

### 1.1 Por que status e regime são ortogonais

**Status operacional** é estado **do objeto** (a task em si): ela está pendente, ativa, done, bloqueada, cancelada, ou arquivada? Esse estado é **local à entity** — uma Task DONE continua sendo Task DONE independente do regime do dia.

**Regime de policy** é estado **do dia operacional** (decidido pelo hysteresis FSM): estamos em PUSH (alta intensidade), MAINTAIN (sustentação), REDUCE (carga reduzida), ou RECOVER (emergência)? Esse estado é **global ao dia** — afeta todas as tasks ativas, mas não muda status de tasks DONE.

**Cruzar os dois** é útil porque a **ação do agente** depende da combinação. Exemplo:
- Task PENDING × regime PUSH = "create task normally" (regime permite, status permite)
- Task DONE × regime RECOVER = "celebrate + log" (status terminal, regime de recuperação torna celebração um sinal de progresso)
- Task BLOCKED × regime REDUCE = "preserve block, lower load" (block é legítimo, regime já reduz carga automaticamente)
- Task ACTIVE × regime RECOVER = "force pause + escalate" (regime de emergência força interrupção)

### 1.2 Onde a matriz é consultada

A matriz é consultada em **3 pontos canônicos** do sistema:

1. **`src/mesh/agent_propagator.py`** — ao propagar `PropagationEvent(ueid, action, from_status, from_regime, to_status, to_regime)`, consulta matriz para decidir **fork adapter sync trigger** (qual adapter recebe evento).
2. **`src/ikigai/src/ikigai/core/heuristics/regime.py`** — ao computar regime transition, consulta matriz para decidir **action rule** (regime mudou → forçar status change? ou só log?).
3. **PROPOSTA: `src/operational/packages/core/src/operational/core/daily_consolidator.py` (path place-holder — actual file is `consolidator.py`; doc 33 referes here for canonical name)** — ao consolidar daily log, renderiza matriz 6×4 com terminal escape codes para visual audit.

---

## §2 — Inventário

### 2.1 Row dimensions (status operacional — 6 valores)

**Anchor:** Pattern #23 §2.1 + `src/contracts/task.py` (Task.done, TaskStatus).

| Row | Status | Significado | Terminal state? |
|:----|:-------|:------------|:----------------|
| 1 | `PENDING` | Task criada, aguardando início | Não |
| 2 | `ACTIVE` | Task em progresso (in_progress) | Não |
| 3 | `DONE` | Task concluída (completed) | Sim (terminal) |
| 4 | `BLOCKED` | Task impedida (blocked, requires unblock) | Não |
| 5 | `CANCELLED` | Task cancelada (cancelled,放弃) | Sim (terminal) |
| 6 | `ARCHIVED` | Task soft-deleted (archived, hidden) | Sim (terminal) |

### 2.2 Column dimensions (regime — 4 valores)

**Anchor:** Pattern #15 §2.1 + `src/contracts/common.py:150-156` `RegimeState` enum.

| Col | Regime | hardwork budget | Q_HE target |
|:----|:-------|:----------------|:-------------|
| 1 | `PUSH` | 4.0 h | 0.85 |
| 2 | `MAINTAIN` | 2.5 h | 0.65 |
| 3 | `REDUCE` | 1.5 h | 0.45 |
| 4 | `RECOVER` | 0.5 h | 0.25 |

### 2.3 Existing UX doc a consolidar

**Path atual:** `src/operational/docs/ux/01-inventario/02-matriz-estados.md` (conteúdo deve migrar para este doc).

**Estratégia:** criar `docs/design-system/SCR-002-matriz-estados.md` que importa este doc como referência, adicionar trailer SUPERSEDED ao arquivo antigo. Append-only preserved.

### 2.4 Existing fork docs cross-referenciar

| Fork doc | Cross-ref |
|:---------|:----------|
| `docs/design-system/20-fork-tuiboard-architecture.md` §3 | tuiboard renderiza matriz em view "audit" |
| `docs/design-system/21-fork-taskdog-architecture.md` §3 | taskdog SQLite trigger fires em cell transitions |
| `docs/design-system/22-fork-solverforge-calendar-architecture.md` §3 | solverforge-calendar UPI status field consome matriz |

---

## §3 — Conteúdo principal

### 3.1 Matriz 6×4 canônica (24 cells)

**Legenda:** ✓ = sync trigger; ✗ = no sync; ⏸ = preserve state; ⤴ = force transition; 🎉 = celebrate + log; 🔴 = escalate.

| Status \ Regime | **PUSH** | **MAINTAIN** | **REDUCE** | **RECOVER** |
|:----------------|:---------:|:------------:|:----------:|:-----------:|
| **PENDING** | ✓ create normally | ✓ create normally | ✓ create + warn "low-load day" | ⤴ force cancel (regime overrides) |
| **ACTIVE** | ✓ continue + boost | ✓ continue normally | ⏸ pause + reassess | ⤴ force pause + 🔴 escalate |
| **DONE** | 🎉 celebrate + log KPI-001 | 🎉 celebrate + log | 🎉 celebrate + log | 🎉 celebrate + log (extra: signal recovery progress) |
| **BLOCKED** | ⏸ preserve block + retry soon | ⏸ preserve block + retry normal | ⏸ preserve block + lower load | ⏸ preserve block + 🔴 escalate blocker |
| **CANCELLED** | ✗ no sync (terminal) | ✗ no sync (terminal) | ✗ no sync (terminal) | ✗ no sync (terminal) |
| **ARCHIVED** | ✗ no sync (terminal) | ✗ no sync (terminal) | ✗ no sync (terminal) | ✗ no sync (terminal) |

### 3.2 Action rules per cell (detalhamento)

**Row PENDING:**

| Regime | Rule | Justificativa |
|:-------|:-----|:--------------|
| PUSH | Agent cria task normalmente; fork adapters (cli/taskdog/solverforge-calendar) recebem `PropagationEvent(action=create)` | Regime PUSH = alta intensidade; tasks novas bem-vindas |
| MAINTAIN | Agent cria task normalmente; sem warning | Regime MAINTAIN = sustentação; tasks novas permitidas |
| REDUCE | Agent cria task + warning notification "low-load day, prioritize existing" | Regime REDUCE = carga reduzida; tasks novas devem ser excepcionais |
| RECOVER | Agent **força cancel** de task criada (override); fork adapters recebem `PropagationEvent(action=cancel)` + reason "regime_override" | Regime RECOVER = emergência; criar task nova viola regime |

**Row ACTIVE:**

| Regime | Rule | Justificativa |
|:-------|:-----|:--------------|
| PUSH | Agent continua normalmente; fork adapters mantêm `status=in_progress` | Regime PUSH permite alta intensidade em tasks ativas |
| MAINTAIN | Agent continua normalmente; sem mudança | Regime MAINTAIN = sustentação; tasks ativas em ritmo normal |
| REDUCE | Agent **pausa** task + registra "paused_due_to_reduce"; fork adapters recebem `PropagationEvent(action=pause)` | Regime REDUCE = carga reduzida; tasks ativas em pausa para liberar tempo |
| RECOVER | Agent **força pause** + **escalation** para user (notification "interromper AGORA"); fork adapters recebem `PropagationEvent(action=force_pause)` + severity=CRITICAL | Regime RECOVER = emergência; tasks ativas devem parar imediatamente |

**Row DONE:**

| Regime | Rule | Justificativa |
|:-------|:-----|:--------------|
| PUSH | Agent celebra (UI toast "✓ done!") + log KPI-001 (QHE mean); fork adapters recebem `PropagationEvent(action=log_done)` | DONE em PUSH = contribuição visível |
| MAINTAIN | Agent celebra + log | DONE em MAINTAIN = sustentação mantida |
| REDUCE | Agent celebra + log | DONE em REDUCE = progresso apesar de carga reduzida |
| RECOVER | Agent celebra **+ log especial** "recovery_progress" (sinaliza ao hysteresis FSM que usuário está melhorando) | DONE em RECOVER = indicador crítico de progresso (recovery é celebração amplificada) |

**Row BLOCKED:**

| Regime | Rule | Justificativa |
|:-------|:-----|:--------------|
| PUSH | Agent preserva block + retry soon (próximo sync cycle); fork adapters mantêm `status=blocked` | BLOCKED em PUSH = block legítimo; regime não interfere |
| MAINTAIN | Agent preserva block + retry normal | BLOCKED em MAINTAIN = block legítimo |
| REDUCE | Agent preserva block + lower load (regime já reduz carga automaticamente, block fica intacto) | BLOCKED em REDUCE = block + carga reduzida = compõe |
| RECOVER | Agent preserva block + **escalation** "blocker impedindo recovery"; fork adapters recebem `PropagationEvent(action=escalate_blocker)` | BLOCKED em RECOVER = block impede recuperação → escalar |

**Row CANCELLED (terminal):**

| Regime | Rule | Justificativa |
|:-------|:-----|:--------------|
| ALL | No sync (status terminal); fork adapters early-return on `status=cancelled` propagation | CANCELLED é sink; não propaga |

**Row ARCHIVED (terminal):**

| Regime | Rule | Justificativa |
|:-------|:-----|:--------------|
| ALL | No sync (status terminal); fork adapters early-return on `status=archived` propagation | ARCHIVED é sink; não propaga |

### 3.3 Terminal escape codes per cell

**Renderer canônico (ANSI 256-color para TUI ratatui ou Python textual):**

```python
# Definição de cores por status × regime
MATRIX_COLORS = {
    # Row PENDING
    ("PENDING", "PUSH"):      "\x1b[38;5;42m",   # bright green (T-color-scr-push dark)
    ("PENDING", "MAINTAIN"):  "\x1b[38;5;67m",   # bright blue (T-color-scr-maintain dark)
    ("PENDING", "REDUCE"):    "\x1b[38;5;214m",  # bright orange (warning)
    ("PENDING", "RECOVER"):   "\x1b[1;38;5;196m", # bold bright red (force cancel)
    # Row ACTIVE
    ("ACTIVE", "PUSH"):       "\x1b[38;5;42m",   # bright green
    ("ACTIVE", "MAINTAIN"):   "\x1b[38;5;67m",   # bright blue
    ("ACTIVE", "REDUCE"):     "\x1b[38;5;214m",  # orange (paused)
    ("ACTIVE", "RECOVER"):    "\x1b[1;38;5;196m", # bold red (force pause)
    # Row DONE
    ("DONE", "PUSH"):         "\x1b[2;38;5;42m",  # dim green (celebration quiet)
    ("DONE", "MAINTAIN"):     "\x1b[2;38;5;67m",  # dim blue
    ("DONE", "REDUCE"):       "\x1b[2;38;5;214m", # dim orange
    ("DONE", "RECOVER"):      "\x1b[1;38;5;42m",  # bold green (recovery progress amplified)
    # Row BLOCKED
    ("BLOCKED", "PUSH"):      "\x1b[38;5;214m",  # orange (preserved)
    ("BLOCKED", "MAINTAIN"):  "\x1b[38;5;214m",  # orange
    ("BLOCKED", "REDUCE"):    "\x1b[38;5;214m",  # orange
    ("BLOCKED", "RECOVER"):   "\x1b[1;38;5;196m", # bold red (escalate)
    # Row CANCELLED
    ("CANCELLED", "*"):       "\x1b[2;38;5;240m", # dim gray (terminal)
    # Row ARCHIVED
    ("ARCHIVED", "*"):        "\x1b[2;38;5;240m", # dim gray (terminal)
}
RESET = "\x1b[0m"
```

**Visual rendering (TUI exemplo):**

```
┌────────────┬──────────┬──────────┬──────────┬──────────┐
│            │  PUSH    │ MAINTAIN │  REDUCE  │ RECOVER  │
├────────────┼──────────┼──────────┼──────────┼──────────┤
│ PENDING    │ ✓green   │ ✓blue    │ ✓orange  │ ⤴red     │
│ ACTIVE     │ ✓green   │ ✓blue    │ ⏸orange  │ ⤴red     │
│ DONE       │ ✓dim-grn │ ✓dim-blu │ ✓dim-org │ ✓bold-grn │
│ BLOCKED    │ ⏸orange  │ ⏸orange  │ ⏸orange  │ ⏸red     │
│ CANCELLED  │ ✗gray    │ ✗gray    │ ✗gray    │ ✗gray    │
│ ARCHIVED   │ ✗gray    │ ✗gray    │ ✗gray    │ ✗gray    │
└────────────┴──────────┴──────────┴──────────┴──────────┘
```

### 3.4 Fork adapter sync triggers

**Regras de propagação cross-fork:**

| Cell type | Sync trigger |
|:----------|:-------------|
| ✓ (create normally) | CliAdapter + TaskdogAdapter + SolverforgeCalendarAdapter (all 3) |
| ⤴ (force transition) | All 3 + severity=CRITICAL |
| ⏸ (preserve state) | Adapter local only (no cross-fork sync); apenas logging |
| 🎉 (celebrate + log) | CliAdapter + TaskdogAdapter (2 of 3; solverforge-calendar só log) |
| ✗ (no sync, terminal) | Early-return em todos adapters |

**Implementação em `src/mesh/agent_propagator.py`:**

```python
def decide_sync_triggers(from_status, to_status, regime) -> list[ForkAdapter]:
    if to_status in ("CANCELLED", "ARCHIVED"):
        return []  # terminal; no sync
    if regime == "RECOVER" and to_status == "ACTIVE":
        return [CliAdapter, TaskdogAdapter, SolverforgeCalendarAdapter]  # force_pause with CRITICAL
    if regime == "REDUCE" and to_status == "ACTIVE":
        return [CliAdapter, TaskdogAdapter]  # pause; 2 adapters (calendar not relevant)
    if to_status == "DONE":
        return [CliAdapter, TaskdogAdapter]  # celebration + log
    # default
    return [CliAdapter, TaskdogAdapter, SolverforgeCalendarAdapter]
```

### 3.5 Worked example

**Cenário:** user completa task "Revisar case BYD" (status PENDING → ACTIVE → DONE) durante regime MAINTAIN.

```text
[1] User clica "marcar como done" na SCR-001 dashboard (cell ACTIVE × MAINTAIN)
[2] fork tuiboard envia action=update(status=DONE) ao deep agent
[3] agent consulta matriz: cell (DONE, MAINTAIN) = 🎉 celebrate + log
[4] agent propaga PropagationEvent(action=log_done, ueid="tsk:byd-...:...:...")
[5] 2 adapters recebem:
    - CliAdapter → data/tasks.jsonl.append({status: "done", done_at: "2026-08-28T..."})
    - TaskdogAdapter → SQLite UPDATE tasks SET status='completed', done_at=... WHERE ueid=?
    - SolverforgeCalendarAdapter → early-return (not in sync trigger list)
[6] User vê toast "✓ Revisar case BYD done!" + KPI-001 (QHE mean) atualiza
```

**Variação:** mesmo task completion, mas em regime RECOVER (cell DONE × RECOVER = 🎉 amplified).

```text
[1] User clica "marcar como done" durante regime RECOVER (após intervention do hysteresis)
[2] agent consulta matriz: cell (DONE, RECOVER) = 🎉 celebrate + log ESPECIAL
[3] agent propaga PropagationEvent(action=log_done_recovery, severity=HIGH)
[4] 3 adapters recebem (todos, para garantir audit trail em recovery):
    - CliAdapter → append + log "recovery_progress"
    - TaskdogAdapter → UPDATE + log
    - SolverforgeCalendarAdapter → UPDATE done_at + tag recovery
[5] User vê toast "🎉 Revisar case BYD done! Recovery progress: 1/3"
[6] Hysteresis FSM recebe sinal recovery_progress → upgrade chance para REDUCE
```

---

## §4 — Cross-references

### 4.1 Design-system docs (Layer 3 + Layer 5)

- **`docs/design-system/00-INDEX.md`** §3 — Layer 5 mapa (este doc é peça load-bearing)
- **`docs/design-system/15-pattern-hysteresis-fsm.md`** §2.1 — regime enum canônico (anchor para colunas da matriz)
- **`docs/design-system/23-fork-status-enum-mapping.md`** §2.1 — status enum canônico (anchor para linhas da matriz)
- **`docs/design-system/30-tokens-deep-agent-era.md`** §3.1 — `T-color-scr-*` cores usadas para cell rendering
- **`docs/design-system/30-tokens-deep-agent-era.md`** §3.4 — `T-glyph-*` glyphs usados para symbols (✓, ⤴, ⏸, 🎉, ✗, 🔴)
- **`docs/design-system/31-ueid-visual-representation.md`** §3 — UEID renderer para labels de matriz
- **`docs/design-system/32-component-naming-conventions.md`** §3 — naming convention (`SCR-002-matriz-estados.md` derivado deste doc)

### 4.2 Forks catalog (Layer 4)

- **`docs/design-system/20-fork-tuiboard-architecture.md`** §3 — tuiboard renderiza matriz em "audit view" + recebe sync triggers
- **`docs/design-system/21-fork-taskdog-architecture.md`** §3 — taskdog SQLite triggers baseados em cell transitions
- **`docs/design-system/22-fork-solverforge-calendar-architecture.md`** §3 — UPI status field consome matriz (excluded for CANCELLED/ARCHIVED)

### 4.3 Code anchors

| Path | Conteúdo | Matriz binding |
|:-----|:---------|:----------------|
| `src/contracts/common.py:150-156` | `RegimeState` enum (PUSH/MAINTAIN/REDUCE/RECOVER) | Colunas da matriz |
| `src/contracts/task.py` | `Task.done`, `TaskStatus` enum | Linhas da matriz |
| `src/mesh/agent_propagator.py` | `decide_sync_triggers()` | Implementação §3.4 |
| `src/ikigai/src/ikigai/core/heuristics/regime.py` | `compute_regime()` | Consulta matriz em transitions |
| PROPOSTA: `src/operational/packages/core/src/operational/core/daily_consolidator.py` (path place-holder — actual file is `consolidator.py`; doc 33 referes here for canonical name) | `render_matrix()` | Renderer §3.3 |
| `src/mesh/adapters/taskdog.py:69` | SQLite `tasks.status` column | Sync trigger target |
| `src/mesh/adapters/solverforge_calendar.py:88` | UPI `status` column | Sync trigger target |

### 4.4 UX doc consolidado

- **`src/operational/docs/ux/01-inventario/02-matriz-estados.md`** — origem do conteúdo (a receber trailer SUPERSEDED após migration)

### 4.5 Memory cross-refs

- **`[[master-branch-carro-chefe-2026-08-28]]`** — master = deep-agent; matriz é contrato cross-fork
- **`[[interfaces-architecture-2026-08-27]]`** — dual-layer architecture (forks=user views que renderizam matriz)
- **`[[data-first-methodology]]`** — ADR-007 gate de 5 SONHO logs (bloqueia tuning de thresholds, **não** estrutura da matriz)

---

## §5 — Fontes

### Code (verificado via Read tool)
- `src/contracts/common.py` — `RegimeState` enum anchor (Pattern #15)
- `src/contracts/task.py` — `TaskStatus`, `Task.done`, `Task.done_at`
- `src/mesh/agent_propagator.py` — `decide_sync_triggers()` implementação
- `src/ikigai/src/ikigai/core/heuristics/regime.py` — `compute_regime()` consumer
- PROPOSTA: `src/operational/packages/core/src/operational/core/daily_consolidator.py` (path place-holder — actual file is `consolidator.py`; doc 33 referes here for canonical name) — `render_matrix()` consumer
- `src/mesh/adapters/cli.py`, `taskdog.py`, `solverforge_calendar.py` — adapter storage topology

### Docs design-system
- `docs/design-system/00-INDEX.md` — Layer 5 mapa
- `docs/design-system/15-pattern-hysteresis-fsm.md` §2.1 — regime anchor
- `docs/design-system/23-fork-status-enum-mapping.md` §2.1 — status anchor
- `docs/design-system/30-tokens-deep-agent-era.md` §3.1, §3.4 — cores + glyphs
- `docs/design-system/31-ueid-visual-representation.md` — UEID renderer
- `docs/design-system/32-component-naming-conventions.md` — `SCR-002` derived

### Forks docs (Layer 4)
- `docs/design-system/20-fork-tuiboard-architecture.md` — tuiboard renderer + sync consumer
- `docs/design-system/21-fork-taskdog-architecture.md` — taskdog SQLite triggers
- `docs/design-system/22-fork-solverforge-calendar-architecture.md` — UPI sync consumer

### Docs UX (origem a consolidar)
- `src/operational/docs/ux/01-inventario/02-matriz-estados.md` — origem (trailer SUPERSEDED pós-migration)

### Memory cross-refs
- `[[master-branch-carro-chefe-2026-08-28]]` — canonical master
- `[[interfaces-architecture-2026-08-27]]` — dual-layer architecture
- `[[data-first-methodology]]` — ADR-007 5 SONHO logs gate (bloqueia tuning, não estrutura)

---

> **Próxima ação recomendada:** após 5 SONHO logs ([[data-first-methodology]] gate), revisar thresholds internos da matriz (atualmente valores qualitativos "✓/⤴/⏸/🎉/✗"; pode evoluir para numeric thresholds + Bayesian Optimization por cell). **Não mexer** na estrutura 6×4 antes do gate — estrutura é load-bearing e cruza 2 contracts Pydantic canônicos.