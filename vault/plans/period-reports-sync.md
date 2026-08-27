# Period Reports Sync Layer v1.1

> **Plan ID:** `period-reports-sync`
> **Status:** ✅ **CLOSED** — 10/10 tasks complete, F1-F4 all APPROVED
> **Source draft:** `.omo/drafts/period-reports-sync.md` (archived after plan generation)
> **Dependencies:** `vault-bidirectional-sync` plan T1-T13 must complete first
> **Codebase commit:** a0d6630 (latest fix)
> **SPEC.md:** `specs/period-reports-sync/SPEC.md`

---

## TL;DR

> **Quick Summary**: Build a period_reports-specific sync layer that ingests the 5 official period templates (`_templates_periodos/`) from the vault into `vibe_ops.db` and `operational.db`. Uses a dedicated `PeriodReportSync` class with hierarchy validation (parent_period FK), multi-pass orphan recovery, vault-only sync direction, and aggregate views (`v_period_hierarchy`, `v_onda_aggregated`). Exposes `pav sync vault|list|hierarchy` CLI commands with `--json` output.
>
> **Deliverables**:
> - Migration 004 (vibe-ops): `period_reports` table + 6 indexes + 1 trigger + 2 views
> - Migration 002 (operational mirror): 3 JSON-blob indexes
> - `PeriodReport` Pydantic entity (lenient) + `PeriodReportParser`
> - `PeriodReport` mirror entity (strict `extra="forbid"`)
> - `PeriodReportSync` class with `sync_vault_to_db()` + `get_period_hierarchy()` + no-op `sync_db_to_vault()`
> - CLI: `pav sync vault|list|hierarchy --json` + extended `pav state migrate`
> - Tests: unit + integration + property (Hypothesis) + E2E
>
> **Estimated Effort**: Small-Medium (~30-50KB plan, 8 tasks, sequential after dependency)
> **Parallel Execution**: NO — depends on vault-bidirectional-sync T2 completion
> **Critical Path**: T1 (migration SQL) → T2 (Pydantic entity) → T3 (sync layer) → T4 (CLI) → T5-T8 (tests) → F1-F4

---

## Context

### Original Request
User invoked `/write-tech-spec` style spec for the period_reports sync layer (option 3 from "1. 3." previous round). Source: ADR-006 (Period Reports Schema) + vault-bidirectional-sync plan (T1-T13).

### Interview Summary
**Locked Decisions** (2026-06-26):
- D1 — Migration timing: **Apply on first sync** (`PeriodReportSync.__init__` runs `CREATE IF NOT EXISTS`)
- D2 — Schema validation: **Hybrid** (`extra="allow"` vibe-ops + `extra="forbid"` operational mirror)
- D3 — Sync direction: **Vault-only** (bidirectional structure exists, `sync_db_to_vault()` is no-op)
- D4 — Orphan handling: **Multi-pass retry** (first sync ingests roots, subsequent syncs resolve orphans)
- D5 — Aggregation views: **Yes, include** (`v_period_hierarchy` + `v_onda_aggregated` in migration 004)

### Research Findings
- `vibe-ops/migrations/002_roadmap_sync_v1.sql:1-37` — migration pattern with CHECK constraints, indexes, triggers
- `vibe-ops/src/storage/schema.sql:218-226` — `planning_entities` generic json-blob table
- `vibe-ops/src/middleware/sync_engine.py:1-138` — existing one-way sync pattern
- `vibe-ops/src/pipeline/frontmatter_parser.py:13-77` — FrontmatterParser with MODEL_MAP
- `vibe-ops/src/models/__init__.py:1-29` — entity export pattern
- `life-ops/operational/packages/core/src/operational/persistence/runner.py:24-193` — MigrationRunner (apply_all, apply_one)
- `life-ops/operational/packages/core/src/operational/persistence/migrations/001_initial.sql:1-34` — operational single-table approach
- `life-ops/operational/apps/cli/src/operational/cli/commands/policy_cmd.py:1-60` — Typer command pattern
- `life-ops/operational/apps/cli/src/operational/cli/app.py:25-100` — add_typer registration pattern
- `vibe-ops/tests/test_knowledge_telemetry.py:1-50` — existing test patterns
- `_templates_periodos/00-README.md` — schema contract (5 templates, 6 required fields)

### Metis Review
**Identified Gaps (addressed)**:
- **G1**: Pydantic v2 strict mode vs lenient — chosen hybrid (lenient ingestion + strict mirror) ✅
- **G2**: Orphan handling could lose data — chosen multi-pass retry (self-healing) ✅
- **G3**: Aggregation views vs Python computation — chosen SQL views (faster, declarative) ✅
- **G4**: Vault-wins conflict policy doesn't apply (no computed fields) — explicitly documented as no-op for v1.1 ✅
- **G5**: Sync direction future-proofing — bidirectional structure exists, code→vault is no-op stub ✅

---

## Work Objectives

### Core Objective
Eliminate the gap between the user's structured period_reports in the vault (5 templates × N filled reports) and the algorithmic engine's SQLite database. Reports become queryable, hierarchy-traversable, and triggerable downstream (PolicyEngine, FalsifiableHypothesis evaluator).

