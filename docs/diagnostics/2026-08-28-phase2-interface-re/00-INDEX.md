# Phase 2 Interface Reverse-Engineering — INDEX

**Date:** 2026-08-28
**Scope:** Reverse-engineer 5 interface surfaces (3 forks + 2 native interfaces) and synthesize mesh readiness against Phase 1's 10 Open Questions.
**Mode:** RE + synthesis. No patches, no design proposals.
**Phase 1 baseline:** `docs/diagnostics/2026-08-28-phase1-audit/00-INDEX.md`

---

## File map

| # | File | LOC | Contents |
|---|------|-----|----------|
| 1 | `01-fork-tuiboard.md` | 332 | tuiboard fork — Bun + SolidJS + OpenTUI TUI; 5 `board_*` MCP tools; markdown round-trip; optimistic concurrency |
| 2 | `02-fork-taskdog.md` | 497 | taskdog fork — 5-package Python uv workspace; 26 MCP tools; SQLAlchemy + Alembic; Pydantic + dataclass hybrid |
| 3 | `03-fork-solverforge-calendar.md` | 418 | solverforge-calendar fork — Rust 2021 + rmcp; 30 MCP tools; dual DB (calendar.db + unified_planning.db); Google OAuth |
| 4 | `04-interfaces-cli.md` | 197 | Native Typer CLI (v0.1.0) — single-file `read_tasks.py`; broken `[project.scripts]` entry-point; producer-consumer gap |
| 5 | `05-interfaces-tui.md` | 165 | Native TUI scaffold (PLANNED) — 44-line README only; zero source code; 10 gaps (4 P0) |
| 6 | `06-synthesis-mesh-readiness.md` | ~340 | Cross-fork matrix, tool collision analysis, shared data shapes, OQ readiness, mesh-vs-federation trade-offs |
| 7 | `00-INDEX.md` | this | Index |

**Total:** ~2,100 LOC across 7 files.

---

## Headline findings (1 line each)

- **Zero prefix collisions across forks today** — `board_`, `taskdog_*`, `calendars_/events_/projects_/dependencies_/google_/upi_` are disjoint; mesh is route-safe at the prefix layer (`06-synthesis §Tool collision analysis`).
- **20 of 26 taskdog MCP tools unreachable via gateway** — prefix list omits lifecycle/query/decomposition/tags/audit/optimization (`02-fork-taskdog.md:244-253`); `archive_task` is a dead entry, `taskdog_*` prefix matches no tool.
- **All forks use stdio MCP transport today** — solverforge-calendar's HTTP+SSE is compile-dead (`http` feature not in `Cargo.toml`, `03-fork-solverforge-calendar.md:199`); OQ-8 reduces to "keep decoupled (Option A)".
- **`data/tasks.jsonl` MISSING** — 3 writers never invoked (`04-interfaces-cli.md:140-142`); confirms Phase 1 B-04; CLI/TUI render zero rows on first launch.
- **Each fork declares its own storage root** — tuiboard filesystem, taskdog `~/.local/share/taskdog/`, solverforge-calendar `$SOLVERFORGE_DATA_DIR/solverforge/`, interfaces/cli `life/data/`; OQ-1 needs Option C (declared registry).
- **solverforge-calendar UPI is the only fork designed as a superset** — `unified_planning_items` already has status + time_block + ikigai + provenance + blocked_by + tags JSON (`03-fork-solverforge-calendar.md:90`); natural mesh substrate.
- **UEID exists only in life** — taskdog uses int id, solverforge-calendar uses UUID v4, tuiboard uses position-based; OQ-7 forced to Option C (add `mesh_ueid` join field).
- **interfaces/tui is README-only** — 0 source code, 0 deps, 0 entry-points, 10 gaps (4 P0) (`05-interfaces-tui.md:33-44`); cannot start until Step 0+2+3+6 land.
- **4 known solverforge-calendar mesh blockers** — `google_sync` stub, HTTP+SSE feature-gated, `google-calendar3 7.0` unused dep, `recurrence_exceptions` dead schema (`03-fork-solverforge-calendar.md:397-401`).
- **Phase 3 readiness: 6 of 10 OQs have new fork evidence** — OQ-1, OQ-2, OQ-5, OQ-7, OQ-8, OQ-10 resolvable; OQ-3, OQ-4, OQ-6, OQ-9 unchanged.

---

## Cross-references

### Phase 1 audit
- `docs/diagnostics/2026-08-28-phase1-audit/00-INDEX.md` — entry point
- `docs/diagnostics/2026-08-28-phase1-audit/01-verified.md` — 8 verified items (B-01 gateways.yaml STALE, B-04 tasks.jsonl MISSING, B-07 PolicyEngine misidentification)
- `docs/diagnostics/2026-08-28-phase1-audit/02-critic-gaps.md` — 10 NEW gaps (P0×4, P1×4, P2×2) including CLI architectural lie (#4) and contracts drift (#7)
- `docs/diagnostics/2026-08-28-phase1-audit/03-priority-matrix.md` — PR-1 through PR-5 ranking
- `docs/diagnostics/2026-08-28-phase1-audit/04-sequencing.md` — 8-step sequencing (Step 0..Step 8)
- `docs/diagnostics/2026-08-28-phase1-audit/05-open-questions.md` — OQ-1..OQ-10 carried into Phase 3

### Phase 2 sister docs
- `06-synthesis-mesh-readiness.md` — synthesis (this index's companion)
- `01-fork-tuiboard.md` through `05-interfaces-tui.md` — individual RE reports

### Memory references
- `[[interfaces-architecture-2026-08-27]]` — dual-layer (forks = user views, native = operator control plane)
- `[[windows-orphan-dir-delete]]` — apps/{kanban,dev-tools,calendar} cleared 2026-08-28
- `[[orchestration-clone-playground]]` — forks are vendored MIT/Apache
- `[[ag3-gateway-orphan-2026-08-27]]` — gateway unmerged (OQ-10)
- `[[data-first-methodology]]` — SONHO 1/5; data-first gate (OQ-4)

### Pitfalls (critical)
- `gateways.yaml:4,9,14` cwd paths reference DELETED dirs (B-01)
- 20/26 taskdog tools unreachable via gateway prefix list
- `data/tasks.jsonl` MISSING (3 writers never invoked)
- solverforge-calendar HTTP+SSE compile-dead (`http` feature not declared)
- interfaces/tui has no source code (README only)
