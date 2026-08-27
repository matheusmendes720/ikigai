# Spec: Merge Plan for 4 OTel Branches

**Status:** Proposed
**Date:** 2026-08-27
**Owner:** IKIGAI

## Goal

Merge the 4 OTel feature branches back to their respective default branches, in dependency order. No merge should land until the smoke test (Spec 02) passes against the merge candidate.

## Branches in scope

| Repo | Branch | Default | Commits to merge |
|---|---|---|---|
| `apps/kanban/tuiboard` | `feat/otel-tracing` | `main` | `590ea60`, `2c39867` |
| `apps/dev-tools/taskdog` | `feat/otel-tracing` | `main` | `5a8b1bb2`, `600c92b9` |
| `apps/calendar/solverforge-calendar` | `feat/otel-tracing` | `main` | `cfbf12b`, `064b8c9` |
| `apps/calendar/solverforge-calendar` | `feat/rust-build-fix` | `main` | `1716b16` |
| `life-oss/life` (IKIGAI) | `life-mcp-observability-worktree` (worktree) | `gitbutler/workspace` | `f803fb6`, `2b94724`, `87f6ef9`, `0e528d0`, `ca4e65c`, `0ff111d`, `eeac3aa`, `e31777f` |

## Dependency order

**solverforge first** — Task 6's build fix (`1716b16`) is the foundation. Without it, the OTel build won't link. Merge `feat/rust-build-fix` to `main` first, then rebase `feat/otel-tracing` on the new main before merging.

**Then in parallel** (no cross-deps):
- tuiboard `feat/otel-tracing` → main
- taskdog `feat/otel-tracing` → main
- solverforge `feat/otel-tracing` → main (rebased on the build-fix merge)
- IKIGAI observability worktree → `gitbutler/workspace`

## Pre-merge checklist (per branch)

1. ✅ Branch is up-to-date with target (rebase if behind)
2. ✅ Smoke test (Spec 02) passes against the branch
3. ✅ CI green (each repo's existing CI workflow)
4. ✅ PR description references the related spec (`docs/observability/0X-*.md`)
5. ✅ Reviewer approval recorded (each branch already has task-level reviews)

## Merge procedure

### Step 1: solverforge build-fix

```bash
cd "C:/Users/mathe/code_space/apps/calendar/solverforge-calendar"
git checkout main
git pull --ff-only
git merge --no-ff feat/rust-build-fix -m "merge: solverforge build fix (adds http feature)"
git push origin main
```

### Step 2: solverforge OTel (rebase first)

```bash
cd "C:/Users/mathe/code_space/apps/calendar/solverforge-calendar-otel-worktree"
git fetch origin
git rebase origin/main    # rebases onto the build-fix merge
# resolve any conflicts (likely none, since the build-fix only touched Cargo.toml [features])
git push --force-with-lease origin feat/otel-tracing
# open PR via gh CLI; merge via squash
```

### Step 3: tuiboard + taskdog OTel (parallel)

```bash
# tuiboard
cd "C:/Users/mathe/code_space/apps/kanban/tuiboard-otel-worktree"
gh pr create --base main --head feat/otel-tracing --title "feat(observability): dual OTLP/HTTP exporters (LangSmith + Langfuse)"
# squash-merge after CI green + approval

# taskdog
cd "C:/Users/mathe/code_space/apps/dev-tools/taskdog-otel-worktree"
gh pr create --base main --head feat/otel-tracing --title "feat(observability): dual OTLP/HTTP exporters (LangSmith + Langfuse)"
# squash-merge after CI green + approval
```

### Step 4: IKIGAI observability worktree

The IKIGAI worktree (`life-mcp-observability-worktree`) is on `gitbutler/workspace` (or a branch off it). Two options:

**Option A — branch + PR (preferred for audit trail):**
```bash
cd "C:/Users/mathe/code_space/life-oss/life"
git checkout gitbutler/workspace
git branch feat/mcp-observability life-mcp-observability-worktree   # convert worktree branch to local branch
git checkout -b feat/mcp-observability
gh pr create --base gitbutler/workspace --head feat/mcp-observability --title "feat(observability): IKIGAI MCP stack tracing + reliability layer + schema reconciliation"
```

**Option B — direct merge (faster but no audit trail):**
```bash
cd "C:/Users/mathe/code_space/life-oss/life"
git checkout gitbutler/workspace
git merge --no-ff life-mcp-observability-worktree -m "merge: IKIGAI observability work"
```

## Post-merge verification

After all 4 merges:
1. Re-run the smoke test against `main` branches
2. Verify CI is green on each main
3. Confirm `OTEL_ENABLED=false` still works (no overhead regression)

## Rollback plan

If post-merge smoke fails:
1. **Fast rollback**: `git revert -m 1 <merge-sha> && git push` (preserves history)
2. **Hard rollback**: revert the merge commit + delete the merged branch
3. For IKIGAI: `git reset --hard HEAD~N` where N = number of merge commits

## Out of scope

- Tagging releases (separate decision)
- Updating CHANGELOG (separate task per repo's policy)
- Notifying consumers of the MCP servers (separate comms task)

## Risks

1. **solverforge rebase conflicts** — if `feat/otel-tracing` has changes that overlap with the build-fix branch, rebase fails. Mitigation: build-fix only touches `[features]` section; OTel work added new files (`src/observability.rs`) and modified `Cargo.toml` deps — minimal conflict surface.
2. **CI divergence** — each repo may have different CI gates. Mitigation: each PR must pass its own CI before merge.
3. **Mid-merge API key exposure** — if smoke test fails mid-merge, partial state is exposed. Mitigation: use `--no-ff` for merge commits so each merge is atomic and revertable.

## Open questions

1. Should we squash-merge or merge-commit each branch? (Squash = clean history; merge-commit = preserves per-commit history)
2. Should IKIGAI use Option A (PR) or Option B (direct merge)?
3. Should we batch-merge via a release branch that depends on all 4 merges, then tag?

## Estimated effort

~1 day (assuming no CI flakes), ~3 days if rebases need attention.

---

*Spec generated 2026-08-27 as part of the observability follow-up work.*
