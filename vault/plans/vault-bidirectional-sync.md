# Vault Bidirectional Sync

> **Plan ID:** `vault-bidirectional-sync`
> **Status:** ✅ **CLOSED** — 13/13 tasks complete, SPEC.md delivered
> **Source spec:** `specs/vault-bidirectional-sync/SPEC.md` (Warp format)
> **Codebase commit:** `e89400c` (SPEC.md latest)

---

## TL;DR

> **Quick Summary**: Build a bidirectional sync layer between the user's Obsidian vault (`notas_estudo`, 234+ notes) and the `vibe-ops` algorithmic engine. The vault's manual fields (xp, mastery, subject) flow into entities; the engine's computed fields (PolicyDecision, RICE, FalsifiableHypothesis) flow back as frontmatter. Idempotent, conflict-aware, append-only safe.
>
> **Deliverables**:
> - `FalsifiableHypothesis` Pydantic entity (Axis 1-3 from strategic framework)
> - `BidirectionalSync` middleware (vault→code + code→vault + conflict resolution)
> - Extended `Project`, `StudyProject`, new `Dream` entities with vault metadata
> - `life sync vault|code|all|status|conflicts` CLI commands
> - ≥90% test coverage across `vibe-ops/tests/` and `life-ops/operational/tests/`
> - `specs/vault-bidirectional-sync/PRODUCT.md` and `TECH.md` (created by Sisyphus)
>
> **Estimated Effort**: Large (4 parallel agents, 3-5 days wall clock)
> **Parallel Execution**: YES — 4 agents on 4 worktrees, 1 final integration wave
> **Critical Path**: Agent A (vault import) → Agent D (CLI) → F1-F4 review

---

## Context

### Original Request
User invoked `/write-tech-spec` for a bidirectional sync between two systems:
- **Obsidian vault** (`notas_estudo`): 234+ enriched notes with `xp-points`, `mastery-level`, `subject`, `learning-phase`, `tech-stack` fields
- **`vibe-ops` engine** (`vibe-ops/src/pipeline/policy_engine.py`): computes PolicyDecision, RICE scores, never exported back
- **Strategic framework** (`docs/chat-Framework de Planejamento Estratégico.txt:1-78`): FalsifiableHypothesis exists as prose only, no Pydantic entity

### Interview Summary
**Key Discussions**:
- D1 — FalsifiableHypothesis ships in **v1** (full entity + evaluator + CLI exposure)
- D2 — `life sync watch` defers to **v1.1**
- D3 — Conflict policy: **vault-wins for manual, code-wins for computed, ambiguous → `.sync-conflicts.md`**
- D4 — Test infra: **both `vibe-ops/tests/` and `life-ops/operational/tests/`** (separate)
- D5 — Worktree strategy: **4 parallel agents** (vault-import, code-export, hypothesis, sync-cli)

**Research Findings**:
- `vibe-ops/src/middleware/sync_engine.py:1-138` is one-way only; `reverse_sync.py:1-32` is stub
- `Project` entity (`vibe-ops/src/models/project_entities.py:26-30`) missing 9 enrichment fields
- `PolicyEngine` (`vibe-ops/src/pipeline/policy_engine.py:43-104`) outputs `PolicyDecision` but never reaches vault
- Vault dashboards (`00_Master_Dashboard.md`, `00_DataCore_Dashboard.md`) already query these fields — they just don't have data

### Metis Review
**Identified Gaps (addressed)**:
- **G1**: `ReverseSync` is a stub — must extend, not just import. → Specified in T2.3
- **G2**: `FrontmatterParser` silently returns `None` on parse errors — sync would hide failures. → Added error counter + log to B1.3, B3.3
- **G3**: SQLite race conditions under parallel writes. → Mitigation: WAL mode + per-entity_type advisory lock (Risks section)
- **G4**: Append-only rule for `vibe-ops/` means new tables only, no entity removal. → B6.1 invariant, no deletes
- **G5**: 234+ existing notes have inconsistent schemas. → T2.4 tolerant parser + B3.3 don't-abort policy

---

## Work Objectives

### Core Objective
Eliminate the data silo between the user's Obsidian vault (where they manually track learning progress) and the `vibe-ops` engine (which computes policy decisions, RICE scores, and falsification verdicts). Both sides become queryable from either system.

### Concrete Deliverables
1. `vibe-ops/src/models/hypothesis_entities.py` — `FalsifiableHypothesis`, `HypothesisEvaluation` Pydantic v2 models
2. `vibe-ops/src/models/dream_entities.py` — new `Dream` entity with falsification + vault enrichment fields
3. Extended `Project` and `StudyProject` entities with 9 enrichment fields each
4. `vibe-ops/src/middleware/bidirectional_sync.py` — `BidirectionalSync` class
5. `vibe-ops/src/pipeline/hypothesis_evaluator.py` — `HypothesisEvaluator` (Axis 1-3 logic)
6. `life-ops/operational/apps/cli/src/operational/cli/commands/sync_cmd.py` — Typer CLI
7. DB migrations: `vibe-ops/migrations/2026_06_22_vault_sync.sql`, `life-ops/operational/packages/core/src/operational/persistence/migrations/2026_06_22_vault_sync.sql`
8. Test suites: `vibe-ops/tests/test_bidirectional_sync.py`, `vibe-ops/tests/test_hypothesis_evaluator.py`, `life-ops/operational/tests/test_sync_cmd.py`
9. `specs/vault-bidirectional-sync/PRODUCT.md` and `TECH.md` (Sisyphus creates these in the worktree per skill protocol)

### Definition of Done
- [ ] `uv run pytest vibe-ops/tests/ life-ops/operational/tests/test_sync_cmd.py` → 100% pass
- [ ] `uv run mypy --strict` on all new code → 0 errors
- [ ] `uv run ruff check` on all new code → 0 errors
- [ ] Manual E2E: `life sync vault` → `life sync code` round-trip on a fixture vault with 5 sample notes → all fields populated, no duplicates, conflicts file empty
- [ ] `life sync status --json` returns valid JSON with entity counts and last sync timestamps

### Must Have
- FalsifiableHypothesis entity with all 5 statuses (active/validated/falsified/pivoted/abandoned)
- `life sync vault` and `life sync code` both idempotent (re-runnable without duplicates)
- Atomic frontmatter writes (`.tmp` + rename, no corruption on crash)
- `.sync-conflicts.md` written on ambiguous conflicts, sync does not fail
- ≥90% line coverage on new modules

### Must NOT Have (Guardrails)
- No deletion of existing entities, files, or frontmatter keys (append-only rule)
- No LLM in the sync path (pure arithmetic + YAML I/O)
- No real-time daemon in v1 (defer to v2)
- No auto-migration of existing 234+ notes in v1 (v1.1 has `life sync migrate`)
- No cloud sync, no API keys, no OAuth (fully local)
- No new CLI command without `--json` support

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (2518 tests in `life-ops/operational/`, pytest strict mypy)
- **Automated tests**: YES (TDD per task — RED → GREEN → REFACTOR)
- **Framework**: pytest with markers `unit`, `integration`, `property`, `e2e`
- **Coverage target**: ≥90% line coverage on new modules

