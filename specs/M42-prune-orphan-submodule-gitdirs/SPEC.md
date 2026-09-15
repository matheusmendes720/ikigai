---
name: M42-prune-orphan-submodule-gitdirs
description: Reclaim 13.7MB by removing .git/modules/{taskdog,solverforge-calendar,tuiboard}/ which have no parent gitlink on master.
status: DONE
owner: loop-orchestrator
constitution_refs:
  - state_on_disk_not_conversation
  - reversibility_over_cleverness
  - tests_are_the_contract
dependencies:
  - M41 (planning-with-files submodule unlink — established the precedent of unlinking phantom/orphan submodule state)
estimated_ticks: 1
---

# M42 — Prune orphan submodule gitdirs

## Problem

`.git/modules/` contains 3 fully-initialized gitdirs (backing stores for
git submodules) that are unreachable from any parent gitlink on master:

| Gitdir | Size | Last-modified | HEAD |
|---|---|---|---|
| `taskdog` | 7.8 MB | 2026-08-27 20:40 | `da19ce5` (packed `refs/remotes/origin/main`) |
| `solverforge-calendar` | 4.0 MB | 2026-08-27 20:40 | `49a4fee` |
| `tuiboard` | 1.9 MB | 2026-08-27 20:40 | `e4ea13f` |

These were originally registered as submodules at `interfaces/{taskdog,solverforge-calendar,tuiboard}`
(via the historical `.gitmodules` at `7fafc31c`, deleted at `248e359`).
The parent gitlinks were removed at `ec6d9cec`, but the backing stores
were never cleaned up. Today they exist as 13.7 MB of dead weight that:

1. Confuses `git worktree list` output (shows them as orphaned worktrees)
2. Inflates `du -sh .git/` measurements
3. Provides a false signal to anyone reading `.git/modules/` that these
   submodules are registered (they are not)

## Why this matters

- Index bloat: 13.7 MB on every clone
- Mental overhead: future agents seeing `.git/modules/taskdog/` will
  assume `taskdog` is a submodule and look for `.gitmodules` / gitlinks
- Reversibility preserved: if you ever want to restore these submodules,
  run `git submodule add <url> interfaces/<name>` from each recorded SHA
  in commit `7fafc31c` — git will reuse the local backing store if it
  matches, or create a fresh one.

## Acceptance

- [ ] `rm -rf .git/modules/{taskdog,solverforge-calendar,tuiboard}/`
- [ ] `du -sh .git/modules/` reports ≤0.5 MB (just `.keep` file or empty)
- [ ] Drift net preserved: 68/68 (ikigai drift) + 11/11 (test_loop_infra)
- [ ] `git submodule status` returns clean (no fatal errors)
- [ ] `git status` clean
- [ ] 1 atomic commit + push to origin

## Dependencies

- M41 — established the precedent of unlinking orphan submodule state

## Estimated ticks

1 (single atomic rm + commit + push).

## Constitution gate

- **state_on_disk_not_conversation:** the orphan state is visible only
  on disk; this SPEC + commit makes it explicit.
- **reversibility_over_cleverness:** trivially reversible via
  `git submodule add <url> <path>` from each recorded SHA.
- **tests_are_the_contract:** drift net stays green.

## Reversibility recipe (kept here for audit)

If you ever need to restore any of these submodules:

```bash
# From a fresh clone, with these SHAs from commit 7fafc31c:
git -c protocol.version=2 submodule add \
  https://github.com/matheusmendes720/taskdog.git interfaces/taskdog
git -c protocol.version=2 submodule add \
  https://github.com/matheusmendes720/solverforge-calendar.git interfaces/solverforge-calendar
git -c protocol.version=2 submodule add \
  https://github.com/matheusmendes720/tuiboard.git interfaces/tuiboard
```

The recorded SHAs (from `.git/modules/<name>/packed-refs`):
- taskdog: `da19ce5229a4dc9ce5badfd77d7a0eafe8977551`
- solverforge-calendar: `49a4feede202626798070d25c93d83cebcf1e927`
- tuiboard: `e4ea13fc476767b8df96059bc9d4892181db00c8`