### Concrete Deliverables
1. **Migration 004 SQL** — `vibe-ops/migrations/004_period_reports.sql`
2. **Migration 002 SQL (mirror)** — `life-ops/operational/.../migrations/002_period_reports.sql`
3. **Pydantic entity** — `vibe-ops/src/models/period_report.py` (PeriodReport + PeriodReportParser)
4. **Mirror entity** — `life-ops/operational/.../entities/period_report.py`
5. **Sync layer** — `vibe-ops/src/middleware/period_sync.py` (PeriodReportSync + PeriodSyncStats)
6. **CLI commands** — `life-ops/operational/apps/cli/src/operational/cli/commands/sync_cmd.py`
7. **State migrate** — extend `life-ops/operational/.../commands/state_cmd.py`
8. **Tests** — `vibe-ops/tests/{test_period_report.py, integration/test_period_sync.py, e2e/test_period_reports_full_cycle.py, property/test_period_report_properties.py}`
9. **SPEC.md** — `specs/period-reports-sync/SPEC.md` (created by Sisyphus per `/write-tech-spec` skill)

### Definition of Done
- [ ] `uv run pytest vibe-ops/tests/{test_period_report.py, integration/test_period_sync.py, e2e/test_period_reports_full_cycle.py, property/test_period_report_properties.py}` → 100% pass
- [ ] `uv run mypy --strict` on all new code → 0 errors
- [ ] `uv run ruff check` on all new code → 0 errors
- [ ] Manual E2E: `pav sync vault --folder _templates_periodos --json` on fixture vault with 5 sample reports → JSON returns valid stats
- [ ] Multi-pass test: first sync ingests 1 (sonho), second sync ingests 4 (children), no orphans
- [ ] `pav sync hierarchy --sonho X --json` returns valid nested tree
- [ ] SPEC.md committed to `specs/period-reports-sync/`

### Must Have
- Migration 004 idempotent (`CREATE IF NOT EXISTS` for all DDL)
- 6 indexes covering: period, sonho_id, parent_period, verdict, policy_recommendation, vault_hash, updated_at
- 2 aggregate views: `v_period_hierarchy` (recursive CTE) + `v_onda_aggregated` (3-week rollup)
- 4 Pydantic validators: verdict per period, date range, hierarchy (sonho no parent), verdict-score consistency warning
- Idempotent sync via `vault_hash` (sha256 canonical JSON, 16 chars)
- Multi-pass orphan recovery (run sync N times until orphans=0)
- 3 CLI commands: `vault`, `list`, `hierarchy` (all with `--json`)
- ≥95% line coverage on `models/period_report.py` and `middleware/period_sync.py`

### Must NOT Have (Guardrails)
- No deletion of existing reports (append-only, even when verdict changes)
- No LLM in the sync path (pure arithmetic + YAML I/O)
- No code→vault sync in v1.1 (no-op stub only — structure exists for v2)
- No required schema fields beyond what ADR-006 specifies (extra="allow" preserves user additions)
- No cloud sync, no API keys, no OAuth (fully local)
- No new CLI command without `--json` support
- No breaking changes to existing `planning_entities` table (period_reports is separate)

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (2518 tests in life-ops/operational + 2 existing tests in vibe-ops/tests)
- **Automated tests**: YES (TDD per task — RED → GREEN → REFACTOR)
- **Framework**: pytest with markers `unit`, `integration`, `property`, `e2e`
- **Coverage target**: ≥95% line coverage on new vibe-ops modules

### QA Policy
Every task includes agent-executed QA scenarios. Evidence saved to `.omo/evidence/period-{N}-{scenario-slug}.{ext}`.

---

## Execution Strategy

### Sequential Execution (no parallelization)

This plan cannot run in parallel because:
1. Depends on `vault-bidirectional-sync` T2 completion
2. Migration must apply before entity can be tested
3. Entity must validate before sync layer can use it
4. Sync layer must work before CLI can call it

```
Wave 1 (Sequential — 1 agent):
├── T1: Migration 004 SQL (vibe-ops)
├── T2: Pydantic entity + parser
├── T3: Sync layer (PeriodReportSync + PeriodSyncStats)
├── T4: CLI commands + state migrate extension
├── T5: Unit tests
├── T6: Integration tests
├── T7: Property tests (Hypothesis)
└── T8: E2E test (full month simulation)

Wave 2 (Sequential — 1 agent):
├── T9: Mirror migration 002 (operational) + entity
├── T10: SPEC.md creation (via /write-tech-spec skill)

Wave FINAL (4 parallel reviews):
├── F1: Plan compliance audit
├── F2: Code quality review
├── F3: Real manual QA
└── F4: Scope fidelity check
```

### Dependency Matrix

- **T1**: None → T2, T5, T6, T7, T8
- **T2**: T1 → T3, T5, T7
- **T3**: T1, T2 → T4, T6, T8
- **T4**: T3 → T8
- **T5**: T2 → F1-F4
- **T6**: T3 → F1-F4
- **T7**: T2 → F1-F4
- **T8**: T3, T4 → F1-F4
- **T9**: None (independent of vibe-ops path; uses operational runner) → F1-F4
- **T10**: T2, T3 → F1-F4

### Agent Dispatch Summary

- **Wave 1**: **1** — sequential agent executing T1-T8 (could be split if needed)
- **Wave 2**: **1** — sequential agent executing T9-T10
- **FINAL**: **4** — F1 (oracle), F2 (unspecified-high), F3 (unspecified-high), F4 (deep)

---

## TODOs