### QA Policy
Every task includes agent-executed QA scenarios. Evidence saved to `.omo/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Module/Entity tests**: pytest with assertions
- **CLI tests**: subprocess + `--json` parsing
- **Atomic write tests**: simulate crash mid-write, verify file integrity
- **Round-trip tests**: vault → DB → vault, assert field preservation
- **Conflict tests**: force conflicts, verify `.sync-conflicts.md` written

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — 4 parallel agents, separate worktrees):
├── Agent A: T1-T3 — Vault import + entity extensions (worktree: ../life-vault-import, branch: feat/vault-import)
├── Agent B: T4-T5 — Code export + atomic frontmatter writes (worktree: ../life-code-export, branch: feat/code-export)
├── Agent C: T6-T7 — FalsifiableHypothesis entity + evaluator (worktree: ../life-hypothesis, branch: feat/hypothesis)
└── Agent D: T8-T9 — CLI commands + test scaffolding (worktree: ../life-sync-cli, branch: feat/sync-cli)

Wave 2 (After Wave 1 — integration + DB migrations):
├── T10: DB migrations + advisory locks (depends: T1, T4, T6)
├── T11: End-to-end integration test (depends: T2, T5, T7, T8)
├── T12: Conflict resolution E2E test (depends: T3, T5)
└── T13: Final PRODUCT.md + TECH.md creation (depends: T8)

Wave FINAL (After ALL tasks — 4 parallel reviews):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review (unspecified-high)
├── F3: Real manual QA (unspecified-high)
└── F4: Scope fidelity check (deep)

Critical Path: T1 (entity extensions) → T10 (migrations) → T11 (E2E) → F1-F4 → user okay
Parallel Speedup: ~65% faster than sequential
Max Concurrent: 4 (Wave 1)
```

### Dependency Matrix

- **T1**: None → T2, T3, T10
- **T2**: T1 → T11
- **T3**: T1, T4 → T12
- **T4**: None → T3, T5, T10
- **T5**: T4 → T11, T12
- **T6**: None → T7, T10
- **T7**: T6 → T11
- **T8**: None → T11, T13
- **T9**: T8 → T13
- **T10**: T1, T4, T6 → T11, T12
- **T11**: T2, T5, T7, T8, T10 → F1-F4
- **T12**: T3, T5, T10 → F1-F4
- **T13**: T8, T9 → F1-F4

### Agent Dispatch Summary

- **Wave 1**: **4** — Agent A (T1-T3) → `unspecified-high`, Agent B (T4-T5) → `unspecified-high`, Agent C (T6-T7) → `deep`, Agent D (T8-T9) → `quick`
- **Wave 2**: **4** — T10 → `unspecified-high`, T11 → `deep`, T12 → `unspecified-high`, T13 → `writing`
- **FINAL**: **4** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Extend `Project` and `StudyProject` entities with vault enrichment fields

  **What to do**:
  - Add 9 fields to `vibe-ops/src/models/project_entities.py:26-30` `Project`: `xp_points: int = 0`, `mastery_level: Literal["beginner","intermediate","advanced","expert"] = "beginner"`, `subject: Optional[str] = None`, `learning_phase: Optional[Literal["metalearning","direct_practice","retrieval","iteration"]] = None`, `tech_stack: List[str] = []`, `milestone: Optional[date] = None`, `deliverable: Optional[str] = None`, `commercial_goal: Optional[str] = None`, `vault_path: Optional[str] = None`, `last_synced_at: Optional[datetime] = None`
  - Add same 9 fields to `vibe-ops/src/models/study_entities.py:5-24` `StudyProject`
  - Set `extra="allow"` (not `forbid`) so unknown vault fields don't break validation — preserve append-only
  - Add unit tests in `vibe-ops/tests/test_project_entities.py` and `vibe-ops/tests/test_study_entities.py` asserting all new fields have defaults

  **Must NOT do**:
  - Do not remove existing fields
  - Do not change `entity_type` literal values
  - Do not add `frozen=True` (these entities need to be mutable for sync)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `git-master`
  - **Skills Evaluated but Omitted**:
    - `code-reviewer`: not needed for entity extension; covered by F2 final review
    - `python-pro`: existing patterns are well-established; no need for advanced Python guidance

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1, Agent A
  - **Blocks**: T2, T3, T10
  - **Blocked By**: None

  **References**:
  - `vibe-ops/src/models/project_entities.py:26-30` — `Project` model to extend
  - `vibe-ops/src/models/study_entities.py:5-24` — `StudyProject` model to extend
  - `vibe-ops/specs/schema-pydantic-models-v2.md` — schema conventions (frozen vs mutable, extra policies)

  **Acceptance Criteria**:
  - [ ] `Project(**{existing_fields})` instantiates with all defaults (xp_points=0, mastery_level="beginner", etc.)
  - [ ] `Project(xp_points=150, mastery_level="advanced", subject="ai-engineering")` validates
  - [ ] `Project(unknown_field="x")` does NOT raise (extra="allow")
  - [ ] `uv run mypy --strict vibe-ops/src/models/project_entities.py` → 0 errors
  - [ ] `uv run pytest vibe-ops/tests/test_project_entities.py -v` → 100% pass

  **QA Scenarios**:
  ```
  Scenario: Project accepts all new fields with defaults
    Tool: Bash (uv run python -c)
    Preconditions: None
    Steps:
      1. Run: uv run --with pydantic python -c "from models.project_entities import Project; p = Project(id='proj_test', title='Test Project'); assert p.xp_points == 0; assert p.mastery_level == 'beginner'; assert p.tech_stack == []"
    Expected Result: exit code 0, no AssertionError
    Evidence: .omo/evidence/task-1-project-defaults.txt

  Scenario: Project rejects invalid mastery_level
    Tool: Bash (uv run python -c)
    Preconditions: None
    Steps:
      1. Run: uv run --with pydantic python -c "from models.project_entities import Project; Project(id='proj_x', title='X', mastery_level='godlike')" 2>&1
    Expected Result: exit code 1, ValidationError mentioning mastery_level
    Evidence: .omo/evidence/task-1-project-validation.txt

  Scenario: Project tolerates unknown extra fields
    Tool: Bash (uv run python -c)
    Preconditions: None
    Steps:
      1. Run: uv run --with pydantic python -c "from models.project_entities import Project; p = Project(id='proj_y', title='Y', future_field='x'); assert p.future_field == 'x'"
    Expected Result: exit code 0, attribute accessible (extra="allow")
    Evidence: .omo/evidence/task-1-project-extra-allow.txt
  ```

  **Commit**: YES
  - Message: `feat(sync): extend Project/StudyProject with vault enrichment fields`
  - Files: `vibe-ops/src/models/project_entities.py`, `vibe-ops/src/models/study_entities.py`, `vibe-ops/tests/test_project_entities.py`, `vibe-ops/tests/test_study_entities.py`

