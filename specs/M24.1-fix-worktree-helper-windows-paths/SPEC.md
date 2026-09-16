---
name: M24.1-fix-worktree-helper-windows-paths
description: Apply M54 cygpath -m pattern to scripts/worktree-helper.sh + tests so `git -C` works on Windows Git Bash.
status: DONE
owner: loop-orchestrator
constitution_refs:
  - correctness_over_speed
  - reversibility_over_cleverness
estimated_ticks: 1
---

# M24.1 — Fix worktree-helper.sh Windows path handling

## Problem (M24 closeout documented, 2026-09-16T01:00Z)

`scripts/worktree-helper.sh` had `git -C "$PROJECT_ROOT"` calls where
`$PROJECT_ROOT` is a Cygwin mount path (`/c/Users/...`). On Windows + Git
Bash, `git -C /c/Users/...` fails with:

```
fatal: cannot change to '/c/Users/mathe/code_space/life-oss/life':
No such file or directory
```

…even though bash sees the path fine. This caused
`tests/test_worktree_helper.sh` (15/15 tests) to fail at the
pre-cleanup step (the script's `git worktree remove --force` calls
couldn't find the git repo).

## Fix (same pattern as M54)

Both `scripts/worktree-helper.sh` and `tests/test_worktree_helper.sh`:

1. After computing `PROJECT_ROOT="$(cd ... && pwd)"` (which bash sees as
   `/c/Users/.../life`), add:
   ```bash
   PROJECT_ROOT_WIN="$(cygpath -m "$PROJECT_ROOT" 2>/dev/null || echo "$PROJECT_ROOT")"
   ```
   This translates `/c/Users/...` → `C:/Users/...`. Falls back to
   `$PROJECT_ROOT` on Linux/macOS where cygpath isn't installed.

2. Replace all `git -C "$PROJECT_ROOT"` calls with
   `git -C "$PROJECT_ROOT_WIN"` (11 in helper + 5 in test).

3. In the helper's `create` and `cleanup` blocks, also translate
   `$WT_PATH` to `$WT_PATH_WIN` because `git worktree add` /
   `git worktree remove` need Windows paths when `git -C` is using
   one.

## Acceptance

- [x] `bash tests/test_worktree_helper.sh` 15/15 PASS (T-24.1.1)
- [x] Drift net preserved: 69/69 PASS (ikigai) + 11/11 PASS (loop_infra) (T-24.1.2)
- [x] Pattern matches M54 (daemon-watchdog.sh) — same cygpath -m translation
      approach, so future scripts can adopt the pattern via reference (T-24.1.3)
- [x] 1 atomic commit + push to origin master (T-24.1.4)

## What did NOT need fixing

- `$WORKTREE_BASE` is used by `mkdir -p` and `[ -d ... ]` checks, both
  of which bash handles natively with Cygwin paths. Only `git -C` and
  `git worktree {add,remove}` need Windows paths.
- `git worktree list --porcelain` output is consumed by the script for
  the `cleanup-all` path; those paths are returned by git already in
  Windows format when invoked from `git -C "$PROJECT_ROOT_WIN"`, so no
  extra translation needed.

## Reversibility

`git revert HEAD`. Two files changed (script + test), one-line addition
+ sed-style replacements.

## Why M6 ship-time review missed this

M6 ship-time (commit `fcb0d9e0`) included `test_worktree_helper.sh` as
part of the M6 deliverable. The author presumably ran the test on POSIX
or in an environment where `git -C` accepted Cygwin paths — but on
this Windows + Git Bash setup (the user's actual development host),
the test has been silently failing since M6 ship date (2026-09-08).
