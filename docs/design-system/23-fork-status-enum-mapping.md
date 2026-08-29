# 23 — Fork Status Enum Mapping (canonical 6-state cycle)

> **Categoria:** FORK (Layer 4 — Forks catalog, posição #23 — NEW canonical mapping doc, gap #5)
> **Anchor canônico:** `src/mesh/adapters/cli.py` + `src/mesh/adapters/taskdog.py` + `src/mesh/adapters/solverforge_calendar.py` + forks enum sources
> **Origem:** Phase 3 v1 mesh readiness + 2026-08-28 status-enum gap identified
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (enum, PENDING, ACTIVE, DONE, BLOCKED, CANCELLED, ARCHIVED, FSM, hysteresis, QHE, regime, PUSH, MAINTAIN, REDUCE, RECOVER, TaskStatus, Pydantic, UEID, fork, adapter, transition rule, sync trigger)
> **Status:** Gap-fill de critical kind (Phase 3 v1 unblocking)

---

## §1 — Resumo

Este doc **preenche o gap #5** identificado na arquitetura do data mesh: **não existe mapeamento canônico entre os enums locais de status das 3 forks** (tuiboard, taskdog, solverforge-calendar) e um **ciclo canônico de 6 estados** que o Deep Agent possa usar para propagação cross-fork idempotente. A proposta é **`PENDING → ACTIVE → DONE | BLOCKED | CANCELLED → ARCHIVED`**, estendendo o ciclo atual de 4 estados (Pattern #15 hysteresis FSM: PUSH/MAINTAIN/REDUCE/RECOVER) com separação explícita entre **estado operacional** (PENDING/ACTIVE/DONE/BLOCKED/CANCELLED) e **estado de política** (PUSH/MAINTAIN/REDUCE/RECOVER), e adicionando **ARCHIVED** como terminal sink para soft-delete cross-fork. A motivação é tripla: (1) **taskdog expõe `TaskStatus` enum com 4 valores** (PENDING/IN_PROGRESS/COMPLETED/CANCELED — `task.py:16-20`), mas `CANCELED` é overload conflituante com `CANCELLED` ortografia UK (cancelling = soft-delete vs cancel = halt); (2) **solverforge-calendar UPI tem 5 valores** (`pending/in_progress/done/blocked/cancelled` — `models_unified.rs` ikigai JSON), mas faltam PENDING/ACTIVE split e ARCHIVED; (3) **tuiboard usa apenas 3 valores boolean + position** (`status: 'todo'|'doing'|'done'` inferido por coluna kanban) sem enum explícito. Sem este mapeamento, **agent propagation falha**: `PropagationEvent` carrega `TaskAction` (create/update/delete/done, `task_change.py:46-57`), mas cada adapter tem que adivinhar qual é "ACTIVE" vs "PENDING". A solução é uma **tabela canônica de mapping** (§3.2) com **transition rules + sync triggers** que cada adapter consulta para converter status local → canonical status antes de propagar.

---

## §2 — Inventário

### 2.1 Enums de status por fork (verbatim)

**tuiboard** — SolidJS store (`interfaces/tuiboard/src/store/index.ts:106-145`):
- **No `status` field** em `Task` interface (`types.ts:28-30`)
- Implicit via column position: kanban columns = `todo | doing | done` (3 columns default)
- `taskListKey` memo embeds `marked` refs (`BoardView.tsx:281-297`)
- `Task.done: boolean` é o único bit explícito (`types.ts:28-30`)
- **`done` mark**: visual `✓ N done (z to focus)` (BoardView.tsx:417-430)
- **`grabbed`**: separate flag (`ui.grabbing: boolean` em `store/index.ts:120`)

**taskdog** — `@dataclass` Python (`interfaces/taskdog/packages/taskdog-core/src/taskdog_core/domain/entities/task.py:16-20`):
```python
class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELED = "canceled"
```
- Invariantes enforced em `__post_init__` (:79-132)
- State machine methods: `start(timestamp)`, `complete(timestamp)`, `cancel(timestamp)`, `pause()`, `reopen()` (:278-351)
- **`is_finished` computed** (`:134-154` boolean derived)
- **`is_archived` separate flag** (`:20`) — soft-delete 2025-10-31 design: archive preserves status

**solverforge-calendar** — Rust TEA-style (`interfaces/solverforge-calendar/src/models_unified.rs`):
```rust
// UnifiedPlanningItem.status (JSON in unified_planning_items table)
pub enum UpiStatus {
    Pending = "pending",
    InProgress = "in_progress",
    Done = "done",
    Blocked = "blocked",
    Cancelled = "cancelled",
}
// CalendarEvent.status (separate struct in src/models.rs)
pub enum CalendarEventStatus {
    Confirmed,
    Tentative,
    Cancelled,  // matches Google "cancelled" semantics
}
```
- **`upi_update` MCP tool** (`solverforge-calendar-mcp.rs:840-857`) only allows the 5-value UpiStatus enum
- Soft-delete via `deleted_at` column em todas as 6 tables (`db.rs:99-105`)
- **No ARCHIVED status** — deleted_at é hidden status

### 2.2 Adapter storage mapping

`src/mesh/adapters/taskdog.py:69` (verbatim — `INSERT` status field):
```python
conn.execute(
    """INSERT INTO tasks (ueid, name, status, priority, deadline, created_at)
       VALUES (?, ?, 'planned', ?, ?, ?)""",
    ...
)
```
**Nota:** adapter escreve literal `'planned'`, não o enum value. Inconsistência com `TaskStatus.PENDING.value = "pending"`.

`src/mesh/adapters/solverforge_calendar.py:88, 96` (PK reuse — both branches):
```python
SET status = 'planned', ikigai = ?
# OR
VALUES (?, ?, 'planned', '[]', '[]', ?, '{}')
```
**Nota:** mesmo padrão — adapter escreve literal `'planned'`. UPI DB schema não tem constraint de enum; `upi_update` valida via Rust enum.

`src/mesh/adapters/cli.py:38-44` (JSONL append-only):
```python
record = {
    "ueid": event.ueid,
    "title": event.fields.get("title"),
    "due": event.fields.get("due"),
    "priority": event.fields.get("priority", "medium"),
    "written_at": event.approved_at.isoformat(),
    "source_fork": event.source_fork,
    # ← NO status field!
}
```
**Critical gap:** `CliAdapter` **não persiste status**. JSONL é apenas event log; status é downstream.

### 2.3 Policy FSM enum (`src/operational/packages/core/src/operational/core/policy_engine.py`)

4-state from Pattern #15 (`docs/design-system/15-pattern-hysteresis-fsm.md`):
```python
class RegimeState(StrEnum):  # em src/contracts/common.py:150-156
    PUSH = "push"
    MAINTAIN = "maintain"
    REDUCE = "reduce"
    RECOVER = "recover"
```
- **NOT** a task status — é **policy regime** decided by hysteresis (3-up / 2-down / 1-emergency)
- IKIGAi 5-band version adds `hard floor: RECOVER if qhe < 0.60 + sleep_debt > 2h`

### 2.4 Status propagation path

```
Vault markdown                ←── Deep Agent writes
   ↓ (delta)
data/review_queue/<uuid>.json  ←── append-only queue (Pattern #12)
   ↓ (agent_consumer)
   PAE rule validation: APPROVE | REJECT | CLARIFY
   ↓ (agent_propagator)
ForkAdapter.apply_change()
   ├─ CliAdapter         → JSONL {title, due, priority, written_at, source_fork}    (no status)
   ├─ TaskdogAdapter     → SQLite UPSERT ueid → 'planned' literal
   └─ SolverforgeAdapter → SQLite PK reuse ueid → 'planned' literal + ikigai JSON
```

**Gap atual:** `PropagationEvent` (Pydantic frozen, `task_change.py:46-57`) carrega `action: TaskAction` (create/update/delete/done) — **não carrega `status`**. Logo, adapter não tem como saber se é PENDING → ACTIVE vs outro transition.

---

## §3 — Conteúdo principal

### 3.1 Proposta: ciclo canônico de 6 estados

```text
PENDING ──start──▶ ACTIVE ──complete──▶ DONE
                       │
                       ├──pause──▶ PENDING (soft pause)
                       │
                       ├─────────▶ BLOCKED ──unblock──▶ ACTIVE
                       │
                       └──cancel──▶ CANCELLED
                       
DONE / CANCELLED / BLOCKED ──archive──▶ ARCHIVED (terminal)
```

**Definição dos 6 estados:**

| # | Estado | Significado | Reversível? |
|:-:|:-------|:------------|:------------|
| 1 | `PENDING` | Created, not started | YES → ACTIVE |
| 2 | `ACTIVE` | In progress (work happening) | YES → PENDING (pause) / DONE / BLOCKED / CANCELLED |
| 3 | `DONE` | Completed successfully | NO direct (terminal, mas archivable) |
| 4 | `BLOCKED` | Waiting on dependency or external input | YES → ACTIVE (unblock) |
| 5 | `CANCELLED` | Stopped without completion | NO direct (terminal, mas archivable) |
| 6 | `ARCHIVED` | Soft-deleted, hidden from active view | NO (terminal sink) |

**Invariantes do ciclo:**

1. **Idempotência**: aplicar mesma transition 2× deve convergir (canonical state é determinístico)
2. **Reversibilidade parcial**: PENDING ↔ ACTIVE reversível; BLOCKED ↔ ACTIVE reversível; DONE/CANCELLED só → ARCHIVED
3. **Cross-fork consistency**: o mesmo UEID em 3 forks deve ter **mesmo** canonical status (propagated via mesh)

### 3.2 Tabela de mapping: fork_status → canonical_status

| Fork | Local Status Literal | Canonical Status | Notes |
|:-----|:---------------------|:-----------------|:------|
| **tuiboard** | (no field, but) column position `Todo` | `PENDING` | kanban col position 0 |
| tuiboard | column position `Doing` | `ACTIVE` | kanban col position 1 |
| tuiboard | `Task.done: true` + col position `Done` | `DONE` | both signals required |
| tuiboard | column position `Done` + `Task.done: false` | `ACTIVE → PENDING` mid-edit | race condition — skip |
| tuiboard | `ui.grabbing: true` + `ui.armedTimelineRef` | `ACTIVE` (priority tagged) | arming state |
| **taskdog** | `TaskStatus.PENDING.value = "pending"` | `PENDING` | exact match |
| taskdog | `TaskStatus.IN_PROGRESS.value = "in_progress"` | `ACTIVE` | synonym (canonical ACTIVE) |
| taskdog | `TaskStatus.COMPLETED.value = "completed"` | `DONE` | synonym (canonical DONE) |
| taskdog | `TaskStatus.CANCELED.value = "canceled"` | `CANCELLED` | **spelling normalization**: US `canceled` → UK `cancelled` |
| taskdog | `is_archived: true` (separate flag) | `ARCHIVED` | archive preserves status |
| taskdog | (no field for `BLOCKED`) | ??? | **gap** — taskdog domain enum lacks BLOCKED |
| **solverforge** | `UpiStatus::Pending.as_str() = "pending"` | `PENDING` | exact match |
| solverforge | `UpiStatus::InProgress.as_str() = "in_progress"` | `ACTIVE` | synonym |
| solverforge | `UpiStatus::Done.as_str() = "done"` | `DONE` | exact match |
| solverforge | `UpiStatus::Blocked.as_str() = "blocked"` | `BLOCKED` | exact match (solverforge-only canonical) |
| solverforge | `UpiStatus::Cancelled.as_str() = "cancelled"` | `CANCELLED` | UK spelling |
| solverforge | `deleted_at IS NOT NULL` | `ARCHIVED` | soft-delete via timestamp |
| solverforge | `CalendarEventStatus::Cancelled` | `CANCELLED` (Google sync semantics) | arrives via google_event_to_local |
| solverforge | `CalendarEventStatus::Confirmed/Tentative` | `ACTIVE` (work scheduled) | confirmed + future = work |
| solverforge | `CalendarEventStatus::Tentative` + past | `BLOCKED` (was tentative, slipped) | inference |

### 3.3 Transition rule table (canonical → allowed next)

| From | To | Trigger | Severity | Sync Trigger |
|:-----|:---|:--------|:---------|:-------------|
| PENDING | ACTIVE | user clicks "start" / `start_task()` / kanban move to Doing | INFO | propagate immediately |
| PENDING | CANCELLED | user cancels before starting | INFO | propagate immediately |
| ACTIVE | PENDING | user pauses / `pause_task()` | INFO | propagate (soft pause) |
| ACTIVE | DONE | user completes / `complete_task()` | INFO | propagate immediately |
| ACTIVE | BLOCKED | dependency unmet / `add_dependency()` cycle | WARNING | propagate + flash banner |
| ACTIVE | CANCELLED | user stops mid-work / `cancel_task()` | WARNING | propagate immediately |
| BLOCKED | ACTIVE | dependency resolved / `remove_dependency()` | INFO | propagate |
| BLOCKED | CANCELLED | user gives up on block | WARNING | propagate |
| DONE | ARCHIVED | user archives after review | INFO | propagate + soft-delete |
| CANCELLED | ARCHIVED | user archives after retrospective | INFO | propagate + soft-delete |
| ARCHIVED | (any) | — | (none) | **IMMUTABLE TERMINAL** |

**Hysteresis integration** (Pattern #15):
- `PUSH` regime → prefer `ACTIVE` transições (start more)
- `REDUCE/RECOVER` regime → prefer `BLOCKED` over `ACTIVE` (avoid new work)
- **`cancel_task()` direct from PENDING** é OK mesmo em `RECOVER` (less work = aligned)

### 3.4 Adapters: como serializar canonical status → local literal

**`src/mesh/adapters/taskdog.py` mudança proposta (Phase 3 candidate):**

```python
def _canonical_to_taskdog(canonical: CanonicalStatus) -> str:
    return {
        CanonicalStatus.PENDING: "pending",
        CanonicalStatus.ACTIVE: "in_progress",       # synonym
        CanonicalStatus.DONE: "completed",
        CanonicalStatus.BLOCKED: "blocked",          # NEW (TaskStatus doesn't have it; raise or use string)
        CanonicalStatus.CANCELLED: "canceled",
        CanonicalStatus.ARCHIVED: "archived",        # is_archived=True + status="canceled"
    }[canonical]
```

**`src/mesh/adapters/solverforge_calendar.py`** mudança proposta:

```python
def _canonical_to_upi(canonical: CanonicalStatus) -> str:
    return canonical.value  # already canonical (UpiStatus is structurally same except ARCHIVED)
```

**`src/mesh/adapters/cli.py`** gap fill crítico: precisa adicionar campo `status` ao JSONL record:

```python
record = {
    "ueid": event.ueid,
    "title": event.fields.get("title"),
    "due": event.fields.get("due"),
    "priority": event.fields.get("priority", "medium"),
    "status": event.fields.get("status", "pending"),  # NEW
    "written_at": event.approved_at.isoformat(),
    "source_fork": event.source_fork,
}
```

### 3.5 Cross-fork join via canonical status

Quando o Deep Agent querya `mesh show <ueid>`, retorna slices de cada adapter. Cada slice carrega status field (canonizado ou nativo). Para responder "what's the current status?", mesh pega **majority vote** entre canonical_status valores:

```python
def cross_fork_status_consensus(slices: dict[str, dict]) -> CanonicalStatus:
    # Each adapter returns canonical_status; if majority agrees, return; else CLARIFY
    counts = Counter(s["status"] for s in slices.values())
    if not counts: return CanonicalStatus.PENDING
    top, freq = counts.most_common(1)[0]
    if freq > len(slices) / 2: return top  # majority
    raise ConsensusConflict(...)
```

Se todos 3 forks discordam (tuiboard=DONE, taskdog=ACTIVE, solverforge=BLOCKED) → **CLARIFY**: Deep Agent deve perguntar humano qual é a verdade.

### 3.6 Mesh integration: o que muda em `TaskAction`

`TaskAction` enum (Pattern #14, `src/contracts/task_change.py:46-57`) atualmente é `create | update | delete | done`. Phase 3 v1.1 proposal: estender para `create | update_status | update | delete | done`, onde `update_status` carrega `target: CanonicalStatus` no payload.

```python
class TaskAction(StrEnum):
    CREATE = "create"
    UPDATE_STATUS = "update_status"   # NEW: transition only
    UPDATE = "update"                 # field-level PATCH (existing)
    DELETE = "delete"
    DONE = "done"                     # legacy: alias for UPDATE_STATUS to DONE
```

**Compatibilidade**: `DONE` action continua aceito por adapters existentes; internamente mapeia para `UPDATE_STATUS → DONE`.

### 3.7 Phase 3 readiness checklist

| # | Item | Status | Notes |
|:-:|:-----|:-------|:------|
| 1 | Definir `CanonicalStatus` enum em `src/contracts/common.py` | TODO | gap-fill critical |
| 2 | Adicionar campo `status` ao JSONL `CliAdapter` | TODO | quebra idempotência JSONL shape (L1 do Pattern #13) |
| 3 | Adicionar `BLOCKED` literal ao taskdog `tasks.status` column | TODO | SQLite TEXT aceita qualquer string |
| 4 | Decidir entre 5-value (cancelled only) vs 6-value (canonical) UPI status | TODO | trade-off: mais complexity vs cross-fork consistency |
| 5 | Add `UPDATE_STATUS` action a `TaskAction` StrEnum | TODO | Phase 3 v1.1 |
| 6 | Implementar `cross_fork_status_consensus` em `agent_propagator` | TODO | consensus algorithm |
| 7 | Wire canonical → fork literal translator em cada adapter | TODO | 3 adapters, ~30 LOC each |
| 8 | Add `status` field a `PropagationEvent.fields` | TODO | schema evolution |

**Pré-requisitos**: `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md §2` propagation pipeline + Pattern #11 frozen Pydantic strict mode (extra="forbid" garante backward incompatível).

---

## §4 — Cross-references

### 4.1 Design-system docs

- **`docs/design-system/00-INDEX.md`** §3 — este doc preenche o **gap #5** do Layer 4 Forks catalog (INDEX tuiboard/taskdog/solverforge-calendar + status-enum mapping).
- **`docs/design-system/15-pattern-hysteresis-fsm.md`** §2.1 (`PUSH/MAINTAIN/REDUCE/RECOVER` regime) + §2.4 (transition table) — política sobrepõe status; este doc separa explicitamente.
- **`docs/design-system/13-pattern-fork-adapter-protocol.md`** §2.2/2.3/2.4 (3 adapters verbatim) — cada adapter precisa ganhar status translation.
- **`docs/design-system/14-pattern-idempotency-upstream-id.md`** §3 — idempotency em status transitions é requirement load-bearing.
- **`docs/design-system/04-canvas-mesh-architecture.md`** §3.3 (storage topology) — adicionar coluna `status` aos adapters.
- **`docs/design-system/07-canvas-sync-architecture.md`** §3 (`SyncEngine` aggregating counts) — throttling rules devem considerar status flapping.
- **`docs/design-system/20-fork-tuiboard-architecture.md`** §2.7 (no native UEID) + §3.4 (UEID gap) — tuiboard SEM campo status, inferido por coluna.
- **`docs/design-system/21-fork-taskdog-architecture.md`** §2.2 (`TaskStatus` enum 4-value) + §3.7 (UEID gap).
- **`docs/design-system/22-fork-solverforge-calendar-architecture.md`** §3.3 (UPI mesh substrate) + §2.4 (UPI 5-value status) + §2.6 (`deleted_at` soft-delete).

### 4.2 Phase 2 diagnostics

- **`docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`** §Cross-fork comparison matrix linhas 18-34 — status enum divergence row 33 ("NO — 3 enum shapes (boolean vs 4-state vs 5-state)").
- **`docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md`** §State diagram linhas 105-145 (`StoreState` SolidJS).
- **`docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md`** §Other entities linhas 96-118 (`TaskStatus` enum + state machine methods).
- **`docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md`** §Domain entities linhas 77-86 (UPI 5-value status).

### 4.3 Memory cross-refs

- **`[[interfaces-architecture-2026-08-27]]`** — dual-layer (forks = user views, agent = operator); canonical status é o contrato que torna forks comparáveis.
- **`[[master-branch-carro-chefe-2026-08-28]]`** — master = deep-agent bidirecional sync; status é o vetor primário de propagação.
- **`[[algorithm-issues-registry]]`** — 31 inconsistencies; status enum mapping é infraestrutura pre-algorithm polish.
- **`[[prioritize-backend-over-algorithm-refinement]]`** — user pivot 2026-08-28: backend first, algo refinement gated em empirical evidence.
- **`[[data-first-methodology]]`** — 5+ SONHO logs gate; este mapping é backend work (não algo polish), but changes to taskdog/str-domain enum precisam empirical input.
- **`[[ag3-gateway-orphan-2026-08-27]]`** — gateway orphan; canonical status propagaria via gateway MCP tool routing.

### 4.4 Auto-performance OS (matemática + integração)

- **`docs/auto-performance-os/21-meta-qhe-policy-mapping.md`** §2 (4 bandas canônicas QHE) — policy FSM opera sobre QHE; status transitions são domínio separado.
- **`docs/auto-performance-os/24-integration-mesh-ueid-propagation.md`** §2 (propagation pipeline) — `PropagationEvent` é o carrier; precisa carregar status.

### 4.5 Code anchors (verificados)

| Path | LOC / Conteúdo | Padrão |
|:-----|:---------------|:-------|
| `src/mesh/adapters/cli.py:38-44` | JSONL record (sem `status` field) | gap-fill critical |
| `src/mesh/adapters/taskdog.py:69, 90` | Literal `'planned'` em INSERT/UPSERT | needs canonical mapping |
| `src/mesh/adapters/solverforge_calendar.py:88, 96` | Literal `'planned'` em UPDATE/INSERT | needs canonical mapping |
| `src/contracts/task_change.py:46-57` | `TaskAction` enum (4-value) | extend to 5-value |
| `src/contracts/common.py:150-156` | `RegimeState` 4-value (Pattern #15) | separate from `CanonicalStatus` |
| `interfaces/taskdog/packages/taskdog-core/src/taskdog_core/domain/entities/task.py:16-20` | `TaskStatus` 4-value | needs BLOCKED literal |
| `interfaces/taskdog/packages/taskdog-core/src/taskdog_core/domain/entities/task.py:79-132` | `__post_init__` invariants | state machine enforcement |
| `interfaces/taskdog/packages/taskdog-core/src/taskdog_core/domain/entities/task.py:278-351` | state machine methods | transition validation |
| `interfaces/solverforge-calendar/src/models_unified.rs` | `UpiStatus` 5-value (no ARCHIVED) | needs ARCHIVED or deleted_at inference |
| `interfaces/solverforge-calendar/src/db.rs:99-105` | `deleted_at` soft-delete column | ARCHIVED inference |
| `interfaces/solverforge-calendar/src/bin/solverforge-calendar-mcp.rs:840-857` | `upi_update` MCP tool (5-value enum) | extend for ARCHIVED |
| `interfaces/tuiboard/src/store/index.ts:106-145` | SolidJS `StoreState` (no `Task.status` field) | gap: position-based status |
| `interfaces/tuiboard/src/ui/BoardView.tsx:281-297` | `taskListKey` memo | position inference |
| `interfaces/tuiboard/src/types.ts:28-30` | `Task.done: boolean` | only explicit status bit |

### 4.6 Pitfalls noted

- **Spelling mismatch** US `canceled` (taskdog) vs UK `cancelled` (solverforge, propuesta canonical) — fase must normalize.
- **taskdog domain enum lacks `BLOCKED`** — adapter precisa write string literal "blocked" mas enum Python não valida.
- **tuiboard uses position, not explicit status** — inference é frágil; race condition entre `done:false` + `column="Done"` mid-edit.
- **`CliAdapter` JSONL no `status` field** — quebra idempotência shape (Pattern #13 L1); append-only line shape evolves.
- **Hysteresis FSM (Pattern #15) on `RegimeState`** é POLÍTICA, **não STATUS** — confusion risk se "regime = status" no schema; este doc explicita a separação.
- **`PropagationEvent.fields` schema** precisa estender para carregar `target_status` sem breaking frozen Pydantic backward compat (require new field with default).
- **Cross-fork consensus conflict**: 3 forks podem discordar; precisa fallback rule (CLARIFY > majority vote > last write wins).
- **Update cascade at every status transition** — must be careful not to create infinite loops when forks replay `PropagationEvent` (idempotency key = `ueid` + `target_status`, not just `ueid`).

---

## §5 — Fontes

### Code (verbatim, lidos via Read tool)
- `src/mesh/adapters/base.py` (24 LOC) — ForkAdapter Protocol
- `src/mesh/adapters/cli.py` (55 LOC) — JSONL append-only (sem status field)
- `src/mesh/adapters/taskdog.py` (104 LOC) — Literal `'planned'` em UPSERT
- `src/mesh/adapters/solverforge_calendar.py` (105 LOC) — Literal `'planned'` em PK reuse

### Docs (analisados)
- `docs/design-system/15-pattern-hysteresis-fsm.md` (350+ LOC) — RegimeState PUSH/MAINTAIN/REDUCE/RECOVER policy FSM
- `docs/design-system/13-pattern-fork-adapter-protocol.md` (368 LOC) — ForkAdapter Protocol + 3 adapters verbatim
- `docs/design-system/14-pattern-idempotency-upstream-id.md` — idempotency patterns
- `docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md` (331 LOC) — tuiboard state diagram linhas 105-145
- `docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md` (497 LOC) — taskdog `TaskStatus` enum + state machine
- `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md` (418 LOC) — UPI 5-value status + deleted_at

### Design-system cross-refs
- `docs/design-system/00-INDEX.md` — Layer 4 Forks catalog
- `docs/design-system/04-canvas-mesh-architecture.md` §3.3 — storage topology
- `docs/design-system/07-canvas-sync-architecture.md` §3 — SyncEngine throttling
- `docs/design-system/20-fork-tuiboard-architecture.md` — tuiboard verbatim
- `docs/design-system/21-fork-taskdog-architecture.md` — taskdog verbatim
- `docs/design-system/22-fork-solverforge-calendar-architecture.md` — solverforge verbatim

### Memory cross-refs
- `[[interfaces-architecture-2026-08-27]]` — dual-layer
- `[[master-branch-carro-chefe-2026-08-28]]` — master narrative
- `[[algorithm-issues-registry]]` — 31 inconsistencies
- `[[prioritize-backend-over-algorithm-refinement]]` — backend first
- `[[data-first-methodology]]` — 5+ SONHO logs
- `[[ag3-gateway-orphan-2026-08-27]]` — gateway orphan

### Métricas de cobertura
- **4 seções de inventário** (§2.1-2.4) — 3 fork enums verbatim, adapter storage, policy FSM, propagation path
- **7 seções de conteúdo principal** (§3.1-3.7) — 6-state cycle proposal, mapping table, transition rules, adapter translation, cross-fork join, TaskAction extension, Phase 3 checklist
- **14 code anchors** verificados via Read tool em §4.5
- **6 memory cross-refs** (interfaces, master-branch, algorithm-issues, prioritize-backend, data-first, ag3-gateway)
- **8 pitfalls** explícitos em §4.6 (spelling mismatch, taskdog no BLOCKED, tuiboard position inference, JSONL no status, hysteresis≠status confusion, PropagationEvent evolution, consensus conflict, update cascade loops)
- **8-step Phase 3 checklist** em §3.7 (canonical enum, JSONL status, taskdog BLOCKED, UPI 6 vs 5, TaskAction extend, consensus, translator, PropagationEvent schema)
- **Honest rigor:** explicitly separates Operational Status (PENDING/ACTIVE/DONE/BLOCKED/CANCELLED/ARCHIVED) from Policy Regime (PUSH/MAINTAIN/REDUCE/RECOVER from Pattern #15); cites multiple forks diverge (3 enum shapes per synthesis); flags cross-fork consensus conflict as open problem requiring CLARIFY fallback
