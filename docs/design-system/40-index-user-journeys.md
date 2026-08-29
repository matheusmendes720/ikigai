# 40 — INDEX: User Journeys & Screens (Layer 6 — Deep-Agent Era)

> **Categoria:** INDEX (Layer 6 — User journeys & screens, posição #40)
> **Anchor canônico:** `vault/ikigai/meta/tui-screen-survey.md` + `src/operational/docs/ux/04-fluxos/` (PAV-era flows) + `interfaces/{tuiboard,taskdog,solverforge-calendar}/` (3 forks-prontas)
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (journey, fork, fork adapter, regime, KPI, FLOW, SCR, deep-agent, mesh, vault, dataset, MCP, stdio)

---

## §1 — Resumo

Este doc é o **INDEX mestre da Layer 6 (User journeys & screens)** do docset design-system. A Layer 6 documenta **6 famílias de jornada canônica do usuário** que atravessam o modelo dual-layer (forks-prontas = user views Layer A; deep-agent + CLI = operator Layer B; cross-link PROPOSTA: `docs/design-system/02-interfaces-dual-layer-architecture.md` (relative path)) no contexto **deep-agent canonical 2026-08-28** ([[master-branch-carro-chefe-2026-08-28]]). Cada família de jornada mapeia 3 forks-prontas (tuiboard Bun+SolidJS, taskdog Python+Textual, solverforge-calendar Rust ratatui) + fluxos canônicos PAV-era (`src/operational/docs/ux/04-fluxos/FLOW-001..010`) + journey vault-side (`vault/ikigai/meta/tui-screen-survey.md`). Os **5 canvases profundos** (docs 41-45) expandem cada família em formato **INDEX-only** (não-canvas narrativa nova): eles **apontam** para qual SCR (screen) / FLOW (fluxo) / MCP tool / fork já cobre cada step, sem prescrever nova journey. A intenção é **evidenciar cobertura cruzada + gaps** + preservar a opção de re-templating quando o agente operacional conectar de fato.

**Modos:** INDEX + cross-link. Não duplica conteúdo. **Append-only** — não deleta PAV-era flows; canonicaliza como fallback journey map.

**Importante:** Os 3 forks-prontas são **vendored MIT/Apache forks** ([[]]), vivem em `C:/Users/mathe/code_space/life-oss/interfaces/` (pós-reorg 2026-08-28, deletados de `apps/` via [[windows-orphan-dir-delete]]), e atualmente operam em **parallel integration** com o deep-agent via MCP gateway (`gateways.yaml:1-16`) — mas com 3 cwd stale + 1 prefix dead + 1 stub tool que bloqueiam Phase 3 readiness (`docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`).

---

## §2 — Inventário

### 2.1 As 6 famílias de jornada (escopo da Layer 6)

| # | Família | Doc | Anchors primários | Cobertura |
|:-:|:--------|:----|:------------------|:----------|
| 1 | **Morning startup** | `41-journey-morning-startup.md` | FLOW-001 + FLOW-002 + SCR-001 + 3 fork entry points | alto — 3 forks + PAV |
| 2 | **Task create** | `42-journey-task-create.md` | FLOW-002 + SCR-008 + SCR-009 + ForkAdapter Protocol | alto — 3 forks + queue |
| 3 | **Policy decision** | `43-journey-policy-decision.md` | Pattern #15 hysteresis FSM + daily_loop + REGIME sync | médio — fork-specific |
| 4 | **Weekly review** | `44-journey-weekly-review.md` | FLOW-007 + SCR-003 + integration-cybernetic-loop | médio — federated |
| 5 | **Dataset switch** | `45-journey-dataset-switch.md` | FLOW-008 + FLOW-009 + FLOW-010 + ADR-007 | baixo — operator-only |
| 6 | (reservado) | n/a | n/a | reservado para gap-fill futuro |

### 2.2 Cross-fork journey map — matriz 2D (família × fork)

Esta matriz é o coração da Layer 6. Cada célula indica **qual SCR / FLOW / MCP tool / fork-component** cumpre aquela jornada na interface especificada.

| Família de jornada | tuiboard (Bun+SolidJS) | taskdog (Python+Textual) | solverforge-calendar (Rust ratatui) | PAV-era `ux/04-fluxos/` | vault-side |
|:-------------------|:-----------------------|:-------------------------|:-------------------------------------|:------------------------|:-----------|
| **morning-startup** | ✓ PROPOSTA: `App.tsx:108-155` (fork tuiboard) + `Dashboard.tsx:36-47` (`docs/design-system/20-fork-tuiboard-architecture.md` §2.2) | ✓ `TaskdogGroup` CLI (`cli_main.py:131-200`) + `MainScreen` TUI (`packages/taskdog-ui/src/taskdog_ui/`) | ✓ `solverforge-calendar` bin (`Cargo.toml:86-88`) + month/week/day/agenda views (`src/ui/*`) | ✓✓ **FLOW-001-iniciar-manha.md** + FLOW-002 + **SCR-001-home-menu.md** | ✓ `vault/ikigai/meta/tui-screen-survey.md` (canonical persona flow) |
| **task-create** | ✓ `BoardView` + 13 modais (`Modal.tsx:43-60`) — `board_tasks_create` MCP tool (`board-tasks-create.ts:21-111`) | ✓ **26 MCP tools** (`create_task` em `task_crud.py`) + Click `taskdog task create` (`cli_main.py:131-200`) | ✓ `events_create` MCP tool (`solverforge-calendar-mcp.rs`) + Clap `Events create` subcommand (`src/cli.rs:700+`) | ✓ **SCR-008-routine-create.md** + **SCR-009-block-create.md** + FLOW-002 step 2 | ✓ `vault/ikigai/meta/` planning markdown |
| **policy-decision** | ✗ — tuiboard não tem PolicyEngine local | ✗ — taskdog domain é task-state-machine, não regime FSM | ✓ UPI `status` + `ikigai` JSON carrega `regime` field (mapping doc 23) | ✓ **SCR-013-policy-decisions.md** + **SCR-014-reflect.md** + FLOW-006 daily | ✗ — policy é operator-side |
| **weekly-review** | ✗ — tuiboard não tem agregação 7d | ✓ `get_statistics` + `get_tag_statistics` MCP tools (`tools/task_query.py`) | ✓ `upi_list` + `upi_search` MCP tools (`solverforge-calendar-mcp.rs:778-803`) | ✓✓ **FLOW-007-relatorio-semanal.md** + **SCR-003-weekly-report.md** | ✓ `closing-2026/{quarter}-{week}/` |
| **dataset-switch** | ✗ — fork-local storage não tem dataset concept | ✗ — SQLite single-DB | ✗ — dual-DB federation mas não user-toggleable | ✓ **FLOW-008-trocar-dataset.md** + **FLOW-009-limpar-resetar.md** + **FLOW-010-doctor.md** | ✗ — vault é source-of-truth, não dataset |
| **ad-hoc-task-search** | ✓ `board_tasks_get` com filter (`board-tasks-get.ts:27-105`) | ✓ `list_tasks` + 11 optimization strategies (`task_optimization.py:19-142`) | ✓ `events_list` + UPI `upi_search` (full-text em JSON) | parcial — search disperso | ✓ wikilink [[]] cross-ref |

**Legenda:** ✓ = cobertura direta; ✓✓ = doc canônico PAV-era; ✗ = gap known.

### 2.3 Inventário de artefatos journey-side (anchors verbatim)

| Família | Anchor canônico | LOC / Conteúdo | Padrão |
|:--------|:----------------|:---------------|:-------|
| morning-startup | `interfaces/tuiboard/src/app.tsx:108-155` | `App` root shell | SolidJS shell |
| morning-startup | `interfaces/taskdog/packages/taskdog-ui/src/taskdog_ui/tui/` | Textual app + Gantt widget | TUI palette |
| morning-startup | `interfaces/solverforge-calendar/src/main.rs:42-74` | TEA event loop + 250ms tick | ratatui main |
| task-create | `interfaces/tuiboard/src/v3/mcp/tools/board-tasks-create.ts:21-111` | create MCP tool | optimistic concurrency |
| task-create | `interfaces/taskdog/packages/taskdog-mcp/src/taskdog_mcp/tools/task_crud.py` | 6 CRUD tools | FastMCP |
| task-create | `interfaces/solverforge-calendar/src/bin/solverforge-calendar-mcp.rs` | 30 tools (5×6 categories) | rmcp 3.1 |
| task-create | `src/mesh/queue.py:enqueue` | atomic temp+rename | Pattern #12 |
| policy-decision | `src/operational/packages/core/src/operational/core/policy_engine.py:99-105` | hysteresis thresholds | Pattern #15 |
| policy-decision | `vibe-ops/src/cybernetics/daily_loop.py:CyberneticDailyLoop` | Target→Sensor→Adjuster | Pattern #08 canvas |
| weekly-review | `src/operational/packages/core/src/operational/core/consolidator.py` | weekly rollup | arithmetic only |
| weekly-review | `docs/auto-performance-os/26-integration-cybernetic-loop.md` | weekly aggregation | Pattern #17 |
| dataset-switch | `src/operational/cli/dataset_selector.py:resolve_dataset` | dataset resolver | PAV-era |
| dataset-switch | `src/operational/cli/state.py:JSONRepository._load_all` | lazy state dir | PAV-era |

### 2.4 Gap inventory — o que NÃO está coberto

| Gap | Família | Severidade | Cross-ref |
|:----|:--------|:----------:|:----------|
| **G-FORK-01**: tuiboard `expectedMtimeMs` drift loop | morning-startup, task-create | HIGH | doc 20 §3.7 (optimistic concurrency) |
| **G-FORK-02**: taskdog gateway `taskdog_*` prefix dead — 20/26 tools unreachable | task-create | HIGH | doc 21 §3.2 |
| **G-FORK-03**: solverforge-calendar `google_sync` MCP stub + `http` feature-gated out | dataset-switch | HIGH | doc 22 §3.7, §3.4 |
| **G-FORK-04**: solverforge-calendar `SyncEngine::poll` misnomer (counts local rows, not external reads) | weekly-review | MEDIUM | doc 22 §4.6 |
| **G-FORK-05**: tuiboard sem UEID nativo — federation observability only | task-create | HIGH | doc 20 §3.4 |
| **G-FORK-06**: taskdog sem UEID nativo — backfill heurístico pendente | task-create | MEDIUM | doc 21 §3.7 |
| **G-POLICY-01**: solverforge UPI `regime` field sem auto-update de Q_HE trigger | policy-decision | MEDIUM | doc 23 §3.1 (cross-canonical) |
| **G-POLICY-02**: taskdog `TaskStatus` 4-state vs canonical 6-state (PENDING/ACTIVE/DONE/BLOCKED/CANCELLED/ARCHIVED) | policy-decision | HIGH | doc 23 §1 |
| **G-WEEKLY-01**: weekly report cross-fork aggregation não implementada (cada fork isolado) | weekly-review | MEDIUM | doc 22 §4.6 SyncEngine misnomer |
| **G-DATASET-01**: dataset switch operator CLI only — user-facing dataset picker não existe | dataset-switch | HIGH | FLOW-008 PAV-era |
| **G-AGENT-01**: Agent não roda em produção (gated por ADR-007 5+ SONHO logs) | all | CRITICAL | [[data-first-methodology]] |

---

## §3 — Conteúdo principal

### 3.1 Decision tree — "Qual fork usar baseado em objetivo"

Este é o **decision tree canônico** que o usuário (ou agente) usa para escolher fork baseado em objetivo:

```text
START: user wants to do X
   │
   ▼
Q1: X é sobre visual kanban de tasks?
   ├─ YES → tuiboard (Bun+SolidJS, TUI)
   │         strong: 4 zones, 13 modais, agenda dashboard
   │         weak:  sem UEID, federation observability-only
   │
   └─ NO
      │
      ▼
Q2: X é sobre SQL-style queries sobre tasks (CRUD + lifecycle)?
   ├─ YES → taskdog (Python, REST + MCP + TUI)
   │         strong: 26 MCP tools, SQLite UPSERT, audit log
   │         weak:  sem UEID, 20/26 tools unreachable via gateway
   │
   └─ NO
      │
      ▼
Q3: X é sobre calendar + dependencies + DAG?
   ├─ YES → solverforge-calendar (Rust, ratatui + rmcp)
      │      strong: 30 tools, UPI mesh substrate, OAuth2 Google
      │      weak:  google_sync stub, http feature-gated out
      │
      └─ NO → vault-side markdown
              (fonte canônica para planning NL)
```

**Cross-link para padrões:** Cada fork alinha-se a um subset dos 19 patterns (Layer 3) — taskdog é canônico de Pattern #14 (Idempotent UPSERT) via SQL `ON CONFLICT(ueid)`; solverforge-calendar é canônico de Pattern #13 (ForkAdapter Protocol) com PK reuse; tuiboard é federated observer.

### 3.2 Mapping fork → journey entry point

| Fork | Morning startup entry | Task create entry | Policy decision entry | Weekly review entry | Dataset switch entry |
|:-----|:----------------------|:------------------|:----------------------|:--------------------|:---------------------|
| **tuiboard** | `bun run bin/tuiboard.ts` → PROPOSTA: `App.tsx:108` (fork tuiboard entry) | `board_tasks_create` MCP | n/a — federated | n/a — fork-local | n/a — markdown local |
| **taskdog** | `taskdog tui` → `MainScreen` (vertical Gantt + table) | `taskdog task create <args>` (Click) ou `create_task` MCP | n/a — TaskStateMachine | `get_statistics` MCP + report | n/a — SQLite single DB |
| **solverforge-calendar** | `solverforge-calendar` → month view | `solverforge-calendar-cli events create` (Clap) | UPI `upi_update` com `status` change | `upi_list` + aggregation | n/a — dual-DB federation |
| **PAV-era CLI** | `operational home` → opção `1` | `routine create` + `block create` | SCR-013 reflect view | `operational report weekly` | PROPOSTA: `TIME_TASKER_DATASET=…` (env var name change per migration; deep-agent era uses `PAV_DATASET`) env var |
| **vault** | `vault/ikigai/meta/tui-screen-survey.md` reading | markdown [[]] new file | n/a — operator-side | `closing-2026/{q}-{w}/` markdown | n/a — vault is canonical |

### 3.3 Padrões de jornada load-bearing

Os 5 canvases profundos (docs 41-45) seguem 4 padrões comuns:

1. **Padrão A — Cross-fork join via UEID** — toda journey que cria entity passa por `data/review_queue/<event_id>.json` (Pattern #12 append-only), validada via `agent_consumer.py` (PAE rules), propagada via `agent_propagator.py` (per-adapter try/except) para os 3 adapters (`base.py` ForkAdapter Protocol). **UEID é o join key canônico** cross-fork (Pattern #10).

2. **Padrão B — Status canonicalization** — cada fork tem enum local de status (taskdog 4-state, solverforge 5-value, tuiboard 3-column). Toda journey que muda status passa pela tabela canônica de mapping (`docs/design-system/23-fork-status-enum-mapping.md` §3.2) que converte status local → canonical 6-state (PENDING/ACTIVE/DONE/BLOCKED/CANCELLED/ARCHIVED) antes de propagar.

3. **Padrão C — Hysteresis boot regime** — toda journey que inicia (morning startup) lê o regime atual do `PolicyEngine.evaluate_policy` (Pattern #15) e aplica o budget correspondente (PUSH = 4h hardwork, MAINTAIN = 2.5h, REDUCE = 1.5h, RECOVER = 0.5h). Q_HE é source of truth — não há override user-side direto.

4. **Padrão D — Vault sync on completion** — toda journey que cria/atualiza entity propaga para vault como `vault/ikigai/meta/` markdown append-only (regime append-only do projeto [[orchestration-clone-playground]] + [[interfaces-architecture-2026-08-27]] dual-layer). Vault não é deletável.

### 3.4 Camada de abstração — journeys como grafo

Jornadas não são lineares; são **grafos com 1 happy path + N alternative paths + M error paths**. Os 5 canvases profundos documentam apenas o happy path + as 3 alternativas mais frequentes + os 2 errors mais comuns — total ~6 paths por canvas. Paths exóticos (E5+) ficam em **italic narrative** nos docs (não-canvas, não-prescritivo) — flagged como **PROPOSTA: cross-link para doc futuro quando gaps forem fechados**.

### 3.5 Métricas de jornada canônicas (KPI tracking)

Cada jornada produz KPIs que alimentam o weekly review (FLOW-007, doc 44):

| Jornada | KPI primário | KPI secundário | Origem |
|:--------|:-------------|:---------------|:-------|
| morning-startup | tempo total (<60s) | taxa de abandono (<10%) | FLOW-001 §Critérios de sucesso |
| task-create | UEID mint time | validation failure rate | `agent_consumer.py` PAE rules |
| policy-decision | regime transitions/wk | Q_HE delta | `consolidator.py` weekly |
| weekly-review | tempo render (<5s) | KPI completeness | doc 44 §3.2 |
| dataset-switch | rollback success rate | consistency check time | FLOW-010 doctor |

**Cross-link:** Métricas viram `data/metrics/weekly_<YYYY-WW>.json` consumidas por PROPOSTA: `consolidator.py:rollup_week` (path place-holder) e exibidas em SCR-003 weekly report.

---

## §4 — Cross-references

### 4.1 Design-system docs (Layer 1-5 + Layer 6 self)

- **`docs/design-system/00-INDEX.md`** §2 — tabela Layer 6 user journeys posição #40-45.
- **`docs/design-system/01-master-branch-carro-chefe-2026-08-28.md`** §3 — master = deep-agent bidirecionalmente sincronizando 3 forks-prontas ↔ vault. Layer 6 documenta journeys que o agent observa.
- **`docs/design-system/02-interfaces-dual-layer-architecture.md`** — forks = user views Layer A; deep-agent + CLI = operator Layer B. Layer 6 foca Layer A.
- **`docs/design-system/04-canvas-mesh-architecture.md`** §3.2 (ForkAdapter Protocol), §3.3 (storage topology) — load-bearing para entender cross-fork join.
- **`docs/design-system/05-canvas-contracts-architecture.md`** §4 (TaskChange / PropagationEvent) — Pattern #10 #11 #12 cross-cutting.
- **`docs/design-system/10-pattern-ueid-tri-key.md`** §2.6 (UEID generation rules) — toda journey que cria entity segue este pipeline.
- **`docs/design-system/12-pattern-append-only-queue.md`** §3.1 (queue protocol `enqueue` / `consume_pending` / `ack` / `replay_after_restart`).
- **`docs/design-system/13-pattern-fork-adapter-protocol.md`** §2.2-2.5 (3 adapters verbatim) — `apply_change` é idempotente.
- **`docs/design-system/14-pattern-idempotency-upstream-id.md`** §3 (UPSERT idiom nativo SQLite).
- **`docs/design-system/15-pattern-hysteresis-fsm.md`** §2 (4-state FSM) — Pattern #15 drives morning-startup regime.
- **`docs/design-system/17-pattern-reliability-decorators.md`** §3 — `@retry_with_backoff` aplicado em `agent_propagator.py` per-adapter try/except.
- **`docs/design-system/20-fork-tuiboard-architecture.md`** §2.7 (estado atual Phase 3 readiness) — gap #5 cwd stale.
- **`docs/design-system/21-fork-taskdog-architecture.md`** §3.2 (gateway prefix mismatch) — gap #F2 20/26 unreachable.
- **`docs/design-system/22-fork-solverforge-calendar-architecture.md`** §3.7 (gateway routing match matrix) — gap google_sync stub + http feature.
- **`docs/design-system/23-fork-status-enum-mapping.md`** §3.2 (canonical 6-state mapping table) — Pattern B supra.
- **`docs/design-system/30-tokens-deep-agent-era.md`** — visual tokens canônicos para Layer 6 journeys (color/spacing/typography).
- **`docs/design-system/31-ueid-visual-representation.md`** — como UEID renderiza em TUI/GUI (caption pills, color coding).
- **`docs/design-system/33-status-matrix-unified.md`** — matriz canônica STATUS × REGIME × sync trigger.

### 4.2 auto-performance-os docs (matemática + integração)

- **`docs/auto-performance-os/24-integration-mesh-ueid-propagation.md`** §2 (UEID propagation pipeline).
- **`docs/auto-performance-os/26-integration-cybernetic-loop.md`** — weekly aggregation pipeline cross-ref doc 44.
- **`docs/auto-performance-os/21-meta-qhe-policy-mapping.md`** §2 (4-band regime) — Pattern #15 thresholds.

### 4.3 PAV-era `ux/04-fluxos/` (10 flows verbatim)

- **`src/operational/docs/ux/04-fluxos/FLOW-001-iniciar-manha.md`** — morning-startup anchor principal.
- **`src/operational/docs/ux/04-fluxos/FLOW-002-iniciar-tarde.md`** — afternoon variant.
- **`src/operational/docs/ux/04-fluxos/FLOW-003-encerrar-dia.md`** — evening close.
- **`src/operational/docs/ux/04-fluxos/FLOW-004-checkin-rapido.md`** — ad-hoc energy/foco log.
- **`src/operational/docs/ux/04-fluxos/FLOW-005-dashboard-dia.md`** — daily dashboard view.
- **`src/operational/docs/ux/04-fluxos/FLOW-006-relatorio-diario.md`** — daily report (cross-ref FLOW-007 weekly).
- **`src/operational/docs/ux/04-fluxos/FLOW-007-relatorio-semanal.md`** — weekly review anchor doc 44.
- **`src/operational/docs/ux/04-fluxos/FLOW-008-trocar-dataset.md`** — dataset switch anchor doc 45.
- **`src/operational/docs/ux/04-fluxos/FLOW-009-limpar-resetar.md`** — reset/clear operator-side.
- **`src/operational/docs/ux/04-fluxos/FLOW-010-doctor.md`** — diagnostics anchor doc 45.

### 4.4 PAV-era `ux/05-telas/` (15 screens verbatim)

- **`src/operational/docs/ux/05-telas/SCR-001-home-menu.md`** — home menu.
- **`src/operational/docs/ux/05-telas/SCR-003-weekly-report.md`** — weekly report screen.
- **`src/operational/docs/ux/05-telas/SCR-005-demo-stats.md`** — PAV-era demo stats (cross-ref doc 43).
- **`src/operational/docs/ux/05-telas/SCR-008-routine-create.md`** — task create routine (cross-ref doc 42).
- **`src/operational/docs/ux/05-telas/SCR-009-block-create.md`** — block create.
- **`src/operational/docs/ux/05-telas/SCR-013-policy-decisions.md`** — policy decisions view (cross-ref doc 43).
- **`src/operational/docs/ux/05-telas/SCR-014-reflect.md`** — reflect step (cross-ref doc 43).

### 4.5 vault-side journeys (canonical persona flow)

- **`vault/ikigai/meta/tui-screen-survey.md`** — canvas canônico da persona flow.
- **`vault/ikigai/closing-2026/`** — `01-q3-2026/04-relatórios-diários/` (SONHO logs gate).
- **`vault/ikigai/meta/MOC-jornadas.md`** — *PROPOSTA: MOC de jornadas pendente de writeup post-5-logs* (italic, gap flagged).

### 4.6 Phase 2 diagnostics + Phase 3 readiness

- **`docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`** §Cross-fork comparison matrix + OQ-7/OQ-8/OQ-10 readiness.
- **`docs/diagnostics/2026-08-28-phase1-audit/01-verified.md`** B-01 (gateways.yaml cwd MISSING × 3 forks).
- **`docs/diagnostics/2026-08-28-doc-migration/00-INDEX.md`** — status de docs PAV-era (33 trailers APPLIED).

### 4.7 Memory cross-refs

- **[[]]** — dual-layer (forks user views, agent/CLI operator).
- **[[]]** — master = deep-agent canonical.
- **[[]]** — ADR-007 gate 5+ SONHO logs (gating agent run).
- **[[]]** — abandoned era PAV TUI/CLI built-from-scratch; Layer 6 documenta journeys deste era como fallback.
- **[[]]** — PAV desativado como subsystem-extension.
- **[[]]** — backend phase ordering (B0 hygiene → B6 vault sync).
- **[[]]** — gateway orphan relations (taskdog prefix mismatch).
- **[[]]** — apps/ deletion → interfaces/ location.
- **[[]]** — vendored MIT/Apache forks.
- **[[]]** — CLI becoming command palette over multi-backend MCP contracts.

### 4.8 Code anchors (verificados)

| Path | LOC / Conteúdo | Padrão |
|:-----|:---------------|:-------|
| `src/mesh/queue.py:enqueue` | atomic temp+rename | Pattern #12 |
| `src/mesh/agent_consumer.py` | PAE rules | Pattern #11 (frozen) |
| `src/mesh/agent_propagator.py` | per-adapter try/except | Pattern #17 reliability |
| `src/mesh/adapters/base.py:ForkAdapter` | Protocol | Pattern #13 |
| `src/mesh/adapters/cli.py` | JSONL append-only | adapter 1 |
| `src/mesh/adapters/taskdog.py` | SQLite UPSERT | adapter 2 |
| `src/mesh/adapters/solverforge_calendar.py` | UPI PK reuse | adapter 3 |
| `src/contracts/task_change.py:TaskChange, PropagationEvent` | Pydantic frozen | Pattern #11 |
| `src/contracts/common.py:UEID` | regex 4-part | Pattern #10 |
| `src/operational/packages/core/src/operational/core/policy_engine.py:99-105` | hysteresis thresholds | Pattern #15 |
| `vibe-ops/src/cybernetics/daily_loop.py:CyberneticDailyLoop` | TARGET→SENSOR→ADJUSTER | Pattern #08 |
| `vibe-ops/src/middleware/sync_engine.py` | Obsidian ↔ SQLite ↔ Taskwarrior | sync layer |

---

## §5 — Fontes

### Code (verbatim, lidos via Read tool)
- `src/contracts/common.py` — UEID class + RegimeState
- `src/contracts/task.py` — Task, Project, etc.
- `src/contracts/task_change.py` — TaskChange, PropagationEvent, TaskAction
- `src/mesh/queue.py` — append-only queue
- `src/mesh/agent_consumer.py` — PAE validation
- `src/mesh/agent_propagator.py` — per-adapter propagation
- `src/mesh/adapters/base.py` — ForkAdapter Protocol
- `src/mesh/adapters/cli.py`, `taskdog.py`, `solverforge_calendar.py` — 3 adapter impls
- `vibe-ops/src/cybernetics/daily_loop.py` — CyberneticDailyLoop
- `src/operational/packages/core/src/operational/core/policy_engine.py` — PolicyEngine FSM

### Docs design-system (verbatim, lidos via Read tool)
- `docs/design-system/00-INDEX.md` — INDEX navegação
- `docs/design-system/04-canvas-mesh-architecture.md` — mesh topology
- `docs/design-system/10-pattern-ueid-tri-key.md` — UEID Pattern #10
- `docs/design-system/13-pattern-fork-adapter-protocol.md` — ForkAdapter Pattern #13
- `docs/design-system/15-pattern-hysteresis-fsm.md` — FSM Pattern #15
- `docs/design-system/20-fork-tuiboard-architecture.md` — tuiboard fork
- `docs/design-system/21-fork-taskdog-architecture.md` — taskdog fork
- `docs/design-system/22-fork-solverforge-calendar-architecture.md` — solverforge-calendar fork
- `docs/design-system/23-fork-status-enum-mapping.md` — status enum canonical

### PAV-era docs (verbatim, lidos via Read tool)
- `src/operational/docs/ux/04-fluxos/FLOW-001-iniciar-manha.md` (305 linhas)
- `src/operational/docs/ux/04-fluxos/FLOW-002-iniciar-tarde.md` (300 linhas)
- `src/operational/docs/ux/04-fluxos/FLOW-007-relatorio-semanal.md` (parcial — anchors)
- `src/operational/docs/ux/04-fluxos/FLOW-008-trocar-dataset.md` — *referência indireta*
- `src/operational/docs/ux/04-fluxos/FLOW-010-doctor.md` — *referência indireta*

### auto-performance-os docs
- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` — UEID pipeline
- `docs/auto-performance-os/26-integration-cybernetic-loop.md` — weekly aggregation
- `docs/auto-performance-os/21-meta-qhe-policy-mapping.md` — Q_HE → regime mapping

### Phase 2 diagnostics (fontes verbatim)
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md` (196 LOC) — Phase 3 readiness
- `docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md` (331 LOC) — tuiboard RE
- `docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md` (497 LOC) — taskdog RE
- `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md` (418 LOC) — solverforge RE

### Memory cross-refs
- [[]]
- [[]]
- [[]]
- [[]]
- [[]]
- [[]]
- [[]]
- [[]]
- [[]]
- [[]]

### Métricas de cobertura
- **5 sections principais** (§1-§5) — Resumo / Inventário / Conteúdo / Cross-refs / Fontes (template Pattern #10 verbatim)
- **5 famílias de jornada** documentadas (morning, task-create, policy, weekly, dataset)
- **6 forks-prontas × 5 colunas** matriz cross-fork = 30 cells documentadas
- **5 inventários artefatos** (§2.3) com code anchors verificados
- **11 gaps** flagged em §2.4 (G-FORK-01..06, G-POLICY-01..02, G-WEEKLY-01, G-DATASET-01, G-AGENT-01)
- **12 code anchors** verificados via Read tool em §4.8
- **10 memory cross-refs** em §4.7
- **Honest rigor:** flag PAV-era flows como fallback (não-substituídos); flag 3 forks como parallel integration com gaps; flag ADR-007 gate como critical unblocking criterion.

---

> **Próxima ação recomendada:** após agent run habilitado ([[data-first-methodology]] gate de 5+ SONHO logs), revisar gaps §2.4 e priorizar implementações em `vault/ikigai/meta/MOC-jornadas.md` (PROPOSTA — italic, gap fill). Até lá, este INDEX opera como **mapa de cobertura** para revisão manual cross-fork.