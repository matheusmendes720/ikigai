# Spec: Dissolve IKIGAI Observability Worktree Post-Merge

**Status:** Proposed
**Date:** 2026-08-27
**Owner:** IKIGAI
**Related work:** Spec 03 (merge plan), Spec 02 (smoke test)

## Goal

After the IKIGAI observability worktree (`life-mcp-observability-worktree`) is merged back to `gitbutler/workspace`, cleanly remove the worktree and prune all stale references. Leave no dangling worktrees, branches, or hooks.

## Background

The worktree was created at the start of the observability sprint to isolate OTel + reliability + schema work from the main branch. It holds 8 commits across:
- Task 3 (decorator signature fix)
- Task 4 (reliability layer + fix)
- Task 5 (stack tracing)
- Task 2 (schema reconciliation + fix)

Once merged, the worktree serves no purpose. Leaving it on disk wastes disk space and risks confusion (developers might `cd` into a stale worktree and see commits that are already on main).

## Cleanup steps

### Step 1: Confirm the merge is complete

```bash
cd "C:/Users/mathe/code_space/life-oss/life"
git log --oneline gitbutler/workspace | grep -E "(f803fb6|2b94724|87f6ef9|0e528d0|ca4e65c|0ff111d|eeac3aa|e31777f)"
```

Expected: all 8 SHAs present on `gitbutler/workspace`.

If any are missing, **stop** — re-merge before proceeding.

### Step 2: Remove the worktree

```bash
cd "C:/Users/mathe/code_space/life-oss/life"
git worktree remove "C:/Users/mathe/code_space/life-oss/life/life-ops/life-mcp-observability-worktree" --force
```

The `--force` flag is needed because the worktree likely has uncommitted noise (e.g. lock files, swap files) that survived earlier sessions.

### Step 3: Delete the worktree's branch

The worktree branch has no name (it's the worktree HEAD). After the merge, the branch is fully merged and can be deleted:

```bash
git branch -d <branch-name>    # use the name from `git worktree list`
```

If Git refuses with "not fully merged", force delete with `-D`. This is safe since we've confirmed the commits are on `gitbutler/workspace`.

### Step 4: Prune refs

```bash
git remote prune origin        # remove stale remote-tracking branches
git reflog expire --expire=now --all
git gc --prune=now             # reclaim disk space from dangling objects
```

### Step 5: Verify no remaining references

```bash
git worktree list              # should NOT include the observability worktree
git branch -a | grep -i "observ\|otel\|reliability\|stack-tracing"   # should return 0 rows
ls "C:/Users/mathe/code_space/life-oss/life/life-ops/" | grep observability   # should be empty
```

### Step 6: Verify CI green on main

```bash
gh run list --branch gitbutler/workspace --limit 5
```

Expected: most recent CI run is green.

## Acceptance criteria

1. `git worktree list` returns only the main `life/` worktree (no `life-mcp-observability-worktree`)
2. The directory `C:/Users/mathe/code_space/life-oss/life/life-ops/life-mcp-observability-worktree/` does not exist
3. All 8 commits from the worktree are reachable from `gitbutler/workspace`
4. `git status` on `gitbutler/workspace` is clean
5. CI is green on `gitbutler/workspace`

## Out of scope

- Deleting the actual code commits (they're now on main and serve as history)
- Removing related branches in other repos (tuiboard/taskdog/solverforge — handled in Spec 03)
- Removing the `.hermes/` or `0`/`1`/`10`/etc. stray files from the parent `life-ops/ikigai/` directory (these are pre-existing session clutter, not from this work)

## Risks

1. **Orphan commits** — if the merge was a squash, the original 8 commits are gone. Recovery: ensure merge-commit, not squash. Mitigation: Spec 03 mandates `--no-ff` merge.
2. **Concurrent work** — if someone else is using the worktree, `--force` will break them. Mitigation: announce cleanup in #dev-tools before removing.
3. **Local unpushed commits** — the worktree might have commits not yet pushed. Mitigation: the smoke test + merge step requires everything to be pushed first.

## Open questions

1. Should we keep a tag like `pre-observability-cleanup` before deleting, in case rollback is needed?
2. Should we archive the worktree to a tarball first (low cost, high safety)?
3. Should the IKIGAI-specific cleanup also include deleting `data/matheus/ikigai_state/projects-status-review.md` and similar ephemeral files?

## Estimated effort

~30 minutes, mostly automated.

---

*Spec generated 2026-08-27 as part of the observability follow-up work.*