- [x] 1. Create migration 004 (vibe-ops period_reports schema)

  **What to do**:
  - Create `vibe-ops/migrations/004_period_reports.sql`
  - Include: `period_reports` table with 4 CHECK constraints
  - Include: 6 indexes (period, sonho_id, parent_period, verdict, policy_recommendation, vault_hash, updated_at)
  - Include: 1 trigger (`trg_period_reports_updated` for `updated_at`)
  - Include: 2 views (`v_period_hierarchy` recursive CTE + `v_onda_aggregated` 3-week rollup)
  - All DDL idempotent (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `CREATE TRIGGER IF NOT EXISTS`, `CREATE VIEW IF NOT EXISTS`)
  - Verify by applying to fresh test DB and inspecting schema

  **Must NOT do**:
  - Do not use `CREATE TABLE` (must be `IF NOT EXISTS`)
  - Do not modify existing tables (schema.sql, roadmap_sync, planning_entities)
  - Do not add columns not specified in draft §1.1

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: None (SQL is well-known)

  **Parallelization**:
  - **Can Run In Parallel**: YES (T9 mirror migration is independent)
  - **Parallel Group**: Wave 1
  - **Blocks**: T2, T5, T6, T7, T8
  - **Blocked By**: None

  **References**:
  - `vibe-ops/migrations/002_roadmap_sync_v1.sql:1-37` — CHECK constraints, indexes, triggers pattern
  - `vibe-ops/src/storage/schema.sql:218-226` — existing planning_entities structure
  - `.omo/drafts/period-reports-sync.md` §1.1 — full SQL spec

  **Acceptance Criteria**:
  - [ ] `sqlite3 test.db < migrations/004_period_reports.sql` succeeds on fresh DB
  - [ ] `sqlite3 test.db ".schema period_reports"` shows all columns + 4 CHECK constraints
  - [ ] `sqlite3 test.db ".indexes period_reports"` shows 6 indexes
  - [ ] `sqlite3 test.db ".schema v_period_hierarchy"` shows recursive CTE
  - [ ] `sqlite3 test.db ".schema v_onda_aggregated"` shows aggregate query
  - [ ] Re-applying migration is no-op (idempotent)

  **QA Scenarios**:
  ```
  Scenario: Migration applies on fresh DB
    Tool: Bash (sqlite3)
    Preconditions: None
    Steps:
      1. rm -f test_period.db
      2. sqlite3 test_period.db < migrations/004_period_reports.sql
      3. sqlite3 test_period.db ".tables"
    Expected Result: shows period_reports, v_period_hierarchy, v_onda_aggregated
    Evidence: .omo/evidence/period-1-migration-tables.txt

  Scenario: Migration is idempotent
    Tool: Bash (sqlite3)
    Preconditions: Migration already applied
    Steps:
      1. sqlite3 test_period.db < migrations/004_period_reports.sql (second time)
    Expected Result: no error (IF NOT EXISTS clauses work)
    Evidence: .omo/evidence/period-1-migration-idempotent.txt

  Scenario: All indexes created
    Tool: Bash (sqlite3)
    Preconditions: Migration applied
    Steps:
      1. sqlite3 test_period.db ".indices period_reports"
    Expected Result: 6 indexes listed
    Evidence: .omo/evidence/period-1-indexes.txt
  ```

  **Commit**: YES
  - Message: `feat(period-sync): migration 004 — period_reports schema + indexes + views`
  - Files: `vibe-ops/migrations/004_period_reports.sql`

---

