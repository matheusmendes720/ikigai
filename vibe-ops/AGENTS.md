# vibe-ops — cybernetic engine (data-mesh runtime)

Python/uv subproject of Life OS: vault→SQLite ingest, vector store, contract catalog,
period reports, and a Rust TUI. Not an installable package — every entry point is a script
run with `vibe-ops/src` on `sys.path`.

## OVERVIEW
Bare-namespace Python packages under `src/`; SQLite + Chroma + filesystem only, no network
at runtime. Owns its own `uv.lock` and `.venv` (py3.13), separate from the repo-root
setuptools build and the `src/ikigai` Poetry env.

## STRUCTURE
```
vibe-ops/
├── src/           # Python packages (map in src/AGENTS.md)
├── tests/         # pytest suite + fixture vault (map in tests/AGENTS.md)
├── migrations/    # 001-005 .sql, applied idempotently
├── scripts/       # PowerShell ops loop + search_mesh.py
├── vibeops-tui/   # Rust ratatui TUI (own Cargo.lock, reads ../vibe_ops.db)
├── architecture/  # ADR-001..006 (ADR-006 = period reports schema)
├── planning/ specs/ doc/ vectors/ artifacts/ base/ context/   # requirement docs
└── contracts/     # JSON contract samples
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Entity models | `src/models/` | 42 exported names, deliberately lenient pydantic |
| Orchestration | `src/pipeline/` | 32 modules, `MVLOrchestrator` is the entry |
| Vault↔code sync | `src/middleware/` | append-only, per-layer conflict policy |
| Persistence | `src/storage/` | SQLAlchemy ORM + Chroma + a local `UEID` |
| Contract catalog | `src/contracts/` | YAML registry + `SyncContractV1` |
| Schema history | `architecture/ADR-00*.md` | ADR-006 governs period reports |
| Period-report DDL | `migrations/004_period_reports.sql` | also inlined in `src/middleware/period_sync.py` |

## CONVENTIONS
- **Not a package**: `pyproject.toml` has `[project]` but no `[build-system]` and no
  `[project.scripts]`. Do not add one — the hyphen in `vibe-ops` blocks dotted imports.
- **Top-level imports inside the tree**: `from models.period_report import PeriodReport`,
  never `from vibe_ops.models...` (the module path `vibe_ops` cannot exist).
- **Bilingual code**: pt-BR docstrings/logs next to English identifiers — match the file.
- **Ruff**: line-length 100, py311, `E501` ignored globally; `RUF002` ignored only for
  `src/pipeline/rice_exporter.py` (the `×` is intentional).
- **Mypy**: `mypy_path=["src"]`, `explicit_package_bases`, `ignore_missing_imports`.

## ANTI-PATTERNS
- **Never reintroduce PAV/IKIGAI scoring math under `src/`** — `vibe-ops/src/` is scanned
  by the ADR-013 drift test (`src/ikigai/tests/test_canonical_scope.py`): `compute_score`,
  `compute_qhe`, `IkigaiScorer`, `cybernetics.daily_loop` fail CI.
- **Never add `extra="forbid"`/`frozen=True` to `src/models/*`** — the leniency is a
  deliberate vault contract (user-added frontmatter keys must not break validation).
- **Never delete rows during a sync** — the middleware layer is append-only by contract.
- **Never `pip install -e vibe-ops`** — there is nothing to install; use `uv sync`.

## COMMANDS
```bash
cd vibe-ops && uv sync
cd vibe-ops && uv run pytest            # pytest + hypothesis, sys.path-based imports
cd vibe-ops && uv run ruff check .
cd vibe-ops && uv run mypy .
cd vibe-ops/src && python -m scripts.vault_sync status --db ../vibe_ops.db
```

## KNOWN-BROKEN (read before touching)
- `src/agents/pae_maintainer/channels.py` imports `.state`, which does not exist → the
  agent package is unimportable.
- `src/pipeline/{metadata_catalog,pipeline_state_machine,knowledge_telemetry}.py` import
  `src.storage...` / `vibe_ops.src.models...` → paths that cannot resolve here.
- `run_loop.ps1`, `scripts/vibeops_loop.ps1`, `scripts/setup_scheduler.ps1` all invoke
  `src/main.py`, which no longer exists.
- Undeclared runtime deps: `jsonschema`, `semver`, `numpy`, `sentence_transformers`,
  `sqlite_vec` (plus `alembic` for `migrations/versions/`).
