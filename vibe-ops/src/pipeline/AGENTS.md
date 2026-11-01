# vibe-ops/src/pipeline — Engine Kernel

## OVERVIEW
The 32-module ingest → validate → enrich → index kernel, and the only package
in `src/` with a curated public facade (`__init__.__all__` = 14 names).

## WHERE TO LOOK
| Role | Modules | Notes |
|------|---------|-------|
| Orchestration | `mvl_orchestrator.py`, `ingestion_engine.py`, `sync_orchestrator.py`, `roadmap_sync_ingest.py` | `MVLOrchestrator.ingest_markdown` is the master path |
| Validation gate | `schema_registry.py`, `contracts.py` | `DataMeshContract` mesh rules; `ValidationResult.errors` |
| Policy / state | `policy_engine.py`, `pipeline_state_machine.py` | 4-state FSM + `RAW→VALIDATED→INDEXED→ENRICHED→FAILED` |
| Enrichment | `enrichment.py`, `enrichment_engine.py`, `hypothesis_evaluator.py`, `harness_epistemic.py`, `harness_metrics.py`, `cognitive_debt_tracker.py`, `learning_outcome_processor.py` | metadata is computed, never typed by hand |
| Routing / query | `router.py`, `unified_router.py`, `gap_engine.py`, `knowledge_tree.py`, `metadata_catalog.py` | `UnifiedQueryRouter` does the hybrid deep join |
| Index / sinks | `rag_indexer.py`, `analytics_emitter.py`, `reverse_sync.py`, `tw_sync.py`, `tw_sync_adapter.py`, `fk_resolver.py` | `tw_sync.py` is legacy; `tw_sync_adapter.py` supersedes it |
| Scoring | `rice_exporter.py` | the **only** place RICE scoring is allowed to live |
| Telemetry | `knowledge_telemetry.py` | daily reports; drives `scripts/audit_github_execution.ps1` |
| Not in `__all__` | `analytics_emitter`, `contracts`, `fk_resolver`, `gap_engine`, `hypothesis_evaluator`, `knowledge_telemetry`, `knowledge_tree`, `metadata_catalog`, `pipeline_state_machine`, `policy_engine`, `rag_indexer`, `roadmap_sync_ingest`, `rice_exporter`, `tw_sync`, `tw_sync_adapter` | imported by path |

## CONVENTIONS
- **One flow, five stages**: parse frontmatter → validate against the registry →
  enrich metadata → index (SQLite + Chroma) → emit telemetry. Every stage is a
  separate module; do not merge them.
- **Fail fast, never persist invalid payloads.** `MVLOrchestrator` records a
  `FAILED_VALIDATION` / `CONTRACT_VOLATION` state trace instead of writing.
- **Idempotency key is `upstream_id`** — SHA-256 truncated to 12 hex chars,
  computed from `id`+`title` (`enrichment.py`) or the whole payload
  (`roadmap_sync_ingest.py`); every write is `ON CONFLICT … DO UPDATE`.
- **Config is a `ClassVar` dict**, not a file: `FrontmatterParser.MODEL_MAP` (24
  entity types), `PolicyEngine.POLICY_MAP` (per-state setpoints),
  `FKResolver.FK_SCHEMA`. `SchemaRegistry` is the only YAML-backed one
  (`schema_registry/registry.yaml`).
- **State machines, never boolean flags** — every transition carries trigger,
  precondition, postcondition and an audit row (`StateMachineORM`).
- **Mixed imports**: `gap_engine.py` and `sync_orchestrator.py` use relative
  (`from .knowledge_tree import …`); the rest use absolute (`from pipeline.x import …`).
- **`from __future__ import annotations`** appears in only 9 of 30 modules. Match
  the file you edit; do not mass-add.
- **Docstrings are PT-BR in the older modules, English in the newer ones**
  (`hypothesis_evaluator`, `rice_exporter`, `knowledge_telemetry`, `sync_orchestrator`
  carry a `Source: .omo/plans/<plan>.md (T<n>)` provenance header).

## ANTI-PATTERNS (THIS PROJECT)
- **No LLM in the pipeline.** Pure arithmetic + SQLite queries only (ADR-001 §2.1,
  ADR-004 §2.2).
- **No boolean-flag state** (ADR-002 §3.1) — illegal states and lost history.
- **No runtime-only validation** (ADR-002 §3.2) — contracts gate the write.
- **No Event Sourcing / Kafka-style bus** (ADR-002 §3.3, ADR-005 §3.4) — rejected
  for complexity.
- **No monolithic unified schema** (ADR-001 §3.4) — one cluster's change must not
  break every other cluster.
- **No raw FK spaghetti** (ADR-005 §3.3) — everything goes through `contracts.py`.
- **Never delete** — pipelines are append-only.
- **`print()` instead of `logging`** in `frontmatter_parser.py` and `reverse_sync.py`;
  `datetime.utcnow()` (deprecated, naive) in 9 modules.

## NOTES
- `policy_engine.py` is the semantic centre of the cybernetic loop and the widest
  blast radius in the repo — its 4 states (`PUSH/MAINTAIN/REDUCE/RECOVER`) and
  hysteresis (≥3 days at MAINTAIN before escalating to PUSH) are contractual.
- `hypothesis_evaluator.py` embeds its own DDL for `falsifiable_hypotheses` /
  `hypothesis_evaluations`, duplicating `migrations/005_vault_sync.sql`.
- `tw_sync_adapter.py` is a stub: `full_pull` returns `[]`, `full_push` is `pass`.
  `fk_resolver.validate` always returns `True`.
- `code_review_sync.py` and `study_manager.py` are 0-byte placeholders named in
  ADR-001 §2.3 as pipelines "still to be created".