- [x] 2. Implement PeriodReport Pydantic entity + parser

  **What to do**:
  - Create `vibe-ops/src/models/period_report.py`
  - Define `PeriodReport` (BaseModel) with `model_config = ConfigDict(frozen=False, extra="allow")`
  - Define `_PERIOD_VERDICTS` dict mapping period → allowed verdict set
  - Define `_PERIOD_DAYS` dict mapping period → expected day count
  - Add 4 validators:
    - `@field_validator("verdict")` — verdict per period enum
    - `@model_validator(mode="after")` — `date_end >= date_start`
    - `@model_validator(mode="after")` — date range matches period (±1 day tolerance, exempt for sonho)
    - `@model_validator(mode="after")` — sonho cannot have parent_period
    - `@model_validator(mode="after")` — verdict-score consistency warning (FAIL with score >= 0.5)
  - Define `PeriodReportParser.parse_file(file_path: str) -> PeriodReport | None`
    - Uses `python-frontmatter` to parse YAML
    - Returns None if `type != "period_report"` or `entity_type != "period_report"`
    - Injects `vault_path` from file location
    - Computes `vault_hash` = sha256(json.dumps(metadata, sort_keys=True, default=str))[:16]
  - Export from `vibe-ops/src/models/__init__.py` (add `PeriodReport`, `PeriodReportParser` to imports + `__all__`)
  - Extend `FrontmatterParser.MODEL_MAP` (vibe-ops/src/pipeline/frontmatter_parser.py:18-39) to include `"period_report": PeriodReport`

  **Must NOT do**:
  - Do not use `extra="forbid"` (chose lenient for vibe-ops)
  - Do not require all fields (only the 6 ADR-006 required: type, period, date_start, date_end, verdict, verdict_score)
  - Do not validate tags, policy_recommendation ranges, or ikigai_vector content (optional fields)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO (T3 depends on this)
  - **Parallel Group**: Wave 1
  - **Blocks**: T3, T5, T7
  - **Blocked By**: T1

  **References**:
  - `.omo/drafts/period-reports-sync.md` §1.2 — full entity spec
  - `vibe-ops/src/models/policy_entities.py:10-22` — PolicyDecision pattern
  - `vibe-ops/src/models/__init__.py:1-29` — entity export pattern
  - `vibe-ops/src/pipeline/frontmatter_parser.py:18-39` — MODEL_MAP extension point

  **Acceptance Criteria**:
  - [ ] `PeriodReport(id="x", period="daily", date_start=..., date_end=..., verdict="PASS", verdict_score=0.85, vault_path="x.md", vault_hash="a"*16)` validates
  - [ ] `PeriodReport(...period="daily", verdict="KILL_WAVE", ...)` raises ValueError
  - [ ] `PeriodReport(...period="sonho", parent_period="x", ...)` raises ValueError
  - [ ] `PeriodReport(...period="weekly", date_start=2026-06-01, date_end=2026-07-01, ...)` raises ValueError
  - [ ] `PeriodReportParser.parse_file(non_period_file)` returns None
  - [ ] `PeriodReportParser.parse_file(valid_period_file)` returns PeriodReport with computed vault_hash
  - [ ] `FrontmatterParser.MODEL_MAP["period_report"]` is `PeriodReport`

  **QA Scenarios**:
  ```
  Scenario: Valid daily report instantiates
    Tool: Bash (uv run python -c)
    Preconditions: None
    Steps:
      1. Construct PeriodReport with valid daily fields
      2. Assert no exception
    Expected Result: instance created
    Evidence: .omo/evidence/period-2-entity-valid.txt

  Scenario: Invalid verdict for period raises
    Tool: Bash (uv run python -c)
    Preconditions: None
    Steps:
      1. Construct PeriodReport with period="daily", verdict="KILL_WAVE"
    Expected Result: ValueError mentioning verdict per period
    Evidence: .omo/evidence/period-2-entity-verdict.txt

  Scenario: Parser returns None for non-period file
    Tool: Bash (uv run python -c)
    Preconditions: Temp file with type="project"
    Steps:
      1. Parse file
      2. Assert return value is None
    Expected Result: None
    Evidence: .omo/evidence/period-2-parser-none.txt
  ```

  **Commit**: YES
  - Message: `feat(period-sync): PeriodReport entity + parser`
  - Files: `vibe-ops/src/models/period_report.py`, `vibe-ops/src/models/__init__.py`, `vibe-ops/src/pipeline/frontmatter_parser.py`

---

- [x] 3. Implement PeriodReportSync class

  **What to do**:
  - Create `vibe-ops/src/middleware/period_sync.py`
  - Define `PeriodSyncStats` (BaseModel) with fields: `ingested`, `skipped`, `updated`, `errors`, `conflicts`, `orphans`, `file_errors`
  - Define `PeriodReportSync` class:
    - `__init__(self, vault_path: Path, db_path: Path, template_folder: str = "_templates_periodos")`
      - Apply migration 004 via `CREATE TABLE IF NOT EXISTS` exec (locked decision D1)
    - `sync_vault_to_db() -> PeriodSyncStats`
      - Scan `vault_path / template_folder / *.md`
      - For each file: parse, check existing via vault_hash or id, check parent_period FK, upsert
      - Increment stats counters appropriately
      - Return PeriodSyncStats
    - `_fetch_existing(vault_hash: str, report_id: str) -> bool`
      - SQL: `SELECT 1 FROM period_reports WHERE id = ? OR vault_hash = ? LIMIT 1`
    - `_exists(report_id: str) -> bool`
      - SQL: `SELECT 1 FROM period_reports WHERE id = ? LIMIT 1`
    - `_upsert(report: PeriodReport) -> None`
      - SQL `INSERT INTO period_reports (...) VALUES (...) ON CONFLICT(id) DO UPDATE SET ...`
    - `get_period_hierarchy(sonho_id: str) -> dict`
      - SQL query for all reports with `sonho_id = ? OR id = ?`
      - Build nested tree using `parent_period` FK
      - Return `{"sonho_id": ..., "tree": [...]}`
    - `_build_subtree(node: dict, nodes: dict) -> dict` (private recursive helper)
    - `sync_db_to_vault() -> PeriodSyncStats` — no-op stub for v1.1 (returns zero stats)

  **Must NOT do**:
  - Do not use `extra="allow"` (use `ConfigDict(frozen=True)` for stats; sync class is plain)
  - Do not add complex conflict resolution logic (vault-wins for all fields in v1.1)
  - Do not introduce new dependencies (use stdlib `sqlite3` + `pathlib` + `hashlib`)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**:
  - **Can Run In Parallel**: NO (T4, T6, T8 depend on this)
  - **Parallel Group**: Wave 1
  - **Blocks**: T4, T6, T8
  - **Blocked By**: T1, T2

  **References**:
  - `vibe-ops/src/middleware/sync_engine.py:11-138` — existing sync pattern
  - `.omo/drafts/period-reports-sync.md` §1.3 — full sync layer spec
  - `vibe-ops/migrations/002_roadmap_sync_v1.sql:1-37` — `INSERT INTO ... ON CONFLICT DO UPDATE` pattern

  **Acceptance Criteria**:
  - [ ] `PeriodReportSync(vault, db)` applies migration 004 automatically
  - [ ] `sync_vault_to_db()` on fixture vault (5 valid + 1 broken) returns `PeriodSyncStats(ingested=5, errors=1, orphans=0)`
  - [ ] Second `sync_vault_to_db()` returns `PeriodSyncStats(skipped=5, ingested=0)` (idempotent)
  - [ ] File with broken YAML increments `errors` counter, doesn't abort
  - [ ] File with missing `parent_period` FK increments `orphans` counter, doesn't insert
  - [ ] `get_period_hierarchy("sonho-1")` returns nested tree with children sorted by date

  **QA Scenarios**:
  ```
  Scenario: Sync ingests all valid reports
    Tool: Bash (uv run python -c)
    Preconditions: Fixture vault with 5 valid period reports + 1 broken YAML
    Steps:
      1. Construct PeriodReportSync
      2. Call sync_vault_to_db()
      3. Assert stats.ingested == 5, stats.errors == 1
    Expected Result: stats match
    Evidence: .omo/evidence/period-3-sync-ingest.txt

  Scenario: Idempotent re-sync
    Tool: Bash (uv run python -c)
    Preconditions: After previous scenario
    Steps:
      1. Call sync_vault_to_db() again
      2. Assert stats.skipped == 5, stats.ingested == 0
    Expected Result: stats.skipped matches
    Evidence: .omo/evidence/period-3-sync-idempotent.txt

  Scenario: Multi-pass orphan recovery
    Tool: Bash (uv run python -c)
    Preconditions: Fixture with 1 sonho + 4 children
    Steps:
      1. First sync: assert stats.ingested == 1, stats.orphans == 4
      2. Second sync: assert stats.ingested == 4, stats.orphans == 0
    Expected Result: orphans resolve on second pass
    Evidence: .omo/evidence/period-3-orphan-recovery.txt

  Scenario: Hierarchy tree assembly
    Tool: Bash (uv run python -c)
    Preconditions: After multi-pass sync
    Steps:
      1. Call get_period_hierarchy("sonho-1")
      2. Assert tree has 1 root, 4 children, children sorted by date_start
    Expected Result: nested dict structure
    Evidence: .omo/evidence/period-3-hierarchy.txt
  ```

  **Commit**: YES
  - Message: `feat(period-sync): PeriodReportSync class with vault_hash idempotency + orphan recovery`
  - Files: `vibe-ops/src/middleware/period_sync.py`

