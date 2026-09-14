# loop/phase-4-vendor-taskdog — ARCHIVED

**Date archived:** 2026-09-14
**Reason:** Stale branch — `vendor/taskdog/` subtree removed during 2026-09-14 rebuild

## What this branch was

The `loop/phase-4-vendor-taskdog` branch was created during the **Phase 4
vendoring milestone** (2026-09-10). It contained:

- **865 vendored files** from upstream `Kohei-Wada/taskdog` at commit
  `2352f6120f4941528ebfcd4e1dc203ec76896292` (subtree-imported into
  `vendor/taskdog/`)
- **5 vendored packages:** `taskdog-core` (334 files), `taskdog-server` (67),
  `taskdog-client` (49), `taskdog-ui` (317), `taskdog-mcp` (23)
- An IKIGAI↌vendored taskdog integration design:
  `docs/superpowers/plans/2026-09-10-phase-4-vendor-upstream.md`
- The FORK_WORKFLOW doc (`docs/FORK_WORKFLOW.md`) describing the subtree sync
  strategy (`git subtree pull --prefix=vendor/taskdog upstream main --squash`)
- ~10 Phase 4 / system-review specs & plans in `docs/superpowers/`

### Branch metadata

- **HEAD:** `0326bc6f9a58c268bcd61b90fe2677a80afae488`
  (2026-09-10, "docs(fork): FORK_WORKFLOW.md Phase 4 status update +
  vendoring cleanup notes")
- **Key vendoring commit:** `0cfd84e4` ("Add 'vendor/taskdog/' from commit
  '2352f6120f4941528ebfcd4e1dc203ec76896292'")
- **Total diff vs master:** 1019 files changed, 108656 insertions(+),
  46847 deletions(-)
- **Branch state:** 73 commits ahead of master, 1138 commits behind
  (most "ahead" commits are upstream chore/deps + pre-commit autoupdates
  from the original Kohei-Wada/taskdog history; only 2 are branch-specific:
  the subtree import + the FORK_WORKFLOW update)
- **Local branch:** NO (remote tracking only — `origin/loop/phase-4-vendor-taskdog`)

## What happened (2026-09-14 rebuild)

Between sessions, a major rebuild occurred (per MEMORY.md "VANISH FIX +
FULL REBUILD" entries). The rebuild:

1. Restored `ikigai_serve.py`, `souls/loader.py`, and 4 mesh adapter stubs
   after subagent-hallucination commits were empty.
2. Followed `docs/superpowers/plans/2026-09-14-ikigai-rebuild-honest.md` to
   ship all 9 locked decisions.
3. **Removed the `vendor/taskdog/` subtree** in favor of the existing
   `src/mesh/adapters/taskdog.py` adapter delegation pattern (Phase 4.1.B).

This made the `loop/phase-4-vendor-taskdog` branch **STALE** — its 865
vendored files no longer exist in the codebase, and M16 wired the REPL
(`scripts/chat_repl.py`) to use the existing adapter instead of the
vendored bridge.

## Why not delete

The branch was NOT deleted because:

- It contains **historical context** (commit messages, plan files,
  FORK_WORKFLOW doc) about the Phase 4 effort.
- Force-deletion has caused prior data loss (per session memory).
- The user may want to **cherry-pick specific commits** later — e.g., the
  FORK_WORKFLOW doc or the bridge plan file if Phase 4.1.A is ever
  re-attempted with a different approach.
- Recovery is cheap if needed: `git checkout` the branch into a worktree
  and pick the relevant files.

## How to recover the work if needed

If the vendored taskdog approach is ever revisited:

```bash
# Check out the branch to a worktree (do NOT merge to master)
git worktree add .worktrees/phase-4-revival loop/phase-4-vendor-taskdog

# Inspect what was on the branch
ls .worktrees/phase-4-revival/vendor/taskdog/

# Cherry-pick specific commits if needed
git log --oneline loop/phase-4-vendor-taskdog | head -20
git cherry-pick <commit-sha>

# Clean up
git worktree remove .worktrees/phase-4-revival
```

**Note:** the branch has diverged from upstream by 1138 commits, so any
re-attempt would need to re-base or re-vendor from a newer upstream
commit than `2352f612`.

## Current state

- **Branch exists locally:** NO (only as `remotes/origin/loop/phase-4-vendor-taskdog`)
- **Branch exists on origin:** YES
- **Commits ahead of master:** 73
- **Files unique to branch (vendor/):** 865
- **Files unique to branch (non-vendor):** ~50 (mostly `.claude-flow/` state,
  `.tmp/` test fixtures, Phase 4 plans/specs in `docs/superpowers/`)
- **Recommendation:** **KEEP branch** (don't delete), just stop merging it

## Related milestones

- **M11 IKIGAI Agentic System Review** (41 gaps, 2 P0) — found 5 pre-existing
  broken tests (now deleted in M13)
- **M12 P0 Attribution Violations Fix** — closed bridge/server drift + UEID
  schema drift
- **M13 V2-Node/Bridge Alignment + Stale Test Cleanup** — deleted 5 PAV tests
  + cleaned 8 dead v2-node calls
- **M16 REPL End-to-End** — wired `scripts/chat_repl.py` to use existing
  `src/mesh/adapters/taskdog.py` (NOT the vendored bridge)
- **M18 Doc Updates** — sibling archive notes (this is one of them)
- **M19 Stale Branch Cleanup** — this archive note + branch kept-not-deleted
  policy decision

---

*Archived 2026-09-14 during the post-rebuild sweep. Branch intentionally
preserved for historical reference and selective cherry-pick access.*