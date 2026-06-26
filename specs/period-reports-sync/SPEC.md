# SPEC: Period Reports Sync Layer v1.1

> **Feature ID:** `period-reports-sync`
> **Status:** Implemented (commit `f43c9742ab44935289721524e0356ec45662618d`)
> **Plan:** `.omo/plans/period-reports-sync.md`
> **ADR:** [`vibe-ops/architecture/ADR-006-period-reports-schema.md`](../../vibe-ops/architecture/ADR-006-period-reports-schema.md)
> **Codebase:** commit `f43c9742ab44935289721524e0356ec45662618d`

---

## 1. Context

Build a `period_reports`-specific sync layer that ingests the 5 official period templates (`_templates_periodos/`) from the Obsidian vault into `vibe_ops.db` and `operational.db`.

### 1.1 Problem
The vault (234+ enriched notes from prior `vault-bidirectional-sync` work) has manually-curated fields (xp-points, mastery-level, subject, learning-phase, etc.) but the `vibe-ops` engine cannot read them. Meanwhile, the `PolicyEngine` computes decisions (PUSH/MAINTAIN/REDUCE/RECOVER), `FalsifiableHypothesis` evaluates dreams, but their outputs never reach the vault dashboards.

### 1.2 Solution
Dedicated `PeriodReportSync` class with:
- Natural key: `(sonho_id, period, date_start)` (more meaningful than generic `upstream_id`)
- Conflict policy: vault-wins for ALL fields (no computed fields in period_reports)
- Idempotency: `vault_hash = sha256(canonical JSON)[:16]`
- Multi-pass orphan recovery: first sync ingests roots, subsequent syncs resolve children
- Hierarchical aggregation via SQL views (`v_period_hierarchy`, `v_onda_aggregated`)

### 1.3 Relevant Files
- [`vibe-ops/src/middleware/sync_engine.py:1-138`](../../vibe-ops/src/middleware/sync_engine.py) — existing one-way sync pattern
- [`vibe-ops/src/middleware/period_sync.py`](../../vibe-ops/src/middleware/period_sync.py) — new `PeriodReportSync` class (created in T3)
- [`vibe-ops/src/models/period_report.py`](../../vibe-ops/src/models/period_report.py) — `PeriodReport` entity + parser (created in T2)
- [`vibe-ops/migrations/004_period_reports.sql`](../../vibe-ops/migrations/004_period_reports.sql) — schema with 6 indexes + 2 views (T1)
- [`vibe-ops/src/cli/period_sync_cli.py`](../../vibe-ops/src/cli/period_sync_cli.py) — subprocess entry point (T4)
- [`life-ops/operational/.../cli/commands/sync_cmd.py`](../../life-ops/operational/apps/cli/src/operational/cli/commands/sync_cmd.py) — Typer wrapper (T4)
- [`life-ops/operational/.../entities/period_report.py`](../../life-ops/operational/packages/core/src/operational/entities/period_report.py) — operational mirror (T9)

---

## 2. Proposed Changes

### 2.1 SQL Schema (vibe-ops side)

**File:** `vibe-ops/migrations/004_period_reports.sql` (115 lines)

Table `period_reports`:
- Identity: `id TEXT PRIMARY KEY`, `entity_type` defaulting to `'period_report'`
- Period contract: `period` (enum: daily|weekly|onda|quarterly|sonho), `date_start`, `date_end`
- Verdict contract: `verdict`, `verdict_score` (0.0-1.0)
- Optional metadata: `sonho_id`, `ikigai_vector`, `xp_gained`, `policy_recommendation`, `parent_period`, `status`, `tags`
- Sync metadata: `vault_path`, `vault_hash`, `last_synced_at`

Indexes:
- `idx_period_reports_period` — `(period, date_start DESC)`
- `idx_period_reports_sonho` — `sonho_id` (filtered non-null)
- `idx_period_reports_parent` — `parent_period` (filtered non-null)
- `idx_period_reports_verdict` — `(period, verdict)` filtered to FAIL verdicts
- `idx_period_reports_policy` — `policy_recommendation` (filtered non-null)
- `idx_period_reports_vault_hash` — `vault_hash` (idempotency lookup)
- `idx_period_reports_updated` — `updated_at DESC`

Trigger: `trg_period_reports_updated` — auto-updates `updated_at` on row UPDATE.

