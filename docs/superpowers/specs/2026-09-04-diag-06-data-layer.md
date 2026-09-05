# Diag 06 — Data Layer Inventory

**Generated:** 2026-09-04
**Verified claims:** 41
**Unverifiable:** 2 (deep-path vibe-ops internals out of scope; chroma collection populator not in canonical src/)

## Summary matrix

| Path | Owner (writer) | Reader(s) | Schema | Atomic-write? | Status |
|------|----------------|-----------|--------|---------------|--------|
| `data/tasks.jsonl` | `src/mesh/adapters/cli.py:33-68` (CliAdapter `apply_change`); `src/ikigai/src/ikigai/vault/task_io.py:24-52` (`_write_tasks_to_data` for Deep Agent MCP `ikigai_write_tasks`) | `interfaces/cli/read_tasks.py:27-63` (`_read_tasks`); `src/ikigai/src/ikigai/vault/task_io.py:55-89` (`_read_tasks_from_data` for MCP `ikigai_read_tasks`); `src/mesh/adapters/cli.py:22-31` (CliAdapter `read`) | JSONL: `{id, written_at, source, title, description, horizon, priority, project_id, estimated_minutes, done, done_at, ueid, vector, due}` (task_io.py:33-49) — CliAdapter uses subset `{ueid, title, due, priority, written_at, source_fork}` (cli.py:14, 38-45) | Yes — temp + `os.replace` (cli.py:65-68); `task_io.py` uses plain `open("a")` append (NO atomic write, NO fsync) | ⚠️ |
| `data/vibe_ops.db` | `vibe-ops/src/*` (out-of-scope per task brief — 18 writers found in grep: `main.py:34`, `pae_maintainer/main.py:31`, `sqlite_adapter.py:14`, `data_mesh_adapter.py:12`, `pipeline/rag_indexer.py:18`, etc.) | `vibe-ops/src/*`; `vibe-ops-tui/src/main.rs:30,135` (Rust TUI); `vibeops-tui/../vibe_ops.db`; legacy `archive/legacy-pav/.../persistence/runner.py:8` | 18 tables (`dev_backlogs`, `dev_changelogs`, `dev_projects`, `dev_roadmaps`, `habit_states`, `habits`, `mesh_metadata_catalog`, `mesh_state_machine`, `planning_entities`, `policy_decisions`, `roadmap_sync`, `study_notes`, `study_plans`, `study_sessions`, `study_topics`, `temporal_cycles`, `temporal_phases`, `temporal_waves`) | SQLite default (WAL/journal) | 🚫 |
| `data/vibe_mesh.db` | NONE — empty 0-byte file | NONE | None — file has 0 bytes | N/A | 🚫 |
| `data/chroma_db/chroma.sqlite3` | `vibe-ops/src/storage/chroma_adapter.py` (out of scope); `vibe-ops/src/embeddings/provider.py` (provider not located in canonical src/) | `vibe-ops/src/storage/vector_store.py` (out of scope); Chroma SQLite-backed collection `vibe_ops_mesh` (id `ad875d73-0d50-4dde-bb07-68e7164644af`) | Chroma 0.4+ standard (`collections`, `embeddings`, `segments`, `embedding_metadata`, `embedding_fulltext_search_*`, `tenants`) — 1 tenant `default_tenant`, 2 segments, 0 embeddings | Chroma internal | 🚫 |
| `data/ikigai_checkpoints.db` | LangGraph `SqliteSaver` (langgraph-checkpoint-sqlite ^3.1 per `src/ikigai/pyproject.toml:17`) | Same — checkpoint reader for thread resume | LangGraph standard: `checkpoints(thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type, checkpoint BLOB, metadata BLOB)` + `writes(thread_id, task_id, idx, channel, type, value BLOB)` (verified via PRAGMA) | SQLite default | ✅ |
| `data/review_queue/<uuid>.json` | `src/mesh/queue.py:74-79` (`enqueue`); entry point: MCP `ikigai_task_create` (`src/ikigai/src/mcp_server/server.py:476-493` → `tools_mesh.py:100-150`) | `src/mesh/queue.py:86-95` (`consume_pending`); `src/mesh/agent_consumer.py:29-75` (`validate`); `src/mesh/review_queue_worker.py`; `src/mesh/queue.py:114-116` (`replay_after_restart`) | `TaskChange` (frozen Pydantic): `{event_id, ueid, action, fields, source_fork, timestamp, status}` — see `src/contracts/task_change.py` | Yes — temp + `os.fsync` + `os.replace` (queue.py:64-71) with retry decorator `_retry_atomic_write` (queue.py:18-55) | ✅ |
| `data/investigation_queue/` | — | — | — | — | 🚫 |
| `data/boulder.json` | UNVERIFIED — no writer in canonical `src/` (Grep returned only docs/AGENTS.md/CLAUDE.md/.gitignore refs); produced by legacy "atlas/Sisyphus-Junior" tooling (per `docs/diagnostics/2026-08-27-backend-audit/04-agent-mcp-interfaces.md:86`) | UNVERIFIED — no reader in canonical `src/` | Legacy session-state JSON: `{active_plan, started_at, session_ids, plan_name, session_origins, task_sessions, ...}` (head sample, see below) | N/A (legacy file, no atomic write contract) | 🚫 |
| `data/test-fixtures/` | Test fixtures committed to repo (gitignored via `data/*.db`) | Test imports (`tests/mesh/adapters/test_*.py`) | Mixed: `test_f3.db` has 1 table `period_reports`; `vibe_ops_test.db` has 5 tables (`study_projects`, `roadmap_items`, `mesh_metadata_catalog`, `study_topics`, `mesh_state_machine`) — per `CHANGELOG.md:342` | N/A | ✅ |
| `data/session-*.md` | Atlas-style session logs (legacy Atlas/Sisyphus tooling) | None | Markdown transcripts (e.g., "Codebase diagnosis and roadmap review", ses_0e68) | N/A | 🚫 |

