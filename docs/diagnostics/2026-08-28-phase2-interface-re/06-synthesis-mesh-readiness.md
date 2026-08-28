# 06 — Phase 2 Synthesis: Mesh Readiness Across Forks

**Date:** 2026-08-28
**Phase:** 2 of `2026-08-28-interface-re`
**Mode:** Synthesis. Compares 5 RE outputs (3 forks + 2 native interfaces) against the 10 Open Questions from Phase 1.
**Scope:** No new patches; inform Phase 3 brainstorm by mapping fork-level evidence back to OQ-1..OQ-10.
**Inputs read:**
- `docs/diagnostics/2026-08-28-phase1-audit/{00-INDEX,01-verified,02-critic-gaps,03-priority-matrix,04-sequencing,05-open-questions}.md`
- `docs/diagnostics/2026-08-28-phase2-interface-re/01-fork-tuiboard.md` (332 lines)
- `docs/diagnostics/2026-08-28-phase2-interface-re/02-fork-taskdog.md` (497 lines)
- `docs/diagnostics/2026-08-28-phase2-interface-re/03-fork-solverforge-calendar.md` (418 lines)
- `docs/diagnostics/2026-08-28-phase2-interface-re/04-interfaces-cli.md` (197 lines)
- `docs/diagnostics/2026-08-28-phase2-interface-re/05-interfaces-tui.md` (~165 lines)

---

## Cross-fork comparison matrix

