---
name: M91-drift-bash-path-fix
description: Fix test_progress_md_has_no_double_fires regression - find git-bash explicitly + MSYS path translation
owner: matheus-mendes
status: DONE
milestone: M91
estimated_cost_usd: 0.05
constitution_refs:
  - reversibility_over_cleverness
  - tests_are_the_contract
---

# M91 - Drift bash-script PATH fix + dispatch_sub_agents regression

## Context

Loop wakeup detected `test_progress_md_has_no_double_fires` failing. The
test invokes `detect-double-fire.sh` via `subprocess.run(shell=True)`. The
failure had two stacked causes:

1. **PATH issue**: Test subprocess inherits limited PATH (no git-bash).
   `bash` command resolves to `C:\WINDOWS\system32\bash.EXE` (Windows
   native shell, not git-bash) which has different path semantics.
2. **MSYS path translation**: Even with git-bash, `C:\Users\foo` becomes
   `C:Usersfoo` (backslashes stripped by shell). Need `/c/Users/foo`
   format (lowercase drive + slash, no colon).

The test's `shell=True` call passed `str(script)` directly which has
backslashes.

## What changed

### src/ikigai/tests/test_drift_extended_invariants.py

- Added `import sys` (needed for sys.executable reference)
- Replaced `subprocess.run(cmd, shell=True)` with explicit
  `subprocess.run([bash_exe, script_path, scoped_path])` (no shell)
- Hardcoded bash to `C:/Program Files/Git/bin/bash.exe` (git-bash) with
  fallback to (x86) variant; pytest.skip if neither found
- Convert path via normalize-then-prefix: `C:\Users\foo` →
  `\\` → `/` → drop leading `/` → drop `:` after lowercase drive →
  prepend `/` → result `/c/Users/foo` which git-bash resolves correctly

## What did NOT need to change

`dispatch_sub_agents` was already real (~660 lines, complete protocol).
The test failure was a regression in `test_progress_md_has_no_double_fires`,
not the subgraph implementation.

## Acceptance

- [x] `test_progress_md_has_no_double_fires` PASSES
- [x] Drift 18/18 PASS
- [x] ikigai 771 PASS + 13 SKIP (unchanged)
- [x] root 361 PASS + 27 SKIP (unchanged)

## Lessons

- **shutil.which("bash") lies on Windows**: Returns the Windows native
  bash alias, not git-bash. Hardcode the git-bash path instead.
- **subprocess + bash + shell=True is fragile**: Better to call the
  binary directly without a shell. Path quoting issues disappear.
- **MSYS path translation table**:
  - Windows `C:\Users\foo` → subprocess arg → bash strip → `C:Usersfoo` (FAIL)
  - Fix: `\\` → `/`, lowercase drive, drop `:`, prepend `/` → `/c/Users/foo` (OK)
- **Test PATH ≠ shell PATH**: subprocess.run doesn't inherit the full
  shell PATH by default; only what Python's `os.environ['PATH']` has.
  Tests that depend on shell binaries need to find them explicitly.

## Out of scope

- 5 v2 test files still skip-tagged (daily_skill, interface_dispatch,
  e2e_smoke, invoke_skill_taskdog, multi_level_smoke)
- `langgraph.json` v2 re-registration
- Real LLM integration with Anthropic API key (vs IKIGAI_FAKE_LLM)