---

- [x] 2. Implement `BidirectionalSync.sync_vault_to_code()` (B1)

  **What to do**:
  - Create `vibe-ops/src/middleware/bidirectional_sync.py` with class `BidirectionalSync(vault_path: Path, db_path: Path)`
  - Method `sync_vault_to_code(folders: List[str] = ["2_projeto", "5_atomicas", "3_indice", "4_leitura"]) -> dict`:
    - For each `.md` file, load frontmatter via `frontmatter` lib
    - Map `entity_type` to Pydantic class via `FrontmatterParser.MODEL_MAP` (extended)
    - Compute `upstream_id = sha256(json.dumps(payload, sort_keys=True, default=str))[:12]`
    - Check `vault_sync_state` table for last hash; skip if unchanged
    - Upsert into `planning_entities` (vibe-ops DB) with ON CONFLICT DO UPDATE
    - Return `{"ingested": N, "skipped": N, "errors": N, "conflicts": N}`
  - Add to `vibe-ops/src/pipeline/frontmatter_parser.py:18-39` `MODEL_MAP`: `"dream"`, `"falsifiable_hypothesis"`
  - Add unit tests + integration test with fixture vault (5 sample notes)

  **Must NOT do**:
  - Do not silently swallow parse errors (must log + increment error counter)
  - Do not block on parse errors (continue with next file)
  - Do not require network access

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `git-master`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1, Agent A
  - **Blocks**: T11
  - **Blocked By**: T1

  **References**:
  - `vibe-ops/src/middleware/sync_engine.py:1-138` — existing one-way sync pattern
  - `vibe-ops/src/middleware/sync_engine.py:21-24` — `compute_upstream_id` pattern
  - `vibe-ops/src/middleware/sync_engine.py:26-61` — `sync_obsidian_to_sqlite` reference
  - `vibe-ops/src/pipeline/frontmatter_parser.py:13-77` — FrontmatterParser, MODEL_MAP

  **Acceptance Criteria**:
  - [ ] `sync_vault_to_code()` on fixture vault (5 notes) returns `{"ingested": 5, "skipped": 0, "errors": 0}`
  - [ ] Second call returns `{"ingested": 0, "skipped": 5, "errors": 0}` (idempotent)
  - [ ] Call with one invalid YAML file returns errors=1 but still ingests the other 4
  - [ ] `vibe_ops.db` `planning_entities` table has 5 rows with matching `upstream_id`

  **QA Scenarios**:
  ```
  Scenario: Vault → Code ingestion ingests all valid notes
    Tool: Bash (uv run python -c)
    Preconditions: Fixture vault at tests/fixtures/vault/ with 5 valid .md files
    Steps:
      1. Create fixture: 2_projeto/p1.md, 2_projeto/p2.md, 5_atomicas/a1.md, 3_indice/m1.md, 4_leitura/l1.md with valid frontmatter
      2. Run: uv run python -c "from middleware.bidirectional_sync import BidirectionalSync; from pathlib import Path; s = BidirectionalSync(Path('tests/fixtures/vault'), Path('test_sync.db')); print(s.sync_vault_to_code())"
    Expected Result: {"ingested": 5, "skipped": 0, "errors": 0, "conflicts": 0}
    Evidence: .omo/evidence/task-2-vault-ingest.txt

  Scenario: Re-sync is idempotent
    Tool: Bash (uv run python -c)
    Preconditions: Same DB from previous scenario
    Steps:
      1. Run same sync command again
    Expected Result: {"ingested": 0, "skipped": 5, "errors": 0, "conflicts": 0}
    Evidence: .omo/evidence/task-2-vault-idempotent.txt

  Scenario: Invalid YAML does not abort sync
    Tool: Bash (uv run python -c)
    Preconditions: Fixture with 4 valid + 1 broken .md
    Steps:
      1. Add tests/fixtures/vault/2_projeto/broken.md with malformed YAML
      2. Run sync; assert errors=1, ingested=4
    Expected Result: errors counter incremented, other notes still ingested
    Evidence: .omo/evidence/task-2-vault-tolerance.txt
  ```

  **Commit**: YES
  - Message: `feat(sync): BidirectionalSync.sync_vault_to_code with idempotency`
  - Files: `vibe-ops/src/middleware/bidirectional_sync.py`, `vibe-ops/src/pipeline/frontmatter_parser.py`, `vibe-ops/tests/test_bidirectional_sync.py`, `vibe-ops/tests/fixtures/vault/**`

---

- [x] 3. Implement `BidirectionalSync.resolve_conflicts()` (B3)

  **What to do**:
  - Add method `resolve_conflicts() -> List[ConflictRecord]` to `BidirectionalSync`
  - For each entity in `vault_sync_state`, compare `last_vault_hash` vs `last_code_hash` and current values:
    - **Manual fields** (`xp_points`, `mastery_level`, `subject`, `learning_phase`, `tech_stack`, `milestone`, `deliverable`, `commercial_goal`): vault wins
    - **Computed fields** (`regime`, `rice_score`, `falsification_score`, `hardwork_budget_hours`, `policy_decision_at`): code wins
    - **Ambiguous** (other fields where both differ): write to `.sync-conflicts.md` with timestamp + both values, do not resolve
  - Maintain `MANUAL_FIELDS` and `COMPUTED_FIELDS` as class constants
  - Unit tests covering: no conflict, vault-wins scenario, code-wins scenario, ambiguous → file written

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1, Agent A
  - **Blocks**: T12
  - **Blocked By**: T1, T4

  **References**:
  - `vibe-ops/src/middleware/sync_engine.py:21-24` — hash pattern
  - `docs/chat-Framework de Planejamento Estratégico.txt:1-78` — strategic framework context

  **Acceptance Criteria**:
  - [ ] No conflicts → empty list returned
  - [ ] Vault modified `xp_points` (manual) and code has same value → no conflict
  - [ ] Both vault and code modified `xp_points` differently → vault value wins, no conflict logged
  - [ ] Both modified an unlisted field → written to `.sync-conflicts.md` with both values

  **QA Scenarios**:
  ```
  Scenario: Vault-wins for manual fields
    Tool: Bash (uv run python -c)
    Preconditions: Entity with both vault and code having different xp_points
    Steps:
      1. Set vault xp_points=100, code xp_points=80
      2. Run resolve_conflicts(); assert result code xp_points=100
    Expected Result: code value updated to match vault, no conflict logged
    Evidence: .omo/evidence/task-3-vault-wins.txt

  Scenario: Code-wins for computed fields
    Tool: Bash (uv run python -c)
    Preconditions: Entity with both having different regime values
    Steps:
      1. Set vault regime=MAINTAIN, code regime=PUSH
      2. Run resolve_conflicts(); assert vault frontmatter regime updated to PUSH
    Expected Result: vault frontmatter updated, no conflict logged
    Evidence: .omo/evidence/task-3-code-wins.txt

  Scenario: Ambiguous field written to conflicts file
    Tool: Bash (uv run python -c)
    Preconditions: Entity with both having different unknown_field values
    Steps:
      1. Set vault unknown_field="A", code unknown_field="B"
      2. Run resolve_conflicts(); assert .sync-conflicts.md exists with both values
    Expected Result: file written, sync does not fail
    Evidence: .omo/evidence/task-3-ambiguous.txt
  ```

  **Commit**: YES
  - Message: `feat(sync): conflict resolution with vault-wins/computed-wins policy`
  - Files: `vibe-ops/src/middleware/bidirectional_sync.py`, `vibe-ops/tests/test_bidirectional_sync.py`