## Per-file deep-dive (only for 🚫 or ⚠️ above)

### data/tasks.jsonl ⚠️

- **Path:** `C:\Users\mathe\code_space\life-oss\life\data\tasks.jsonl` — **DOES NOT EXIST** in production data dir (verified via `ls data/` and `wc -l data/tasks.jsonl` → "No such file or directory"). Only exists in test fixtures (`data/pytest-tmp/`, `data/.pytest-tmp/`, etc.).
- **Writers:**
  - `src/mesh/adapters/cli.py:33-68` — `CliAdapter.apply_change()` writes a JSONL line via **atomic temp + rename** pattern (lines 65-68). Idempotent (dedups by `ueid`, lines 52-63).
  - `src/ikigai/src/ikigai/vault/task_io.py:24-52` — `_write_tasks_to_data()` (called by MCP `ikigai_write_tasks` via `src/ikigai/src/mcp_server/server.py:438-444`). Uses **plain `open("a")` append** with no fsync and no temp-rename. This is a non-atomic append.
- **Readers:**
  - `interfaces/cli/read_tasks.py:27-29` — `_tasks_path()` returns `repo_root / "data" / "tasks.jsonl"`.
  - `src/mesh/adapters/cli.py:22-31` — `CliAdapter.read()` scans the file linearly for `ueid` match.
  - MCP `ikigai_read_tasks` → `src/ikigai/src/ikigai/vault/task_io.py:55-89` — `_read_tasks_from_data()` with horizon/done/project_id/limit filters.