| Dimension | tuiboard | taskdog | solverforge-calendar | interfaces/cli | interfaces/tui |
|-----------|----------|---------|----------------------|----------------|----------------|
| **Language/runtime** | Bun + SolidJS + OpenTUI (`01-fork-tuiboard.md:4-7`) | Python 3.11+ / uv workspace 5-pkg (`02-fork-taskdog.md:5-7`) | Rust 2021 / rmcp 3.1 (`03-fork-solverforge-calendar.md:7`) | Python 3 / Typer (`04-interfaces-cli.md:5`) | Python / Textual (planned per README) |
| **LOC** | 934-line `handleKey.ts` (`01-fork-tuiboard.md:305`) | 146 Python files in `taskdog-core` alone (`02-fork-taskdog.md:24`) | 11,649 Rust LOC across 30 files (`03-fork-solverforge-calendar.md:8`) | 206 LOC `read_tasks.py` (`04-interfaces-cli.md:5`) | 0 LOC; 44-line README only (`05-interfaces-tui.md:11`) |
| **Persistence** | Markdown boards + atomic rename (`01-fork-tuiboard.md:256-261`) | SQLite + SQLAlchemy 2.0 + Alembic 6 migrations (`02-fork-taskdog.md:131-156`) | rusqlite + 2 migrations + WAL + soft-delete (`03-fork-solverforge-calendar.md:58-75`) | JSONL (`data/tasks.jsonl`, MISSING per B-04) (`04-interfaces-cli.md:79-82`) | None (planned; no code) |
| **DB path** | n/a (filesystem) | `~/.local/share/taskdog/tasks.db` XDG (`02-fork-taskdog.md:170`) | `$SOLVERFORGE_DATA_DIR/solverforge/calendar.db` (`03-fork-solverforge-calendar.md:99`) | `life/data/tasks.jsonl` (`04-interfaces-cli.md:87-89`) | n/a (consumes `data/tasks.jsonl`) |
| **MCP transport** | stdio JSON-RPC only (`01-fork-tuiboard.md:159`) | stdio only via FastMCP (`02-fork-taskdog.md:177`) | stdio + HTTP+SSE feature-gated stub (`03-fork-solverforge-calendar.md:186-199`) | n/a (not MCP server) | n/a |
| **MCP protocol** | `2024-11-05` (`01-fork-tuiboard.md:162`) | mcp `>=1.2,<2.0` (FastMCP) (`02-fork-taskdog.md:6`) | rmcp 3.1, `"2024-11-05"` (`03-fork-solverforge-calendar.md:153`) | n/a | n/a |
| **Tool count** | 5 (`board_*`) (`01-fork-tuiboard.md:170-179`) | 26 (`02-fork-taskdog.md:182`) | 30 (`03-fork-solverforge-calendar.md:155-185`) | 0 (CLI commands, not tools) | 0 |
| **Tool prefix** | `board_` (5/5 routed) (`01-fork-tuiboard.md:233-243`) | none (all unprefixed; gateway expects `taskdog_*` + 7 exact — partial match) (`02-fork-taskdog.md:233-242`) | `calendars_/events_/projects_/dependencies_/google_/upi_` (6/6 prefixes match, `google_sync` is stub) (`03-fork-solverforge-calendar.md:222-230`) | n/a | n/a |
| **Concurrency control** | `expectedMtimeMs` optimistic locking (`01-fork-tuiboard.md:189-190`) | none at MCP layer; SQLAlchemy session per request (`02-fork-taskdog.md:127`) | `Arc<SyncMutex<Connection>>` serialized (`03-fork-solverforge-calendar.md:150,368`) | none (full-file rewrite) (`04-interfaces-cli.md:79-82`) | n/a |
| **Validation** | Zod `.strict()` everywhere (`01-fork-tuiboard.md:185`) | Pydantic v2 DTOs at boundary (`02-fork-taskdog.md:32`) | schemars via rmcp derive; Zod-equivalent (`03-fork-solverforge-calendar.md:152`) | none (JSON-decode errors swallowed) (`04-interfaces-cli.md:53-55`) | n/a |
| **Observability** | OTel OTLP HTTP per tool (`01-fork-tuiboard.md:203`) | OTel only in `taskdog-mcp` (zero in client/server/UI) (`02-fork-taskdog.md:396-407`) | OTel gated on `OTEL_ENABLED=true` (`03-fork-solverforge-calendar.md:206-207`) | none | none |
| **Domain model** | `Task` + `Column` + `Board` markdown-round-tripped (`01-fork-tuiboard.md:290-291`) | `@dataclass Task` + Pydantic DTO hybrid (`02-fork-taskdog.md:64-118`) | `Event/Calendar/Project/EventDependency` + UPI JSON (`03-fork-solverforge-calendar.md:76-86`) | flat dict, 14-field schema (`04-interfaces-cli.md:34-53`) | n/a (planned `Task/Period/Priority` from `src/contracts/`) |
| **UEID support** | none (uses board file mtime as concurrency token) | none (uses `id: int`) | none (uses UUID v4 + `(system, board_card_id)` sync_map) | yes — 5-part `tsk:slug:uuid:hash` (`04-interfaces-cli.md:48`) | planned (`src/contracts/task.py`) |
| **Gateway reachability today** | unreachable (cwd stale per B-01) (`01-fork-tuiboard.md:243-245`) | unreachable (cwd stale + 20/26 tools unreachable by prefix) (`02-fork-taskdog.md:244-253`) | unreachable (cwd stale; `cargo run` cold start 30-60s) (`03-fork-solverforge-calendar.md:236-237`) | n/a | n/a |

---

## Tool collision analysis

The gateway router (`apps/mcp-gateway/src/mcp_gateway/router.py:4-25`) dispatches via `prefix_map` (prefix `_` → startswith) or `exact_map` (exact token match), with `solverforge-calendar` as the FALLBACK backend (`router.py:24`).

**Cross-prefix token analysis** (union of all 61 actual MCP tools exposed by the 3 forks):

