---
name: M66-task-windows-paths
description: Fix task daily-review/weekly-review bash subprocess paths on Windows (backslashes → forward slashes)
owner: matheus-mendes
status: DONE
milestone: M66
estimated_cost_usd: 0.20
constitution_refs:
  - correctness_over_speed
---

# M66 — Fix bash path arguments in `life task daily-review` / `weekly-review`

## Context

Audit of all 16 user-facing `life` subcommands (2026-09-18) revealed
two bugs in `life/cli/centrals/task.py`:

1. `daily_review()` and `weekly_review()` passed
   `subprocess.run(["bash", str(script)])` — passing Windows
   backslash paths (`C:\Users\...`) to git-bash, which strips
   backslashes and treats colons as drive-letter separators → bash
   tried `C:Usersmathecode_space...` and reported "No such file or
   directory" while the script existed on disk.

2. `metrics()` calls `subprocess.run([sys.executable, str(script)])`
   to run `calculate-metrics.py` without passing the required
   `<export.json>` arg — it prints the usage line and exits 1. This
   is a more invasive bug (M67+ requires wiring up `task export` to
   produce the JSON before calling metrics). Logged as out of scope.

## What changed (M66)

`life/cli/centrals/task.py` — 2 sites patched:

```python
# Before
subprocess.run(["bash", str(script)], cwd=scripts, check=False)
# After
bash_script = str(script).replace("\\", "/")
subprocess.run(["bash", bash_script], cwd=scripts, check=False)
```

`metrics()` was inspected but NOT patched in M66 — see Acceptance.

## Acceptance

- [x] `subprocess.run(["bash", ...])` now receives forward-slash paths
- [x] `life daily-review` script is found by bash (now: "task: command
  not found" is the expected downstream error on Windows-without-
  Taskwarrior-installed, NOT a path-mangling error)
- [x] Drift + chat + drift_extended: 39/39 PASS preserved
- [x] `pip install -e .` does not need re-running (no pyproject change)

## Out of scope (M67 candidate)

- `metrics()` calling pattern: should accept `--export PATH` flag OR
  auto-run `task export` to fetch a fresh export before invoking
  `calculate-metrics.py`. Either path needs real Taskwarrior on the
  host to produce a valid JSON, which is itself an M68 candidate.
- `daily_review()` / `weekly_review()` depend entirely on the bash
  scripts at `taskwarrior/scripts/{daily,weekly}-review.sh`, which
  shell out to `task` (Taskwarrior binary). On Windows-without-
  Taskwarrior-installed, the script runs but exits with non-zero
  status downstream — this is **expected behavior**, not a bug.