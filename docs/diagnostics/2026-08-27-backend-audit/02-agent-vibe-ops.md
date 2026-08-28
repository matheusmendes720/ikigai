# Agent 2 — vibe-ops cybernetic engine

**Source:** `Agent` tool dispatched 2026-08-27
**Scope:** Map vibe-ops daily loop, pipeline layer, storage adapters, CLI entry points
**Status:** COMPLETE

---

## 1. Cybernetic Loop — `vibe-ops/src/cybernetics/daily_loop.py`

**Entry:** `CyberneticDailyLoop.execute_daily_cycle()` (line 22)
**Caller:** `vibe-ops/src/main.py:6,66,72` (CLI `run-daily`/`status`/`sync` subcommands)

### Stage mapping (lines 25-40)

| Stage | Implementation | Line |
|-------|----------------|------|
| TARGET | `_compute_target()` (IkigaiScorer-backed setpoint) | 61 |
| SENSOR | `_read_sensor_data()` (SQLite raw reads of `study_sessions`/`habit_states`) | 70 |
| ADJUSTER | `self.policy_engine.evaluate()` (delegates to canonical) | 33 |
| PERSIST | `_persist_decision()` (writes `policy_decisions` row) | 105 |
| SYNC | `self.sync.sync_sqlite_to_taskwarrior()` (SyncEngine) | 37 |
| INDEX | `self.indexer.index_vault()` (HybridRAGIndexer) | 40 |

### Critical imports (lines 1-9)

```python
from schemas.pydantic_v2 import PolicyState, PolicyDecision, QHEMetrics   # LOCAL STUB
from operational.core.policy_engine import PolicyEngine                    # CANONICAL
from pipeline.ikigai_scorer import IkigaiScorer                            # delegates to canonical
```

**Dual PolicyEngine in parallel:**
- Line 4 imports local stub `schemas.pydantic_v2`
- Line 7 imports canonical `operational.core.policy_engine`

Adjuster uses canonical; data shapes come from local stub.

---

## 2. Pipeline Layer — `vibe-ops/src/pipeline/` (35 .py files)

### Canonical / real modules

| File | Status | Notes |
|------|--------|-------|
| `ikigai_scorer.py` | REAL | line 18: `from ikigai.core.scoring.vector_scores import compute_vector_scores` |
| `daily_consolidator.py` | REAL | 327 lines, supports `--dry-run`, writes `data/tasks.jsonl` |
| `cognitive_debt_tracker.py` | REAL | `CognitiveDebtTracker.identify_critical_debt()` |
| `contracts.py` | REAL | DataMesh contract rules |
| `enrichment.py`, `enrichment_engine.py` | REAL | metadata enrichment |
| `gap_engine.py` | REAL | `GapSearchEngine.analyze_gaps()` |
| `harness_epistemic.py` | REAL | EpistemicHarness |
| `hypothesis_evaluator.py` | REAL | T7 falsifiable, B5.3 score formula at line 141 |
| `ingestion_engine.py` | REAL | `IngestionEngine.process_obsidian_note()` |
| `mvl_orchestrator.py` | REAL | MVLOrchestrator.ingest_markdown() |
| `rag_indexer.py` | REAL | HybridRAGIndexer wraps SQLiteVec + EmbeddingProvider |
| `reverse_sync.py` | REAL | ReverseSync (SQLite→vault) |
| `rice_exporter.py` | REAL | compute_rice_score() |
| `schema_registry.py` | REAL | SchemaRegistry.validate_against_contract() |
| `sync_orchestrator.py` | REAL | SyncOrchestrator.process_markdown_file() |
| `unified_router.py` | REAL | Layer-3 SQL+Vector deep join |

### Stub modules

| File | Status | Notes |
|------|--------|-------|
| `policy_engine.py` | **STUB** | 119 lines, line 3: `from schemas.pydantic_v2 import PolicyState, PolicyDecision` |
| `study_manager.py` | EMPTY | 0 bytes |
| `code_review_sync.py` | EMPTY | 0 bytes |

---

## 3. Storage Layer — `vibe-ops/src/storage/` (10 files)

| Adapter | DB | Tables | Used by |
|---------|----|----|---------|
| `SQLiteAdapter` | `vibe_ops.db` | 13-table generic map | `DataMeshAdapter` |
| `ChromaAdapter` | `chroma_db/` | collection `vibe_ops_mesh` | `DataMeshAdapter`, `vibe_cli.py` |
| `DataMeshAdapter` | both above | orchestrates SQLite+Chroma | `vibe_cli.py`, `SyncOrchestrator`, `GapSearchEngine` |
| `SQLiteVecIntegration` | `vibe_ops.db` | owns `semantic_index` table | `HybridRAGIndexer` |
| `MetadataCatalogORM` + `StateMachineORM` | `vibe_ops.db` | SQLAlchemy | `IngestionEngine`, `MVLOrchestrator` |
| `vector_store.py` | n/a | EMPTY | 0 bytes |