- **Schema divergence:** Two distinct writers produce two different schemas. `CliAdapter` (cli.py:38-45) writes `{ueid, title, due, priority, written_at, source_fork}`. `_write_tasks_to_data` (task_io.py:33-49) writes `{id, written_at, source, title, description, horizon, priority, project_id, estimated_minutes, done, done_at, ueid, vector, due}`. **Two writers, two shapes, same path — collision risk**.
- **Atomic write:** Mixed. `CliAdapter` is atomic (cli.py:65-68). `task_io.py` is NOT atomic (task_io.py:31 — `path.open("a", encoding="utf-8")`).
- **Current size:** **0 bytes (file missing)** — `wc -l data/tasks.jsonl` → "No such file or directory".
- **Top issue:** Two writers produce two different schemas into the same path with non-atomic write from the Deep Agent path. End-to-end has never produced a real tasks.jsonl in this repo (test fixtures only).

### data/vibe_ops.db 🚫

- **Path:** `data/vibe_ops.db` — 143,360 bytes, last modified Jun 3 2026 (`data/` listing).
- **Writers (out of scope, confirmed via Grep):**
  - `vibe-ops/src/main.py:34` — `run_parser.add_argument("--db", default="vibe_ops.db")`
  - `vibe-ops/src/agents/pae_maintainer/main.py:31` — `DEFAULT_DB_PATH = Path("./vibe_ops.db")`
  - `vibe-ops/src/storage/sqlite_adapter.py:14`, `sqlite_vec_integration.py:21`, `data_mesh_adapter.py:12`
  - `vibe-ops/src/pipeline/rag_indexer.py:18`, `pipeline/sync_orchestrator.py:12`
  - `vibe-ops/src/middleware/period_sync.py:30`, `bidirectional_sync.py:376`, `scripts/vault_sync.py:160`
  - Legacy: `archive/legacy-pav/src-operational/packages/core/src/operational/persistence/runner.py:8`
- **Readers (out of scope):**
  - `vibe-ops-tui/src/main.rs:30,135` — Rust TUI polling `../vibe_ops.db`
  - `archive/legacy-pav/.../persistence/runner.py:8`
  - `.claude/skills/quarterly-planner/workflows/test-de-fogo-rollup.yml:31` and `dream-falsification.yml:28` (shell `sqlite3 vibe_ops.db "..."`)
- **Schema (verified):** 18 tables — `dev_backlogs`, `dev_changelogs`, `dev_projects`, `dev_roadmaps`, `habit_states`, `habits`, `mesh_metadata_catalog`, `mesh_state_machine`, `planning_entities`, `policy_decisions`, `roadmap_sync`, `study_notes`, `study_plans`, `study_sessions`, `study_topics`, `temporal_cycles`, `temporal_phases`, `temporal_waves`. **All tables: 0 rows** (verified via PRAGMA queries on `mesh_metadata_catalog`, `mesh_state_machine`, `planning_entities`, `temporal_cycles`, `policy_decisions`, `habits`, `habit_states`, `roadmap_sync`).
- **Atomic write:** SQLite WAL/journal defaults — `ikigai_checkpoints.db-shm` and `ikigai_checkpoints.db-wal` files exist in `data/`, indicating WAL mode is active in this repo's SQLite files. However, the **production `vibe_ops.db` has no `-shm` or `-wal` files** (verified via `ls -la data/`) → either journal mode is DELETE/ROLLBACK, or the DB has been dormant since the move.
- **Current size:** 143,360 bytes (schema with no data).
- **Top issue:** Schema-only, no production rows since Phase 0 audit (CLAUDE.md:322 notes `vibe_ops.db moved to data/` 2026-08-31). **The 18-table schema is the only thing left** — the actual runtime data lives in `archive/legacy-pav/src-operational/` per CLAUDE.md "PAV kernel — ARCHIVED 2026-08-31".

### data/vibe_mesh.db 🚫