---

- [x] 4. Implement `BidirectionalSync.sync_code_to_vault()` with atomic writes (B2)

  **What to do**:
  - Add method `sync_code_to_vault() -> dict` to `BidirectionalSync`
  - For each dream/project entity in DB with computed fields:
    - Read current `PolicyDecision` from policy_engine (or stored `policy_decision_at`)
    - Build exported frontmatter dict: `regime`, `hardwork_budget_hours`, `pause_minutes`, `sleep_target_hours`, `qhe_target`, `policy_decision_at`, `policy_severity`, `policy_recommendations`, `policy_alerts`, `rice_score`, `priority_rank`
    - Read existing vault file via `frontmatter` lib
    - Merge: keep existing keys, update/insert new keys (NEVER remove)
    - Atomic write: write to `{path}.tmp`, then `os.replace()` to original
    - Track in `vault_sync_state`: update `last_vault_hash`, `last_synced_at`
  - Return `{"exported": N, "skipped": N, "errors": N}`
  - Unit tests + integration with fixture vault

  **Must NOT do**:
  - Do not remove existing frontmatter keys
  - Do not write directly to original file (always `.tmp` + rename)
  - Do not crash on read-only files (log error, continue)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1, Agent B
  - **Blocks**: T3, T5, T10
  - **Blocked By**: None

  **References**:
  - `vibe-ops/src/pipeline/policy_engine.py:43-104` — PolicyDecision structure
  - `vibe-ops/src/pipeline/policy_engine.py:87-104` — exported fields (hardwork_budget_hours, etc.)
  - `vibe-ops/src/middleware/sync_engine.py:26-61` — sync pattern reference

  **Acceptance Criteria**:
  - [ ] `sync_code_to_vault()` writes 12 new keys to fixture vault notes without removing existing keys
  - [ ] Simulated crash mid-write (kill process during write) → original file is unchanged, `.tmp` file may exist
  - [ ] Second call updates `policy_decision_at` to new timestamp, other fields unchanged
  - [ ] File `mtime` updated only when content actually changed

  **QA Scenarios**:
  ```
  Scenario: Code export adds 12 keys without removing existing
    Tool: Bash (uv run python -c)
    Preconditions: Fixture vault with 3 .md files having pre-existing custom fields
    Steps:
      1. Capture all frontmatter keys before
      2. Run sync_code_to_vault()
      3. Assert all original keys still present, plus 12 new keys added
    Expected Result: union of old + new keys, no removals
    Evidence: .omo/evidence/task-4-export-merge.txt

  Scenario: Atomic write survives simulated crash
    Tool: Bash (subprocess + signal)
    Preconditions: Vault file at known path
    Steps:
      1. Start sync_code_to_vault in subprocess
      2. SIGKILL the process during write
      3. Assert original file is valid YAML (no truncation)
      4. Assert no .tmp file remains (or cleanup)
    Expected Result: original file integrity preserved
    Evidence: .omo/evidence/task-4-atomic-crash.txt

  Scenario: Idempotent export (re-run updates only timestamp)
    Tool: Bash (uv run python -c)
    Preconditions: After first export
    Steps:
      1. Capture file mtime and policy_decision_at
      2. Run sync_code_to_vault() again after 1 second
      3. Assert policy_decision_at changed, other 11 fields unchanged
    Expected Result: only timestamp field differs
    Evidence: .omo/evidence/task-4-export-idempotent.txt
  ```

  **Commit**: YES
  - Message: `feat(sync): BidirectionalSync.sync_code_to_vault with atomic writes`
  - Files: `vibe-ops/src/middleware/bidirectional_sync.py`, `vibe-ops/tests/test_bidirectional_sync.py`

---

- [x] 5. Implement `compute_rice_score()` and `compute_priority_rank()` (B2.4)

  **What to do**:
  - In `vibe-ops/src/middleware/bidirectional_sync.py` or new `vibe-ops/src/pipeline/rice_exporter.py`:
  - Function `compute_rice_score(reach: float, impact: float, confidence: float, effort_h: float) -> float`:
    - Return `(reach * impact * confidence) / max(effort_h, 0.1)` (guard against div-by-zero)
  - Function `compute_priority_rank(tasks: List[Project]) -> Dict[id, int]`:
    - Sort by RICE descending, assign rank 1..N
  - Export as new frontmatter key `rice_score` (float) and `priority_rank` (int) on project notes
  - Pure arithmetic, no LLM, no I/O (testable in isolation)
  - Unit tests for edge cases: effort_h=0, negative values, equal scores

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1, Agent B
  - **Blocks**: T11, T12
  - **Blocked By**: T4

  **References**:
  - `docs/chat-Framework de Planejamento Estratégico.txt:50-77` — RICE/WSJF context
  - `vibe-ops/base/IKIGAi.md` — IKIGAI framework for impact/revenue weights

  **Acceptance Criteria**:
  - [ ] `compute_rice_score(10, 0.5, 0.8, 2.0) == 2.0`
  - [ ] `compute_rice_score(10, 0.5, 0.8, 0.0) == 4.0` (guarded div-by-zero)
  - [ ] `compute_priority_rank([p1, p2, p3])` where p1 has highest score returns `{p1.id: 1, p2.id: 2, p3.id: 3}`
  - [ ] Property test: rank is stable for equal scores (deterministic order)

  **QA Scenarios**:
  ```
  Scenario: RICE formula correct
    Tool: Bash (uv run python -c)
    Preconditions: None
    Steps:
      1. assert compute_rice_score(10, 0.5, 0.8, 2.0) == 2.0
      2. assert compute_rice_score(10, 0.5, 0.8, 0.0) == 4.0
    Expected Result: both assertions pass
    Evidence: .omo/evidence/task-5-rice-formula.txt

  Scenario: Priority rank deterministic
    Tool: Bash (uv run python -c)
    Preconditions: 3 projects with known scores
    Steps:
      1. Create 3 Project with rice fields
      2. Call compute_priority_rank
      3. Assert highest score gets rank 1
    Expected Result: ranks 1, 2, 3 in descending score order
    Evidence: .omo/evidence/task-5-priority-rank.txt
  ```

  **Commit**: YES
  - Message: `feat(sync): RICE score + priority rank export`
  - Files: `vibe-ops/src/pipeline/rice_exporter.py`, `vibe-ops/tests/test_rice_exporter.py`

