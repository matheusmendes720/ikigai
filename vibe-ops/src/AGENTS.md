# vibe-ops/src — Python package tree

## OVERVIEW
Runtime tree of the cybernetic engine — every import here resolves only with `vibe-ops/src` on `sys.path`.

13 bare-namespace packages imported as top-level modules (`models`, `middleware`,
`pipeline`, …). `src/__init__.py` is empty and there is no `src/vibe_ops/` shim.

## STRUCTURE
```
src/
├── models/       # 42 pydantic entities (contract-shaped, lenient)
├── pipeline/     # ingest → enrich → index orchestration (32 modules)
├── middleware/   # vault↔code sync engines
├── storage/      # SQLAlchemy ORM, SQLite/Chroma adapters, local UEID
├── contracts/    # YAML contract catalog + sync contract v1
├── schemas/      # semver registry + DB-facing pydantic models
├── cli/          # subprocess bridge for the operational CLI
├── scripts/      # vault_sync bridge (JSON on stdout)
├── agents/       # pae_maintainer (currently unimportable)
├── cybernetics/  # gap-search over the knowledge tree
├── embeddings/   # provider ABC + openai/local implementations
├── integration/  # semantic engine (sqlite-vec + sentence-transformers)
├── parsers/      # empty placeholder
└── vibe_cli.py   # Typer dashboard
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| Entity shapes | `models/` |
| Orchestration entry | `pipeline/mvl_orchestrator.py` |
| Vault ingest + conflicts | `middleware/bidirectional_sync.py` |
| DB tables | `storage/orm.py`, `storage/schema.sql` |
| Contract versioning | `contracts/registry.yaml` |
| Subprocess bridges | `cli/period_sync_cli.py`, `scripts/vault_sync.py` |

## CONVENTIONS
- **Import styles differ per package** (do not normalise them): `models/` and `middleware/`
  use absolute intra-package imports (`from models.x import Y`); `pipeline/` mixes absolute
  and relative; `storage/` uses relative (`from .orm import Base`). All resolve only because
  `vibe-ops/src` is on `sys.path`.
- **`# noqa: N999`** on package `__init__.py` files is deliberate (hyphenated dir name).
- **Bridges emit JSON on stdout** and are launched as subprocesses — the operational CLI must
  not import this tree directly (`src/cli/period_sync_cli.py`, `src/scripts/vault_sync.py`).
- **Import-time side effects exist**: `vibe_cli.py` opens `vibe_ops.db` + `./chroma_db` and
  registers a schema registry at module import — importing it touches the filesystem.

## ANTI-PATTERNS
- Never import this tree as `vibe_ops.*` — the hyphen makes it impossible. The docstring in
  `src/cli/period_sync_cli.py` showing `python -m vibe_ops.src.cli.period_sync_cli` is wrong;
  run `python src/cli/period_sync_cli.py …` or `cd src && python -m cli.period_sync_cli`.
- Never add a `vibe_ops/` alias package to "fix" imports.
- Never add PAV/IKIGAI scoring math here — the ADR-013 drift test scans this whole tree
  (see `vibe-ops/AGENTS.md`).
- Zero-byte files are placeholders, not stubs to fill casually: `embeddings/config.py`,
  `integration/obsidian_parser.py`, `parsers/code_parser.py`, `storage/vector_store.py`,
  `pipeline/code_review_sync.py`, `pipeline/study_manager.py`.
- Two `SchemaRegistry` classes exist: `pipeline/schema_registry.py` (YAML catalog + JSON-Schema
  gatekeeper) and `schemas/registry.py` (semver pydantic factory) — pick by intent, never merge.