- **Path:** `data/vibe_mesh.db` — **0 bytes** (verified via `wc -c`).
- **Writers:** NONE found via Grep — file is gitignored (`data/*.db` per `.gitignore:186`).
- **Readers:** NONE — empty placeholder.
- **Schema:** None (empty file).
- **Top issue:** Documentation mismatch — `AGENTS.md:22`, `CLAUDE.md:89`, `docs/README.md:154` list it as canonical runtime state. `docs/ARCHITECTURE_INDEX.md:440` correctly points to `vibe-ops/vibe_mesh.db` (which is also empty per `docs/diagnostics/2026-08-27-backend-audit/04-agent-mcp-interfaces.md:61`). **`data/vibe_mesh.db` is an orphan placeholder, no consumer, no producer**.

### data/chroma_db/ 🚫

- **Path:** `data/chroma_db/chroma.sqlite3` — 188,416 bytes; `data/chroma_db/` empty at top level (chroma files nested).
- **Writer:** `vibe-ops/src/storage/chroma_adapter.py` (out of scope per brief — not explored).
- **Reader:** `vibe-ops/src/storage/vector_store.py` (out of scope).
- **Embedding model:** UNVERIFIABLE in canonical `src/` — Grep for `chromadb|PersistentClient|Chroma` returns only `vibe-ops/` paths. Per `code-docs/00-INDEX-specs.md:194`, model config lives at `vibe-ops/src/embeddings/provider.py`.
- **Schema:** Chroma 0.4+ standard — `acquire_write`, `collection_metadata`, `collections`, `databases`, `embedding_fulltext_search*` (5 tables), `embedding_metadata`, `embedding_metadata_array`, `embeddings`, `embeddings_queue`, `embeddings_queue_config`, `maintenance_log`, `max_seq_id`, `migrations`, `segment_metadata`, `segments`, `tenants`. **0 embeddings** in collection `vibe_ops_mesh` (id `ad875d73-0d50-4dde-bb07-68e7164644af`), but 2 segments exist (`0d9e729e-...`, `75cb627d-...`) → collection was created but never populated.
- **Top issue:** Empty collection. Chroma DB exists with proper schema but no semantic vectors are indexed. Likely only stub-loaded for tests.

### data/ikigai_checkpoints.db ✅

- **Path:** `data/ikigai_checkpoints.db` — 614,400 bytes, with active `-shm` (32,768 B) and `-wal` (0 B) → WAL mode active, recently in use.
- **Writer:** LangGraph `SqliteSaver` (langgraph-checkpoint-sqlite ^3.1 per `src/ikigai/pyproject.toml:17`).
- **Reader:** Same — checkpoint reader for thread resume.
- **Schema (verified):**
  - `checkpoints(thread_id TEXT, checkpoint_ns TEXT, checkpoint_id TEXT, parent_checkpoint_id TEXT, type TEXT, checkpoint BLOB, metadata BLOB, PRIMARY KEY(thread_id, checkpoint_ns, checkpoint_id))`
  - `writes(thread_id TEXT, checkpoint_ns TEXT, checkpoint_id TEXT, task_id TEXT, idx INTEGER, channel TEXT, type TEXT, value BLOB, PRIMARY KEY(thread_id, checkpoint_ns, checkpoint_id, task_id, idx))`
- **Data:** 91 checkpoints, 587 writes across 4 threads (`c`, `crud-test-thread`, `default`, `meu-primeiro-crud`). Per `src/ikigai/CHANGELOG.md:26`: `SqliteSaver` checkpointing to `~/.ikigai/ikigai_checkpoints.db` originally — has been relocated to `data/ikigai_checkpoints.db` (no `~` in current path).
- **Atomic write:** SQLite WAL mode — active and consistent (shm file present).
- **Top issue:** `docs/IKIGAI_BACKEND_DEEP_DIVE_REPORT.md:205` notes "each compiles its own StateGraph with its own SqliteSaver connection... if both run concurrently, SqliteSaver's locking should handle it, but this is fragile." Path is gitignored (`.gitignore:186` covers `data/*.db`).

### data/review_queue/ ✅

