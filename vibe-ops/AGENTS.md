# vibe-ops — Cybernetic Engine

## OVERVIEW
Cybernetic engine (Target → Sensor → Adjuster) of the Algorithmic Life OS: a
Python data mesh over SQLite + ChromaDB plus a Markdown knowledge base of
specs, ADRs and concept sources. Own build tooling (`uv`), own import root,
own data files. The Rust TUI (`vibeops-tui/`) was removed with the PC-only
scope (ADR-037) and is not published.

## STRUCTURE
```
vibe-ops/
├── src/              # Python package (own AGENTS.md) — `src` is the import root
├── tests/            # pytest suite (own AGENTS.md)
├── migrations/       # idempotent SQL 001…005
├── contracts/        # JSON Schema (draft-07) entity contracts
├── schema_registry/  # semver registry.yaml
├── scripts/          # search_mesh.py + Windows .ps1 ops
├── specs/            # Specs-First contracts (own AGENTS.md)
├── planning/         # PRD board + period templates (own AGENTS.md)
├── architecture/     # ADR-001…006 + README reading order
├── base/             # canonical concept sources (PT-BR)
└── context/ doc/ vectors/ artifacts/   # MOCs, strategy docs, IKIGAI vectors
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Policy FSM (the Adjuster) | `src/pipeline/policy_engine.py` | PUSH/MAINTAIN/REDUCE/RECOVER + hysteresis |
| Markdown → entity ingestion | `src/pipeline/mvl_orchestrator.py` | validate-then-persist master orchestrator |
| Vault ⇄ SQLite sync | `src/middleware/bidirectional_sync.py` | D3: vault wins manual fields, code wins computed |
| Period-report sync | `src/middleware/period_sync.py` | contract lives in `planning/_templates_periodos_v2/` |
| DB DDL | `src/storage/schema.sql` | 18 tables + view `v_epistemic_priority` |
| Entity models | `src/models/` | 42 names in `__all__` |
| CLI entry point | `src/vibe_cli.py` | `hybrid_search` — the only published script here |
| Windows ops | `scripts/*.ps1`, `task.bat` | `run_loop.ps1` calls a missing `src/main.py` |
| Canonical concept | `base/IKIGAi.md` | ADR-003 "single source of truth" |
| Architecture decisions | `architecture/README.md` | read order ADR-001 → 002 → 003 |

## CODE MAP
| Symbol | Type | Location | Refs | Role |
|---|---|---|---|---|
| `PolicyEngine` | class | `src/pipeline/policy_engine.py` | 175 files | severity → policy state |
| `PolicyState` | enum | `src/schemas/pydantic_v2.py` | 108 files | DB payload contract; `str, Enum` on purpose |
| `FrontmatterParser` | class | `src/pipeline/frontmatter_parser.py` | 30 files | 24-type `MODEL_MAP`, frontmatter → Pydantic |
| `PeriodReport` | model | `src/models/period_report.py` | 44 files | ADR-006 period-report contract |
| `BidirectionalSync` | class | `src/middleware/bidirectional_sync.py` | 30 files | D3 conflict resolution |
| `DataMeshAdapter` | class | `src/storage/data_mesh_adapter.py` | 25 files | shared handle for 8 pipeline modules |

## CONVENTIONS
- **Two toolchains in one subtree**: Python `uv` and PowerShell. Never mix them.
- **Flat import root**: `vibe-ops/src` on `sys.path`; siblings import as `pipeline.x`,
  `models.x`, `storage.x` — not the repo-root `src.contracts` dotted style.
- **Pydantic here is permissive** (`extra="allow"`, not `frozen`) — the opposite of
  the repo-wide `src/contracts/` rule. Do not "fix" it.
- **Idempotency key is `upstream_id`**: 12-char truncated SHA-256; every write is
  `ON CONFLICT … DO UPDATE`.
- **`str, Enum` is deliberate** — the value is serialised straight into DB rows.
- **Docs are PT-BR; identifiers, code and comments are English.**

## ANTI-PATTERNS (THIS PROJECT)
- **Never delete content.** `SPEC.md` + `.cursor/rules/append-only.mdc` make this
  subtree strictly append-only and require a stop → plan → approval gate before
  any restructuring.
- **No LLM in the pipeline** — daily/weekly pipelines are pure arithmetic.
- **Never hand-type metadata**; every enrichment is computed.
- **Scoring is not the sync layer's job** — RICE lives only in `pipeline/rice_exporter.py`.
- **Never re-define the repo `UEID`/`Task` contracts** from `src/contracts/`.
- **No cloud dependency** — SQLite + ChromaDB + filesystem only.

## NOTES
- `src/agents/pae_maintainer/channels.py` imports `.state`, which does not exist —
  that package is unimportable as written.
- `requirements.txt` (6 unpinned deps) duplicates `pyproject.toml`; prefer `uv.lock`.
- Committed `.pyc` for CPython 3.11/3.12/3.13 and `__pycache__` variants inside
  `src/pipeline/` are build junk, not source.