---

- [x] 6. Create `FalsifiableHypothesis` entity (B5.1)

  **What to do**:
  - New file `vibe-ops/src/models/hypothesis_entities.py` with class `FalsifiableHypothesis(BaseModel)`:
    - `id: str = Field(pattern=r'^fh_[a-z0-9_]+$')`
    - `dream_id: str` (FK to Dream.id)
    - `hypothesis_text: str = Field(min_length=10, max_length=1000)`
    - `evidence_threshold: str` (what would prove it false)
    - `measurement_window_days: int = Field(ge=1, le=3650)`
    - `leading_indicators: List[str]` (Axis 2: behaviors we control)
    - `lagging_indicators: List[str]` (Axis 2: outcomes)
    - `refactor_triggers: List[str]` (Axis 3: env changes)
    - `kill_switch_date: Optional[date]`
    - `status: Literal["active", "validated", "falsified", "pivoted", "abandoned"] = "active"`
    - `last_evaluated_at: Optional[datetime] = None`
    - `created_at: datetime = Field(default_factory=datetime.utcnow)`
  - New class `HypothesisEvaluation(BaseModel)`:
    - `hypothesis_id: str`
    - `evaluated_at: datetime`
    - `verdict: Literal["validated", "falsified", "pivoted", "no_change"]`
    - `score: float = Field(ge=0.0, le=1.0)`
    - `notes: str = ""`
  - Export from `vibe-ops/src/models/__init__.py`
  - Unit tests for all 5 statuses, validation errors, FK presence

  **Recommended Agent Profile**:
  - **Category**: `deep` (requires understanding the strategic framework deeply)
  - **Skills**: None (domain knowledge is the differentiator)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1, Agent C
  - **Blocks**: T7, T10
  - **Blocked By**: None

  **References**:
  - `docs/chat-Framework de Planejamento Estratégico.txt:55-77` — Axis 1-3 definitions
  - `vibe-ops/specs/schema-pydantic-models-v2.md` — schema conventions
  - `vibe-ops/src/models/project_entities.py:5-22` — pattern reference for similar entities

  **Acceptance Criteria**:
  - [ ] `FalsifiableHypothesis(id="fh_test", dream_id="proj_x", hypothesis_text="I can land a remote AI job in 6 months", evidence_threshold="0 offers after 6 months", measurement_window_days=180)` validates
  - [ ] `hypothesis_text` shorter than 10 chars → ValidationError
  - [ ] `measurement_window_days=4000` → ValidationError
  - [ ] `status` accepts all 5 literal values
  - [ ] All FK references resolve (in test fixture)

  **QA Scenarios**:
  ```
  Scenario: FalsifiableHypothesis validates with full payload
    Tool: Bash (uv run python -c)
    Preconditions: None
    Steps:
      1. Construct full Hypothesis with all fields
      2. Assert validation passes
    Expected Result: instance created successfully
    Evidence: .omo/evidence/task-6-hypothesis-valid.txt

  Scenario: Short hypothesis_text rejected
    Tool: Bash (uv run python -c)
    Preconditions: None
    Steps:
      1. Try to construct with hypothesis_text="too short"
    Expected Result: ValidationError mentioning min_length=10
    Evidence: .omo/evidence/task-6-hypothesis-min-length.txt

  Scenario: All 5 statuses accepted
    Tool: Bash (uv run python -c)
    Preconditions: None
    Steps:
      1. For each of ["active", "validated", "falsified", "pivoted", "abandoned"], construct Hypothesis
    Expected Result: all 5 construct successfully
    Evidence: .omo/evidence/task-6-hypothesis-statuses.txt
  ```

  **Commit**: YES
  - Message: `feat(hypothesis): FalsifiableHypothesis + HypothesisEvaluation entities`
  - Files: `vibe-ops/src/models/hypothesis_entities.py`, `vibe-ops/src/models/__init__.py`, `vibe-ops/tests/test_hypothesis_entities.py`

---

