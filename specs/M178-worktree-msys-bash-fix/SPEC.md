---
name: M178-worktree-msys-bash-fix
description: Paperclip worktree_create_node — fix MSYS bash path mangling via cygpath -u. Unblocks LIVE RUN on Windows.
status: DONE
owner: matheus-mendes
created: 2026-10-12
constitution_refs:
  - tests_are_the_contract
  - state_on_disk_not_conversation
  - composition_over_inheritance
estimated_cost_usd: 0.00
---

# M178 — Paperclip Worktree MSYS Bash Path Fix

**Status:** DONE
**Date:** 2026-10-12
**Author:** matheus-mendes (with Claude Code assist)

---

## TL;DR

When `paperclip run --spec ...` was invoked on Windows (non-dry-run),
`worktree_create_node` failed with:

```
WorktreeCreateError: /bin/bash: C:Usersmathecode_spacelife-osslifescriptsworktree-helper.sh: No such file or directory
```

Root cause: MSYS bash received the Windows-style absolute path
`C:\Users\mathe\code_space\life-oss\life\scripts\worktree-helper.sh`
and mangled it — backslashes were stripped, the drive-letter colon
collided with MSYS path syntax, and the resulting string was
unresolvable.

M178 fixes this by translating Windows paths to POSIX via
`cygpath -u` before handing them to bash. The conversion is gated on
`sys.platform == "win32"` AND `shutil.which("cygpath")` so
Linux/macOS users are completely unaffected, and Windows boxes
without Git for Windows degrade gracefully (fall back to
`str(path)`) rather than crashing. 3 new unit tests + 1 new drift
test. Drift net 74 → 75 (+1 invariant).

---

## Problem in detail

The Paperclip graph's `worktree_create_node` (and `worktree_cleanup_node`)
shells out to `scripts/worktree-helper.sh` like:

```python
proc = _run(["bash", str(helper), "create", task_id], cwd=repo_root, timeout=30)
```

where `helper = repo_root / "scripts" / "worktree-helper.sh"` and
`repo_root` is computed by walking up until `.git` is found.

On Windows, `repo_root` resolves to something like:

```
C:\Users\mathe\code_space\life-oss\life
```

so `str(helper)` is:

```
C:\Users\mathe\code_space\life-oss\life\scripts\worktree-helper.sh
```

MSYS bash (Git for Windows) interprets backslashes as escape
characters and the drive-letter colon as path-syntax collision. The
resulting mangled path doesn't exist anywhere on disk — bash reports
"no such file or directory" with the colon-stripped form. The M24.1
fix in `scripts/worktree-helper.sh` already handles the
**reverse** direction (`cygpath -m` to translate Cygwin paths back
to Windows for `git -C`), but Python was handing bash a Windows
path in the first place — the very translation M24.1 works around.

---

## What changed

```
src/ikigai/src/agents/paperclip/nodes/worktree.py    # +_to_posix_path helper, 2 call sites wired
src/ikigai/src/agents/paperclip/tests/test_worktree_path.py   # NEW (3 tests)
src/ikigai/tests/test_paperclip_drift.py             # +1 drift invariant
.claude/loop/roadmap.md                              # +M178 entry
specs/M178-worktree-msys-bash-fix/SPEC.md            # this file
```

**Total: 1 new test file + 2 modified source files + 1 modified
test file. Drift net 74 → 75.**

The two graph-node call sites that needed the fix:

```python
# worktree_create_node (line ~81)
proc = _run(["bash", _to_posix_path(helper), "create", task_id], cwd=repo_root, timeout=30)

# worktree_cleanup_node (line ~213)
proc = _run(["bash", _to_posix_path(helper), "cleanup", task_id], cwd=repo_root, timeout=30)
```

Other `_run` calls in `worktree.py` invoke `git` directly (not
`bash`), so they don't need the translation — `git` on Windows
handles both path styles natively.

---

## Architecture decisions

### D16 — `_to_posix_path` is gated on BOTH platform AND cygpath availability

The helper checks `sys.platform != "win32"` first (early return with
`str(path)`) so Linux/macOS users pay zero cost. Then on Windows it
checks `shutil.which("cygpath")` so a Windows box without Git for
Windows (e.g. WSL-only setup, pure Windows cmd environment) falls
back to `str(path)` rather than crashing. The fallback IS the same
path the original buggy code used, so failure mode is unchanged for
non-Git-for-Windows users — just no improvement. A user with Git for
Windows installed (the vast majority on this project) gets the fix.

### D17 — Wrap `subprocess.run` in `try/except`, log fallback

The helper catches both `subprocess.SubprocessError` (any
`subprocess`-family exception) and `OSError` (file-not-found, etc.)
and logs a WARNING before falling back. This way:

* An unexpected subprocess hiccup never crashes the worktree
  node — it falls through to the existing
  `WorktreeCreateError` reporting path.
* The log line lets post-mortem debugging see WHY the fallback
  happened (e.g. cygpath timed out, cygpath not in PATH, etc.).

### D18 — `cygpath -u` is the correct direction flag

`cygpath -u` converts to **unix (POSIX) path** form — exactly what
bash on Windows wants. The existing M24.1 fix uses
`cygpath -m` (mixed/Windows native form) for the **reverse** call
inside the bash script itself. Together they form a complete
round-trip: Python (Windows) → bash (POSIX) → script logic
(unix form) → `cygpath -m` → git (Windows form).

### D19 — Helper is private (`_to_posix_path`), not in `__all__`

