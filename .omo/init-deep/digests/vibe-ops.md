# DIGEST — vibe-ops subtree

## AGENTS_LOCATIONS (written)

| Path | Score | One-line role |
|---|---|---|
| `vibe-ops/AGENTS.md` | 15 | Subtree root: cybernetic engine (Python mesh + Rust TUI + Markdown knowledge base), 3 toolchains |
| `vibe-ops/src/AGENTS.md` | 16 | Python package: 12 sibling layers under a flat import root (`vibe-ops/src` on `sys.path`) |
| `vibe-ops/src/pipeline/AGENTS.md` | 14 | The engine kernel: 32 modules, ingest→validate→enrich→index→sink, `__all__` = 14 names |
| `vibe-ops/tests/AGENTS.md` | 12 | Self-bootstrapping pytest suite (23 modules + integration/e2e/property sub-suites) |
| `vibe-ops/specs/AGENTS.md` | 10 | Specs-First declarative contracts (Pydantic v2 schemas, frontmatter contract, planner extension) |
| `vibe-ops/planning/AGENTS.md` | 13 | Requirements board: PRD-01…07, Cluster-PLAN drilldowns, period-report templates |

Directories scored but **skipped** (parent covers): `base/` (3), `architecture/` (3),
`context/` (3), `doc/` (3), `vectors/` (3), `artifacts/` (2), `migrations/` (2),
`contracts/` (2), `schema_registry/` (2), `scripts/` (4), `vibeops-tui/` (4 — own
Rust crate, covered in the subtree root), `src/models/` (11), `src/storage/` (9),
`src/middleware/` (7), `src/schemas|contracts|cli|scripts|cybernetics|agents|
embeddings|integration|parsers/` (<8).

## CROSS-SUBTREE FACTS THE ROOT FILE MUST KNOW

1. **vibe-ops is a separate import root, not part of the repo `src/` tree.**
   Siblings import flat (`from pipeline.x import Y`, `from models.x import Z`,
   `from storage.x import W`) because `vibe-ops/src` goes on `sys.path`. The repo
   rule "`from src.contracts.X` vs `from sys_ikigai.X`" does **not** apply here.
   There is also a `vibe-ops/src/contracts/` that collides by name with the repo's
   canonical `src/contracts/`.
2. **UEID drift — real, inside vibe-ops.** `vibe-ops/src/storage/ueid.py` builds a
   **3-part** `<CLUSTER>:<ENTITY_TYPE>:<ID>` id, and
   `vibe-ops/specs/SPEC-05-cybernetic-epistemic-mesh.md` §4 declares the same
   3-part form. The canonical UEID (ADR-014, 4-part, drift-test-guarded) is
   `src/contracts/common.py`. The root rule "never re-define `UEID`" is violated
   here; the root file should say so explicitly.
3. **Pydantic strictness is inverted in vibe-ops.** `vibe-ops/src/models/` and
   `vibe-ops/src/schemas/` are permissive (`extra="allow"`, mutable) — the
   opposite of the repo-wide `frozen=True, extra="forbid"` rule for `src/contracts/`.
   This is deliberate (see `period_report.py`: "Lenient mode … so user-added fields
   don't break validation"), not a bug to fix.
4. **vibe-ops has a stricter append-only rule than the repo.** `vibe-ops/SPEC.md`
   and `vibe-ops/.cursor/rules/append-only.mdc` forbid deleting anything and
   require a **stop → action plan → user approval** gate before restructuring any
   file under `vibe-ops/`. This applies to markdown, not just code.
5. **Three toolchains live under `vibe-ops/`**: the Python package (uv, own
   `uv.lock`), a Rust `ratatui` crate (`vibe-ops/vibeops-tui/`, own `Cargo.toml`,
   reads a hardcoded `../vibe_ops.db`), and Windows PowerShell ops scripts.
   The root "Tooling split" table should list the Rust crate too.
6. **`PolicyState` / `PolicyDecision` in `vibe-ops/src/schemas/pydantic_v2.py` is
   a shared payload contract** between the Python engine and the Rust TUI's SQL.
   Changing it breaks both sides.
7. **Spec-level drift worth flagging**: `WaveEntity`, `CycleEntity`, `PhaseEntity`
   and `HabitEntity` are each declared **twice** — in
   `vibe-ops/specs/schema-pydantic-models-v2.md` and in
   `vibe-ops/specs/schema-planner-extension.md` — with near-disjoint fields.
8. **Broken wiring to be aware of** (do not treat as working code):
   `vibe-ops/src/agents/pae_maintainer/channels.py` imports a `.state` module that
   does not exist; `vibe-ops/run_loop.ps1`, `scripts/vibeops_loop.ps1` and
   `scripts/setup_scheduler.ps1` invoke a non-existent `vibe-ops/src/main.py`;
   `vibe-ops/src/pipeline/tw_sync_adapter.py` is a stub (`full_pull` returns `[]`);
   `code_review_sync.py`, `study_manager.py`, `embeddings/config.py`,
   `integration/obsidian_parser.py` and `parsers/code_parser.py` are 0 bytes;
   committed `.pyc` files for CPython 3.11/3.12/3.13 sit inside `src/pipeline/`,
   `tests/property/` and `tests/e2e/`.
9. **Scoring is not the sync layer's job.** RICE lives only in
   `vibe-ops/src/pipeline/rice_exporter.py`;
   `vibe-ops/src/middleware/bidirectional_sync.py` `_build_computed_fields`
   raises `NotImplementedError` on purpose.