---

- [x] 4. Implement CLI commands (sync vault | list | hierarchy) + state migrate

  **What to do**:
  - Create `life-ops/operational/apps/cli/src/operational/cli/commands/sync_cmd.py` with Typer app
  - Commands (all with `--json` flag):
    - `pav sync vault [--folder _templates_periodos] [--vault PATH] [--json]`
      - Default folder: `_templates_periodos`
      - Default vault: `./vault`
      - Constructs PeriodReportSync, calls sync_vault_to_db(), prints stats
      - Outputs JSON or formatted text
    - `pav sync list [--period <period>] [--limit 50] [--json]`
      - SQLite query against `period_reports` table
      - Prints recent reports sorted by date_start DESC
    - `pav sync hierarchy --sonho <id> [--json]`
      - Calls PeriodReportSync.get_period_hierarchy()
      - Outputs JSON or ASCII tree
  - Register in `life-ops/operational/apps/cli/src/operational/cli/app.py` (add_typer near line 102)
  - Extend `state_cmd.py` with `pav state migrate [--json]` command that calls `MigrationRunner.apply_all()`

  **Must NOT do**:
  - Do not add commands without `--json` support
  - Do not import from `vibe-ops/` directly in CLI (use subprocess or well-defined interface)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**:
  - **Can Run In Parallel**: NO (T8 depends on this)
  - **Parallel Group**: Wave 1
  - **Blocks**: T8
  - **Blocked By**: T3

  **References**:
  - `life-ops/operational/apps/cli/src/operational/cli/commands/policy_cmd.py:1-60` — Typer command pattern
  - `life-ops/operational/apps/cli/src/operational/cli/app.py:25-100` — add_typer registration
  - `.omo/drafts/period-reports-sync.md` §1.4 — full CLI spec

  **Acceptance Criteria**:
  - [ ] `pav sync --help` shows vault, list, hierarchy subcommands
  - [ ] `pav sync vault --folder _templates_periodos --json` returns valid JSON with stats fields
  - [ ] `pav sync list --period daily --limit 10 --json` returns array of reports
  - [ ] `pav sync hierarchy --sonho X --json` returns nested tree dict
  - [ ] `pav state migrate --json` applies pending migrations and returns applied list
  - [ ] Exit codes: 0 on success, 1 on error

  **QA Scenarios**:
  ```
  Scenario: pav sync vault --json returns valid JSON
    Tool: Bash (subprocess)
    Preconditions: Fixture vault configured
    Steps:
      1. Run: pav sync vault --folder _templates_periodos --json
      2. Assert exit code 0
      3. Parse stdout as JSON
      4. Assert keys: ingested, skipped, updated, errors, conflicts, orphans, file_errors
    Expected Result: JSON parsed successfully
    Evidence: .omo/evidence/period-4-cli-vault.txt

  Scenario: pav sync list filters by period
    Tool: Bash (subprocess)
    Preconditions: DB with multiple periods populated
    Steps:
      1. Run: pav sync list --period daily --limit 5
      2. Assert output has ≤ 5 lines, all from daily
    Expected Result: filtered list
    Evidence: .omo/evidence/period-4-cli-list.txt

  Scenario: pav sync hierarchy renders tree
    Tool: Bash (subprocess)
    Preconditions: DB with multi-level hierarchy
    Steps:
      1. Run: pav sync hierarchy --sonho <test_id>
      2. Assert output contains nested structure markers
    Expected Result: hierarchy visible
    Evidence: .omo/evidence/period-4-cli-hierarchy.txt

  Scenario: pav state migrate applies migrations
    Tool: Bash (subprocess)
    Preconditions: Operational DB with pending migrations
    Steps:
      1. Run: pav state migrate --json
      2. Parse JSON, assert applied list contains "002_period_reports"
    Expected Result: migration recorded
    Evidence: .omo/evidence/period-4-cli-migrate.txt
  ```

  **Commit**: YES
  - Message: `feat(period-sync): CLI commands (sync vault|list|hierarchy) + state migrate`
  - Files: `life-ops/operational/apps/cli/src/operational/cli/commands/sync_cmd.py`, `life-ops/operational/apps/cli/src/operational/cli/commands/state_cmd.py`, `life-ops/operational/apps/cli/src/operational/cli/app.py`