- [x] 7. Implement `HypothesisEvaluator` (B5.2, B5.3)

  **What to do**:
  - New file `vibe-ops/src/pipeline/hypothesis_evaluator.py` with class `HypothesisEvaluator(db_connection)`
  - Method `evaluate_all() -> List[HypothesisEvaluation]`:
    - Query all FalsifiableHypothesis with `kill_switch_date <= today` OR `last_evaluated_at` older than 7 days
    - For each, apply rules:
      - If `leading_indicators` all met AND `lagging_indicators` below threshold → status="validated"
      - If `leading_indicators` all met AND `lagging_indicators` above threshold → status="falsified"
      - If any `refactor_trigger` detected (via simple keyword match in user's journal) → status="pivoted"
    - Persist HypothesisEvaluation rows
    - Update FalsifiableHypothesis.status
  - Method `compute_falsification_score(hypothesis: FalsifiableHypothesis, leading_met: int, lagging_met: int) -> float`:
    - Score = (leading_met / total_leading) * 0.5 + (1 - lagging_met / total_lagging) * 0.5
    - Returns 0-1
  - Export `hypothesis_status` and `falsification_score` to vault dream frontmatter (extend T4 export)
  - Unit tests + integration with fixture dreams

  **Recommended Agent Profile**:
  - **Category**: `deep`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1, Agent C
  - **Blocks**: T11
  - **Blocked By**: T6

  **References**:
  - `docs/chat-Framework de Planejamento Estratégico.txt:55-77` — Axis 1-3 logic
  - `vibe-ops/src/pipeline/policy_engine.py:43-104` — pattern for state machine evaluation

  **Acceptance Criteria**:
  - [ ] Hypothesis with all leading met + lagging below → status="validated", score ≥0.7
  - [ ] Hypothesis with all leading met + lagging above → status="falsified", score ≤0.3
  - [ ] Hypothesis with refactor_trigger detected → status="pivoted"
  - [ ] `compute_falsification_score(2_leading, 1_lagging, 3_total_leading, 4_total_lagging) ≈ 0.71`
  - [ ] Evaluation results persisted to DB

  **QA Scenarios**:
  ```
  Scenario: Validated hypothesis status
    Tool: Bash (uv run python -c)
    Preconditions: Fixture hypothesis with 3 leading, 2 lagging indicators
    Steps:
      1. All 3 leading met, 0 lagging met
      2. Run evaluator
      3. Assert status="validated"
    Expected Result: validated
    Evidence: .omo/evidence/task-7-validated.txt

  Scenario: Falsified hypothesis status
    Tool: Bash (uv run python -c)
    Preconditions: Fixture hypothesis with leading and lagging indicators
    Steps:
      1. All leading met, all lagging met (over threshold)
      2. Run evaluator
      3. Assert status="falsified"
    Expected Result: falsified
    Evidence: .omo/evidence/task-7-falsified.txt

  Scenario: Falsification score formula
    Tool: Bash (uv run python -c)
    Preconditions: None
    Steps:
      1. compute_falsification_score(2, 1, 3, 4)
    Expected Result: ~0.708 (within 0.01)
    Evidence: .omo/evidence/task-7-score-formula.txt
  ```

  **Commit**: YES
  - Message: `feat(hypothesis): HypothesisEvaluator with Axis 1-3 logic`
  - Files: `vibe-ops/src/pipeline/hypothesis_evaluator.py`, `vibe-ops/tests/test_hypothesis_evaluator.py`

---

- [x] 8. Create `life sync` CLI commands (B4.1-B4.5)

  **What to do**:
  - New file `life-ops/operational/apps/cli/src/operational/cli/commands/sync_cmd.py` with Typer app
  - Commands:
    - `life sync vault [--vault PATH] [--json]` — calls `BidirectionalSync.sync_vault_to_code()`, prints JSON
    - `life sync code [--vault PATH] [--json]` — calls `sync_code_to_vault()` + `HypothesisEvaluator.evaluate_all()`
    - `life sync all [--vault PATH] [--json]` — runs both in sequence
    - `life sync status [--json]` — shows last sync timestamp per entity_type, pending conflicts, entity counts
    - `life sync conflicts` — opens (or prints) `.sync-conflicts.md`
  - Register in `life-ops/operational/apps/cli/src/operational/cli/app.py` as sub-typer
  - Read vault path from `life.yaml` config (default: from `LifeConfig.vault_path`)
  - All commands support `--json` per repo convention
  - Integration test: subprocess `life sync vault --json`, parse output, assert structure

  **Must NOT do**:
  - Do not add commands without `--json` support
  - Do not import from `vibe-ops/` directly (call via subprocess or well-defined interface boundary)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1, Agent D
  - **Blocks**: T11, T13
  - **Blocked By**: None

  **References**:
  - `life-ops/operational/apps/cli/src/operational/cli/app.py` — Typer sub-typer registration pattern
  - `life-ops/operational/apps/cli/src/operational/cli/commands/policy_cmd.py` — minimal command file pattern
  - `life-ops/operational/packages/core/src/operational/persistence/base.py` — config loading

  **Acceptance Criteria**:
  - [ ] `pav sync --help` shows all 5 subcommands
  - [ ] `pav sync vault --json` on fixture returns valid JSON with `ingested`, `skipped`, `errors`, `conflicts` keys
  - [ ] `pav sync status --json` returns entity counts and timestamps
  - [ ] Exit codes: 0 on success, 1 on error

  **QA Scenarios**:
  ```
  Scenario: pav sync vault --json returns valid JSON
    Tool: Bash (subprocess)
    Preconditions: Fixture vault configured
    Steps:
      1. Run: pav sync vault --vault tests/fixtures/vault --json
      2. Assert exit code 0
      3. Parse stdout as JSON
      4. Assert keys: ingested, skipped, errors, conflicts
    Expected Result: JSON parsed successfully
    Evidence: .omo/evidence/task-8-cli-vault.txt

  Scenario: pav sync status reports entity counts
    Tool: Bash (subprocess)
    Preconditions: After running sync vault
    Steps:
      1. Run: pav sync status --json
      2. Assert JSON has last_sync_at, entity_counts
    Expected Result: structured status output
    Evidence: .omo/evidence/task-8-cli-status.txt

  Scenario: pav sync conflicts prints conflicts file
    Tool: Bash (subprocess)
    Preconditions: After running sync with conflicts
    Steps:
      1. Create .sync-conflicts.md with sample content
      2. Run: pav sync conflicts
      3. Assert file content printed to stdout
    Expected Result: conflicts file content visible
    Evidence: .omo/evidence/task-8-cli-conflicts.txt
  ```

  **Commit**: YES
  - Message: `feat(sync): pav sync vault|code|all|status|conflicts CLI`
  - Files: `life-ops/operational/apps/cli/src/operational/cli/commands/sync_cmd.py`, `life-ops/operational/apps/cli/src/operational/cli/app.py`, `life-ops/operational/tests/test_sync_cmd.py`

---

- [x] 9. Create fixture vault + integration test scaffolding

  **What to do**:
  - Create `vibe-ops/tests/fixtures/vault/` with representative notes:
    - `2_projeto/p1.md` (project with xp-points, mastery-level, subject)
    - `2_projeto/p2.md` (project with milestone, deliverable)
    - `5_atomicas/a1.md` (atomic with mastery-level, tech-stack)
    - `3_indice/m1.md` (MOC with hub-details)
    - `4_leitura/l1.md` (literature with language, exam-type)
    - `2_projeto/dream1.md` (dream with falsification-criteria)
    - `2_projeto/broken.md` (intentionally malformed YAML for error tests)
  - Create `vibe-ops/tests/conftest.py` with pytest fixtures for `temp_vault`, `temp_db`, `sync_engine`
  - Create `life-ops/operational/tests/test_sync_cmd.py` with subprocess-based CLI tests
  - Document fixture structure in `vibe-ops/tests/fixtures/README.md`

  **Recommended Agent Profile**:
  - **Category**: `quick`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1, Agent D
  - **Blocks**: T13
  - **Blocked By**: T8

  **References**:
  - `vibe-ops/tests/` — existing test structure
  - `life-ops/operational/tests/` — existing test patterns (unit, integration, property, e2e markers)

  **Acceptance Criteria**:
  - [ ] `vibe-ops/tests/fixtures/vault/` exists with 7 sample .md files (6 valid + 1 broken)
  - [ ] `pytest --collect-only vibe-ops/tests/` discovers all new tests
  - [ ] `temp_vault` and `temp_db` fixtures work in isolation

  **QA Scenarios**:
  ```
  Scenario: Fixture vault loads correctly
    Tool: Bash (pytest --collect-only)
    Preconditions: None
    Steps:
      1. Run: uv run pytest --collect-only vibe-ops/tests/test_bidirectional_sync.py
    Expected Result: discovers ≥6 tests
    Evidence: .omo/evidence/task-9-fixture-discover.txt

  Scenario: conftest fixtures work
    Tool: Bash (pytest)
    Preconditions: None
    Steps:
      1. Write a test that uses temp_vault + temp_db
      2. Run: uv run pytest vibe-ops/tests/test_fixture_smoke.py -v
    Expected Result: test passes
    Evidence: .omo/evidence/task-9-conftest.txt
  ```

  **Commit**: YES
  - Message: `test(sync): fixture vault + test scaffolding`
  - Files: `vibe-ops/tests/fixtures/vault/**`, `vibe-ops/tests/fixtures/README.md`, `vibe-ops/tests/conftest.py`, `life-ops/operational/tests/test_sync_cmd.py`

---

- [x] 10. Create DB migrations + advisory locks

  **What to do**:
  - New file `vibe-ops/migrations/2026_06_22_vault_sync.sql`:
    ```sql
    CREATE TABLE vault_sync_state (
      entity_type TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      last_vault_hash TEXT,
      last_code_hash TEXT,
      last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (entity_type, entity_id)
    );
    CREATE TABLE hypothesis_evaluations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      hypothesis_id TEXT NOT NULL,
      evaluated_at TIMESTAMP NOT NULL,
      verdict TEXT NOT NULL,
      score REAL NOT NULL,
      notes TEXT DEFAULT '',
      FOREIGN KEY (hypothesis_id) REFERENCES falsifiable_hypotheses(id)
    );
    ```
  - New file `life-ops/operational/packages/core/src/operational/persistence/migrations/2026_06_22_vault_sync.sql` (mirror)
  - In `BidirectionalSync.__init__`, enable SQLite WAL mode + use `BEGIN IMMEDIATE` for write transactions
  - Add advisory lock helper `_acquire_lock(entity_type) -> context manager` using `sqlite3` advisory locks
  - Migration test: fresh DB applies migration, existing DB idempotent

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T1, T4, T6)
  - **Parallel Group**: Wave 2
  - **Blocks**: T11, T12
  - **Blocked By**: T1, T4, T6

  **References**:
  - `life-ops/operational/packages/core/src/operational/persistence/sqlite.py` — migration runner
  - `life-ops/operational/packages/core/src/operational/persistence/migrations/` — existing migration pattern
  - `vibe-ops/src/storage/schema.sql` — existing schema

  **Acceptance Criteria**:
  - [ ] `python -m operational.persistence --migrate` applies new migration without error
  - [ ] `vault_sync_state` table exists with correct schema
  - [ ] `hypothesis_evaluations` table exists with FK to `falsifiable_hypotheses`
  - [ ] Re-running migration is a no-op (idempotent)
  - [ ] WAL mode enabled (verify via `PRAGMA journal_mode`)

  **QA Scenarios**:
  ```
  Scenario: Migration creates new tables
    Tool: Bash (sqlite3)
    Preconditions: Clean test DB
    Steps:
      1. Run migration
      2. sqlite3 test.db ".schema vault_sync_state"
      3. sqlite3 test.db ".schema hypothesis_evaluations"
    Expected Result: both tables exist with expected columns
    Evidence: .omo/evidence/task-10-migration-tables.txt

  Scenario: WAL mode enabled
    Tool: Bash (sqlite3)
    Preconditions: After migration
    Steps:
      1. sqlite3 test.db "PRAGMA journal_mode"
    Expected Result: "wal"
    Evidence: .omo/evidence/task-10-wal-mode.txt

  Scenario: Re-running migration is idempotent
    Tool: Bash (subprocess)
    Preconditions: Migration already applied
    Steps:
      1. Run migration again
    Expected Result: no error, no duplicate tables
    Evidence: .omo/evidence/task-10-migration-idempotent.txt
  ```

  **Commit**: YES
  - Message: `feat(sync): DB migrations for vault_sync_state + hypothesis_evaluations`
  - Files: `vibe-ops/migrations/2026_06_22_vault_sync.sql`, `life-ops/operational/packages/core/src/operational/persistence/migrations/2026_06_22_vault_sync.sql`, `vibe-ops/src/middleware/bidirectional_sync.py`

