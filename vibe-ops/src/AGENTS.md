# vibe-ops/src — Python Package

## OVERVIEW
The engine package: 12 sibling layers under one flat import root, with
`src/` itself acting as the import boundary (`vibe-ops/src` on `sys.path`).

## STRUCTURE
```
src/
├── pipeline/       # ingest→validate→enrich→index kernel (own AGENTS.md)
├── middleware/     # vault ⇄ SQLite sync; period-report sync
├── models/         # 42 Pydantic entities, re-export hub (__all__ = 42)
├── storage/        # SQLite/Chroma adapters, ORM, schema.sql, ueid.py
├── schemas/        # PolicyState, PolicyDecision, QHEMetrics, registry
├── contracts/      # planning.v1.yaml, registry.yaml, sync/roadmap contracts
├── cli/ scripts/   # argparse CLIs: period_sync_cli, vault_sync
├── cybernetics/ agents/ embeddings/ integration/   # engine, PAE, providers, semantic
├── parsers/        # code_parser.py (0 bytes)
└── vibe_cli.py     # typer dashboard: sync-file, debt-dashboard, hybrid-search, gaps
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Re-export the public surface | `pipeline/__init__.py`, `models/__init__.py`, `storage/__init__.py` | `__all__` is the contract — 14 / 42 / 9 names |
| Add an entity model | `models/<domain>_entities.py` | then add it to `models/__init__.py.__all__` |
| Add a DB table | `storage/schema.sql` + `migrations/00N_*.sql` | migrations are idempotent SQL |
| Sync vault ↔ DB | `middleware/bidirectional_sync.py` | manual vs computed field sets are explicit constants |
| Policy / DB payload types | `schemas/pydantic_v2.py` | shared with the Rust TUI's SQL |
| Frontmatter → entity parsing | `pipeline/frontmatter_parser.py` | `MODEL_MAP` pins 24 entity types |
| CLI entry points | `cli/period_sync_cli.py`, `scripts/vault_sync.py`, `vibe_cli.py` | all emit a JSON envelope |
| Embeddings | `embeddings/provider.py` | `get_provider(config)` factory, local-first |

## CONVENTIONS
- **`src/` is the import root.** `mypy_path = ["src"]`, `namespace_packages = true`.
  Siblings import flat (`from pipeline.x import Y`, `from storage.x import Z`); only
  `models/`, `storage/` and `pipeline/` have `__init__.py` — the rest are PEP 420
  namespace packages.
- **Two import styles coexist** — absolute flat (`from models.X import Y`) and
  relative (`from .orm import Base` inside `storage/`). `middleware/`, `schemas/`,
  `cybernetics/`, `embeddings/`, `integration/` have no `__init__.py` at all.
- **`# noqa: N999`** on every `__init__.py`: the directory `vibe-ops` contains a
  hyphen and cannot be renamed. The same waiver lives in `pyproject.toml`.
- **Pydantic here is permissive** — `extra="allow"` and mutable models, the
  opposite of the repo-wide `src/contracts/` rule. `period_report.py` says so
  explicitly: "Lenient mode … so user-added fields don't break validation".
- **`from __future__ import annotations` is inconsistent** (present in only ~1/3 of
  the modules here). Match the file you are editing instead of mass-adding it.
- **Config lives in `ClassVar` dicts**, not YAML: `FrontmatterParser.MODEL_MAP`,
  `PolicyEngine.POLICY_MAP`, `FKResolver.FK_SCHEMA`. Only `SchemaRegistry` reads
  a YAML file (`schema_registry/registry.yaml`).
- **`str, Enum` is deliberate** (`# noqa: UP042`) — the member value is serialised
  straight into DB rows.
- **Docstrings: PT-BR in older modules, English in newer ones** (`hypothesis_evaluator`, `rice_exporter`).

## ANTI-PATTERNS (THIS PROJECT)
- **Never import from the repo's `src/contracts/` here** — vibe-ops owns its own
  entity contracts, and `UEID`/`Task` already collide across the two trees.
- **No cloud dependency.** OpenAI embeddings are an opt-in provider; the default
  path is SQLite + ChromaDB + filesystem.
- **Never delete vault or vector content** — the sync layers only append.
- **Never score inside a sync layer** — `bidirectional_sync._build_computed_fields`
  raises `NotImplementedError` on purpose.
- **`datetime.utcnow()` is deprecated** (naive UTC) and still used in
  `middleware/sync_engine.py` and `storage/metadata_orm.py`; use `datetime.now(UTC)`.
- **Bare `except Exception` swallows failures** in 6 places (`middleware/`,
  `models/period_report.py`, `storage/sqlite_vec_integration.py`).
- **Avoid raw SQL f-string interpolation** — `storage/sqlite_adapter.py` builds
  table/column names inline; values are parameterised.

## NOTES
- `src/vibe_cli.py` creates 7 module-level singletons (engine, session, adapter,
  registry, orchestrator, router, debt tracker) at **import time** and opens
  `vibe_ops.db` in the CWD — importing the module has side effects.
- `src/integration/semantic_engine.py` hard-imports `sqlite_vec` and
  `sentence_transformers` at module import (no lazy import).
- `src/embeddings/config.py`, `src/integration/obsidian_parser.py`,
  `src/parsers/code_parser.py` are 0-byte placeholders.
- `models/knowledge_entities.py` (`DailyKnowledgeReport`) is absent from
  `models/__init__.py.__all__` — unreachable through the package hub.
