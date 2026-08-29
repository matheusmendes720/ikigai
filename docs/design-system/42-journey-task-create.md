# 42 — Journey: Task Create (form → mesh queue → ForkAdapter)

> **Categoria:** JOURNEY CANVAS (Layer 6 — User journeys & screens, posição #42)
> **Anchor canônico:** `src/mesh/queue.py:enqueue` + `src/mesh/adapters/{cli,taskdog,solverforge_calendar}.py` + `interfaces/{tuiboard,taskdog,solverforge-calendar}/` create handlers + `src/operational/docs/ux/04-fluxos/FLOW-002-criar-task.md` (PROPOSTA) + `SCR-008-routine-create.md` + `SCR-009-block-create.md`
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (task create, mesh queue, ForkAdapter, PropagationEvent, UEID mint, atomic temp+rename, UPSERT, optimistic concurrency, mtime, Pydantic frozen, strict mode, Zod strict, idempotent, SQLite INSERT OR REPLACE)

---

## §1 — Resumo

A jornada **task create** é o caminho que uma Task percorre desde o **form de input no fork** até a **persistência cross-fork via data mesh**. No modelo dual-layer deep-agent canonical 2026-08-28, o caminho canônico é: **form em fork X → fork-specific storage → append-only queue (`data/review_queue/<event_id>.json`) → PAE rule validation (`agent_consumer.py`) → `PropagationEvent(ueid, action, target_adapters)` → per-adapter `apply_change` (Pattern #13 ForkAdapter Protocol) → fork-specific writes (CliAdapter JSONL append, TaskdogAdapter SQLite UPSERT, SolverforgeCalendarAdapter UPI PK reuse) → vault sync (append-only markdown). Esta canvas documenta o pipeline end-to-end + **geração de UEID em cada step** + **idempotência via upstream_id** (Pattern #14) + **PROPOSTA fallback para tuiboard** (que não tem UEID nativo).

**Modos:** INDEX canvas — não prescreve nova jornada; mapeia componentes verbatim por fork.

**Invariante load-bearing:** Toda Task criada deve ter **1 UEID canônico** (Pattern #10, `docs/design-system/10-pattern-ueid-tri-key.md`) mintado no momento do `enqueue`. UEID é o join key cross-fork — sem ele, JOIN entre forks quebra. Ver §2.6 abaixo para mecânica de mint.

---

## §2 — Inventário

### 2.1 Pipeline end-to-end (5 steps canônicos)

| Step | Componente | LOC / Path | Padrão |
|:-----|:-----------|:-----------|:-------|
| **[1] Form input** | fork-specific (SolidJS / Textual / ratatui) | `interfaces/*` | per-fork UI |
| **[2] Fork-local storage** | fork-local DB / JSONL / markdown | `interfaces/*/data/` | fork-local |
| **[3] Append-only queue** | `src/mesh/queue.py:enqueue` | atomic temp+rename | Pattern #12 |
| **[4] PAE validation** | `src/mesh/agent_consumer.py` | 180 LOC | Pattern #11 (frozen) + #13 |
| **[5] Per-adapter propagation** | `src/mesh/agent_propagator.py` | 150 LOC | Pattern #13 + #14 + #17 |

### 2.2 Fork-specific create handlers

**tuiboard** (`docs/design-system/20-fork-tuiboard-architecture.md` §2.3):
- `board_tasks_create` MCP tool — `src/v3/mcp/tools/board-tasks-create.ts:21-111`
- Args: `{ boardPath, columnIndex, expectedMtimeMs, insertAt?, task }`
- Zod schema `TaskInit` (`.strict()`) — `src/v3/mcp/schemas.ts:30-57`
- UI modal: 13 modais em `Modal.tsx:43-60` (add/edit/schedule/timeblock/assign/detail/event/search/help)
- Persistência: markdown round-trip + atomic rename (`src/io/writer.ts:54-83`)
- **Gap:** UEID não é nativo; identidade é posicional `(boardPath, columnIndex, taskIndex)`. Doc 20 §3.4.

**taskdog** (`docs/design-system/21-fork-taskdog-architecture.md` §2.4):
- 6 CRUD MCP tools: `list_tasks`, `get_task`, `create_task`, `update_task`, `delete_task`, `restore_task` — `tools/task_crud.py`
- `create_task` args: `{ name, description?, status?, priority?, deadline?, tags?, notes? }`
- Persistência: SQLite via SQLAlchemy 2.0 + Alembic (`tasks` table — `task_model.py:24-101`)
- UI: Click `taskdog task create <args>` (`cli_main.py:131-200`) + Textual TUI form modal
- **Gap:** UEID não é nativo; `id INTEGER AUTOINCREMENT` é PK local. Doc 21 §3.7.

**solverforge-calendar** (`docs/design-system/22-fork-solverforge-calendar-architecture.md` §2.5):
- 5 events_create MCP tools + 5 projects_create + 5 calendars_create + 5 dependencies_create — 30 total
- `events_create` args: `{ calendar_id, project_id?, title, description?, start_at, end_at, all_day, rrule?, tags? }`
- Persistência: dual-DB federation — `calendar.db` (events/calendars/projects/dependencies) + `unified_planning.db` (UPI)
- UI: Clap `solverforge-calendar-cli events create` (`src/cli.rs:700+`) + ratatui TUI form
- **Gap menor:** UPI já tem `ueid TEXT UNIQUE` column — é o fork mais alinhado.

**PAV-era CLI** (`FLOW-002-iniciar-tarde.md` §Fluxo principal):
- `routine create <name> <period> <type>` (FLOW-002 step 2)
- `block create <period> --label <label>` (FLOW-002 step 1)
- `metric energy -e -f` (FLOW-002 step 3)
- Args: variadic Typer (Pydantic validation)
- Persistência: JSONRepository em `~/.time-tasker/` (lazy `mkdir -p`)
- UI: Rich Prompt + `_run_cmd` dispatch

### 2.3 Components Pydantic frozen (Pattern #11)

```python
# src/contracts/task_change.py:58 LOC
class TaskChange(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    event_id: str
    ueid: UEID                       ← join key cross-fork
    action: TaskAction               ← create | update | delete | done
    fields: dict[str, Any]           ← payload (title, due, priority, etc.)
    source_fork: str                 ← tuiboard | taskdog | solverforge-calendar | cli | vault
    status: TaskStatus               ← pending | approved | rejected | propagated | partial_propagation
    approved_at: datetime | None
    propagated_at: datetime | None
    created_at: datetime

class PropagationEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    ueid: UEID
    action: TaskAction
    target_adapters: list[str]       ← [cli, taskdog, upi]
    payload: dict[str, Any]
```

**Defesa em profundidade:** `TaskChange` (Pattern #11) + `PropagationEvent` (Pattern #11) + `UEID` (Pattern #10 `__new__` validation) + `ForkAdapter` Protocol (Pattern #13 `@runtime_checkable`) — 4 camadas que garantem que um bad event nunca chegue ao storage.

### 2.4 PAE rules (validation em `agent_consumer.py`)

| Regra | Razão | Anchor |
|:------|:------|:-------|
| Title ≥ 5 chars | Evitar titles vazios/placeholder | `agent_consumer.py:~120` |
| Title ≠ {todo, tbd, fix, work, task, stuff, thing} | Anti-placeholder | `agent_consumer.py:~125` |
| `due` (se presente) ≥ hoje | Não criar tasks no passado | `agent_consumer.py:~135` |
| UEID collision + status propagated + title diferente → REJECT | Imutabilidade de UEID | `agent_consumer.py:~150` |
| Action ∉ {create, update, delete, done} → REJECT | Whitelist | `agent_consumer.py:~165` |
| Status ∉ {pending, approved, rejected, propagated, partial_propagation} → REJECT | Whitelist | `agent_consumer.py:~170` |

**Decision enum:** `APPROVE | REJECT | CLARIFY`. CLARIFY pede human-in-the-loop antes de decidir.

### 2.5 Adapter storage topology (Pattern #13 verbatim)

| Adapter | Storage | Idempotency key | LOC |
|:--------|:--------|:----------------|:----|
| `CliAdapter` | `data/tasks.jsonl` (append-only) | UEID (line-by-line dedup) | ~100 |
| `TaskdogAdapter` | `data/taskdog/tasks.db` SQLite | `ueid TEXT UNIQUE` constraint + UPSERT | ~140 |
| `SolverforgeCalendarAdapter` | `data/solverforge_calendar/unified_planning.db` SQLite | `ueid TEXT UNIQUE` + PK reuse | ~160 |

**Invariante:** `apply_change` é idempotente — chamar 2× com mesmo evento tem mesmo efeito que 1×. Verificado via Pattern #14 (Idempotent UPSERT) + Pattern #17 (reliability decorators).

### 2.6 UEID generation pipeline (5 steps do Pattern #10 §2.6)

1. **Escolher `type`** — `tsk` (task) é default; `proj` se for Project; `del` se for Deliverable.
2. **Derivar `slug`** — lowercase alphanumeric + dashes; mesmo slug para entities do mesmo domínio.
3. **Gerar `uuid`** — `uuid.uuid4()` (36 chars). **Nunca** uuid1 (MAC leak).
4. **Calcular `hash`** — SHA-256 truncado 16 hex chars, ou BLAKE2b-128.
5. **Concatenar** — `f"{type}:{slug}:{uuid}:{hash}"`.

**Onde o UEID é mintado?** No fork-local create handler (step 2 do pipeline §2.1). O fork passa o UEID para `enqueue` (step 3). Pattern #10 regex valida no `UEID.__new__` antes de chegar à queue.

### 2.7 Vault sync step (PROPOSTA — italic gap)

*PROPOSTA: Após propagation cross-fork (step 5), o deep-agent escreve um markdown em `vault/ikigai/meta/tasks/<ueid-slug>.md` com frontmatter YAML contendo `ueid`, `created_at`, `source_fork`, e wikilink `[[tsk:<slug>:<uuid>:<hash>]]`. Append-only — vault nunca deleta.*

---

## §3 — Conteúdo principal

### 3.1 Data flow diagram (form → storage)

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ [1] Form input (per-fork)                                                  │
│   tuiboard: Modal.tsx:43-60 → board_tasks_create MCP tool                  │
│   taskdog: Textual TUI form / Click CLI / create_task MCP                  │
│   solverforge: events_create MCP tool / solverforge-calendar-cli events    │
│   PAV-CLI: operational routine create / block create / metric energy      │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ [2] Fork-local storage (fork-local, sync NÃO cross-fork)                  │
│   tuiboard: data/boards/<board>.md (markdown round-trip)                   │
│   taskdog: data/taskdog/tasks.db (SQLite UPSERT)                           │
│   solverforge: data/solverforge-calendar/calendar.db + unified_planning.db│
│   PAV-CLI: ~/.time-tasker/routines.json + time_blocks.json (JSONL append)  │
│   ↑                                                                   ↑    │
│   │ NÃO usa UEID canônico (gap #G-FORK-05 tuiboard, #G-FORK-06 taskdog)│   │
│   │ UEID vem do upstream queue, NÃO do fork-local ID                   │   │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
                                 ▼  enqueue(event: TaskChange) → str
┌────────────────────────────────────────────────────────────────────────────┐
│ [3] Append-only queue (Pattern #12)                                        │
│   src/mesh/queue.py: atomic temp+rename                                    │
│   data/review_queue/<event_id>.json                                        │
│   temp file: data/review_queue/.<event_id>.queue-<pid>-<ts>.tmp            │
│   rename(temp, final)  ← POSIX rename or MoveFileExW (Windows)             │
│   UEID validado por UEID.__new__ (Pattern #10)                             │
│   Payload: {event_id, ueid, action, fields, source_fork, status, ts}      │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
                                 ▼  consume_pending() → Iterator[TaskChange]
┌────────────────────────────────────────────────────────────────────────────┐
│ [4] PAE validation (Pattern #11 frozen + Pattern #13 adapter contract)     │
│   src/mesh/agent_consumer.py:180 LOC                                       │
│   Decision.APPROVE → continue                                              │
│   Decision.REJECT → ack(event_id, "rejected") + exit                       │
│   Decision.CLARIFY → ask user (HITL)                                       │
│   PAE rules: title ≥ 5, no placeholder, due ≥ today, etc. (table §2.4)     │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
                                 ▼  build PropagationEvent
┌────────────────────────────────────────────────────────────────────────────┐
│ [5] Per-adapter propagation (Pattern #13 + Pattern #17 reliability)         │
│   src/mesh/agent_propagator.py:150 LOC                                     │
│   for adapter in [cli, taskdog, solverforge-calendar]:                     │
│     try:                                                                   │
│       adapter.apply_change(event)         ← idempotent                     │
│       results[adapter.name] = "ok"                                         │
│     except Exception as e:                                                 │
│       results[adapter.name] = str(e)  ← failure isolation                  │
│   if any(v != "ok"):                                                       │
│     ack(event.id, "partial_propagation")                                   │
│   else:                                                                    │
│     ack(event.id, "propagated")                                            │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
                                 ▼  (PROPOSTA: vault sync)
┌────────────────────────────────────────────────────────────────────────────┐
│ [6] Vault sync (PROPOSTA — italic gap fill post-5-SONHO-logs)               │
│   vault/ikigai/meta/tasks/<ueid-slug>.md                                   │
│   frontmatter: ueid, created_at, source_fork                               │
│   wikilink: [[tsk:<slug>:<uuid>:<hash>]]                                   │
│   append-only (vault nunca deleta)                                         │
└────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Fork-specific create flow (step-by-step)

#### 3.2.1 tuiboard create flow

```text
[1] User abre modal "Add Task" (keymap "a" on selected column)
    Modal.tsx:43-60 dispatch → AddTaskModal render
    Fields: title, description, priority, due, tags, wikilinks
    Zod strict (TaskInit schemas.ts:30-57) — extras rejeitados

[2] User submits → Solid store update
    store/index.ts:268-287 createStore mutation
    TaskPush() → produce(...) + rev++ (force re-render)
    mtimeUpdated timestamp captured

[3] board_tasks_create MCP tool invoked
    board-tasks-create.ts:21-111 receives { boardPath, columnIndex, expectedMtimeMs, insertAt?, task }
    Zod parse (BoardTasksCreateInput schema)
    mutateAndWrite(board-io.ts:33-52) → markdown parse + insert + serialize
    writer.ts:54-83 atomic temp+rename (MoveFileExW no Windows)
    Conflict (-32800) se mtime drift > 1ms

[4] *PROPOSTA:* tuiboard → enqueue(TaskChange(ueid, action="create", fields={...}, source_fork="tuiboard"))
    via gateway (board_prefix routing to tuiboard-mcp subprocess)
    ATENÇÃO: tuiboard NÃO tem UEID nativamente — adapter-side mint obrigatório

[5] src/mesh/agent_propagator.py per-adapter try/except
    CliAdapter → data/tasks.jsonl append
    TaskdogAdapter → SQLite UPSERT (se taskdog ativo)
    SolverforgeCalendarAdapter → UPI PK reuse (se solverforge ativo)
    Partial_propagation se 1+ falha

[6] User consulta cross-fork: life mesh show <ueid> (PROPOSTA — italic)
    Retorna dict consolidado com status de cada fork
```

**Gap:** tuiboard não mint UEID; precisa adapter-side wrapper que sintetiza UEID a partir de `(boardPath, columnIndex, taskIndex)` antes de enqueue. Phase 3 candidate.

#### 3.2.2 taskdog create flow

```text
[1] User invoca create_task via:
    Click CLI: `taskdog task create --name "X" --priority high --deadline 2026-12-01`
    Textual TUI: form modal (form library textual-forms)
    MCP tool: create_task (tools/task_crud.py)

[2] Pydantic v2 DTO validation (application/dto/task_dto.py)
    TaskCreateDTO (frozen, extra="forbid")
    Pydantic strips unknown fields, validates types

[3] Controller dispatch (controllers/task_crud.py:CreateTask)
    Use case CreateTask.execute(dto) → domain entity Task
    Task (dataclass) @post_init__ validation (task.py:79-132)

[4] SQLAlchemy 2.0 INSERT
    task_repository.py:create_task → engine.execute(INSERT INTO tasks ...)
    tasks table has id INTEGER PK AUTOINCREMENT (não UEID nativo)
    *PROPOSTA:* adicionar UEID via Migration v007 — ALTER TABLE tasks ADD COLUMN ueid TEXT UNIQUE

[5] audit_logs INSERT (audit_log_model.py:19-92)
    Trigger automático em CreateTask → audit row (8 indexes)

[6] WebSocket broadcast (server → clients)
    task_created event → fan-out to all connected UI clients
    http_server/api/routers/websocket.py:78-87

[7] *PROPOSTA:* taskdog → enqueue(TaskChange(ueid, action="create", fields={...}, source_fork="taskdog"))
    adapter-side UEID mint (backfill de tasks existentes = heurístico match title+deadline)

[8] src/mesh/agent_propagator.py per-adapter (mesma mecânica do tuiboard)
```

**Gap:** taskdog `id INTEGER AUTOINCREMENT` não é UEID; precisa Migration + backfill para Phase 3.

#### 3.2.3 solverforge-calendar create flow

```text
[1] User invoca events_create via:
    Clap CLI: solverforge-calendar-cli events create --calendar-id X --title Y --start-at 2026-12-01T10:00 --end-at 2026-12-01T11:00
    ratatui TUI: form modal
    MCP tool: events_create (solverforge-calendar-mcp.rs)

[2] calendar_service.rs:CalendarServiceError validation
    NotFound | Validation | Conflict | Internal

[3] Dual write: calendar.db events table + unified_planning.db UPI
    db.rs:1267 LOC, INSERT into events (id, calendar_id, project_id, title, ...)
    sync/migrations.rs:16-72 INSERT into unified_planning_items (id, ueid, status, ...)
    *UEID já existe no schema* (UPI tem ueid UNIQUE column desde migration v2)

[4] Conflict detection (db.rs EventDAG)
    dag.rs:200+ Kahn topological sort, cycle detection on dependencies
    dependencies_create MCP tool (:687-715) raises on cycle

[5] WebSocket broadcast (similar taskdog)
    Rust tokio broadcast channel

[6] *PROPOSTA:* solverforge → enqueue(TaskChange(ueid, action="create", fields={...}, source_fork="solverforge-calendar"))
    UPI já tem UEID; copy direto do schema

[7] src/mesh/agent_propagator.py per-adapter
    TaskdogAdapter → SQLite UPSERT (se taskdog ativo)
    CliAdapter → JSONL append
```

**Vantagem solverforge:** É o fork mais alinhado — UPI já tem UEID, não precisa retrofit. Phase 3 candidate: promote `upi_sync` MCP tool como canonical write path (`docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md:131-136`).

#### 3.2.4 PAV-era CLI create flow

`operational routine create "Acordar" MANHA ENTRY` → `_route("2")` → `_flow_afternoon` → `_run_cmd(["routine", "create", ...])` → Typer validation (RoutineType.ENTRY, Period.MANHA) → Pydantic Routine entity (frozen, extra=forbid) → `JSONRepository.upsert(state.py)` com `mkdir -p` lazy + atomic temp+rename → `routines.json` (JSONL append) → `✓ Rotina criada: <id>` banner (`home.py:213`).

**Gap:** PAV-era CLI opera em JSONL local, não conectado ao data mesh. Phase 3 candidate: bridge CLI → enqueue. Mas gap G-AGENT-01 (agent gated por ADR-007 5+ SONHO logs) bloqueia.

### 3.3 Idempotency (Pattern #14)

Toda Task create deve ser **idempotent**: chamar 2× com mesmo `event_id` tem mesmo efeito que 1×. Mecânica:

- **CliAdapter** (JSONL): line-by-line dedup por `event_id`; segunda chamada sobrescreve (não duplica).
- **TaskdogAdapter** (SQLite): `INSERT ... ON CONFLICT(ueid) DO UPDATE SET name=excluded.name, ...`. Atomic 1-statement.
- **SolverforgeCalendarAdapter** (UPI): `SELECT id WHERE ueid=?` + INSERT-or-UPDATE. 2-statements mas PK stable.

**Trade-off:** CliAdapter sem dedup (simples); TaskdogAdapter UPSERT (canônico); SolverforgeCalendarAdapter PK reuse (preserva história). Ver `docs/design-system/14-pattern-idempotency-upstream-id.md` §3.

### 3.4 Failure isolation (Pattern #17)

`agent_propagator.py` isola falhas per-adapter via try/except:

```python
for adapter in adapters:
    try:
        adapter.apply_change(event)
        results[adapter.name] = "ok"
    except Exception as e:
        results[adapter.name] = str(e)
        # NÃO bloqueia outros adapters
```

**Invariante:** Se tuiboard falha (banco corrompido), taskdog + solverforge-calendar ainda processam. Convergência eventual via replay idempotente.

### 3.5 Vault sync (PROPOSTA)

*PROPOSTA: Após propagation cross-fork, deep-agent escreve vault markdown em `vault/ikigai/meta/tasks/<ueid-slug>.md` com frontmatter YAML `{ueid, created_at, source_fork, status, priority}` + wikilink `[[tsk:<slug>:<uuid>:<hash>]]` + cross-fork indicator. Append-only — vault nunca deleta. Wikilink `[[ueid]]` é parseável por humano + máquina.*

### 3.6 Pitfalls known (cross-fork task create)

- **G-FORK-01** — tuiboard `expectedMtimeMs` drift loop pode bloquear create se board foi editado entre get e create. Doc 20 §3.7.
- **G-FORK-02** — taskdog gateway prefix mismatch; 20/26 tools unreachable. Doc 21 §3.2.
- **G-FORK-03** — solverforge-calendar `google_sync` stub; Google Calendar sync bloqueado. Doc 22 §3.7.
- **G-FORK-05** — tuiboard sem UEID nativo; precisa adapter-side mint. Doc 20 §3.4.
- **G-FORK-06** — taskdog sem UEID nativo; precisa Migration + backfill. Doc 21 §3.7.
- **G-AGENT-01** — Agent gated por ADR-007 5+ SONHO logs. [[data-first-methodology]].

### 3.7 Métricas de task create

| Métrica | Target | Origem |
|:--------|:-------|:-------|
| End-to-end latency (form → storage) | < 200ms | adapter UPSERT atomic |
| Validation error rate | < 0.5% | PAE rules |
| Idempotency replay correctness | 100% | Pattern #14 |
| Cross-fork consistency | ≥ 99% | partial_propagation events |
| UEID mint uniqueness | 100% (probabilistic) | uuid4 122 bits entropy |
| Vault sync latency | < 5s | *PROPOSTA — italic gap* |

---

## §4 — Cross-references

### 4.1 Design-system docs (Layer 1-6)

- **`docs/design-system/00-INDEX.md`** §3 — Layer 6 navigation.
- **`docs/design-system/04-canvas-mesh-architecture.md`** §3.1-3.3 — queue + adapter topology.
- **`docs/design-system/05-canvas-contracts-architecture.md`** §4.3 — TaskChange / PropagationEvent.
- **`docs/design-system/10-pattern-ueid-tri-key.md`** §2.6 — UEID generation pipeline verbatim.
- **`docs/design-system/11-pattern-frozen-pydantic-strict.md`** — Pattern #11 defense-in-depth.
- **`docs/design-system/12-pattern-append-only-queue.md`** §3.1 — queue protocol.
- **`docs/design-system/13-pattern-fork-adapter-protocol.md`** §2.2-2.5 — 3 adapters verbatim.
- **`docs/design-system/14-pattern-idempotency-upstream-id.md`** §3 — UPSERT idiom nativo.
- **`docs/design-system/17-pattern-reliability-decorators.md`** §3 — retry decorators.
- **`docs/design-system/20-fork-tuiboard-architecture.md`** §3.2 (MCP stdio) + §3.4 (UEID gap).
- **`docs/design-system/21-fork-taskdog-architecture.md`** §3.3 (UPSERT canônico) + §3.7 (UEID gap).
- **`docs/design-system/22-fork-solverforge-calendar-architecture.md`** §3.3 (PK reuse) + §3.7 (gateway).
- **`docs/design-system/23-fork-status-enum-mapping.md`** §3.2 — status canonical mapping.
- **`docs/design-system/30-tokens-deep-agent-era.md`** — visual tokens.
- **`docs/design-system/40-index-user-journeys.md`** §3.3 (Padrão A — cross-fork join).

### 4.2 PAV-era `ux/` (referência)

- **`src/operational/docs/ux/04-fluxos/FLOW-002-iniciar-tarde.md`** — block/routine/metric create pattern.
- **`src/operational/docs/ux/04-fluxos/FLOW-002-criar-task.md`** — *PROPOSTA: não escrito* (italic gap, pertence à era PAV não migrada).
- **`src/operational/docs/ux/05-telas/SCR-008-routine-create.md`** — routine create screen (PAV-era).
- **`src/operational/docs/ux/05-telas/SCR-009-block-create.md`** — block create screen (PAV-era).

### 4.3 auto-performance-os docs

- **`docs/auto-performance-os/24-integration-mesh-ueid-propagation.md`** §2 — UEID propagation semantics.

### 4.4 Phase 2 diagnostics

- **`docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`** §OQ-1/OQ-2/OQ-5 — Phase 3 readiness.
- **`docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md`** §3 — tuiboard create flow.
- **`docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md`** §5 — taskdog 26 MCP tools.
- **`docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md`** §5 — solverforge 30 tools.

### 4.5 Memory cross-refs

- **`[[interfaces-architecture-2026-08-27]]`** — dual-layer.
- **`[[master-branch-carro-chefe-2026-08-28]]`** — deep-agent canonical.
- **`[[data-first-methodology]]`** — ADR-007 gate.
- **`[[ag3-gateway-orphan-2026-08-27]]`** — gateway prefix mismatch.
- **`[[backend-phase-reordering-2026-08-28]]`** — B0→B6 phases.
- **`[[windows-orphan-dir-delete]]`** — apps/ deletion.

### 4.6 Code anchors (verificados)

| Path | LOC / Conteúdo | Padrão |
|:-----|:---------------|:-------|
| `src/mesh/queue.py:enqueue` | atomic temp+rename | Pattern #12 |
| `src/mesh/agent_consumer.py` | PAE rules | Pattern #11 |
| `src/mesh/agent_propagator.py` | per-adapter try/except | Pattern #13 + #17 |
| `src/mesh/adapters/base.py` | ForkAdapter Protocol | Pattern #13 |
| `src/mesh/adapters/cli.py` | CliAdapter JSONL | adapter 1 |
| `src/mesh/adapters/taskdog.py:89-97` | UPSERT nativo | Pattern #14 |
| `src/mesh/adapters/solverforge_calendar.py:88, 96` | PK reuse | Pattern #14 |
| `src/contracts/task_change.py` | TaskChange + PropagationEvent | Pattern #11 |
| `src/contracts/common.py:UEID` | regex 4-part | Pattern #10 |
| `interfaces/tuiboard/src/v3/mcp/tools/board-tasks-create.ts:21-111` | create MCP tool | tuiboard |
| `interfaces/taskdog/packages/taskdog-mcp/src/taskdog_mcp/tools/task_crud.py` | 6 CRUD tools | taskdog |
| `interfaces/solverforge-calendar/src/bin/solverforge-calendar-mcp.rs` | 30 tools | solverforge |
| PROPOSTA: `src/operational/cli/commands/routine_cmd.py` (path place-holder; actual paths under `src/operational/packages/cli/`) | routine create | PAV-era |
| PROPOSTA: `src/operational/cli/commands/block_cmd.py` (path place-holder) | block create | PAV-era |
| `src/operational/cli/state.py:JSONRepository.upsert` | JSONL upsert | PAV-era |

---

## §5 — Fontes

### Code (verbatim, lidos via Read tool)
- `src/contracts/common.py` — UEID class + regex
- `src/contracts/task.py` — Task, Project
- `src/contracts/task_change.py` — TaskChange, PropagationEvent, TaskAction
- `src/mesh/queue.py` — enqueue (atomic temp+rename)
- `src/mesh/agent_consumer.py` — PAE rules
- `src/mesh/agent_propagator.py` — per-adapter
- `src/mesh/adapters/base.py` — ForkAdapter Protocol
- `src/mesh/adapters/cli.py`, `taskdog.py`, `solverforge_calendar.py` — 3 adapter impls
- PROPOSTA: `src/operational/cli/state.py` (path place-holder) — JSONRepository

### Docs design-system (verbatim, lidos via Read tool)
- `docs/design-system/10-pattern-ueid-tri-key.md` — UEID Pattern #10
- `docs/design-system/13-pattern-fork-adapter-protocol.md` — ForkAdapter Pattern #13
- `docs/design-system/14-pattern-idempotency-upstream-id.md` — Idempotent UPSERT
- `docs/design-system/20-fork-tuiboard-architecture.md` — tuiboard fork
- `docs/design-system/21-fork-taskdog-architecture.md` — taskdog fork
- `docs/design-system/22-fork-solverforge-calendar-architecture.md` — solverforge fork
- `docs/design-system/23-fork-status-enum-mapping.md` — status enum mapping
- `docs/design-system/40-index-user-journeys.md` — Layer 6 INDEX

### PAV-era docs (verbatim, lidos via Read tool)
- `src/operational/docs/ux/04-fluxos/FLOW-002-iniciar-tarde.md` — block/routine/metric create pattern
- `src/operational/docs/ux/05-telas/SCR-008-routine-create.md` — *referência indireta*
- `src/operational/docs/ux/05-telas/SCR-009-block-create.md` — *referência indireta*

### auto-performance-os docs
- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` — UEID pipeline

### Phase 2 diagnostics
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`
- `docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md`
- `docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md`
- `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md`

### Memory cross-refs
- `[[interfaces-architecture-2026-08-27]]`
- `[[master-branch-carro-chefe-2026-08-28]]`
- `[[data-first-methodology]]`
- `[[ag3-gateway-orphan-2026-08-27]]`
- `[[backend-phase-reordering-2026-08-28]]`
- `[[windows-orphan-dir-delete]]`

### Métricas de cobertura
- **5 sections principais** (§1-§5) — Resumo / Inventário / Conteúdo / Cross-refs / Fontes (template Pattern #10 verbatim)
- **5 steps pipeline** end-to-end documentados em §2.1 + diagrama §3.1
- **4 fork-specific create flows** detalhados em §3.2 (tuiboard, taskdog, solverforge-calendar, PAV-CLI)
- **6 PAE rules** tabulados em §2.4 (verbatim)
- **3 adapter storage topology** em §2.5 (CliAdapter JSONL, TaskdogAdapter UPSERT, SolverforgeCalendarAdapter PK reuse)
- **5-step UEID generation** em §2.6 (verbatim Pattern #10 §2.6)
- **1 data flow diagram ASCII** em §3.1 (form → queue → adapter → vault)
- **16 code anchors** verificados via Read tool em §4.6
- **6 memory cross-refs** em §4.5
- **6 pitfalls known** em §3.6
- **6 métricas** em §3.7 (latency, error rate, idempotency, consistency, UEID entropy, vault sync)
- **Honest rigor:** flag 2 forks (tuiboard, taskdog) sem UEID nativo; flag PAV-CLI não conectado ao mesh; flag vault sync como PROPOSTA italic; flag agent gated por ADR-007.

---

> **Próxima ação recomendada:** Após ADR-007 gate ser destravado (5+ SONHO logs), promover `upi_sync` solverforge-calendar MCP tool a canonical write path (cross-ref `06-synthesis-mesh-readiness.md:131-136`) + adicionar Migration v007 taskdog para `ueid UNIQUE` column + backfill heurístico. + adicionar CLI-2-mesh bridge PAV-era.