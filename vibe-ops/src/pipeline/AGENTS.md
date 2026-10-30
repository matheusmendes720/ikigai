# src/pipeline — ingest, enrich, evaluate, export

## OVERVIEW
Data-mesh orchestration stage by stage — pure arithmetic, no LLM calls anywhere in the pipeline.

32 single-class modules: frontmatter → entities → metadata → indexes → analytics.
`MVLOrchestrator` is the master entry point; the rest are one-stage-per-file.

## WHERE TO LOOK
| Stage | Module | Role |
|-------|--------|------|
| Orchestrator | `mvl_orchestrator.py` | `MVLOrchestrator` — top-level pipeline runner |
| Ingest | `ingestion_engine.py` | `IngestionEngine` — frontmatter → typed entities |
| Frontmatter | `frontmatter_parser.py` | `FrontmatterParser` — YAML/frontmatter extraction |
| Enrichment | `enrichment.py`, `enrichment_engine.py` | `MetadataEnricher` (v1) vs `EnrichmentEngine` (v2) |
| Routing | `router.py`, `unified_router.py` | `DataRouter`, `UnifiedQueryRouter` |
| Contract gate | `schema_registry.py` | YAML catalog + JSON-Schema validation, `ContractStatus` |
| Epistemics | `harness_epistemic.py`, `hypothesis_evaluator.py` | verdict scoring (arithmetic only) |
| Metrics | `harness_metrics.py`, `analytics_emitter.py` | metric snapshots, event emission |
| Debt / gaps | `cognitive_debt_tracker.py`, `gap_engine.py`, `knowledge_tree.py` | unfinished-work detection |
| RAG | `rag_indexer.py` | `HybridRAGIndexer` — hybrid keyword + vector index |
| Export | `rice_exporter.py` | RICE scoring + priority rank (uses the `×` sign) |
| Sync | `sync_orchestrator.py`, `reverse_sync.py`, `roadmap_sync_ingest.py`, `tw_sync.py`, `tw_sync_adapter.py` | code→vault and Taskwarrior bridges |
| Telemetry | `knowledge_telemetry.py` | code → knowledge feedback loop |
| State | `pipeline_state_machine.py` | `PipelineState`, `PipelineStateMachine` |
| Contracts | `contracts.py` | `DataMeshContract` |

## CONVENTIONS
- **One class per module** (AST-verified) — keep one responsibility per file.
- **Idempotency**: stage-local `compute_upstream_id()` = sha256 of canonical JSON truncated
  to 12 chars (`enrichment_engine.py`, `fk_resolver.py`).
- **Hypothesis verdict precedence lives in the module docstring** of `hypothesis_evaluator.py`:
  score = `leading_met*0.5 + (1-lagging_met)*0.5`, and `refactor_trigger` → "pivoted" wins
  over validated/falsified. Read it before touching scoring.
- **Import style is mixed here** (absolute `from models import ...` plus relative imports) —
  the only package in the tree that does both.
- `schema_registry.py` imports `jsonschema` at module level; that package is not declared in
  `pyproject.toml` — install it or the import fails.

## ANTI-PATTERNS
- Never add LLM/chat/streaming calls or scoring kernels here — the pipeline is pure
  arithmetic, and `vibe-ops/src/` is scanned by the ADR-013 drift test.
- Never re-add `compute_score` / `IkigaiScorer` / `cybernetics.daily_loop` — deleted
  2026-08-31 and still forbidden by the drift net.
- Do not "fix" `metadata_catalog.py`, `pipeline_state_machine.py` or `knowledge_telemetry.py`
  by renaming blindly: they import `src.storage...` / `vibe_ops.src.models...`, paths that
  cannot resolve in this layout — point them at the correct sibling import instead.
- Duplicated implementations exist on purpose: `schema_registry.SchemaRegistry` (catalog +
  JSON-Schema) vs `schemas.registry.SchemaRegistry` (semver factory); `gap_engine.GapSearchEngine`
  vs `cybernetics.engine.GapSearchEngine`. Do not add a third.
- `code_review_sync.py` and `study_manager.py` are 0-byte placeholders.