---

- [x] 5. Write unit tests for PeriodReport entity + parser

  **What to do**:
  - Create `vibe-ops/tests/test_period_report.py`
  - Test classes:
    - `TestPeriodReportValidation` — 8 tests covering all 4 validators
    - `TestPeriodReportParser` — 3 tests covering happy path, None for non-period, error on missing field
  - All tests use `tmp_path` fixture for file creation
  - ≥95% line coverage target

  **Must NOT do**:
  - Do not skip edge cases (empty fields, wrong types, missing required)
  - Do not test implementation details (test behavior only)

  **Recommended Agent Profile**:
  - **Category**: `quick`

  **Parallelization**:
  - **Can Run In Parallel**: YES (independent of T6/T7/T8)
  - **Parallel Group**: Wave 1
  - **Blocks**: F1-F4
  - **Blocked By**: T2

  **References**:
  - `vibe-ops/tests/test_knowledge_telemetry.py:1-50` — existing test patterns
  - `.omo/drafts/period-reports-sync.md` §1.5 — test plan

  **Acceptance Criteria**:
  - [ ] `uv run pytest vibe-ops/tests/test_period_report.py -v` → 100% pass
  - [ ] Coverage ≥95% on `models/period_report.py`
  - [ ] All 5 periods × all valid verdicts tested (positive cases)
  - [ ] All 5 invalid period × verdict combinations tested (negative cases)
  - [ ] All 3 hierarchy violations tested (sonho with parent, missing parent, etc.)
  - [ ] Date range validator tested for each period

  **QA Scenarios**:
  ```
  Scenario: All unit tests pass
    Tool: Bash (pytest)
    Preconditions: None
    Steps:
      1. Run: uv run pytest vibe-ops/tests/test_period_report.py -v
    Expected Result: all tests pass, 100% coverage
    Evidence: .omo/evidence/period-5-unit-tests.txt

  Scenario: Coverage report
    Tool: Bash (pytest --cov)
    Preconditions: None
    Steps:
      1. Run: uv run pytest vibe-ops/tests/test_period_report.py --cov=vibe_ops.src.models.period_report --cov-report=term-missing
    Expected Result: ≥95% line coverage
    Evidence: .omo/evidence/period-5-coverage.txt
  ```

  **Commit**: YES
  - Message: `test(period-sync): unit tests for PeriodReport entity + parser`
  - Files: `vibe-ops/tests/test_period_report.py`

---

- [x] 6. Write integration tests for PeriodReportSync

  **What to do**:
  - Create `vibe-ops/tests/integration/test_period_sync.py`
  - Fixtures:
    - `temp_vault` — creates `_templates_periodos/` with 1 sonho + 1 trimestral
    - `temp_db` — fresh SQLite DB with migration 004 applied
  - Test class `TestPeriodReportSync` with 5 tests:
    - Sync sonho first (children are orphans)
    - Multi-pass recovery
    - Idempotent (re-sync skipped)
    - Broken YAML doesn't abort
    - Hierarchy tree assembly
  - Mark with `@pytest.mark.integration`

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**:
  - **Can Run In Parallel**: YES (independent of T5/T7/T8)
  - **Parallel Group**: Wave 1
  - **Blocks**: F1-F4
  - **Blocked By**: T3

  **References**:
  - `vibe-ops/tests/test_knowledge_telemetry.py` — fixture patterns

  **Acceptance Criteria**:
  - [ ] All 5 integration tests pass
  - [ ] Tests use real SQLite (in `tmp_path`), not mocks
  - [ ] Tests verify both happy and error paths
  - [ ] Multi-pass scenario verified (first pass orphans, second pass ingests)

  **QA Scenarios**:
  ```
  Scenario: Integration tests pass
    Tool: Bash (pytest)
    Preconditions: None
    Steps:
      1. Run: uv run pytest vibe-ops/tests/integration/test_period_sync.py -v --tb=short
    Expected Result: 5 tests pass
    Evidence: .omo/evidence/period-6-integration-tests.txt
  ```

  **Commit**: YES
  - Message: `test(period-sync): integration tests for PeriodReportSync`
  - Files: `vibe-ops/tests/integration/test_period_sync.py`

---