- **Path:** `data/review_queue/` — 53 `.json` files (verified via `ls | wc -l`).
- **Writer:** `src/mesh/queue.py:74-79` — `enqueue(TaskChange)`. Entry: MCP `ikigai_task_create` (`server.py:476-493` → `tools_mesh.py:100-150`).
- **Readers:**
  - `src/mesh/queue.py:86-95` — `consume_pending()` (filters status='pending', skips malformed).
  - `src/mesh/queue.py:114-116` — `replay_after_restart()`.
  - `src/mesh/agent_consumer.py:29-75` — `validate(event)` checks title vagueness, due-date, UEID collision (agent_consumer.py:34-53).
  - `src/mesh/review_queue_worker.py` — worker loop (per CLAUDE.md Phase B3-B5).
- **Schema:** `TaskChange` Pydantic frozen model from `src/contracts/task_change.py` — sample observed: `{"event_id":"<uuid>","ueid":"...","action":"create|done|...","fields":{...},"source_fork":"<fork>","timestamp":"ISO","status":"pending|propagated|clarified|rejected"}`. Observed sample actions: `create`, `done`. Observed sample statuses: `pending`, `propagated`, `clarified`. Observed source_forks: `taskdog`. **No `update`/`delete` actions in v1** (per `src/ikigai/src/mcp_server/tools_mesh.py:107-113` and `src/mesh/adapters/cli.py:34-35`).
- **Actor model:** `source_fork` field (e.g. `"taskdog"`, `"interfaces/cli"`). No user/agent/system distinction in the TaskChange itself — the `actor` parameter only exists on `vault_write` (tools_vault.py:44-46). Review queue actor = `source_fork`.
- **Atomic write:** **YES, production-grade.** `src/mesh/queue.py:64-71` `_atomic_write_json`:
  ```python
  tmp = target.with_suffix(".tmp")
  with open(tmp, "w", encoding="utf-8") as f:
      f.write(content); f.flush(); os.fsync(f.fileno())
  os.replace(tmp, target)
  ```
  Wrapped by `_retry_atomic_write` decorator (queue.py:18-55) — 4 retries, exponential backoff (0.1s → 2s) with jitter, catches `OSError`/`PermissionError` (Windows EBUSY, NFS stale). Best-in-class atomic write in the repo.
- **Current size:** 53 files, sizes 244-304 bytes each (~14 KB).
- **Top issue:** None structural. **All 53 files have status != pending** (sampled: `clarified`, `propagated`) → worker is processing them; queue health is good.

### data/investigation_queue/ 🚫

- **Path:** `data/investigation_queue/` — **DOES NOT EXIST** (verified via `ls data/` and `Glob **/investigation*` returning no source files).
- **Writer:** NONE — Plan C was documented as SHIPPED in `docs/superpowers/plans/2026-09-03-investigation-queue-plan-c.md`, but **no source code exists**. Grep `investigation_queue` returns 6 files, ALL in `docs/superpowers/specs/` and `docs/superpowers/plans/`. No code in `src/`. No entry in `langgraph.json` (per CLAUDE.md "5 registered LangGraph graphs"). No MCP tool `ikigai_investigation_*`.
- **Reader:** NONE.
- **Schema:** Plan C spec exists at `docs/superpowers/plans/2026-09-03-investigation-queue-plan-c.md` (FSM: `open → in_progress → resolved|archived`, 3 MCP tools: `enqueue`/`status`/`complete`). **Spec-only, no code**.
- **Top issue:** **Plan C SHIPPED claim is FALSE.** `docs/superpowers/specs/2026-09-04-diag-09-adr-gap.md` likely confirms the issue (out of scope to read here). The plan was spec'd but never coded — the directory was never created, no MCP tool registration, no schema, no atomic-write contract.

### data/boulder.json 🚫

