---
name: M43-agents-md-cleanup
description: Strip fictional paths (src/operational/, apps/, data/taskdog/) from AGENTS.md or annotate them as removed.
status: DONE
owner: loop-orchestrator
constitution_refs:
  - state_on_disk_not_conversation
  - spec_driven_not_vibe_driven
estimated_ticks: 1
---

# M43 — AGENTS.md cleanup

## Problem

AGENTS.md (41744 bytes) was 14+ commits stale at the start of this
session. It described several paths that did NOT exist at master HEAD:

- `src/operational/` — PAV kernel removed in `604d6af`; ~25 references in AGENTS.md
- `apps/` — was removed (no `apps/` directory at master HEAD; references only on unmerged `origin/gitbutler/target`)
- `data/taskdog/` — does not exist at master (the taskdog adapter returns None)
- `life-ops/operational` — pre-`src/*` reorg path

Every future coding agent reading AGENTS.md would be misled into
trying to use paths that don't exist.

## Disposition applied

**Approach:** strike-through + archive annotation, not deletion. The
historical context is preserved for audit trail (per the project's
append-only convention), but each fictional reference now carries a
visible "(REMOVED in `604d6af`)" or "(this section describes a removed
package)" banner. Future agents reading AGENTS.md will see the warning
on the first encounter and know to look at `archive/legacy-pav/`.

Sections modified:
- Top-of-file status banner (new): "Status (2026-09-15)" pointing to
  `.claude/loop/roadmap.md` as the actual source of truth
- Project Overview table row for `src/operational/`: strike-through +
  archive pointer
- `### src/operational/ — PAV kernel (uv workspace)` section: banner +
  all `cd`/`uv` commands commented out
- `### src/operational/ — uv workspace layout` section: banner +
  historical-context prose only
- "Recent Major Changes" commits referencing `src/operational/tests/`:
  strike-through + redirect to archive
- "Observability sprint" section: strike-through on the 3 `apps/*`
  unmerged branches
- LangGraph `make test` target: STALE annotation
- Testing section: `src/operational/tests/` row struck through
- Important Rules section: 3 bullets struck through
- Pitfalls section: 4 bullets struck through
- File Roles Quick Reference table: 6 rows struck through

## Acceptance

- [x] Fictional paths annotated or struck-through (no orphan live references)
- [x] Drift net preserved: 68/68 + 11/11
- [x] 1 atomic commit + push
- [x] AGENTS.md remains readable as a historical reference

## Reversibility

`git revert` restores the old content. No data loss.