- [x] 7. Write property tests (Hypothesis) for period × verdict matrix

  **What to do**:
  - Create `vibe-ops/tests/property/test_period_report_properties.py`
  - Use `hypothesis` library
  - Property: For all (period, verdict) combinations, `PeriodReport.__init__` accepts iff `verdict in _PERIOD_VERDICTS[period]`
  - Property: All valid verdict scores are in [0, 1]
  - Property: Date end >= date start always

  **Must NOT do**:
  - Do not test edge cases that should fail (e.g., verdict_score > 1.0) — those are unit tests
  - Do not generate Hypothesis examples that exceed score range (use `st.floats(min_value=0.0, max_value=1.0)`)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**:
  - **Can Run In Parallel**: YES (independent of T5/T6/T8)
  - **Parallel Group**: Wave 1
  - **Blocks**: F1-F4
  - **Blocked By**: T2

  **References**:
  - Hypothesis library docs — `given`, `strategies`

  **Acceptance Criteria**:
  - [ ] `uv run pytest vibe-ops/tests/property/test_period_report_properties.py` → 100% pass
  - [ ] At least 100 examples generated per test
  - [ ] No `Flaky` failures

  **QA Scenarios**:
  ```
  Scenario: Property tests pass with 100+ examples
    Tool: Bash (pytest)
    Preconditions: hypothesis installed
    Steps:
      1. Run: uv run pytest vibe-ops/tests/property/test_period_report_properties.py -v --hypothesis-seed=0
    Expected Result: all tests pass, no flaky
    Evidence: .omo/evidence/period-7-property-tests.txt
  ```

  **Commit**: YES
  - Message: `test(period-sync): Hypothesis property tests for period × verdict matrix`
  - Files: `vibe-ops/tests/property/test_period_report_properties.py`

---

- [x] 8. Write E2E test: full month simulation

  **What to do**:
  - Create `vibe-ops/tests/e2e/test_period_reports_full_cycle.py`
  - Simulate full month: 1 sonho + 1 onda + 3 weeks + 21 days
  - Mark with `@pytest.mark.e2e`
  - Verify:
    - First sync: 1 sonho + 1 onda ingested, 24 children orphaned
    - Re-running sync until orphans=0
    - Final DB count = 26
    - Hierarchy tree correctly assembled
  - Test takes < 5 seconds

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T4 CLI being importable)
  - **Parallel Group**: Wave 1
  - **Blocks**: F1-F4
  - **Blocked By**: T3, T4

  **Acceptance Criteria**:
  - [ ] E2E test passes in < 5 seconds
  - [ ] All 26 reports in DB after multi-pass sync
  - [ ] Hierarchy tree has 1 root + 1 onda + 3 weeks + 21 days
  - [ ] No flaky behavior

  **QA Scenarios**:
  ```
  Scenario: E2E full cycle test passes
    Tool: Bash (pytest)
    Preconditions: None
    Steps:
      1. Run: uv run pytest vibe-ops/tests/e2e/test_period_reports_full_cycle.py -v --tb=short
    Expected Result: test passes in <5s
    Evidence: .omo/evidence/period-8-e2e-cycle.txt
  ```

  **Commit**: YES
  - Message: `test(period-sync): E2E full month simulation (1 sonho + 1 onda + 3 weeks + 21 days)`
  - Files: `vibe-ops/tests/e2e/test_period_reports_full_cycle.py`

---

- [x] 9. Create mirror migration 002 + PeriodReport mirror entity (operational)

  **What to do**:
  - Create `life-ops/operational/packages/core/src/operational/persistence/migrations/002_period_reports.sql`
  - Add 3 indexes on existing `entities` table (operational uses single-table JSON approach):
    - `idx_entities_period_report` on (entity_type, json_extract(data, '$.period'), json_extract(data, '$.date_start'))
    - `idx_entities_period_report_sonho` on json_extract(data, '$.sonho_id')
    - `idx_entities_period_report_verdict` on (json_extract(data, '$.period'), json_extract(data, '$.verdict')) filtered to FAIL verdicts
  - Create `life-ops/operational/packages/core/src/operational/entities/period_report.py`
  - Define `PeriodReport` (BaseModel) with `model_config = ConfigDict(frozen=False, extra="forbid", validate_assignment=True)` (operational convention)
  - Same fields as vibe-ops PeriodReport (id, period, dates, verdict, score, optionals, sync metadata)
  - Verify migration applies via `MigrationRunner.apply_all()`
  - Verify indexes work via `EXPLAIN QUERY PLAN`

  **Must NOT do**:
  - Do not use `extra="allow"` (operational uses strict `extra="forbid"`)
  - Do not re-define fields that operational already has in other entities
  - Do not break existing migration 001

  **Recommended Agent Profile**:
  - **Category**: `quick`

  **Parallelization**:
  - **Can Run In Parallel**: YES (independent of vibe-ops path)
  - **Parallel Group**: Wave 2
  - **Blocks**: F1-F4
  - **Blocked By**: None

  **References**:
  - `life-ops/operational/packages/core/src/operational/persistence/migrations/001_initial.sql:1-34` — operational migration pattern
  - `life-ops/operational/packages/core/src/operational/entities/policy.py:1-80` — entity pattern
  - `.omo/drafts/period-reports-sync.md` §1.2 (mirror) — full spec

  **Acceptance Criteria**:
  - [ ] `pav state migrate --json` applies `002_period_reports` migration
  - [ ] `EXPLAIN QUERY PLAN SELECT * FROM entities WHERE entity_type = 'period_report'` uses `idx_entities_period_report`
  - [ ] PeriodReport mirror validates with all required fields
  - [ ] PeriodReport mirror rejects unknown fields (extra="forbid")

  **QA Scenarios**:
  ```
  Scenario: Operational migration applies
    Tool: Bash (subprocess)
    Preconditions: None
    Steps:
      1. Run: rm -f test_operational.db; pav state migrate --db test_operational.db --json
      2. Assert applied list contains "002_period_reports"
    Expected Result: migration recorded
    Evidence: .omo/evidence/period-9-mirror-migration.txt

  Scenario: Index is used by query planner
    Tool: Bash (sqlite3)
    Preconditions: Migration applied, some period_report entities inserted
    Steps:
      1. sqlite3 test_operational.db "EXPLAIN QUERY PLAN SELECT * FROM entities WHERE entity_type = 'period_report' AND json_extract(data, '\$.period') = 'daily'"
      2. Assert output mentions idx_entities_period_report
    Expected Result: index used
    Evidence: .omo/evidence/period-9-index-used.txt
  ```

  **Commit**: YES
  - Message: `feat(period-sync): mirror migration 002 + PeriodReport entity (operational)`
  - Files: `life-ops/operational/packages/core/src/operational/persistence/migrations/002_period_reports.sql`, `life-ops/operational/packages/core/src/operational/entities/period_report.py`