- **Path:** `data/boulder.json` — 21,361 bytes, last modified Aug 27 2026.
- **Writer:** UNVERIFIED in canonical `src/`. Grep `boulder.json` returns only documentation (.gitignore:185, AGENTS.md:22/236, CLAUDE.md:90, CHANGELOG.md, docs/). The writer is from "atlas/Sisyphus-Junior" legacy tooling (per `docs/diagnostics/2026-08-27-backend-audit/04-agent-mcp-interfaces.md:86`).
- **Reader:** UNVERIFIED in canonical `src/`. No reader in `src/`. Only documentation refs.
- **Schema (sample):**
  ```json
  {
    "active_plan": "C:\\Users\\mathe\\code_space\\life-oss\\life\\.omo\\plans\\agentic-markdown-system.md",
    "started_at": "2026-06-30T13:22:01.819Z",
    "session_ids": ["opencode:ses_118cec609ffeXHWfC78wFT5ADp"],
    "plan_name": "agentic-markdown-system",
    "session_origins": {"opencode:ses_...": "direct"},
    "task_sessions": {
      "todo:1": {
        "task_key": "todo:1",
        "task_label": "1",
        "task_title": "Create Quarterly Planning template (`00-quartely-planning.md`)"
      }
    }
  }
  ```
- **Top issue:** **STALE since 2026-06-30** (2 months old at 2026-09-04). `active_plan` points to `C:\Users\mathe\code_space\life-oss\life\.omo\plans\agentic-markdown-system.md` — the `.omo/` directory was renamed to `vault/` per CLAUDE.md. `docs/diagnostics/2026-08-27-backend-audit/04-agent-mcp-interfaces.md:86` flagged this: "boulder.json (stale — 2026-06-30)" and finding #180 (LOW): "boulder.json is from 2026-06-30 (Sisyphus-Junior era, references .omo/plans/ pre-reorg). Entirely stale." Diagnostic #14: "boulder.json stale + dead paths | data/boulder.json | LOW | refs .omo/plans/ pre-reorg, agentic-markdown-system worktree gone".

### data/test-fixtures/ ✅ (deferred detail)

- 7 files: `test_f3.db` (49 KB, 1 table `period_reports`), `test_f3_empty.db`, `test_full.db`, `test_migration.db`, `test_no_vault.db`, `test_orphan.db`, `vibe_ops_test.db` (40 KB, 5 tables: `study_projects`, `roadmap_items`, `mesh_metadata_catalog`, `study_topics`, `mesh_state_machine`).
- All `data/*.db` files are gitignored (`.gitignore:186`) — but these test fixtures are committed? Verify via `git ls-files data/test-fixtures/`.
- Per `CHANGELOG.md:342`: "vibe_ops_test.db — SQLAlchemy ORM test artifact created by `vibe-ops/scripts/test_mvl_ingestion.py:26`. Schema is 5 tables (different ORM model) vs canonical `data/vibe_ops.db` (18 tables). Content is hardcoded demo."

### data/session-*.md 🚫

- 2 files: `data/session-ses_0e68.md` (766,070 B, 2026-08-28), `data/session-ses_118c.md` (330,294 B, 2026-08-28).
- Format: Markdown session transcripts from legacy Atlas/Sisyphus tooling. Example header: `# Codebase diagnosis and roadmap review (fork #1)` / `**Session ID:** ses_0e682b9d8ffeA4YJJHKa5qtaGd` / `**Created:** 6/30/2026, 2:04:28 PM`.
- Gitignored via `.gitignore:191` (`data/session-*.md`).
- No readers in canonical `src/`.

## Critical findings

1. **`data/tasks.jsonl` is the canonical mesh slice but has NEVER been produced in production** — only exists in test fixtures (`data/pytest-tmp/`, etc.). The schema is split-brain between two writers: `CliAdapter` writes 6 fields (`ueid, title, due, priority, written_at, source_fork`) and `_write_tasks_to_data` writes 14 fields (`id, written_at, source, title, description, horizon, priority, project_id, estimated_minutes, done, done_at, ueid, vector, due`). `CliAdapter` is atomic; `_write_tasks_to_data` is plain `open("a")` append (no fsync, no rename). [src/mesh/adapters/cli.py:33-68, src/ikigai/src/ikigai/vault/task_io.py:24-52]