---

- [x] 11. End-to-end integration test: full sync cycle

  **What to do**:
  - New file `vibe-ops/tests/e2e/test_full_sync_cycle.py` (or `vibe-ops/tests/integration/test_full_sync_cycle.py`)
  - Test scenario:
    1. Start with empty DB + fixture vault
    2. Run `BidirectionalSync.sync_vault_to_code()` → assert all 6 valid notes ingested, 0 errors
    3. Simulate PolicyEngine decision (mock or use real engine on fixture metrics)
    4. Run `sync_code_to_vault()` → assert 12 new frontmatter keys added per note
    5. Run `HypothesisEvaluator.evaluate_all()` → assert dream hypothesis evaluated
    6. Run `sync_code_to_vault()` again → assert only timestamps changed
    7. Verify vault files are valid YAML and parseable
  - Use real SQLite (in temp dir), real YAML I/O
  - Asserts on DB state + vault file content
  - Mark with `@pytest.mark.e2e` for selective runs

  **Recommended Agent Profile**:
  - **Category**: `deep`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: F1-F4
  - **Blocked By**: T2, T5, T7, T8, T10

  **References**:
  - All Wave 1 task outputs

  **Acceptance Criteria**:
  - [ ] Test runs in <10 seconds
  - [ ] All assertions pass
  - [ ] DB has expected row counts
  - [ ] Vault files have expected frontmatter structure
  - [ ] No data loss (all original vault keys preserved)

  **QA Scenarios**:
  ```
  Scenario: Full sync cycle end-to-end
    Tool: Bash (pytest)
    Preconditions: Fixture vault + fresh DB
    Steps:
      1. Run: uv run pytest vibe-ops/tests/e2e/test_full_sync_cycle.py -v --tb=short
    Expected Result: all assertions pass, test completes <10s
    Evidence: .omo/evidence/task-11-e2e-cycle.txt
  ```

  **Commit**: YES
  - Message: `test(sync): end-to-end full sync cycle integration test`
  - Files: `vibe-ops/tests/e2e/test_full_sync_cycle.py`

---

- [x] 12. Conflict resolution E2E test

  **What to do**:
  - New file `vibe-ops/tests/integration/test_conflict_resolution.py`
  - Test scenarios:
    1. Vault modifies `xp_points` (manual field) → code has different value → after sync, code value matches vault (vault wins), no conflict logged
    2. Engine computes new `regime` → vault has stale value → after sync_code_to_vault, vault updated, no conflict logged
    3. Both vault and code modify an unknown/ambiguous field → after sync, value written to `.sync-conflicts.md`, no exception raised
  - Property test: 100 random field modifications, assert correct resolution policy applied
  - Use real fixture, not mocks

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: F1-F4
  - **Blocked By**: T3, T5, T10

  **References**:
  - T3 conflict resolution policy

  **Acceptance Criteria**:
  - [ ] Test covers all 3 conflict scenarios
  - [ ] Property test runs 100 iterations without failure
  - [ ] `.sync-conflicts.md` is correctly formatted (markdown with timestamp + values)

  **QA Scenarios**:
  ```
  Scenario: All conflict scenarios covered
    Tool: Bash (pytest)
    Preconditions: None
    Steps:
      1. Run: uv run pytest vibe-ops/tests/integration/test_conflict_resolution.py -v
    Expected Result: all 3 scenarios + property test pass
    Evidence: .omo/evidence/task-12-conflict-e2e.txt
  ```

  **Commit**: YES
  - Message: `test(sync): conflict resolution E2E + property tests`
  - Files: `vibe-ops/tests/integration/test_conflict_resolution.py`