---

- [x] 10. Create `specs/period-reports-sync/SPEC.md` (Sisyphus executes /write-tech-spec skill)

  **What to do**:
  - Invoke `/write-tech-spec` skill with feature id `period-reports-sync`
  - Skill creates `specs/period-reports-sync/SPEC.md` per Warp spec format
  - Cross-reference this plan file for behavior invariants, acceptance criteria, and QA scenarios
  - Commit spec alongside code

  **Recommended Agent Profile**:
  - **Category**: `writing`

  **Parallelization**:
  - **Can Run In Parallel**: NO (final consolidation step)
  - **Parallel Group**: Wave 2
  - **Blocks**: F1-F4
  - **Blocked By**: T2, T3

  **Acceptance Criteria**:
  - [ ] `specs/period-reports-sync/SPEC.md` exists with Context, Proposed changes, Testing, Parallelization sections
  - [ ] Both files (SPEC.md) committed

  **QA Scenarios**:
  ```
  Scenario: SPEC.md exists
    Tool: Bash (ls)
    Preconditions: None
    Steps:
      1. ls specs/period-reports-sync/
    Expected Result: SPEC.md present
    Evidence: .omo/evidence/period-10-spec-exists.txt
  ```

  **Commit**: YES
  - Message: `docs(period-sync): SPEC.md per Warp spec format`
  - Files: `specs/period-reports-sync/SPEC.md`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
>
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback → fix → re-run → present again → wait for okay.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in `.omo/evidence/period-*.txt`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `mypy --strict` + linter + `pytest`. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (full sync cycle works end-to-end). Test edge cases: empty vault, vault with all broken files, sync during write. Save to `.omo/evidence/period-final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **T1**: `feat(period-sync): migration 004 — period_reports schema + indexes + views`
- **T2**: `feat(period-sync): PeriodReport entity + parser`
- **T3**: `feat(period-sync): PeriodReportSync class with vault_hash idempotency + orphan recovery`
- **T4**: `feat(period-sync): CLI commands (sync vault|list|hierarchy) + state migrate`
- **T5**: `test(period-sync): unit tests for PeriodReport entity + parser`
- **T6**: `test(period-sync): integration tests for PeriodReportSync`
- **T7**: `test(period-sync): Hypothesis property tests for period × verdict matrix`
- **T8**: `test(period-sync): E2E full month simulation`
- **T9**: `feat(period-sync): mirror migration 002 + PeriodReport entity (operational)`
- **T10**: `docs(period-sync): SPEC.md per Warp spec format`

---

## Success Criteria

### Verification Commands
```bash
# Apply migration
cd vibe-ops && sqlite3 test_period.db < migrations/004_period_reports.sql

# Run all tests
cd vibe-ops && uv run pytest tests/test_period_report.py tests/integration/test_period_sync.py tests/property/test_period_report_properties.py tests/e2e/test_period_reports_full_cycle.py -v

# Quality gates
cd vibe-ops && uv run mypy src/models/period_report.py src/middleware/period_sync.py --strict
cd vibe-ops && uv run ruff check src/models/ src/middleware/

# Operational migration
cd life-ops/operational && uv run pytest tests/  # 2518 existing + new mirror entity tests
cd life-ops/operational && uv run ruff check packages/core/src/operational/entities/period_report.py

# CLI smoke test
cd life-ops/operational && uv run pav sync vault --folder /path/to/test/vault/_templates_periodos --json
cd life-ops/operational && uv run pav sync list --period daily --limit 5 --json
cd life-ops/operational && uv run pav sync hierarchy --sonho <test_id> --json
```

### Final Checklist
- [ ] All "Must Have" present (idempotent migration, 6 indexes, 2 views, 4 validators, idempotent sync, multi-pass, 3 CLI, ≥95% coverage)
- [ ] All "Must NOT Have" absent (no deletions, no LLM, no code→vault, no required beyond ADR-006, no cloud, no --json-less commands, no breaking changes)
- [ ] All 10 tasks completed
- [ ] All 4 final verification tasks (F1-F4) approved
- [ ] User has given explicit "okay"
- [ ] Draft file deleted from `.omo/drafts/`

---

*End of plan — awaiting user approval*