Views:
- `v_period_hierarchy` — recursive CTE: root_id, depth, parent chain
- `v_onda_aggregated` — onda with avg child score + concatenated child verdicts

CHECK constraints:
- `date_end >= date_start`
- Sonho (no parent) vs non-sonho (with or without parent) hierarchy rule
- Verdict-score consistency: PASS/CONTINUE_WAVE/VALIDATED need score >= 0.5; FAIL/KILL_WAVE/FALSIFIED/ABANDONED need score < 0.5; PARTIAL/CORRECT_TRAJECTORY/PIVOTED >= 0.25

### 2.2 Pydantic Entities

**vibe-ops PeriodReport** (`models/period_report.py`, ~190 lines):
- `model_config = ConfigDict(frozen=False, extra="allow", validate_assignment=False)` — lenient for ingestion
- 4 validators: verdict per period, date range, hierarchy (sonho no parent), verdict-score consistency (warning)
- `PeriodReportParser.parse_file(file_path)` — uses python-frontmatter, returns PeriodReport or None
- `PeriodReport.vault_hash` = sha256 of canonical metadata JSON, 16 chars
- Auto-derives `id` from `vault_path.stem` if missing

**operational PeriodReport** (`entities/period_report.py`, ~120 lines):
- `model_config = ConfigDict(frozen=False, extra="forbid", validate_assignment=True)` — strict
- All same fields + sync metadata (vault_path, vault_hash, last_synced_at)
- Same 4 validators (consolidated in single `model_validator(mode="after")`)

### 2.3 Sync Layer

**File:** `vibe-ops/src/middleware/period_sync.py` (~250 lines)

```python
class PeriodReportSync:
    def __init__(self, vault_path: Path, db_path: Path, template_folder: str = "_templates_periodos")
    def _ensure_migration(self) -> None  # applies 004 SQL on init
    def sync_vault_to_db(self) -> PeriodSyncStats  # multi-pass capable
    def _fetch_existing(vault_hash, report_id) -> bool  # OR idempotency check
    def _exists(report_id) -> bool  # FK resolution
    def _upsert(report) -> None  # INSERT ... ON CONFLICT DO UPDATE
    def get_period_hierarchy(sonho_id) -> dict  # recursive tree builder
    def _build_subtree(node, nodes) -> dict
    def sync_db_to_vault() -> PeriodSyncStats  # no-op stub for v1.1
```

Key behavior:
- Migration auto-applies in `__init__` (CREATE TABLE IF NOT EXISTS via migration file or inline DDL fallback)
- `sync_vault_to_db` parses each `.md` in template_folder, checks idempotency, validates FK, upserts
- Multi-pass orphan recovery: callers should run sync multiple times until `stats.orphans == 0`
- Frozen PeriodSyncStats requires accumulating in local vars then constructing once at return

### 2.4 CLI

**Subprocess entry:** `vibe-ops/src/cli/period_sync_cli.py` (139 lines)
- argparse-based: `sync`, `list`, `hierarchy` subcommands
- Adds `vibe-ops/src` to `sys.path` so `from middleware.X` resolves
- Outputs JSON or human-readable text

**Typer wrapper:** `life-ops/operational/apps/cli/src/operational/cli/commands/sync_cmd.py` (~140 lines)
- Sub-typer: `pav sync vault|list|hierarchy [--json]`
- Invokes subprocess via `sys.executable + script`
- Resolves vault path via config
- All commands support `--json`

**Extended:** `state_cmd.py` — added `pav state migrate [--json]` using `MigrationRunner.apply_all()`

**Registered in:** `app.py` via `app.add_typer(sync_app, name="sync", ...)`

### 2.5 Operational Mirror

**File:** `life-ops/operational/packages/core/src/operational/persistence/migrations/002_period_reports.sql` (20 lines)

3 partial indexes on existing `entities` table (operational uses single-table JSON blob):
- `idx_entities_period_report` — `(entity_type, json_extract(data, '$.period'), json_extract(data, '$.date_start'))` filtered to period_report
- `idx_entities_period_report_sonho` — `json_extract(data, '$.sonho_id')` filtered
- `idx_entities_period_report_verdict` — `(period, verdict)` filtered to FAIL verdicts

Migration auto-applies via existing `MigrationRunner._discover_pending()`.

---

## 3. Testing and Validation

