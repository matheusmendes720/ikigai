# DEPRECATED — This is a Deployment Snapshot

> **⚠️ DO NOT EDIT FILES IN THIS DIRECTORY. ⚠️**
>
> This is a **deployment snapshot** of the root `life/` workspace.
> All canonical files live at `C:\Users\mathe\code_space\life-oss\life\`.
>
> Any change you make here will be **LOST** on the next snapshot sync.

---

## What This Is

- **Snapshot date:** 2026-05-05 (last full snapshot)
- **Snapshot is OUTDATED** — root has 30+ files NOT in this snapshot
- **Missing from snapshot:**
  - `CONCEPTUAL_MODEL.md`, `SYSTEMS_TOPOLOGY.md`, `ARCHITECTURE_INDEX.md` (new architecture docs)
  - 3 `CLUSTER_*.md` Standalone Memory Machines (~3800 lines combined)
  - `vibe-ops/architecture/ADR-003, 004, 005` (5 ADRs total)
  - `vibe-ops/planning/CLUSTER_PLAN_*.md` (6 drilldowns)
  - `life-ops/planner/ikigai_planning/` (5 IKIGAi planning docs)
  - `vibe-ops/doc/03-data-mesh-enrichment.md` (27K, canonical enrichment)
  - Multiple diagrams in `diagrams/`

## What To Do Instead

| If you want to edit... | Edit at... |
|---|---|
| Planning (strategy, IKIGAi) | `life/strategics/`, `life/life-ops/planner/`, `life/vibe-ops/base/`, `life/vibe-ops/vectors/` |
| Specs (PRDs, ADRs, schemas) | `life/vibe-ops/{planning,specs,architecture,doc}/` |
| Code (CLI, centrals, handlers) | `life/{cli,centrals,handlers,plugins}/` and `life/vibe-ops/src/` |
| Standalone Python submodule | `life/life-ops/life_tatics/` |
| Data (DB schema, contracts) | `life/vibe-ops/src/storage/schema.sql` (canonical) |
| Documentation navigation | `life/docs/` and `life/ARCHITECTURE_INDEX.md` |
| Taskwarrior config | `life/taskwarrior/` (not this directory's `taskwarrior/`) |

## Why This Snapshot Exists

Historical context only. Some tooling (deployment scripts, IDE workspace
backups) still reference this path. The plan is to **deprecate completely**
by end of 2026-Q3 and remove this directory entirely.

Until then, this snapshot is kept read-only for:

- **Backward compatibility** with older deployment scripts
- **Historical reference** of what the workspace looked like on 2026-05-05
- **Recovery** if the root is somehow corrupted (use as last-resort fallback)

## See Also

- [`life/AGENTS.md`](../AGENTS.md) §6.4 (Known Issues — snapshot deprecation)
- [`life/CLAUDE.md`](../CLAUDE.md) §Project Overview (snapshot explanation)
- [`life/ARCHITECTURE_INDEX.md`](../ARCHITECTURE_INDEX.md) (canonical architecture map)
- [`life/time-tasker/DEPRECATED-SNAPSHOT.md`](../time-tasker/DEPRECATED-SNAPSHOT.md) (this file, mirrored at the snapshot root)

---

*⚠️ This file is a deprecation notice. It is the only file in this snapshot that should be edited when needed. ⚠️*