| Tool name | Origin | Prefix | Routes to | Conflict? |
|-----------|--------|--------|-----------|-----------|
| `board_list`, `board_tasks_get/update/create/delete` | tuiboard | `board_` | tuiboard | NO — no other fork uses `board_*` |
| `list_tasks`, `get_task`, `create_task`, `update_task`, `delete_task`, `restore_task` | taskdog | unprefixed (gateway has these in `exact_map`) | taskdog | NO |
| `start_task`, `complete_task`, `pause_task`, `cancel_task`, `reopen_task`, `fix_actual_times` | taskdog | unprefixed | **NOT IN GATEWAY** (`02-fork-taskdog.md:244-253`) | unreachable |
| `get_statistics`, `get_tag_statistics`, `get_executable_tasks` | taskdog | unprefixed | **NOT IN GATEWAY** | unreachable |
| `decompose_task`, `add_dependency`, `remove_dependency`, `set_task_tags`, `update_task_notes`, `get_task_notes`, `delete_tag` | taskdog | unprefixed | **NOT IN GATEWAY** | unreachable |
| `list_audit_logs`, `get_audit_log`, `optimize_schedule`, `list_algorithms` | taskdog | unprefixed | **NOT IN GATEWAY** | unreachable |
| `archive_task` (gateway exact-match) | **NO SUCH MCP TOOL** | — | dead entry | mismatch (`02-fork-taskdog.md:241-243`) |
| `taskdog_*` (gateway prefix) | **NO MCP TOOL USES THIS PREFIX** | — | dead entry | mismatch (`02-fork-taskdog.md:235`) |
| `calendars_*` (5) | solverforge-calendar | `calendars_` | solverforge-calendar | NO |
| `events_*` (5) | solverforge-calendar | `events_` | solverforge-calendar | NO |
| `projects_*` (5) | solverforge-calendar | `projects_` | solverforge-calendar | NO |
| `dependencies_*` (5) | solverforge-calendar | `dependencies_` | solverforge-calendar | NO |
| `google_sync` (stub only) | solverforge-calendar | `google_` | solverforge-calendar | NO but `google_sync` returns `not_implemented` (`03-fork-solverforge-calendar.md:179`) |
| `upi_*` (5) | solverforge-calendar | `upi_` | solverforge-calendar | NO — but `upi_*` could collide with future `upi_*` from any other fork (none today) |