---

- [x] 13. Create `specs/vault-bidirectional-sync/PRODUCT.md` and `TECH.md` (Sisyphus executes the write-tech-spec skill)

  **What to do**:
  - Invoke `/write-tech-spec` skill with feature id `vault-bidirectional-sync`
  - Skill creates `specs/vault-bidirectional-sync/PRODUCT.md` and `TECH.md` per the Warp spec format
  - Cross-reference this plan file for behavior invariants and acceptance criteria
  - Commit spec files alongside code

  **Recommended Agent Profile**:
  - **Category**: `writing`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: F1-F4
  - **Blocked By**: T8, T9

  **References**:
  - `.claude/skills/write-tech-spec/SKILL.md` — skill instructions
  - `.omo/plans/vault-bidirectional-sync.md` — this plan (source for spec content)

  **Acceptance Criteria**:
  - [ ] `specs/vault-bidirectional-sync/PRODUCT.md` exists with 6 Behavior invariants (B1-B6)
  - [ ] `specs/vault-bidirectional-sync/TECH.md` exists with Context, Proposed changes, Testing, Parallelization sections
  - [ ] Both files are committed

  **QA Scenarios**:
  ```
  Scenario: PRODUCT.md and TECH.md exist
    Tool: Bash (ls)
    Preconditions: None
    Steps:
      1. ls specs/vault-bidirectional-sync/
    Expected Result: PRODUCT.md and TECH.md present
    Evidence: .omo/evidence/task-13-specs-exist.txt
  ```

  **Commit**: YES
  - Message: `docs(sync): PRODUCT.md and TECH.md per Warp spec format`
  - Files: `specs/vault-bidirectional-sync/PRODUCT.md`, `specs/vault-bidirectional-sync/TECH.md`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
>
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback → fix → re-run → present again → wait for okay.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in `.omo/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `tsc --noEmit` + linter + `pytest`. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp).
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (full sync cycle works end-to-end). Test edge cases: empty vault, vault with all broken files, sync during write. Save to `.omo/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination: Task N touching Task M's files. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **T1**: `feat(sync): extend Project/StudyProject with vault enrichment fields` — `vibe-ops/src/models/*.py`, `vibe-ops/tests/test_*.py`
- **T2**: `feat(sync): BidirectionalSync.sync_vault_to_code with idempotency` — `vibe-ops/src/middleware/bidirectional_sync.py`, `vibe-ops/src/pipeline/frontmatter_parser.py`, `vibe-ops/tests/test_bidirectional_sync.py`, `vibe-ops/tests/fixtures/vault/**`
- **T3**: `feat(sync): conflict resolution with vault-wins/computed-wins policy` — `vibe-ops/src/middleware/bidirectional_sync.py`, `vibe-ops/tests/test_bidirectional_sync.py`
- **T4**: `feat(sync): BidirectionalSync.sync_code_to_vault with atomic writes` — `vibe-ops/src/middleware/bidirectional_sync.py`, `vibe-ops/tests/test_bidirectional_sync.py`
- **T5**: `feat(sync): RICE score + priority rank export` — `vibe-ops/src/pipeline/rice_exporter.py`, `vibe-ops/tests/test_rice_exporter.py`
- **T6**: `feat(hypothesis): FalsifiableHypothesis + HypothesisEvaluation entities` — `vibe-ops/src/models/hypothesis_entities.py`, `vibe-ops/src/models/__init__.py`, `vibe-ops/tests/test_hypothesis_entities.py`
- **T7**: `feat(hypothesis): HypothesisEvaluator with Axis 1-3 logic` — `vibe-ops/src/pipeline/hypothesis_evaluator.py`, `vibe-ops/tests/test_hypothesis_evaluator.py`
- **T8**: `feat(sync): pav sync vault|code|all|status|conflicts CLI` — `life-ops/operational/apps/cli/src/operational/cli/commands/sync_cmd.py`, `life-ops/operational/apps/cli/src/operational/cli/app.py`, `life-ops/operational/tests/test_sync_cmd.py`
- **T9**: `test(sync): fixture vault + test scaffolding` — `vibe-ops/tests/fixtures/vault/**`, `vibe-ops/tests/fixtures/README.md`, `vibe-ops/tests/conftest.py`, `life-ops/operational/tests/test_sync_cmd.py`
- **T10**: `feat(sync): DB migrations for vault_sync_state + hypothesis_evaluations` — `vibe-ops/migrations/2026_06_22_vault_sync.sql`, `life-ops/operational/packages/core/src/operational/persistence/migrations/2026_06_22_vault_sync.sql`, `vibe-ops/src/middleware/bidirectional_sync.py`
- **T11**: `test(sync): end-to-end full sync cycle integration test` — `vibe-ops/tests/e2e/test_full_sync_cycle.py`
- **T12**: `test(sync): conflict resolution E2E + property tests` — `vibe-ops/tests/integration/test_conflict_resolution.py`
- **T13**: `docs(sync): PRODUCT.md and TECH.md per Warp spec format` — `specs/vault-bidirectional-sync/PRODUCT.md`, `specs/vault-bidirectional-sync/TECH.md`

---

## Success Criteria

### Verification Commands
```bash
# Unit + integration tests
cd vibe-ops && uv run pytest tests/ -v --tb=short

# CLI tests
cd life-ops/operational && uv run pytest tests/test_sync_cmd.py -v

# Quality gates
cd vibe-ops && uv run mypy src/middleware/bidirectional_sync.py src/pipeline/hypothesis_evaluator.py src/pipeline/rice_exporter.py --strict
cd life-ops/operational && uv run mypy apps/cli/src/operational/cli/commands/sync_cmd.py --strict

cd vibe-ops && uv run ruff check src/middleware/ src/pipeline/ src/models/
cd life-ops/operational && uv run ruff check apps/cli/src/operational/cli/commands/sync_cmd.py

# Full quality gate
cd life-ops/operational && uv run pytest  # 2518 + new tests
```

### Final Checklist
- [ ] All "Must Have" present (FalsifiableHypothesis, idempotent sync, atomic writes, conflicts file, ≥90% coverage)
- [ ] All "Must NOT Have" absent (no deletions, no LLM, no daemon, no auto-migration, no cloud sync)
- [ ] All 13 tasks completed
- [ ] All 4 final verification tasks (F1-F4) approved
- [ ] User has given explicit "okay"
- [ ] Draft file deleted from `.omo/drafts/`

---

*End of plan — awaiting user approval*
