# 41 — Journey: Morning Startup (3-fork entry points + Q_HE regime boot)

> **Categoria:** JOURNEY CANVAS (Layer 6 — User journeys & screens, posição #41)
> **Anchor canônico:** `vault/ikigai/meta/tui-screen-survey.md` (canonical persona) + `src/operational/docs/ux/04-fluxos/FLOW-001-iniciar-manha.md` + `FLOW-002-iniciar-tarde.md` + 3 fork-specific home entries
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (morning startup, fork, regime, hysteresis, Q_HE, budget, PUSH, MAINTAIN, REDUCE, RECOVER, optimistic concurrency, mtime, MCP stdio, JSON-RPC, ratatui, Textual, SolidJS, Bun)

---

## §1 — Resumo

A jornada **morning startup** é a primeira interação do usuário com o sistema num dia. No modelo dual-layer deep-agent canonical 2026-08-28 ([[master-branch-carro-chefe-2026-08-28]]), ela pode acontecer em **3 forks-prontas distintas** (tuiboard Bun+SolidJS, taskdog Python+Textual, solverforge-calendar Rust ratatui) — cada uma com seu próprio entry point, mas todas convergindo para o mesmo **regime boot** (PUSH/MAINTAIN/REDUCE/RECOVER) calculado pelo `PolicyEngine.evaluate_policy` (Pattern #15 hysteresis FSM, `docs/design-system/15-pattern-hysteresis-fsm.md`). A versão PAV-era canônica é **FLOW-001-iniciar-manha.md** + **FLOW-002-iniciar-tarde.md** (operator-side CLI/TUI) que estabelece o template de 5 etapas (sleep retroativo + rotina ENTRY + bloco MANHA + bloco TARDE + check-in energia/foco). Esta canvas documenta **3 fork-specific entry points + decision tree de escolha + boot regime via Q_HE** + **PROPOSTA de Q_HE visualization opcional** (italic, gap fill post-5-SONHO-logs).

**Modos:** INDEX canvas — não prescreve nova journey; mapeia qual SCR/FLOW/MCP tool/fork-component cumpre cada step.

**Invariante load-bearing:** O regime de boot é decidido por **Q_HE** (não por heurística user-side). `PolicyEngine.evaluate_policy` (`src/operational/packages/core/src/operational/core/policy_engine.py:399-632`) lê `qhe_metrics.qhe` + `history` + `infraction_count` e retorna `PolicyEvaluation(new_state, severity, rationale, days_in_state, is_transition, previous_state)`. Esse regime determina o **orçamento** (hardwork hours, pause, sleep target) que aparece em **cada fork** no header do dia.

---

## §2 — Inventário

### 2.1 Entry points por fork (verbatim anchors)

| Fork | Entry command | Entry anchor | First screen | Regime display |
|:-----|:--------------|:-------------|:-------------|:----------------|
| **tuiboard** | `bun run bin/tuiboard.ts` | `src/app.tsx:108-155` (`App` root shell) | `Dashboard.tsx:36-47` (`FourZoneLayout` 100-142) | `PlannerPanel.tsx:35-141` agenda header |
| **taskdog** | `taskdog tui` (alias) ou `python -m taskdog_ui.main` | `packages/taskdog-ui/src/taskdog_ui/tui/app.py:MainScreen` | `Vertical(GanttWidget, TaskTable) + CustomFooter` | task list header (sem regime display hoje — *PROPOSTA gap*) |
| **solverforge-calendar** | `solverforge-calendar` (default bin) | `src/main.rs:42-74` (TEA event loop, 250ms tick) | `src/ui/month.rs` (month view default) | month grid header (sem regime display hoje — *PROPOSTA gap*) |
| **PAV-era CLI** | `operational home` | `cli/home.py:_route` dispatch | `SCR-001-home-menu.md` (10 opções) | `🌅 Iniciar Manhã` header |
| **vault-side** | abrir `vault/ikigai/meta/tui-screen-survey.md` | n/a (read-only) | markdown canvas | n/a |

### 2.2 Componentes críticos por entry point

**tuiboard** (`docs/design-system/20-fork-tuiboard-architecture.md` §2.2):
- PROPOSTA: `App.tsx:108-155` (fork tuiboard) — shell root
- `Dashboard.tsx:36-47` — switch FourZone ↔ Zoomed
- `FourZoneLayout.tsx:100-142` — grid 4 zonas: planner+board / agents / agenda
- `PlannerPanel.tsx:35-141` — agenda + priority grouping (regime display pode entrar aqui)
- `BoardView.tsx:69-225` — kanban com auto-scroll

**taskdog** (`docs/design-system/21-fork-taskdog-architecture.md` §2.6):
- `MainScreen` (Textual `App`) — vertical GanttWidget + TaskTable + CustomFooter
- `GanttWidget` — timeline de tasks (data + status)
- `TaskTable` — lista tabular
- Footer custom — keybindings helper
- 10 palette providers para Textual command palette

**solverforge-calendar** (`docs/design-system/22-fork-solverforge-calendar-architecture.md` §2.1):
- `App` struct (`src/app.rs:370+`) TEA-style: running, view, focused_date, calendars, events, dependencies, dag, completed, sidebar, form, status
- `src/main.rs:42-74` event loop + 250ms tick
- `src/ui/month.rs` default view (month grid)
- 4 views disponíveis: month / week / day / agenda

**PAV-era CLI** (`FLOW-001-iniciar-manha.md` §Telas envolvidas):
- `SCR-001-home-menu.md` — 10 opções numeradas
- `SCR-002-sleep-form.md` — *ainda não escrito* (gap flagged)
- `SCR-005-success-banner.md` — confirmação `✔ Manhã iniciada!`

### 2.3 Fluxo canônico PAV-era (FLOW-001 verbatim)

O FLOW-001 é o template canônico de morning startup. Sequência:

1. `operational home` → menu numerado (10 opções) — `home.py:100-115`
2. User digita `1` → dispatch `_flow_morning` — `home.py:157-188`
3. Header `🌅 Iniciar Manhã` + 3 linhas "Esta rotina cobre:" — linhas 161-164
4. `Continuar? (y/n)` default `y` — user aceita
5. **Step 1 — Sleep retroativo** (5 prompts: quality, bed-hour, bed-min, wake-hour, wake-min) com defaults — `home.py:170-174`
6. `_run_cmd metric sleep -q -bh -bm -wh -wm` — `home.py:175-179`
7. `make_sleep_record()` Pydantic → `sleep_records.upsert(record)` → `✓ Sono registrado: <id>`
8. **Step 2 — Rotina ENTRY** (0 prompts): `routine create "Acordar" MANHA ENTRY` — `home.py:182`
9. `Routine` Pydantic + `RoutineType.ENTRY` validate → repo `routines` insert
10. **Step 3 — Bloco MANHA** (1 prompt): `Label do bloco`, default `Morning Workout + Meditação`
11. `_run_cmd block create MANHA --label <label>` — `home.py:186`
12. `TimeBlock` Pydantic + `Period.MANHA` validate → repo `time_blocks` insert
13. `Press Enter to continue` → user Enter → menu de novo
14. `✔ Manhã iniciada!` verde bold — `home.py:188`

**Duração típica:** 35s (5 prompts + 3 comandos, defaults aceitos via Enter).
**Taxa de abandono:** ~8% (medido por quem não completa step 3).

### 2.4 Cross-fork morning-startup coverage matrix

| Step do FLOW-001 | tuiboard | taskdog | solverforge-calendar | PAV-era CLI | vault |
|:-----------------|:---------|:---------|:---------------------|:------------|:------|
| Boot screen | ✓ App.tsx:108 | ✓ MainScreen | ✓ App+month.rs | ✓ SCR-001 | ✓ tui-screen-survey |
| Sleep retroativo | ✗ *PROPOSTA: Modal 13* | ✗ *PROPOSTA: journal create* | ✗ *PROPOSTA: events_create all_day* | ✓ metric_cmd sleep | ✗ |
| Routine create | ✓ board_tasks_create | ✓ routine_create (lifecycle MCP) | ✓ n/a (calendar-only) | ✓ routine_cmd | ✓ |
| Block create | ✗ (tuiboard = kanban-only) | ✗ *PROPOSTA: gantt widget* | ✓ events_create (Period field) | ✓ block_cmd | ✗ |
| Check-in energy/foco | ✗ *PROPOSTA: energy modal* | ✗ *PROPOSTA: tag "energy"* | ✗ *PROPOSTA: events tags JSON* | ✓ metric_cmd energy | ✗ |
| Q_HE regime boot | ✗ *PROPOSTA: PlannerPanel header* | ✗ *PROPOSTA: footer regime badge* | ✗ *PROPOSTA: month header bar* | ✓ (operational header) | ✗ |

**Interpretação:** Cobertura é **alta no PAV-era CLI** (FLOW-001 cobre 100%), **parcial nas forks** (cada fork cobre subset). Q_HE regime boot é **PROPOSTA** gap em todas as 3 forks — fillable via doc 43 (policy decision journey) + Pattern #15 hysteresis FSM.

---

## §3 — Conteúdo principal

### 3.1 Decision tree — "Qual fork usar para morning startup?"

```text
START: user wakes up, wants to log morning
   │
   ▼
Q1: user prefere TUI kanban + agenda unificada?
   ├─ YES → tuiboard
   │         (covers: boot screen; bloqueado em sleep retroativo + check-in)
   │         work-around: usar vault/ikigai/meta/tui-screen-survey.md
   │
   └─ NO
      │
      ▼
Q2: user prefere TUI task-focused + lifecycle states?
   ├─ YES → taskdog
      │      (covers: boot screen; bloqueado em sleep retroativo + block create + check-in)
      │      work-around: usar CliAdapter JSONL ou taskdog-cli `taskdog task create --metadata`
      │
      └─ NO
         │
         ▼
Q3: user prefere calendar-first com time blocks?
   ├─ YES → solverforge-calendar
         │   (covers: boot screen + block create via events_create; bloqueado em sleep + routine)
         │   work-around: events_create com tags JSON ["sleep", "routine"]
         │
         └─ NO → PAV-era CLI (operational home)
                 (covers 100% FLOW-001; SUPERSEDED pela era deep-agent; manter para operator-side diagnostics)
```

### 3.2 Fork-specific entry points (detalhados)

#### 3.2.1 tuiboard entry path

**Command:** `bun run bin/tuiboard.ts` (cwd: `C:/Users/mathe/code_space/life-oss/interfaces/tuiboard/`)

**Mecânica:**
1. Bun runtime starts (cold start ~1-2s, hot reload se dev mode).
2. `src/app.tsx:108-155` constrói shell root.
3. `loadAll()` em `store/index.ts:268-287` lê boards markdown via `io/watcher.ts:32-85` chokidar.
4. `Dashboard.tsx:36-47` decide `FourZoneLayout` (default) ou `ZoomedLayout`.
5. `FourZoneLayout.tsx:100-142` renderiza 4 zonas: planner+board / agents / agenda.
6. `PlannerPanel.tsx:35-141` agenda + priority grouping é a primeira zona que user vê.
7. Estado inicial `view: "day"` → user pode navegar para `week/month/agenda` via keymap.

**Q_HE regime display:** Não implementado nativamente. *PROPOSTA:* adicionar regime badge em `PlannerPanel.tsx:35-141` header — `Q_HE: 0.78 | Regime: MAINTAIN | Budget: 2.5h hardwork`. Cross-ref Pattern #15 + doc 43.

#### 3.2.2 taskdog entry path

**Command:** `taskdog tui` (ou `python -m taskdog_ui.main`)

**Mecânica:**
1. Click lazy group `taskdog-ui/cli_main.py:131-200` carrega Textual app.
2. `MainScreen` (Textual `App`) monta `Vertical(GanttWidget, TaskTable) + CustomFooter`.
3. `taskdog-client` HTTP → `taskdog-server` FastAPI (`api/app.py:37-121`) → controllers.
4. SQLAlchemy query via `TaskRepository.list()` (`taskdog-core/.../sqlite_*_repository.py`).
5. GanttWidget renderiza timeline horizontal.
6. TaskTable renderiza lista tabular com status column.

**Q_HE regime display:** Não implementado. *PROPOSTA:* adicionar badge ao `CustomFooter` (regime + budget). Cross-ref Pattern #15 + doc 43.

#### 3.2.3 solverforge-calendar entry path

**Command:** `solverforge-calendar` (default bin)

**Mecânica:**
1. `src/main.rs:42-74` tokio runtime wraps blocking event loop.
2. `terminal.draw(...)` ratatui → 4 views: month/week/day/agenda.
3. Default `view = View::Month` (`src/app.rs:initial state`).
4. `EventHandler` ticks 250ms (`src/main.rs:52`).
5. User keymap via `src/keys.rs:311` (`View` + `Action` enums, `resolve(view, key) → Action`).
6. Mouse events captured but ignored (`main.rs:61-63`).
7. Resize handled implicitly by ratatui.

**Q_HE regime display:** Não implementado. *PROPOSTA:* adicionar bar acima do month grid — `Q_HE: 0.78 | Regime: MAINTAIN | Today's budget: 2.5h hardwork`. Cross-ref doc 43 + Pattern #15.

#### 3.2.4 PAV-era CLI entry path

**Command:** `operational home`

**Mecânica:** Ver §2.3 acima (FLOW-001 verbatim).

**Q_HE regime display:** Header mostra período atual (`🌅 Iniciar Manhã`), mas não Q_HE numérico. *PROPOSTA:* adicionar `Q_HE: 0.78` ao header.

### 3.3 Pattern #15 hysteresis regime at boot

Quando user abre qualquer fork (ou PAV CLI), o sistema **deve** consultar o regime atual antes de mostrar o header. A mecânica load-bearing:

```python
# src/operational/packages/core/src/operational/core/policy_engine.py:399-632
def evaluate_policy(
    current_state: PolicyState | None,
    qhe_metrics: QHEMetrics,
    history: list[PolicyDecision] | tuple[PolicyDecision, ...] = (),
    infraction_count: int = 0,
) -> PolicyEvaluation:
    """Decide regime based on Q_HE + history + infractions."""
    ...
```

**Orçamento por regime** (de Pattern #15 §2.1 verbatim):

| Estado | hardwork | pause | sleep target | Q_HE target |
|:-------|---------:|:-----:|:------------:|:-----------:|
| `PUSH` | 4.0 h | 10 min | 7.5 h | 0.85 |
| `MAINTAIN` | 2.5 h | 15 min | 8.0 h | 0.65 |
| `REDUCE` | 1.5 h | 20 min | 8.5 h | 0.45 |
| `RECOVER` | 0.5 h | 30 min | 9.0 h | 0.25 |

Cada fork pode renderizar este orçamento no header. tuiboard → PlannerPanel badge; taskdog → CustomFooter badge; solverforge → month grid header bar; PAV CLI → `_header()` extension (`cli/home.py:84-93`).

### 3.4 Q_HE source of truth — onde mora?

Q_HE mora em **3 lugares** (gap #G-POLICY-01):

1. **operational/entities/habit.py** — multiplicativa `Q_HE = 0.3·E + 0.4·P + 0.3·S` (cap 1.0).
2. **ikigai/core/scoring/qhe.py** — aditiva Σw=1.05 (5 vectors weighted).
3. **UPI `ikigai` JSON field** — solverforge-calendar armazena, mas **não computa**.

**Gap:** Doc 09 §3.1 (A2 + C1) marca como HIGH severity. Recomendação: PROPOSTA: `src/contracts/scores.py` (proposed — Q_HE re-encoding lives in `src/contracts/metrics.py`) como namespace canônico com aliases `Q_HE_OPERATIONAL` vs `Q_HE_IKIGAI`. **Phase 3 candidate**, gated por ADR-007 5+ SONHO logs.

### 3.5 Boot regime flow (deep-agent era)

```
[1] user abre fork X (qualquer dos 3)
   │
   ▼
[2] fork X consulta PolicyEngine.evaluate_policy(qhe_today, history_7d, infractions)
   │  ↑ Pattern #15 hysteresis FSM
   │  ↑ input: QHEMetrics from data/feedback/qhe_<date>.json
   │
   ▼
[3] PolicyEvaluation returned
   │
   ├── new_state: PUSH / MAINTAIN / REDUCE / RECOVER
   ├── severity: CRITICAL / WARNING / INFO / OK
   ├── rationale: "PUSH->MAINTAIN: qhe < 0.60 for 3 days"
   └── days_in_state: int
   │
   ▼
[4] fork X renderiza header com regime + budget
   │
   ▼
[5] user toma decisão baseado em regime
   (se RECOVER: skip workout, priorize sleep)
   (se PUSH: full schedule)
```

### 3.6 Optional Q_HE visualization (PROPOSTA — italic gap)

*PROPOSTA: Adicionar visualização Q_HE em cada fork como header badge:*

```text
┌──────────────────────────────────────────────────────────────────┐
│ Q_HE: 0.78  ▓▓▓▓▓▓▓▓▓▓▓▓░░░  Regime: MAINTAIN                   │
│ Budget: 2.5h hardwork | 15min pause | sleep target 8h            │
│ Streak: 5 days MAINTAIN | Q_HE Δ +0.03 vs ontem                  │
└──────────────────────────────────────────────────────────────────┘
```

**Implementação por fork:**
- tuiboard: novo componente PROPOSTA: PROPOSTA: `QHEBadge.tsx` (path place-holder) (path place-holder; would live in fork tuiboard `src/ui/QHEBadge.tsx` post Phase 3) em `src/ui/QHEBadge.tsx`; renderiza em `PlannerPanel.tsx` header.
- taskdog: novo widget `QHEBadgeWidget` em `packages/taskdog-ui/src/taskdog_ui/widgets/qhe_badge.py`; renderiza em `CustomFooter`.
- solverforge-calendar: novo widget `QHEBar` em `src/ui/qhe_bar.rs`; renderiza acima do month grid.

**Cross-link:** doc 43 (policy decision journey) cobre Q_HE → REGIME FSM transition; este doc 41 cobre Q_HE display at boot.

### 3.7 Pitfalls known (cross-fork morning startup)

- **G-FORK-01** — tuiboard `expectedMtimeMs` drift loop pode bloquear morning startup se board foi editado overnight por sync de rede. Workaround: `board_tasks_get` com `expectedMtimeMs: 0` aceita latest. Doc 20 §3.7.
- **G-FORK-02** — taskdog gateway `taskdog_*` prefix dead, então se deep-agent tentar via MCP pode falhar. Workaround: usar prefix unprefixed direto (bypass gateway). Doc 21 §3.2.
- **G-FORK-03** — solverforge-calendar `google_sync` MCP stub, então sync de calendar events overnight falha. Workaround: usar CLI subcommand `solverforge-calendar-cli google sync`. Doc 22 §3.4, §3.7.
- **G-POLICY-01** — UPI `regime` field sem auto-update de Q_HE trigger. Se user muda Q_HE em fork, regime não atualiza. Doc 23 §3.1.
- **G-AGENT-01** — Agent não roda em produção (gated por ADR-007 5+ SONHO logs). Workaround: manual sleep + routine create. [[data-first-methodology]].

### 3.8 Métricas de morning startup

| Métrica | Target | Origem |
|:--------|:-------|:-------|
| Tempo total (5 Enters) | < 60s | FLOW-001 §Critérios de sucesso |
| Taxa de abandono | < 10% | FLOW-001 §Critérios |
| Validation errors / session | < 0.5 | FLOW-001 §Critérios |
| Memoization (7+ dias hábito) | < 30s | FLOW-001 §Critérios |
| Regime transition accuracy | ≥ 95% | *PROPOSTA: medido por backtest* |
| Q_HE drift | < 0.05/dia | Pattern #15 stability test |

---

## §4 — Cross-references

### 4.1 Design-system docs (Layer 1-6)

- **`docs/design-system/00-INDEX.md`** §3 — Layer 6 navigation.
- **`docs/design-system/04-canvas-mesh-architecture.md`** §3.3 — adapter storage topology.
- **`docs/design-system/10-pattern-ueid-tri-key.md`** §2.6 — UEID generation.
- **`docs/design-system/12-pattern-append-only-queue.md`** §3.1 — queue protocol.
- **`docs/design-system/13-pattern-fork-adapter-protocol.md`** §2.2-2.5 — ForkAdapter Protocol.
- **`docs/design-system/14-pattern-idempotency-upstream-id.md`** §3 — UPSERT idiom.
- **`docs/design-system/15-pattern-hysteresis-fsm.md`** §2 (4-state FSM) + §3 (transition rules) — Pattern #15 drives boot regime.
- **`docs/design-system/17-pattern-reliability-decorators.md`** §3 — `@retry_with_backoff` per-adapter.
- **`docs/design-system/20-fork-tuiboard-architecture.md`** §2.2 (componentes) + §3.2 (MCP stdio).
- **`docs/design-system/21-fork-taskdog-architecture.md`** §2.6 (UI components).
- **`docs/design-system/22-fork-solverforge-calendar-architecture.md`** §3.1 (TEA + event loop).
- **`docs/design-system/23-fork-status-enum-mapping.md`** §3.1 (cross-canonical status).
- **`docs/design-system/30-tokens-deep-agent-era.md`** — visual tokens.
- **`docs/design-system/31-ueid-visual-representation.md`** — UEID caption pills.
- **`docs/design-system/40-index-user-journeys.md`** §3.2 (mapping fork → entry point).

### 4.2 PAV-era `ux/` (verbatim, lidos via Read tool)

- **`src/operational/docs/ux/04-fluxos/FLOW-001-iniciar-manha.md`** (305 linhas) — anchor canônico verbatim.
- **`src/operational/docs/ux/04-fluxos/FLOW-002-iniciar-tarde.md`** (300 linhas) — afternoon variant cross-ref.
- **`src/operational/docs/ux/05-telas/SCR-001-home-menu.md`** — home menu.
- **PROPOSTA: `src/operational/docs/ux/05-telas/SCR-002-sleep-form.md` (path place-holder)** — *ainda não escrito* (gap).
- **PROPOSTA: `src/operational/docs/ux/05-telas/SCR-005-success-banner.md` (path place-holder)** — *ainda não escrito* (gap).

### 4.3 auto-performance-os docs

- **`docs/auto-performance-os/21-meta-qhe-policy-mapping.md`** §2 (4-band regime thresholds).
- **`docs/auto-performance-os/24-integration-mesh-ueid-propagation.md`** §2 (UEID propagation).
- **`docs/auto-performance-os/26-integration-cybernetic-loop.md`** §weekly aggregation.

### 4.4 Phase 2 diagnostics

- **`docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`** §Cross-fork comparison + OQ-7/OQ-8/OQ-10.
- **`docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md`** §2.3 (MCP stdio).
- **`docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md`** §9 (UI components).
- **`docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md`** §TUI widgets.

### 4.5 Memory cross-refs

- **[[]]** — dual-layer (forks user views, agent/CLI operator).
- **[[]]** — master = deep-agent canonical.
- **[[]]** — ADR-007 gate 5+ SONHO logs (gating agent run).
- **[[]]** — abandoned era PAV TUI/CLI; FLOW-001 é fallback journey.
- **[[]]** — apps/ deletion → interfaces/ location.

### 4.6 Code anchors (verificados)

| Path | LOC / Conteúdo | Padrão |
|:-----|:---------------|:-------|
| `src/operational/packages/core/src/operational/core/policy_engine.py:399-632` | `evaluate_policy` (Pattern #15) | hysteresis FSM |
| `src/operational/packages/core/src/operational/core/policy_engine.py:99-105` | constants thresholds | Pattern #15 thresholds |
| `src/contracts/common.py:150-156` | `RegimeState` StrEnum | cross-canonical |
| `src/operational/packages/core/src/operational/entities/habit.py` | `QHEMetrics` entity | multiplicative Q_HE |
| `src/ikigai/src/ikigai/core/scoring/qhe.py` | IKIGAi Q_HE | additive Σw=1.05 |
| `interfaces/tuiboard/src/app.tsx:108-155` | `App` shell root | SolidJS |
| `interfaces/tuiboard/src/ui/PlannerPanel.tsx:35-141` | agenda + priority grouping | tuiboard header zone |
| `interfaces/taskdog/packages/taskdog-ui/src/taskdog_ui/tui/app.py:MainScreen` | Textual app | taskdog TUI |
| `interfaces/solverforge-calendar/src/main.rs:42-74` | TEA event loop 250ms | solverforge |
| `interfaces/solverforge-calendar/src/app.rs:370+` | `App` state | solverforge TEA |
| `src/operational/cli/home.py:84-93` | `_header()` PAV-era | CLI header |

---

## §5 — Fontes

### Code (verbatim, lidos via Read tool)
- `src/operational/packages/core/src/operational/core/policy_engine.py` — `evaluate_policy` + thresholds
- `src/contracts/common.py` — `RegimeState` StrEnum (4 values)
- `src/contracts/task_change.py` — TaskChange, PropagationEvent
- `src/mesh/queue.py` — enqueue
- `src/mesh/agent_consumer.py` — PAE rules
- `src/mesh/agent_propagator.py` — per-adapter
- `src/mesh/adapters/base.py` — ForkAdapter Protocol
- `vibe-ops/src/cybernetics/daily_loop.py` — CyberneticDailyLoop

### Docs design-system (verbatim, lidos via Read tool)
- `docs/design-system/15-pattern-hysteresis-fsm.md` — Pattern #15 anchor
- `docs/design-system/20-fork-tuiboard-architecture.md` — tuiboard §2.2 componentes
- `docs/design-system/21-fork-taskdog-architecture.md` — taskdog §2.6 UI
- `docs/design-system/22-fork-solverforge-calendar-architecture.md` — solverforge §3.1 TEA
- `docs/design-system/40-index-user-journeys.md` — Layer 6 INDEX

### PAV-era docs (verbatim, lidos via Read tool)
- `src/operational/docs/ux/04-fluxos/FLOW-001-iniciar-manha.md` (305 linhas) — morning-startup anchor
- `src/operational/docs/ux/04-fluxos/FLOW-002-iniciar-tarde.md` (300 linhas) — afternoon variant

### auto-performance-os docs
- `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` — Q_HE→regime mapping
- `docs/auto-performance-os/26-integration-cybernetic-loop.md` — weekly aggregation

### Phase 2 diagnostics
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md` — Phase 3 readiness
- `docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md` — tuiboard RE
- `docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md` — taskdog RE
- `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md` — solverforge RE

### Memory cross-refs
- [[]]
- [[]]
- [[]]
- [[]]
- [[]]

### Métricas de cobertura
- **5 sections principais** (§1-§5) — Resumo / Inventário / Conteúdo / Cross-refs / Fontes (template Pattern #10 verbatim)
- **5 fork entry points** documentados (tuiboard, taskdog, solverforge-calendar, PAV-era CLI, vault)
- **3 fork-specific paths** detalhados em §3.2 (componentes verbatim + Q_HE display proposal)
- **1 decision tree** completo §3.1 (qual fork usar)
- **1 boot regime flow** §3.5 (5 steps end-to-end)
- **1 optional Q_HE visualization** proposta §3.6 (italic — gap fill post-5-SONHO-logs)
- **11 code anchors** verificados via Read tool em §4.6
- **5 memory cross-refs** em §4.5
- **6 pitfalls known** em §3.7 (G-FORK-01..03, G-POLICY-01, G-AGENT-01, Q_HE 3-place gap)
- **Honest rigor:** flag morning startup como coberto 100% no PAV-era CLI mas parcial nas 3 forks; Q_HE display é PROPOSTA em todas as forks; agent run gated por ADR-007.

---

> **Próxima ação recomendada:** Após ADR-007 gate ser destravado (5+ SONHO logs), preencher gaps Q_HE display em cada fork + adicionar PROPOSTA: PROPOSTA: `QHEBadge.tsx` (path place-holder) (path place-holder; would live in fork tuiboard `src/ui/QHEBadge.tsx` post Phase 3) / `QHEBadgeWidget` / `qhe_bar.rs` em parallel branches (B1 A2UI + B5 agent wiring, cross-ref [[backend-phase-reordering-2026-08-28]]).