### `schema.sql` (236 lines)

Defines canonical tables: `policy_decisions` (193), `study_sessions` (211), `planning_entities` (218), `roadmap_sync` (228), `mesh_metadata_catalog` (170), `mesh_state_machine` (181), view `v_epistemic_priority` (236).

---

## 4. CLI entry points (5 different surfaces)

| Entry | Lines | Subcommands |
|-------|-------|-------------|
| `vibe-ops/src/main.py` (argparse) | 30-47 | `run-daily`, `status`, `gaps`, `sync` |
| `vibe-ops/src/vibe_cli.py` (Typer) | 41,68,91,109 | `sync_file`, `debt_dashboard`, `hybrid_search`, `gaps` |
| `vibe-ops/src/cli/period_sync_cli.py` | 111,119,127 | `sync`, `list`, `hierarchy` |
| `vibe-ops/src/agents/pae_maintainer/main.py` | 163,176,183,189 | `run`, `daemon`, `status`, `balance` |
| `vibe-ops/src/scripts/vault_sync.py` | 175-179 | `vault`, `code`, `all`, `status`, `conflicts` |

---

## 5. LangGraph — `vibe-ops/src/langgraph_entry.py` (6 factories)

| Factory | Line | Status | Notes |
|---------|------|--------|-------|
| `make_pae_graph` | 74 | **REAL** | wraps `pae_maintainer.graph.run_pae_cycle()` (5-node) |
| `make_replan_graph` | 189 | **STUB DISPATCHER** | 3 lambdas (`load_yaml`, `execute_steps`, `record_result`) — execute nothing |
| `make_rollup_graph` | 193 | **STUB DISPATCHER** | same pattern, dispatches `test-de-fogo-rollup` |
| `make_correction_graph` | 197 | **STUB DISPATCHER** | dispatches `correction-protocol` |
| `make_falsification_graph` | 201 | **STUB DISPATCHER** | dispatches `dream-falsification` |
| `make_ikigai_graph` | 210 | **REAL BUT BROKEN** | imports from `life-ops/ikigai/src` (path doesn't exist) |

### Path issue at line 27

```python
Path(__file__).parent.parent.parent / "life-ops" / "ikigai" / "src"
```

This path no longer exists. `make_ikigai_graph` will FAIL at import-time without `sys.path` patching.

---

## 6. `unified_router` — NOT orphan (claim Q4 false)

Verified live in production:
- `vibe-ops/src/vibe_cli.py:12` — `from pipeline.unified_router import UnifiedQueryRouter`
- `vibe-ops/src/vibe_cli.py:37` — instantiation
- `vibe-ops/src/vibe_cli.py:94` — `router.query_mesh(...)` called by `hybrid_search`
- `vibe-ops/src/pipeline/__init__.py:9,25` — re-exported in `__all__`

The "orphan" claim in retrospective refers to a different `unified_router` in `feat/data-model-unification` worktree (NOT on master).

---

## 7. `schemas.pydantic_v2` — local 49-line stub

Located at `vibe-ops/src/schemas/pydantic_v2.py`. Defines: `PolicyState`, `PolicyDecision`, `QHEMetrics`, `TaskPayload`, `StudyPlanEntity`.

Imported by:
- `vibe-ops/src/cybernetics/daily_loop.py:4`
- `vibe-ops/src/middleware/sync_engine.py:9`
- `vibe-ops/src/pipeline/policy_engine.py:3`

**NOT the canonical `src/contracts/common.py`.**

---

## 8. Retrospective Claims Verification

| Claim | Status |
|-------|--------|
| B2 ikigai_scorer wrong vectors | ✅ IkigaiScorer REAL (delegates to canonical) |
| B4 daily_consolidator 0 bytes | ✅ DONE — 327 lines, REAL |
| B5 Policy Engine canonical | ⚠️ PARTIAL — `daily_loop.py:7` uses canonical, but `sync_engine.py:9`, `main.py:86`, `policy_engine.py` stub still in parallel |
| B8 pae_maintainer LangGraph | ✅ REAL — wraps `run_pae_cycle` |
| Q2 "4 LangGraph stubs removed" | ❌ FALSE — 4 STUB DISPATCHERS remain |
| Q4 "unified_router zero refs" | ❌ FALSE — actively used in `vibe_cli.py` |
