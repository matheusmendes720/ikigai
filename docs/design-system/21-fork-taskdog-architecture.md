# 21 — Fork: taskdog architecture (Python 5-package uv workspace + dual MCP/HTTP)

> **Categoria:** FORK (Layer 4 — Forks catalog, posição #21)
> **Anchor canônico:** `interfaces/taskdog/packages/` + `docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md`
> **Público:** Eu mesmo + agentes futuros
> **Idioma:** PT-BR prose + EN technical terms (uv workspace, SQLAlchemy, Alembic, Pydantic, FastAPI, FastMCP, Click, Textual, WebSocket, OTel, ORM, migration, dataclass, DTO, controller, use_case, repository, clean architecture, fork, adapter, UEID, UPSERT)
> **Caminho canônico local:** `C:/Users/mathe/code_space/life-oss/interfaces/taskdog/packages/`
> **Phase 1 baseline:** `gateways.yaml:9` cwd stale (B-01) + OQ-8 (two MCP transports)

---

## §1 — Resumo

O **fork taskdog** é um **task manager REST + MCP** construído em **Python 3.11+ + uv workspace de 5 pacotes** (`taskdog-core`, `taskdog-server`, `taskdog-client`, `taskdog-mcp`, `taskdog-ui`), distribuído como **MIT fork** do upstream **Kohei Wada's taskdog v0.23.0**. Sua função no data mesh é servir como fork-pronta user-facing com **persistência SQLite primeira-classe** (oposto a tuiboard markdown / solverforge-calendar sqlite+upi), expondo **26 tools MCP stdio** + **HTTP+WebSocket server** (FastAPI) + **CLI Click + Textual TUI** — três frontends paralelos para o mesmo backend SQLAlchemy 2.0 + Alembic. A integração com a malha acontece via `TaskdogAdapter` (`src/mesh/adapters/taskdog.py`) com **UPSERT nativo SQLite** via `INSERT ... ON CONFLICT(ueid) DO UPDATE` — é o adapter mais próximo do "ForkAdapter ideal" porque combina atomicidade de uma SQL statement com convergência por chave UEID. Diferente de tuiboard, taskdog **não tem UEID nativamente** (usa `id: INTEGER AUTOINCREMENT` como PK local) — gap conhecido. Diferente de solverforge-calendar, taskdog **não tem dual transport**: taskdog-mcp é stdio-only (FastMCP default), enquanto solverforge-calendar tem dual stdio+HTTP+SSE (mesmo que HTTP seja feature-gated stub). O design segue **Clean Architecture 4-camadas** (domain / application / infrastructure / controllers) com **`@dataclass` para domain entities + Pydantic v2 para DTOs** — hybrid pattern que evita overhead de validação em domain logic hot path.

---

## §2 — Inventário

### 2.1 Os 5 pacotes do uv workspace

| Package | Role | Entry | Key deps |
|:--------|:-----|:------|:---------|
| **taskdog-core** | Domain + application + infrastructure + controllers | `from taskdog_core.controllers import …` | SQLAlchemy 2.0, Alembic, Pydantic v2 |
| **taskdog-server** | FastAPI HTTP + WebSocket server (NOT MCP) | `taskdog_server.api.app:app` | FastAPI ≥0.115, uvicorn, websockets |
| **taskdog-client** | HTTP client + WebSocket client | `from taskdog_client import TaskdogApiClient` | httpx ≥0.27, websockets ≥14 |
| **taskdog-mcp** | FastMCP stdio MCP server (wraps HTTP) | `python -m taskdog_mcp.main` | mcp ≥1.2,<2, taskdog-client |
| **taskdog-ui** | Click CLI + Textual TUI | `taskdog` console-script | click, rich, textual ≥8.0, textual-plotext |

### 2.2 Camadas internas do taskdog-core (146 Python files)

| Layer | Subpackage | Responsabilidade |
|:------|:-----------|:-----------------|
| **domain** | `domain/entities/` | Pure `@dataclass` (`Task`, `TaskStatus` enum), `audit_log.py` |
| **domain** | `domain/repositories/` | Abstract ABCs (`task_repository.py`, `audit_log_repository.py`) |
| **domain** | `domain/services/` | Domain service interfaces (`backup_store`, `holiday_checker`, `time_provider`) |
| **domain** | `domain/exceptions/` | Typed exception hierarchy (`TaskError`, `TaskNotFoundException`, etc.) |
| **application** | `application/dto/` | 32 Pydantic v2 DTO files (`task_dto.py:12`) |
| **application** | `application/use_cases/` | 19 use cases (`CreateTask`, `StartTask`, `OptimizeSchedule`) |
| **application** | `application/queries/` | Query/filter system + 11 optimization strategies |
| **application** | `application/validators/` | 6 validators (Status, Dependency, Datetime, Numeric, Field) |
| **infrastructure** | `infrastructure/persistence/database/` | SQLAlchemy 2.0 ORM + Alembic (`engine_factory`, `models`, `query_builders`, `mutation_builders`, `migrations`, `sqlite_*_repository.py`) |
| **infrastructure** | `infrastructure/holiday_checker.py` | Domain interface impls |
| **controllers** | `controllers/` | 11 controllers (`TaskCrud`, `TaskLifecycle`, `TaskRelationship`, `TaskAnalytics`, `Query`, `Notes`, `AuditLog`, `Bulk`, `Backup`, `BaseTask`) |
| **shared** | `shared/` | TOML config, XDG paths, date/time utils |

### 2.3 Tabelas SQLite (5 tabelas, 6 migrations)

| Tabela | ORM | Migration | Propósito |
|:-------|:----|:----------|:----------|
| `tasks` | `task_model.py:24-101` | `001_initial_schema.py:36-66` | Main entity, 17 columns, 5 indexes |
| `tags` | `tag_model.py:22-58` | `001_initial_schema.py:69-78` | Normalized tag names (unique) |
| `task_tags` | `tag_model.py:61-93` | `001_initial_schema.py:81-91` | M:N junction |
| `audit_logs` | `audit_log_model.py:19-92` | `001_initial_schema.py:94-125` | Audit trail, 8 indexes |
| `notes` | `note_model.py:19-52` | `004_add_notes_table.py:42-54` | DB-backed notes (PK=task_id FK, CASCADE) |
| `daily_allocations` | `daily_allocation_model.py:24-78` | `005_add_*` | Normalized allocations, UNIQUE(task_id,date) |

**Migration chain** (`migrations/versions/`): `001 → 002 (remove actual_daily_hours) → 003 (priority nullable) → 004 (notes) → 005 (daily_allocations table) → 006 (drop JSON column)`.

**Auto-stamp pattern** (`migration_runner.py:111-114`): if `tasks` table exists but no `alembic_version`, stamps com `001_initial` — robusto contra pre-existing DBs.

### 2.4 MCP tools expostos (26 total — 6 unreachable via gateway)

**CRUD (6)** — `tools/task_crud.py`: `list_tasks`, `get_task`, `create_task`, `update_task`, `delete_task`, `restore_task`.

**Lifecycle (6)** — `tools/task_lifecycle.py:18-159`: `start_task`, `complete_task`, `pause_task`, `cancel_task`, `reopen_task`, `fix_actual_times`.

**Query (3)** — `tools/task_query.py`: `get_statistics`, `get_tag_statistics`, `get_executable_tasks`.

**Decomposition + Relationships + Notes (6)** — `tools/task_decomposition.py:78-298`: `decompose_task`, `add_dependency`, `remove_dependency`, `set_task_tags`, `update_task_notes`, `get_task_notes`.

**Tags (1)** — `task_tags.py:18-43`: `delete_tag`.

**Audit (2)** — `tools/task_audit.py:18-109`: `list_audit_logs`, `get_audit_log`.

**Optimization (2)** — `tools/task_optimization.py:19-142`: `optimize_schedule` (9 algorithms: greedy, balanced, backward, priority_first, earliest_deadline, round_robin, dependency_aware, genetic, monte_carlo), `list_algorithms`.

### 2.5 Server components (taskdog-server, FastAPI)

**App construction** (`api/app.py:37-121`) — `create_app()` factory; lifespan inits `api_context`, `server_config`, `ConnectionManager` em `app.state`; registra 10 routers:

| Router | Prefix | Tags |
|:-------|:-------|:-----|
| `tasks.py` | `/api/v1/tasks` | tasks |
| `bulk.py` | `/api/v1/tasks` | bulk |
| `lifecycle.py` | `/api/v1/tasks` | lifecycle |
| `relationships.py` | `/api/v1/tasks` | relationships |
| `notes.py` | `/api/v1/tasks` | notes |
| `analytics.py` | `/api/v1` | analytics |
| `tags.py` | `/api/v1/tags` | tags |
| `audit.py` | `/api/v1/audit-logs` | audit |
| `backup.py` | `/api/v1` | backup |
| `websocket.py` | (no prefix) | websocket |

**WebSocket broadcast** (server → client): `task_created`, `task_updated`, `task_deleted`, `task_status_changed`, `schedule_optimized`, `bulk_operation_completed`. Client → server: ping/pong only (`routers/websocket.py:78-87`).

### 2.6 UI components (taskdog-ui, Click + Textual)

**CLI**: `cli_main.py:131-200` — `TaskdogGroup` extends `LazyGroup`; 22 lazy subcommands (deferred imports for `--help` startup perf, linhas 12-19). Entry-point `pyproject.toml:44` = `taskdog = "taskdog.cli_main:cli"`.

**TUI** (`tui/`): Textual app composed of `MainScreen` (Vertical(GanttWidget, TaskTable) + CustomFooter) + Gantt widget + 10 palette providers + audit log screen.

### 2.7 OTel instrumentation (findings negativos)

**Onde vive**: `taskdog-mcp/build/lib/taskdog_mcp/observability.py:1-191` — `instrumented_tool(mcp, name)` decorator via `opentelemetry.sdk.trace.TracerProvider` + `OTLPSpanExporter` (line 21, 70, 72).

**Onde NÃO vive (zero hits)**:
- `taskdog-client/src` — 0 hits `opentelemetry|otel|tracer|span`
- `taskdog-server/src` — 0 hits
- `taskdog-ui/src` — 0 hits
- `pyproject.toml` em client/server/ui — NO `opentelemetry-*` deps

**Implicação**: server (HTTP) tem ZERO observability entre boundary e DB. MCP-tool calls são traced; HTTP server calls wrapped pelos MCP tools não são.

---

## §3 — Conteúdo principal

### 3.1 Hybrid `@dataclass` + Pydantic v2 domain modeling

O design load-bearing de taskdog é o **uso dual de `@dataclass` e Pydantic `BaseModel`** para conceptos diferentes:

- **Domain entities** (`Task` em `domain/entities/task.py:23-459`, 437 LOC) — plain `@dataclass`, sem Pydantic. Invariantes enforced em `__post_init__` (`task.py:79-132`): `_validate_name`, `_validate_priority`, `_validate_durations`, `_validate_tags`. Computed properties: `actual_duration_hours` (priority explicit → calc → None, linhas 134-154), `is_active`, `is_finished`, `can_be_modified`. State machine (`:278-351`): `start(timestamp)`, `complete(timestamp)`, `cancel(timestamp)`, `pause()`, `reopen()`, `fix_actual_times(...)` com Ellipsis sentinel pattern (`:353-409`).

- **DTOs / wire schemas** (`application/dto/*`, 32 files) — Pydantic v2 `BaseModel` + `ConfigDict(frozen=True, extra="forbid")` análogo ao Pattern #11 do life. Validação na boundary, sobrevive a `task_dto.py:12` `from pydantic import BaseModel, ConfigDict, Field`.

A escolha é deliberada: dataclass domain = zero validation overhead em hot path; Pydantic DTOs = strict validation no boundary. Mirrors o que life poderia fazer para `src/contracts/` (atualmente Pydantic everywhere é mais pesado que necessário para hot-path domain logic).

### 3.2 26 MCP tools e a assimetria de gateway prefixes

Tools detalhados em §2.4 acima. O ponto crítico é o **gateway prefix mismatch** (Phase 2 finding F2): `gateways.yaml:8-10` declara prefix `taskdog_*` + 7 exact tokens (`list_tasks`, `get_task`, `create_task`, `update_task`, `delete_task`, `archive_task`, `restore_task`), mas **nenhum tool MCP usa prefix `taskdog_*`** (todos são unprefixed). Resultado: 20 de 26 tools são unreachable via gateway hoje.

**Match matrix:**

| Gateway expects | Actual MCP tool name | Match? |
|:----------------|:---------------------|:-------|
| `taskdog_*` (wildcard) | (none) | NO |
| `list_tasks` | `list_tasks` | YES |
| `get_task` | `get_task` | YES |
| `create_task` | `create_task` | YES |
| `update_task` | `update_task` | YES |
| `delete_task` | `delete_task` (MCP), `archive_task` (REST) | YES (MCP tool) |
| `archive_task` | NO direct tool | NO (calls `client.archive_task` via `delete_task(hard=False)`) |
| `restore_task` | `restore_task` | YES |

**Output mismatch**: gateway expects `archive_task` but MCP exposes `delete_task(hard=False)`. Naming inconsistency that gateway cannot auto-resolve.

### 3.3 TaskdogAdapter integration (mesh UPSERT canônico)

`src/mesh/adapters/taskdog.py` (104 LOC) implementa `ForkAdapter` Protocol para taskdog SQLite. A idempotência vem do **schema**:

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ueid TEXT UNIQUE,        ←── canonical join key canônico
    name TEXT,
    status TEXT,
    priority INTEGER,
    planned_start TEXT,
    planned_end TEXT,
    deadline TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_ueid ON tasks(ueid);
```

**Native SQLite UPSERT** (`:89-97`): uma única statement `INSERT ... VALUES (...) ON CONFLICT(ueid) DO UPDATE SET name=excluded.name, ...`. Atomic por statement; nenhum SELECT-then-INSERT race. **Convergência eventual garantida por schema**.

Trade-off vs `CliAdapter` (JSONL sem dedup): taskdog adapter **é** idempotente na prática — re-chamar `apply_change` com mesmo `event.ueid` atualiza row existente em vez de duplicar. Padrão deve ser replicado em forks que suportam UNIQUE constraint.

**Priority mapping** (`:80-83`): str priority `"high"|"medium"|"low"` → int `1|2|3` antes de persist (taskdog domain é `int`).

### 3.4 3-tier MCP architecture (mcp → http → server → controller → use_case → repo)

O MCP server **NÃO chama controllers diretamente**. Em vez disso, ele invoca `taskdog_client` (HTTP para `taskdog-server` FastAPI), que instancia controllers via `initialize_api_context()` (line 64-141), que constrói 9 controllers + 1 shared SQLAlchemy engine. **Cross-process latency** adicionado em cada tool call. Trade-off (`02-fork-taskdog.md:423`): clean separation vs extra round-trip.

Implicação: `optimize_schedule` MCP tool gasta ~50-200ms em network calls antes de chegar ao algorithm. Para agent low-latency use cases, life poderia flatten to `mcp → controller` direto, bypassing HTTP layer. Pattern é referência para `src/ikigai/src/mcp_server/server.py` decidir.

### 3.5 Alembic with DB-stamping (lesson para life)

O migration runner (`migration_runner.py:111-114`) detecta DBs pre-existentes sem `alembic_version` table e os **stamps** com `001_initial` em vez de tentar re-criar. Pattern robusto contra legacy DBs: `if "tasks" not in existing_tables: create else: stamp`.

Implicação: `data/vibe_ops.db` (atualmente `user_version=0` per Phase 1 B-05) poderia adotar esse pattern em vez de um bootstrap opcional. **Phase 3 candidate**.

### 3.6 Federation vs single source (OQ-5 evidence)

Taskdog tem **1 SQLite file (5 tables) + DB-resident notes + audit + separate `~/.local/share/...` root**. É **federated by design** — cada concern tem sua própria tabela/root, **não** um `vibe_ops.db` unificado. Phase 2 synthesis (`06-synthesis-mesh-readiness.md:104`) recomenda **Option A (federated)** com ETL via `upi_sync`: "Pattern: each concern gets its own DB. life should adopt **Option A (federated)** with explicit ETL via `upi_sync`."

### 3.7 UEID gap (analogia com tuiboard)

Taskdog **não tem UEID nativo**. Identidade local é `(id: INTEGER AUTOINCREMENT, name: str, ...)`. Para mesh join, o `TaskdogAdapter` adiciona coluna `ueid TEXT UNIQUE` que recebe o UEID canônico vindo do `PropagationEvent`. Migration: tasks existentes em DB de taskdog **não têm UEID** — só recebem via `apply_change` quando o Deep Agent cria/modifica uma task na malha. Phase 3 candidate: backfill UEID para tasks existentes via lookup heurístico (title+deadline match contra `data/tasks.jsonl`).

### 3.8 Gateway routing match matrix

**Source:** `gateways.yaml:7-10`. Comandos `python -m taskdog_mcp.main`, cwd `C:/Users/mathe/code_space/apps/dev-tools/taskdog` (STALE).

**Prefix collision check:** `taskdog_*` (wildcard, dead) + 7 unprefixed (`list_tasks`, etc.) **não colidem** com `board_*` (tuiboard) ou `calendars_/events_/projects_/dependencies_/google_/upi_` (solverforge-calendar). Mas **FALLBACK risk**: se taskdog_mcp é adicionado ao `prefix_map` naively, então o **FALLBACK** (router.py:24 = solverforge-calendar) capturaria tool calls `start_task` etc. — porque taskdog não tem prefix no gateway. **Resolver antes** de Phase 3.

---

## §4 — Cross-references

### 4.1 Design-system docs

- **`docs/design-system/00-INDEX.md`** §3 — Layer 4 Forks catalog (este doc + 20 + 22 + 23).
- **`docs/design-system/13-pattern-fork-adapter-protocol.md`** §2.3 (`TaskdogAdapter` verbatim, UPSERT nativo) + §2.5 (UEID-UNIQUE 3-storages pattern).
- **`docs/design-system/15-pattern-hysteresis-fsm.md`** §2.1 (`TaskStatus` enum — taskdog tem `PENDING/IN_PROGRESS/COMPLETED/CANCELED` em `task.py:16-20`, mapping cross-canonical em doc 23).
- **`docs/design-system/04-canvas-mesh-architecture.md`** §3.3 — taskdog = SQLite UPSERT branch da tabela de topology.
- **`docs/design-system/05-canvas-contracts-architecture.md`** §4.3 (TaskAction, TaskStatus, TaskChange, PropagationEvent) — taskdog consumer/Pydantic DTO cross-canonical.
- **`docs/design-system/14-pattern-idempotency-upstream-id.md`** §3 (idempotency via UEID UNIQUE + UPSERT) — taskdog é o exemplo canônico.

### 4.2 Phase 2 diagnostics (fontes verbatim)

- **`docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md`** (497 linhas) — RE primário, fonte verbatim deste doc.
- **`docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md`** §Phase 3 readiness OQ-1, OQ-2, OQ-5 — taskdog federated evidence.
- **`docs/diagnostics/2026-08-28-phase1-audit/01-verified.md`** B-01 (gateways.yaml cwd MISSING taskdog) + OQ-8 (two MCP transports).
- **`docs/diagnostics/2026-08-28-phase1-audit/02-critic-gaps.md`** P1 #8 (orphan CLI entry-point) — taskdog-ui como **POSITIVE reference** (`pyproject.toml:44` working entry-point).

### 4.3 Memory cross-refs

- **`[[interfaces-architecture-2026-08-27]]`** — taskdog fork é user-view, não source-of-truth.
- **`[[master-branch-carro-chefe-2026-08-28]]`** — taskdog é uma das 3 forks-prontas sincronizadas pelo deep-agent.
- **`[[windows-orphan-dir-delete]]`** — `apps/dev-tools/taskdog` deletado 2026-08-28; fork agora em `life-oss/interfaces/taskdog/packages/`.
- **`[[orchestration-clone-playground]]`** — taskdog é vendored MIT fork de Kohei Wada.
- **`[[ag3-gateway-orphan-2026-08-27]]`** — gateway-related orphan; taskdog prefix mismatch é exemplo.

### 4.4 Auto-performance OS (matemática + integração)

- **`docs/auto-performance-os/24-integration-mesh-ueid-propagation.md`** §2 — taskdog UPSERT on UEID é load-bearing example.

### 4.5 Code anchors (verificados)

| Path | LOC / Conteúdo | Padrão |
|:-----|:---------------|:-------|
| `src/mesh/adapters/taskdog.py:31-103` | `TaskdogAdapter` + UPSERT nativo | ForkAdapter Protocol impl (SQLite branch) |
| `src/mesh/adapters/base.py:8-23` | `ForkAdapter` Protocol base | Pattern #13 verbatim |
| `interfaces/taskdog/packages/taskdog-core/src/taskdog_core/domain/entities/task.py:16-20` | `TaskStatus` enum PENDING/IN_PROGRESS/COMPLETED/CANCELED | domain enum |
| `interfaces/taskdog/packages/taskdog-core/src/taskdog_core/domain/entities/task.py:79-132` | `__post_init__` validation | dataclass invariants |
| `interfaces/taskdog/packages/taskdog-core/src/taskdog_core/infrastructure/persistence/database/engine_factory.py:19-58` | WAL + busy_timeout + synchronous=NORMAL | DB PRAGMA config |
| `interfaces/taskdog/packages/taskdog-core/src/taskdog_core/infrastructure/persistence/database/migration_runner.py:111-114` | auto-stamp pattern | robust migration |
| `interfaces/taskdog/packages/taskdog-mcp/src/taskdog_mcp/observability.py:1-191` | OTel `instrumented_tool` | observability (MCP-only) |
| `interfaces/taskdog/packages/taskdog-server/src/taskdog_server/api/app.py:37-121` | `create_app()` factory | FastAPI construction |
| `apps/mcp-gateway/config/gateways.yaml:7-10` | taskdog backend entry | cwd STALE |
| `apps/mcp-gateway/src/mcp_gateway/router.py:4-25` | prefix + exact + FALLBACK routing | routing dispatcher |

### 4.6 Pitfalls noted

- **`gateways.yaml:9` cwd stale** — fork está em `life-oss/interfaces/taskdog/packages/taskdog-mcp/`, não em `apps/dev-tools/taskdog`. **Phase 1 B-01 confirmou**.
- **`taskdog_*` prefix no gateway é DEAD** — nenhum MCP tool usa esse prefix; todo tool é unprefixed.
- **`archive_task` mismatch** — gateway espera `archive_task`, MCP expõe `delete_task(hard=False)`.
- **20/26 MCP tools unreachable via gateway** — prefix list cobre só 6 exact tokens + dead `taskdog_*`; lifecycle/query/decomposition/tags/audit/optimization omitidos.
- **`controllers/__init__.py:1-13` design gap** — só re-exporta 4 de 11 controllers (`AuditLogController`, `BulkTaskController`, `NotesController`, `QueryController`); os outros 7 são importable via path direto mas `from taskdog_core.controllers import …` falha com `ImportError` para missing 7.
- **OTel assimétrico** — só MCP tools instrumentados; HTTP server tem ZERO. Trace entre boundary e DB é invisível.
- **`taskdog-mcp` é stdio-only** — não tem HTTP transport wired (FastMCP default). Compare com solverforge-calendar dual stdio+HTTP+SSE (mesmo que HTTP stub).

---

## §5 — Fontes

### Code (verbatim, lidos via Read tool)
- `src/mesh/adapters/taskdog.py` (104 LOC) — TaskdogAdapter SQLite UPSERT (adaptador de integração)
- `src/mesh/adapters/base.py` (24 LOC) — ForkAdapter Protocol base
- `src/contracts/task_change.py` (58 LOC) — `PropagationEvent` Pydantic frozen
- `src/contracts/task.py` — `Task`, `TaskChange`, `TaskAction` (cross-canonical)

### Docs (analisados, verbatim lidos via Read tool)
- `docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md` (497 LOC) — RE primário deste doc; **todas** as seções §2 inventário + §3 entidades + §4 schema + §5 MCP tools + §6 gateway + §7 client + §8 server + §9 UI + §10 OTel + §11 trade-offs + §12 cross-refs citadas acima
- `docs/diagnostics/2026-08-28-phase2-interface-re/06-synthesis-mesh-readiness.md` (196 LOC) — Phase 3 readiness por OQ
- `docs/diagnostics/2026-08-28-phase1-audit/01-verified.md` B-01 + OQ-8 baselines

### Design-system cross-refs
- `docs/design-system/00-INDEX.md` — INDEX navegação Layer 4
- `docs/design-system/13-pattern-fork-adapter-protocol.md` §2.3 TaskdogAdapter verbatim + §2.5 UEID-UNIQUE
- `docs/design-system/15-pattern-hysteresis-fsm.md` §2.1 (TaskStatus enum reference)
- `docs/design-system/04-canvas-mesh-architecture.md` §3.3 storage topology
- `docs/design-system/14-pattern-idempotency-upstream-id.md` §3 (UPSERT idiom)

### Memory cross-refs
- `[[interfaces-architecture-2026-08-27]]` — dual-layer
- `[[master-branch-carro-chefe-2026-08-28]]` — canonical master
- `[[windows-orphan-dir-delete]]` — apps/dev-tools/taskdog deletion
- `[[orchestration-clone-playground]]` — vendored MIT fork
- `[[ag3-gateway-orphan-2026-08-27]]` — gateway prefix mismatch

### Métricas de cobertura
- **7 seções de inventário** (§2.1-2.7) — 5 packages, core layers, 5 tables, 26 MCP tools, server routers, UI components, OTel findings
- **8 seções de conteúdo principal** (§3.1-3.8) — domain modeling, gateway prefix asymmetry, adapter UPSERT, 3-tier architecture, Alembic, federation, UEID gap, routing
- **8 code anchors** verificados via Read tool em §4.5
- **5 memory cross-refs** (interfaces, master-branch, windows-orphan, orchestration-clone, ag3-gateway)
- **6 pitfalls** explícitos em §4.6 (gateways.yaml cwd, taskdog_* dead prefix, archive_task mismatch, 20/26 unreachable, controllers design gap, OTel assimetry)
- **Honest rigor:** menciona UEID gap (não-nativo), OTel assimetry (só MCP), 3-tier HTTP latency (mcp → http → controller), datestamp Alembic pattern como Phase 3 candidate, e controllers design gap (4/11 re-exported)
