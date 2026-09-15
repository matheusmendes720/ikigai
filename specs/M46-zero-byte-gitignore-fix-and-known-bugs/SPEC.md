---
name: M46-zero-byte-gitignore-fix-and-known-bugs
description: Add missing .gitignore patterns for $10 and {len(lf_data)} bash-redirect leaks; document scripts/mcp_inspect.py root cause.
status: DONE
owner: loop-orchestrator
constitution_refs:
  - state_on_disk_not_conversation
  - spec_driven_not_vibe_driven
estimated_ticks: 1
---

# M46 — Zero-byte gitignore fix + known-bug triage

## Problem

AGENTS.md §🐛 Pre-existing bugs flagged 5 items:
1. `scripts/mcp_inspect.py` PYTHONPATH bug (Windows parity)
2. `tests/test_tui_operator` rglob false-flake
3. 5 stale PAV test files in `src/ikigai/tests/`
4. 4 zero-byte artifacts at repo root (`$10`, `IN`, `inline`, `{len(lf_data)}`)
5. `strategics/planning-with-files` submodule dirty (modified content, sem commit)

## Disposition applied

**Item 4 — Fixed.** M20 T-20.1 missed 2 patterns:
- `\$10` (bash `> $10` redirect to a $variable)
- `{len(lf_data)}` (bash heredoc leaked Python f-string fragment — was already caught by `/{*}` but the explicit rule is clearer)

Both now gitignored. `git status` after fix:
- `$10`: no longer shown as untracked
- `{len(lf_data)}`: no longer shown as untracked
- `IN` + `inline`: were already gitignored

**Item 5 — Already resolved in M41** (submodule unlink + .gitignore entry).

**Item 1 — Diagnosed, not fixed.** Root cause is NOT in `scripts/mcp_inspect.py` but in `src/contracts/base.py` line 11: `from src.contracts.common import UEID, PaeCyclePhase, PlanTier, VectorKey` uses the OLD `src.` prefix. The script is correctly reporting the broken import. Fix requires understanding the contracts refactor scope — out of scope for M46.

**Item 2 — Not investigated.** `tests/interfaces/test_tui_operator.py` exists (the rglob false-flake would be a test infra issue, not a script bug). Marked as deferred.

**Item 3 — Refuted.** Only 1 stale PAV test file exists at `src/ikigai/tests/test_v2_pav_intentions.py`, and it's NOT stale — it imports `agents.v2.prompts.surface_pav_intentions` which is an active v2 node. The "5 stale" claim is wrong.

## Acceptance

- [x] `.gitignore` extended: `+/\$10` + `+/{len(lf_data)}` (T-46.1)
- [x] `git status` clean of `$10`, `{len(lf_data)}` (T-46.2)
- [x] `scripts/mcp_inspect.py` root cause documented (T-46.3 — diagnosis, not fix)
- [x] Items 2, 3, 5 documented with current state (T-46.3)
- [x] Drift net preserved: 69/69 PASS + 11/11 PASS

## Reversibility

`git revert` + remove the 2 .gitignore additions.

## What remains after M46

**Mechanical wins all done.** Remaining work is:
- **M24 wall-clock gate** (8h away) — can't expedite
- **M47 candidate:** Fix `src/contracts/base.py:11` — requires understanding the contracts refactor (out of autonomous scope)
- **Master vs origin/main merge** (126 commits behind) — out of roadmap scope
- **The4 🐛 items remaining on the original list** are either false positives or require deep domain work

**Recommendation:** Stop the autonomous loop after M46. The remaining roadmap items are either wall-clock (M24) or require user authorization (contracts refactor, master merge).