The helper is intentionally module-private — it's an
implementation detail of how `worktree.py` talks to bash on
Windows, not a public utility. Tests access it via direct import
(`from src.ikigai.src.agents.paperclip.nodes.worktree import
_to_posix_path`) which is fine for the test-file in the same
package. No other module should depend on it; if a second paperclip
node ever needs the same translation, the helper should move to a
shared `windows_path.py` utility module — that's a future refactor.

---

## Verification

```bash
# 1. New path tests — must show 3/3 PASS
python -m pytest src/ikigai/src/agents/paperclip/tests/test_worktree_path.py -v

# 2. Full paperclip suite + drift — 58 PASS (was 49 + 3 new + 1 new drift + 5 more from concurrent M183)
python -m pytest src/ikigai/src/agents/paperclip/tests/ src/ikigai/tests/test_paperclip_drift.py

# 3. Drift net — 75 passed, 2 skipped (was 74 + 1 new M178; M183 added 1 too — see concurrent-work note)
python -m pytest src/ikigai/tests/test_drift_invariants.py \
                  src/ikigai/tests/test_drift_extended_invariants.py \
                  src/ikigai/tests/test_canonical_scope.py \
                  src/ikigai/tests/test_paperclip_drift.py

# 4. Lint + format on M178 files
python -m ruff check src/ikigai/src/agents/paperclip/tests/test_worktree_path.py \
                    src/ikigai/tests/test_paperclip_drift.py \
                    src/ikigai/src/agents/paperclip/nodes/worktree.py
python -m ruff format --check src/ikigai/src/agents/paperclip/tests/test_worktree_path.py \
                              src/ikigai/tests/test_paperclip_drift.py \
                              src/ikigai/src/agents/paperclip/nodes/worktree.py
```

> **Concurrent-work note:** while M178 was being authored, the
> parallel `M183 paperclip state persistence` workflow added
> `persistence.py` + `cli.py` + their tests, plus 1 drift invariant.
> The drift total above (75) reflects BOTH M178 (+1) and M183 (+1).
> The `cli.py` / `persistence.py` ruff errors are pre-existing from
> M183 — not introduced by M178. M178's own files are
> ruff-clean.

---

## Acceptance

- [x] `_to_posix_path(Path) -> str` helper exists in
      `src/ikigai/src/agents/paperclip/nodes/worktree.py`
- [x] `worktree_create_node` calls `_to_posix_path(helper)` instead
      of `str(helper)`
- [x] `worktree_cleanup_node` calls `_to_posix_path(helper)` instead
      of `str(helper)`
- [x] Helper is gated on `sys.platform == "win32"` (Linux/macOS
      passthrough preserves original behavior)
- [x] Helper is gated on `shutil.which("cygpath")` (Windows without
      Git Bash falls back without crashing)
- [x] Helper wraps subprocess call in try/except, logs fallback
- [x] 3 new unit tests in `test_worktree_path.py`:
      Windows+cygpath, non-Windows passthrough, cygpath-missing
      fallback
- [x] 1 new drift invariant: `test_paperclip_worktree_path_helper_exists`
- [x] Drift net: **74 → 75** (+1)
- [x] `ruff check` + `ruff format --check` clean on all M178 files
- [x] No existing logic modified — `_resolve_repo_root`, `_run`,
      `worktree_commit_node`, `worktree_merge_node` are untouched
- [x] No graph topology changes — only the 2 worktree-helper
      invocation lines

---

## Lessons

1. **MSYS path mangling is a Windows-classic gotcha.** The
   `scripts/worktree-helper.sh` already had a `cygpath -m` fix at
   the bash-script level (M24.1), but the Python side was still
   handing bash a raw Windows path. The fix had to happen on BOTH
   sides for the round-trip to work. Future bash-invoking code
   should call `_to_posix_path` (or its future shared utility
   equivalent) as the first step.

2. **Gate on capability, not just platform.** Checking
   `sys.platform == "win32"` alone isn't enough — a WSL-only or
   pure-cmd Windows environment doesn't have `cygpath` in PATH.
   The dual-gate (`platform AND shutil.which`) is the right
   pattern: degraded Windows users fall through to the original
   buggy behavior, but Git-for-Windows users (the vast majority)
   get the fix.

3. **Drift tests guard helpers, not just public APIs.** The new
   drift test asserts `_to_posix_path` is importable AND returns a
   non-empty string — not a strict equality (the result is
   platform-dependent: `/tmp/test` on Linux, `/c/tmp/test` on
   Windows). Pinning exact behavior in a drift test would couple
   the test to the cygpath version; the soft "exists + returns
   string" check is the right level of strictness.

---

## Related

* [M169 Paperclip spec](file:///C:/Users/mathe/code_space/life-oss/life/specs/M169-paperclip/SPEC.md)
  — the 4th LangGraph graph that owns the worktree nodes
* [M174 auto-spawner](file:///C:/Users/mathe/code_space/life-oss/life/specs/M174-paperclip-auto-spawner/SPEC.md)
  — the spawner that dispatches to Paperclip; M178 unblocks LIVE
  RUN on Windows so the spawner's end-to-end path now works
* [M24.1 worktree-helper windows paths](file:///C:/Users/mathe/code_space/life-oss/life/specs/M24.1-fix-worktree-helper-windows-paths/SPEC.md)
  — the previous bash-side `cygpath -m` fix; M178 completes the
  round-trip on the Python side