### 3.1 Unit Tests (T5)
**File:** `vibe-ops/tests/test_period_report.py`
- **37 tests** across `TestPeriodReportValidation` (24), `TestPeriodReportParser` (10), `TestPeriodSyncStats` (3)
- **Coverage: 97%** on `models/period_report.py`
- All 4 Pydantic validators tested + 5 periods x all valid verdicts + parser edge cases

### 3.2 Integration Tests (T6)
**File:** `vibe-ops/tests/integration/test_period_sync.py`
- **9 tests** using real SQLite + real vault + real parser (no mocks)
- Scenarios: migration apply, first-pass ingest, idempotent re-sync, hierarchy tree, broken YAML tolerance, missing folder error, update flow, no-op stub

### 3.3 Property Tests (T7)
**File:** `vibe-ops/tests/property/test_period_report_properties.py`
- **9 tests** using Hypothesis, ~700 examples generated
- Properties: verdict x period matrix, score range [0,1], date ordering, hierarchy (sonho no parent)

### 3.4 E2E Test (T8)
**File:** `vibe-ops/tests/e2e/test_period_reports_full_cycle.py`
- **1 test** — full month simulation: 1 sonho + 1 onda + 3 weeks + 21 days = 26 reports
- Multi-pass convergence in 4 passes
- Hierarchy verification: 1 root -> 1 onda -> 3 weeks -> 7 days each
- Performance: < 5s budget (actual: 398ms)

### 3.5 Verification Commands
```bash
cd vibe-ops && uv run pytest tests/ -v
cd life-ops/operational && uv run pav state migrate --json
```

---

## 4. Parallelization

### 4.1 Execution
This spec was implemented sequentially (1 agent) due to heavy inter-task dependencies. Parallelism was NOT used because:
1. T2 (entity) depends on T1 (migration context)
2. T3 (sync) depends on T2 (entity API)
3. T4 (CLI) depends on T3 (sync API)
4. T5-T8 (tests) depend on T2-T4 in cascade
5. T9 (operational mirror) is independent but was scheduled sequentially for simplicity

### 4.2 Sequential Wave Breakdown
```
Wave 1 (sequential):
|- T1: Migration 004 SQL
|- T2: PeriodReport entity + parser
|- T3: PeriodReportSync class
|- T4: CLI commands
|- T5: Unit tests
|- T6: Integration tests
|- T7: Property tests
|- T8: E2E test

Wave 2 (sequential):
|- T9: Operational mirror migration + entity

Wave 3 (parallel -- 4 reviews):
|- F1: Plan compliance audit (oracle)
|- F2: Code quality review (unspecified-high)
|- F3: Real manual QA (unspecified-high)
|- F4: Scope fidelity check (deep)
```

### 4.3 Coordination
- Each task commits atomic units (T1-T9 each = 1 commit)
- Evidence files at `.omo/evidence/period-{N}-*.{txt,json}`
- Final Wave (F1-F4) requires user "okay" before marking complete

---

## 5. Behavior Invariants (from plan B1-B6)

| ID | Invariant | Test |
|----|-----------|------|
| B1 | Vault -> Code ingestion idempotent via vault_hash | T5 + T6 |
| B2 | Code -> Vault export no-op (no computed fields) | T6 (sync_db_to_vault) |
| B3 | Conflict resolution: vault-wins for all fields | T6 + design choice |
| B4 | All CLI commands support --json | T4 + manual CLI test |
| B5 | FalsifiableHypothesis entity + evaluator (ADR-006 Axis 1) | T2 + T9 entities |
| B6 | Append-only safety (no deletions, even on update) | T2 + T6 |

---

## 6. Out of Scope (v1.1)

- Real-time bidirectional daemon (v2)
- Multi-vault support (v2)
- Cloud sync (always NO)
- LLM in sync path (always NO)
- Auto-migration of existing 234+ vault notes (v1.1.1)
- PolicyEngine consume verdict -> emit new period_reports (v2)
- Mermaid cycle diagrams auto-generated (v2)

---

## 7. Follow-ups

- **v1.1.1**: `life sync migrate` command for existing 234+ notes
- **v1.1.1**: `life sync watch` one-shot filesystem watcher
- **v2**: PolicyEngine consume verdict from previous period -> emit next period
- **v2**: Bidirectional sync activation (currently vault-only)

---

*SPEC.md for period-reports-sync v1.1 -- 2026-06-26*