**Findings:**
1. **Zero prefix collisions across forks today** — `board_`, `taskdog_*`, `calendars_/events_/projects_/dependencies_/google_/upi_` are disjoint. The mesh is technically route-safe at the prefix layer.
2. **Unprefixed taskdog tools hit the FALLBACK to solverforge-calendar** (`router.py:24`). 6 taskdog lifecycle tools (`start_task` etc.) would be misrouted if the gateway fixed its prefix list naively — they need to be added to `exact_map` BEFORE solverforge-calendar's prefix table catches them.
3. **`archive_task` gateway entry is a dead token** — MCP exposes `delete_task(hard=False)` (`02-fork-taskdog.md:240-242`). The router would reject unknown exact tokens, but the config currently misleads operators.
4. **20/26 taskdog tools unreachable** (`02-fork-taskdog.md:244-253`) — gateway prefix list (`gateways.yaml:8-10`) covers only 6 exact tokens + dead `taskdog_*` prefix; the remaining 20 (lifecycle/query/decomposition/tags/audit/optimization) cannot route to any backend.
5. **FALLBACK risk is asymmetric** — if a new tool name like `events_query` appears in tuiboard (doesn't exist), it would route to solverforge-calendar by FALLBACK, masking the misconfiguration.

---

## Shared data shape candidates

Examining the wire schemas each fork exposes for potential mesh-level unification (joining OQ-2 + OQ-7):

| Concept | tuiboard Zod schema | taskdog Pydantic DTO | solverforge-calendar | life interfaces/cli | Convergence? |
|---------|---------------------|----------------------|----------------------|---------------------|--------------|
| **Task id** | `columnIndex + taskIndex` + board file path (composite position) (`01-fork-tuiboard.md:175`) | `id: int` auto-assigned (`02-fork-taskdog.md:73`) | `events.id UUID v4` (`03-fork-solverforge-calendar.md:64`) | `id: str` first 8 chars of uuid (`04-interfaces-cli.md:23`) | NO — 4 different key shapes |
| **Title** | `TaskPatch.title?: string` (inferred from `TaskInit`) (`01-fork-tuiboard.md:177-178`) | `Task.name: str` ≤MAX_TASK_NAME_LENGTH (`02-fork-taskdog.md:70`) | `Event.title: str` (`03-fork-solverforge-calendar.md:81`) | `title: str` (`04-interfaces-cli.md:40`) | YES — plain `str` |
| **Status** | `Task.done: bool` + column position implies status (`01-fork-tuiboard.md:261-264`) | `TaskStatus` enum 4-value (`02-fork-taskdog.md:74`) | `UPI.status` enum 5-value (`03-fork-solverforge-calendar.md:84`) | `done: bool` + `done_at?: datetime` (`04-interfaces-cli.md:46-47`) | NO — 3 enum shapes (boolean vs 4-state vs 5-state) |
| **Priority** | `PriorityLevel` enum 6-value (`01-fork-tuiboard.md:184`) | `priority: int \| None` (`02-fork-taskdog.md:72`) | none | `priority: str` ("high"/"medium"/"low") (`04-interfaces-cli.md:43`) | NO — 3 different scales |
| **Dates** | `IsoDate` + `TimeBlock(startMin, endMin)` (`01-fork-tuiboard.md:181-183`) | `planned_start/end`, `deadline`, `actual_*` (`02-fork-taskdog.md:76-78`) | `start_at/end_at` + `rrule` RFC 5545 (`03-fork-solverforge-calendar.md:81`) | `due: date` + `written_at: datetime` (`04-interfaces-cli.md:38-50`) | partial — all have date but no shared format |
| **Tags** | none (`01-fork-tuiboard.md:170-179`) | `tags: list[str]` non-empty + unique (`02-fork-taskdog.md:84`) | `tags JSON` in `unified_planning_items` (`03-fork-solverforge-calendar.md:90`) | none | partial |
| **UEID** | none | none | none | 5-part `tsk:slug:uuid:hash` (`04-interfaces-cli.md:48`) | ONLY CLI has UEID |
| **Wikilinks / cross-refs** | markdown `[[…]]` preserved (`01-fork-tuiboard.md:290`) | none | `sync_map PRIMARY KEY (system, board_card_id)` + 4-strategy resolver (`03-fork-solverforge-calendar.md:91, 40`) | none | solverforge bridges to tuiboard only |
| **Optimistic concurrency** | `expectedMtimeMs: number` (`01-fork-tuiboard.md:190`) | none | none | full-file rewrite race (`04-interfaces-cli.md:79-82`) | only tuiboard |

**Convergence assessment:**
- **Common ground:** title-as-string is universal. Date fields exist in 4 of 5. Status enum and priority scale are FORK-DIVERGENT.
- **Best mesh substrate candidate:** solverforge-calendar's `unified_planning_items` (UPI) at `03-fork-solverforge-calendar.md:90` is the only fork already designed as a superset (status + time_block + ikigai + provenance + blocked_by + tags JSON). It is already the cross-fork sync target via `upi_sync` MCP tool (`03-fork-solverforge-calendar.md:180`).
- **Worst-case divergence:** task id shape — 4 different schemes means joining across forks requires a `mesh_ueid` join field (OQ-7 Option C, `05-open-questions.md:73-77`).
- **Missing semantics in CLI/TUI:** priority enum (only string), tags (none), wikilinks (none). All native interfaces are strictly downstream of `tasks.jsonl` (`05-interfaces-tui.md:14`).

---

## Phase 3 readiness per OQ

Carries the 10 OQs from `05-open-questions.md` and maps new Phase 2 evidence onto each.

| OQ-N | Original question | New evidence from Phase 2 |
|------|-------------------|----------------------------|
| **OQ-1** Storage topology (`05-open-questions.md:7-19`) | `~/.ikigai/` vs `life/data/` vs declared registry? | Each fork declares its OWN root: tuiboard → filesystem (no DB); taskdog → `~/.local/share/taskdog/tasks.db` (`02-fork-taskdog.md:170`); solverforge-calendar → `$SOLVERFORGE_DATA_DIR/solverforge/calendar.db` (`03-fork-solverforge-calendar.md:99`); interfaces/cli → `life/data/tasks.jsonl` (`04-interfaces-cli.md:87-89`). There is NO central registration — every fork invents its own root. Phase 3 needs Option C (declared registry). |
| **OQ-2** Contracts naming (`05-open-questions.md:21-32`) | `src/contracts/` (Pydantic) vs `vibe-ops/src/contracts/` (YAML)? | taskdog uses **two-layer naming**: Pydantic v2 in `application/dto/` (DTOs) + SQLAlchemy ORM in `infrastructure/persistence/database/models/` (persistence contracts) (`02-fork-taskdog.md:130-132`). This disambiguates "wire schema" from "persistence schema". life should adopt this pattern — Option C (different layers, distinct names) from `05-open-questions.md:29`. |
| **OQ-3** tasks.jsonl THE MESH INTERCHANGE? (`05-open-questions.md:34-46`) | Single canonical JSONL or bridge to SQLite+Chroma? | 3 writers (`04-interfaces-cli.md:104-108`) but `tasks.jsonl` is MISSING (`04-interfaces-cli.md:140-142`). Fork architectures (SQLite per fork + UPI as superset at `03-fork-solverforge-calendar.md:90`) suggest JSONL cannot be the mesh interchange — fork DBs are richer. Recommend **bridge role only**; `upi_sync` + UPI tables become the mesh substrate. |
| **OQ-4** Data-first gate interpretation (`05-open-questions.md:48-60`) | Path/contracts repair = "new code" violation? | Phase 2 confirms interfaces/cli + interfaces/tui CANNOT read `tasks.jsonl` because it does not exist (`04-interfaces-cli.md:140-142`, `05-interfaces-tui.md:38`). Step 0 path fixes + Step 2 contracts unification are PREREQUISITES for any data to flow — strictly Option C (hybrid: path fixes OK as plumbing, contracts unification gated on logs) per `05-open-questions.md:58`. |
| **OQ-5** Federation vs single source (`05-open-questions.md:62-74`) | `vibe_ops.db` mesh + operational SQLite as write master, or collapse? | taskdog is **federated by design**: 1 SQLite file (5 tables) + DB-resident notes + audit + separate `~/.local/share/...` root (`02-fork-taskdog.md:131-141, 170`). solverforge-calendar maintains 2 separate DBs (`calendar.db` + `unified_planning.db`) (`03-fork-solverforge-calendar.md:87-91`). Pattern: each concern gets its own DB. life should adopt **Option A (federated)** with explicit ETL via `upi_sync`. |
| **OQ-6** MiniMax proxy — intended or accidental? (`05-open-questions.md:76-87`) | `base_url=api.minimax.io` intentional? | Phase 2 found ZERO references to MiniMax in any fork (`interfaces/{tuiboard,taskdog,solverforge-calendar,cli,tui}` and `apps/mcp-gateway/`). Proxy is purely an ikigai concern, isolated from forks. Phase 3 decision does not block fork integration. |
| **OQ-7** UEID join key (`05-open-questions.md:89-101`) | Unify 5-part `namespace:type:slug:uuid:hash` vs underscore `<prefix>_<slug>`? | interfaces/cli writes 5-part UEIDs (`04-interfaces-cli.md:48`); NO fork has any UEID — taskdog uses int, solverforge-calendar uses UUID v4, tuiboard uses board-path + position. The mesh has NO UEID today. Fork UPI uses `(system, board_card_id)` PK in `sync_map` (`03-fork-solverforge-calendar.md:91`) — a per-system composite key, structurally similar to `system:type:id`. **Option C** (keep both; add `mesh_ueid` join field) is forced by reality — UEID exists only on the life side. |
| **OQ-8** Two MCP transports (`05-open-questions.md:103-115`) | Keep decoupled (ikigai stdio + gateway HTTP) or unify? | All 3 forks use stdio-only (tuiboard stdio only `01-fork-tuiboard.md:159`; taskdog stdio only via FastMCP `02-fork-taskdog.md:177`; solverforge-calendar stdio + HTTP stub **but the http feature is NOT in `Cargo.toml` features list** so the branch is compile-dead `03-fork-solverforge-calendar.md:199`). Net: today, all forks are stdio. ikigai MCP at `src/ikigai/src/mcp_server/server.py` is also stdio. **Option A** (keep decoupled — ikigai stdio for kernel, gateway for forks) is the natural answer; the HTTP question only matters for future remote agents. |
| **OQ-9** 4 stub workflows: implement or deregister? (`05-open-questions.md:117-129`) | `quarterly_replan`, `test_de_fogo_rollup`, `correction_protocol`, `dream_falsification` — build or remove? | Phase 2 confirms forks have NO LangGraph integration at all (taskdog uses controllers, solverforge-calendar uses rmcp + tokio, tuiboard uses SolidJS) — so the 4 stubs are unrelated to fork mesh design. Decision is independent. Recommend **deregister** unless a concrete user demand surfaces (Step 7 of `04-sequencing.md:54-66`). |
| **OQ-10** mcp-gateway orphan: merge or discard? (`05-open-questions.md:131-142`) | ~1600 lines unmerged since 2026-08-26. | Phase 2 traversed the gateway config extensively (`01-fork-tuiboard.md:215-247`, `02-fork-taskdog.md:219-253`, `03-fork-solverforge-calendar.md:213-238`). Findings: (a) 3 cwd paths STALE (B-01 confirmed); (b) `taskdog_*` prefix matches NO tools (`02-fork-taskdog.md:235`); (c) `archive_task` is a dead token (`02-fork-taskdog.md:241`); (d) `solverforge-calendar` is FALLBACK for unknown (`router.py:24`) — risk of misrouting. **Merge is required**, but first must repair the prefix list bugs. Cherry-pick the gateway core; reject the prefix table. |

**Net readiness:** OQ-1, OQ-2, OQ-5, OQ-7, OQ-8, OQ-10 have NEW fork evidence and can be resolved in Phase 3. OQ-3, OQ-4, OQ-6, OQ-9 are unchanged from Phase 1 (no new fork evidence).

---

## Trade-offs (mesh vs federation per fork)

Each fork can integrate with a central mesh OR remain federated. Trade-offs per fork:

### tuiboard
- **Mesh integration:** Adopt a canonical UEID as `board_card_id` in solverforge-calendar's `sync_map` schema (`03-fork-solverforge-calendar.md:91`). Replace tuiboard's `columnIndex + taskIndex` position-based id with UEID + 8-char prefix to match interfaces/cli convention (`04-interfaces-cli.md:23`).
- **Federation:** Keep markdown as source of truth; have a watcher emit `[[wikilink]]` deltas to solverforge-calendar `upi_sync` (already wired at `03-fork-solverforge-calendar.md:180`). UI stays fork-local; mesh is observation-only.
- **Trade-off:** Mesh = simpler joins, but breaks the round-trip markdown fidelity invariant (`01-fork-tuiboard.md:290-291`). Federation = preserves markdown, but mesh queries must reconcile async deltas.
- **Phase 2 recommendation:** Federation. tuiboard's atomic-rename + round-trip pipeline (`01-fork-tuiboard.md:256-291`) is load-bearing; breaking it for a UEID retrofit is high risk for low gain (mesh queries can use `sync_map` instead).

### taskdog
- **Mesh integration:** Repoint all 26 MCP tools under a single `taskdog.*` namespace at gateway (`02-fork-taskdog.md:253`). Adopt UEID as a second column on `tasks` (keep `id: int` as PK; add `ueid TEXT UNIQUE`). Migrate 3 writers (`daily_consolidator.py`, `_write_tasks_to_data`, `_read_tasks_from_data`) onto shared contract (`04-sequencing.md:29-34`).
- **Federation:** Keep taskdog SQLite as source of truth; expose `taskdog.task_created/updated/deleted` WebSocket events to the gateway (`02-fork-taskdog.md:281-285`); solverforge-calendar subscribes via UPI. Each fork polls; no central write authority.
- **Trade-off:** Mesh = single source of truth (good for joins, bad for autonomy). Federation = matches taskdog's clean architecture (5-package workspace + Pydantic/SQLAlchemy split, `02-fork-taskdog.md:117-118`).
- **Phase 2 recommendation:** Federation. taskdog's `controllers/` → `use_cases/` → `repositories/` layering (`02-fork-taskdog.md:36-41`) is well-defined; centralizing writes would force a 6th package just to coordinate.

### solverforge-calendar
- **Mesh integration:** solverforge-calendar IS the mesh substrate. Its `unified_planning_items` (`03-fork-solverforge-calendar.md:90`) is already a superset with `provenance JSON` + `ikigai JSON`. Promote `upi_sync` MCP tool (`03-fork-solverforge-calendar.md:180`) to be the canonical write path.
- **Federation:** Keep `calendar.db` separate; treat `unified_planning.db` as a derived projection (already this way at `03-fork-solverforge-calendar.md:87-91`).
- **Trade-off:** Mesh = solves OQ-1 (storage topology), OQ-5 (federation), OQ-7 (UEID via `sync_map`), but requires fixing 4 known mesh-blocking bugs: (a) `google_sync` stub at `mcp.rs:773`, (b) HTTP+SSE feature-gated out at `mcp.rs:916-958`, (c) `google-calendar3 7.0` unused dependency (`03-fork-solverforge-calendar.md:143, 400`), (d) `recurrence_exceptions` dead schema (`03-fork-solverforge-calendar.md:401`).
- **Phase 2 recommendation:** **Hybrid**. Use solverforge-calendar's UPI as the mesh substrate (Option B for OQ-3). Fix the 4 bugs as part of mesh integration; otherwise solverforge-calendar cannot be the canonical write path.

### interfaces/cli
- **Mesh integration:** Wait for `data/tasks.jsonl` to actually exist (it does not, per `04-interfaces-cli.md:140-142`). Then migrate the 14-field schema (`04-interfaces-cli.md:34-53`) to import from `src/contracts/task.py` (Pydantic v2).
- **Federation:** Keep JSONL as a thin query/replay layer over mesh; CLI never writes (already true: only `done` writes, and only to `feedback.jsonl` per `04-interfaces-cli.md:57-63`).
- **Trade-off:** Mesh = inherits UEID validation; Federation = preserves append-only invariant (`05-interfaces-tui.md:14`).
- **Phase 2 recommendation:** Federation. The CLI is downstream of `tasks.jsonl`; making it a mesh client adds a dependency that does not exist today.

### interfaces/tui
- **Mesh integration:** Cannot happen until code exists (`05-interfaces-tui.md:33-44`). If/when built, follow interfaces/cli pattern.
- **Federation:** Same as CLI.
- **Trade-off:** Mesh requires Step 0 + Step 2 + Step 3 + Step 6 to complete first (`04-sequencing.md`). Federation allows partial functionality (read-only viewer) once Step 6 ships.
- **Phase 2 recommendation:** **Defer**. Per memory `[[data-first-methodology]]` (SONHO 1/5) and `05-interfaces-tui.md:140-145`, no new code until 5+ manual logs prove the workflow. Build sequence: Step 0 → Step 6 → TUI scaffolding → TUI features.

---

## Cross-references

### Phase 1 audit anchors
- `docs/diagnostics/2026-08-28-phase1-audit/00-INDEX.md` (40 lines)
- `docs/diagnostics/2026-08-28-phase1-audit/01-verified.md` B-01, B-04, B-05, B-07, B-08 (verified items)
- `docs/diagnostics/2026-08-28-phase1-audit/02-critic-gaps.md` #4 (CLI architectural lie), #7 (3x contracts drift), #8 (CLI install drift)
- `docs/diagnostics/2026-08-28-phase1-audit/03-priority-matrix.md` PR-1 (path), PR-2 (contracts), PR-3 (sensor), PR-4 (langgraph), PR-5 (PolicyEngine)
- `docs/diagnostics/2026-08-28-phase1-audit/04-sequencing.md` Steps 0-8
- `docs/diagnostics/2026-08-28-phase1-audit/05-open-questions.md` OQ-1..OQ-10

### Phase 2 RE outputs
- `01-fork-tuiboard.md` — 332 lines
- `02-fork-taskdog.md` — 497 lines
- `03-fork-solverforge-calendar.md` — 418 lines
- `04-interfaces-cli.md` — 197 lines
- `05-interfaces-tui.md` — ~165 lines
- `00-INDEX.md` (this synthesis companion)

### Key external files cited
- `apps/mcp-gateway/config/gateways.yaml:1-16` (STALE per B-01)
- `apps/mcp-gateway/src/mcp_gateway/router.py:4-25` (prefix + exact + FALLBACK)
- `apps/mcp-gateway/src/mcp_gateway/process_manager.py:8-47` (subprocess + restart)
- `src/ikigai/src/mcp_server/server.py:287-327` (`_write_tasks_to_data` producer)
- `vibe-ops/src/pipeline/daily_consolidator.py:108, 327, 352, 402` (alternative producer)
- `vibe-ops/src/contracts/sync_contract_v1.py` (load-bearing YAML, 2 importers per OQ-2)
- `src/contracts/{common,task,planning,metrics}.py` (canonical Pydantic, 0 importers)
- `vibe-ops/src/schemas/pydantic_v2.py` (48 LOC stub, 3 importers per B-07)

### Memory references
- `[[interfaces-architecture-2026-08-27]]` — native CLI/TUI = operator control plane; forks = user views
- `[[windows-orphan-dir-delete]]` — apps/{kanban,dev-tools,calendar} cleared 2026-08-28
- `[[orchestration-clone-playground]]` — tuiboard + taskdog + solverforge-calendar are vendored MIT/Apache forks
- `[[ag3-gateway-orphan-2026-08-27]]` — gateway unmerged since 2026-08-26 (OQ-10)
- `[[data-first-methodology]]` — SONHO 1/5; no new code until 5+ manual logs
- `[[pav-cli-tui-future-feature-2026-08-27]]` — PAV CLI/TUI deprecated 2026-08-26 (not in mesh scope)
- `[[ai-native-strategic-model-migration]]` — 2026-08-26 architectural shift to AI-native MCP contracts

### Pitfalls noted
- `gateways.yaml:4,9,14` cwd paths reference DELETED dirs (`apps/{kanban,dev-tools,calendar}`); forks now at `life-oss/interfaces/{tuiboard,taskdog,solverforge-calendar}` (`01-fork-tuiboard.md:243`, `02-fork-taskdog.md:458`, `03-fork-solverforge-calendar.md:402`).
- Gateway command for tuiboard is `["bun", "run", "src/bin/tuiboard.ts", "--mcp"]` — wrong; MCP entry is `bin/tuiboard-mcp.ts:16` not the launcher (`01-fork-tuiboard.md:327`).
- Gateway expects `taskdog_*` prefix + `archive_task` exact — both are dead entries (`02-fork-taskdog.md:235, 241`); 20 of 26 taskdog tools unreachable today.
- solverforge-calendar `google_sync` MCP tool is a stub returning `not_implemented` (`03-fork-solverforge-calendar.md:179`); real sync is CLI-only at `src/cli.rs`.
- solverforge-calendar HTTP+SSE transport is compile-dead (`http` feature not in `Cargo.toml` features list, `03-fork-solverforge-calendar.md:199, 399`).
- `data/tasks.jsonl` MISSING today (`04-interfaces-cli.md:140-142`); 3 writers never invoked.
- interfaces/tui is README-only — no source code, no entry point, no deps (`05-interfaces-tui.md:11-44`).