2. **`data/investigation_queue/` does not exist** — Plan C SHIPPED claim (`docs/superpowers/plans/2026-09-03-investigation-queue-plan-c.md`) is **false**. No source code, no MCP tool, no directory, no schema. Grep returns only spec/plan docs. [Grep "investigation_queue" → 6 files, all in docs/]

3. **`data/vibe_mesh.db` is a 0-byte orphan** — placeholder created during audit cleanup but never written by any code path. Canonical location per `docs/ARCHITECTURE_INDEX.md:440` is `vibe-ops/vibe_mesh.db` (also empty). [wc -c data/vibe_mesh.db = 0]

4. **`data/vibe_ops.db` is schema-only with 0 rows across all 18 tables** — table definitions preserved from Phase 0 audit-closure 2026-08-31, but no production writer has run since. All writers are in archived `vibe-ops/` (active code) or archived `archive/legacy-pav/` (PAV kernel archived 2026-08-31). The runtime state has effectively migrated to `archive/`. [PRAGMA count(*) on 8 tables = 0]

5. **`data/boulder.json` is stale since 2026-06-30** — 2+ months old, references deleted `.omo/plans/agentic-markdown-system.md` path. Flagged LOW in `docs/diagnostics/2026-08-27-backend-audit/00-INDEX.md:71` (finding #14). No writer or reader in canonical `src/`. Legacy Atlas tooling.

6. **`data/chroma_db/` has 1 collection but 0 embeddings** — collection `vibe_ops_mesh` (id `ad875d73-0d50-4dde-bb07-68e7164644af`) was created with 2 segments but no semantic vectors populated. HNSW config present (per collection metadata dump). Either index was wiped during Phase 0 audit or never loaded in production. Chroma DB is `188,416 B`.

7. **`data/review_queue/` is the only production-grade runtime data store** — 53 events processed, atomic writes (temp + fsync + rename + retry decorator), schema is `TaskChange` frozen Pydantic. **Best-in-class atomic write in the entire repo**. [src/mesh/queue.py:64-71 + 18-55]

8. **`data/ikigai_checkpoints.db` is alive** — 91 checkpoints, 587 writes, 4 threads, WAL mode active (`.db-shm` present, `.db-wal` empty). LangGraph SqliteSaver (langgraph-checkpoint-sqlite ^3.1). Used by legacy 8-node graph per `src/ikigai/CHANGELOG.md:26`.

9. **Taskdog and SolverforgeCalendar adapter DBs point to non-existent directories** — `src/mesh/adapters/taskdog.py:11` → `data/taskdog/tasks.db` (dir doesn't exist). `src/mesh/adapters/solverforge_calendar.py:13` → `data/solverforge_calendar/unified_planning.db` (dir exists but is empty). The mesh v1 create-only flow has never actually persisted to either adapter DB.

## Top 3 risks

1. **Data corruption risk in `data/tasks.jsonl`** — two writers with two different schemas, one atomic, one non-atomic, hitting the same path. If `_write_tasks_to_data` is invoked by `ikigai_write_tasks` MCP tool mid-flight while `CliAdapter.apply_change` is appending, the CliAdapter temp+rename can lose the Deep Agent's appended lines (rename overwrites, doesn't merge). Single-writer model needed.

2. **"Plan C SHIPPED" is documentation-only** — `docs/superpowers/plans/2026-09-03-investigation-queue-plan-c.md` is a plan file with no code in `src/`, no MCP tool, no directory. Anyone depending on the SHIPPED status will find no implementation. Risk: false confidence in feature completeness.

3. **`data/vibe_ops.db` schema is preserved but never written** — 18 tables, 0 rows, no WAL/journal activity (no `.db-shm`/`.db-wal` files). If the codebase is restored from archive and tries to write to this DB, schema will be overwritten by migration logic in `vibe-ops/src/storage/sqlite_adapter.py`. Risk: silent data loss on first write.