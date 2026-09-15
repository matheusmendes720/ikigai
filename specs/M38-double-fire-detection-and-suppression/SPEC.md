---
name: M38-double-fire-detection-and-suppression
description: Detect and suppress double-fires in progress.md. Script + drift test.
constitution_refs:
  - tests_are_the_contract
  - state_on_disk_not_conversation
  - correctness_over_speed
status: DONE
owner: loop-orchestrator
created: 2026-09-15
---

# M38 — Double-fire detection and suppression

## Goal

Fix the drift net regression caused by an uncommitted test (`test_progress_md_has_no_double_fires`) that fails because:
1. The test has a Windows path-conversion bug (`cygpath` is unavailable on this Windows host; the fallback `/c/Users/...` path does not resolve under Git Bash for the script)
2. The detect-double-fire.sh script correctly detects 120 "double-fires" — most are legitimate rapid-fire cron dispatches (daemon catchup pattern at 6-25 second intervals), but a smaller subset are true duplicate log artifacts

## Acceptance criteria

1. **`scripts/detect-double-fire.sh` exists** and is executable (chmod +x, commit + push)
2. **`test_progress_md_has_no_double_fires` PASSES** when invoked via the project's standard pytest invocation (Windows-compatible)
3. **Detection is tuned to distinguish real double-fires from legitimate rapid-fire cron**:
   - Real double-fire = same `task_id` AND same timestamp (same minute) with different content
   - Legitimate rapid-fire = same `task_id` within 5 minutes BUT different timestamps (≥2 seconds apart)
   - Pre-existing double-LOG artifacts (Windows Cygwin errno 11) are documented as not-real-double-fires
4. **Drift net restored to 66/66 PASS** (canonical_scope 35 + drift_invariants 7 + drift_extended_invariants 11 + chat_repl 8 + new M38 test = 67 invariants total)
5. **Regression sweep clean** — `pytest` for affected test files + `bash tests/test_dispatch.sh 24/24` + `bash tests/test_notify.sh 11/11` + `bash tests/test_cost_dashboard.sh 7/7` + `bash tests/test_worktree_helper.sh 15/15` + `bash tests/test_streak_tracker.sh 11/11`
6. **State machine reconciled**: `roadmap.md` M38 entry added (STATUS:DONE after close), `tasks.md` M38 section + T-38.1..T-38.5 entries status=done
7. **Atomic commits** — one for the script (executable +x), one for the test path fix + tuning, one for state machine closeout

## Sub-tasks

### T-38.1 — Investigate the 120 detected double-fires
- Run `bash scripts/detect-double-fire.sh .claude/loop/progress.md` and analyze output
- Categorize:
  - Rapid-fire cron (legitimate, daemon catchup): <30 second intervals, same task_id, different verdict (e.g., `pae_maintainer` graph-dispatch every 6s)
  - True double-fire (concurrent): same minute timestamp, different verdict content
  - Double-LOG artifact: same tick_id but two log entries (already documented as non-issue)
- Document findings in `docs/superpowers/specs/2026-09-15-m38-double-fire-analysis.md`

### T-38.2 — Tune detect-double-fire.sh detection logic
- Adjust WINDOW_SECONDS or add per-timestamp discrimination
- Recommendation: change definition to "same task_id AND same minute timestamp (truncated to seconds)" — this matches actual concurrency bugs vs sequential cron ticks
- Add CLI flag `--mode strict|lenient` so future regressions can use either

### T-38.3 — Fix test_progress_md_has_no_double_fires path conversion
- Current bug: `_to_bash_path` falls back to `/c/Users/...` but `bash` invocation fails with "No such file or directory"
- Fix: use `pathlib.Path.resolve()` and rely on Python's subprocess with the Windows path directly (subprocess.run on Windows accepts Windows paths); OR use `BASH_EXE = shutil.which("bash")` and pass POSIX-style via `subprocess.run([BASH_EXE, ...])` instead of going through `bash -c`
- Verify: test invokes successfully, returns expected exit code

### T-38.4 — Commit + verify drift net
- Atomic commits:
  1. `chore(scripts): add executable bit + chmod +x detect-double-fire.sh (M38)`
  2. `test(drift): fix path conversion + tune double-fire detection (M38)`
  3. `chore(loop): M38 double-fire detection shipped — drift 67/67 (drift-bookkeeping)`
- Run full drift net, confirm 67/67 PASS

### T-38.5 — State machine reconciliation
- `roadmap.md` M38 section added (per M27 frontmatter schema — yaml frontmatter: name, description, constitution_refs, status:DONE, owner, created)
- `tasks.md` M38 section + T-38.1..T-38.5 entries status=done
- Atomic state-machine commit + push to origin

## Out of scope

- T-24.4 wall-clock gate closeout (still IN-PROGRESS; not related to M38)
- Anti-idle triage depth for cost-gated ticks (M38-A #1 candidate; can be future M39)
- Signal-discovery scheduling (M38-C #3 candidate; can be future M40)

## Cost budget

- Worker: $0.50 (bash + python verification; minimal LLM)
- Verifier: $0.20 (haiku 5-dim review)
- Total: ~$0.70 (fits in remaining $2.89 budget)

## Risk

- LOW — bash + python only; no architectural changes; restores already-existing infrastructure

## Dependencies

- M34 anti-idle auto-reconcile (already shipped — provides state machine drift detection)
- M37 signal-discovery refresh (provides top candidate ranking + evidence)

## Auto-promotion rationale

Per M37 evidence:
- 120 detected double-fires in progress.md (concrete evidence of redundant invocations)
- 4-parallel-invocation pattern observed 2026-09-15T12:43Z (per T-24.4 wall-clock gate notes)
- Drift net regression blocker (constitution hard rule: never skip deterministic gates)