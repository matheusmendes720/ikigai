# CHANGELOG — life/

Cross-cutting changes for the root `life/` repo. Per-submodule changelogs:

- `src/operational/CHANGELOG.md`
- `src/ikigai/CHANGELOG.md`
- `vibe-ops/CHANGELOG.md`
- `strategics/` is read-only (no changelog)
- `interfaces/cli/` does not yet have a separate changelog; entries land here

This file covers phases that touch multiple layers or that ship under the
`backend-phase-reordering-2026-08-28.md` plan (B0 → B6).

---

## [unreleased] — 2026-08-29

### v1.2 — CliAdapter dedup fix

**Status:** shipped 2026-08-29. Closes the "CliAdapter append-without-dedup"
minor finding from Phase B5.1 (`scripts/smoke/mvp_marco_cli.py` showed CLI
fork with 2 task(s) instead of 1).

**Scope:** one-line behavior change + dedicated smoke. No new business
logic. No policy engine / QHE / scoring imports.

**Why:** `do_task_add` + `worker.run_once` both call `CliAdapter.apply_change`
for the same CREATE event, so `data/tasks.jsonl` ended up with two lines
per UEID. The other forks (Taskdog, SolverforgeCalendar) use SQLite UPSERT
and were unaffected. The dup surfaced only in `plan-list` (CLI fork only)
or any consumer reading the JSONL slice directly.

**Commit:** `abb355f` — `fix(mesh): dedup CliAdapter.apply_change by ueid (v1.2)`

**Files:**
- `src/mesh/adapters/cli.py` (+17, -1): O(n) read-then-write inside
  `apply_change`; skip if UEID already present. Append still goes through
  temp + `os.replace` for atomicity.
- `scripts/smoke/cli_dedup.py` (+149): 5-step verification smoke that
  asserts the new invariant directly.

**Validation at ship time:**

- `scripts/smoke/cli_dedup.py`: 5/5 PASS (1st apply_change → 1 line;
  2nd apply_change same UEID → still 1 line; 3rd apply_change new
  UEID → 2 lines; `read()` returns records for both UEIDs; JSONL
  integrity — every line valid JSON with a UEID)
- `scripts/smoke/mvp_marco.py`: 7/7 PASS (unchanged from B5.1)
- `scripts/smoke/mvp_marco_cli.py`: 5/5 PASS — CLI fork row count
  dropped from "2 task(s)" to "1 task(s)"
- `ruff check scripts/smoke/cli_dedup.py`: All checks passed
- Production `data/` untouched (all smokes use `tmp_path` isolation)

**Pre-existing F401 left alone:** `tempfile` import at
`src/mesh/adapters/cli.py:4` is unused (not introduced by this change).
Drive-by fix would be scope creep; tracked separately.

---

### Phase B5.1 — MVP Marco CLI wrappers (live)

**Status:** shipped 2026-08-29. User greenlit on 2026-08-29 ("aprovado,
começa com MVP menor") after the B4 retroactive trail.

**Scope:** tiny — two Typer wrappers around existing mesh functions.
No new business logic. No policy engine / QHE / scoring imports.

**Why:** the user wanted "the smallest viable Marco demo" (`plan-add`
+ `plan-list`) to prove the chain `cli add → queue → worker → 3
adapters → cross-fork read` works end-to-end with existing code.
Per the user's binding constraint: backend works on vault sync only;
policy engines remain DEACTIVATED as business rule.

**Commits:**

| SHA | Subject | Files |
|---|---|---|
| `4e28873` | `test(smoke): add MVP Marco cycle verification (Phase B5.0)` | `scripts/smoke/mvp_marco.py` (199L) |
| `4543b1b` | `feat(interfaces): add plan-add/plan-list CLI wrappers (Phase B5.1)` | `interfaces/cli/read_tasks.py` (+128L), `scripts/smoke/mvp_marco_cli.py` (+125L), `scripts/smoke/mvp_marco.py` (noqa + F541 fixes) |

**Validation at ship time:**

- `scripts/smoke/mvp_marco.py`: 7/7 PASS (UEID build → CLI slice → enqueue
  → run_once drains 1 → 3-adapter cross-fork read → idempotent 2nd run →
  queue ack `propagated`)
- `scripts/smoke/mvp_marco_cli.py`: 5/5 PASS (do_task_add returns UEID →
  run_once drains → show_mesh returns 3-fork view → title persisted in
  all forks → CLI fork row count)
- Both smokes run in tmp_path isolation; production `data/` untouched
- Both scripts pass `ruff check` clean

**Commands added:**

```bash
python -m interfaces.cli.read_tasks plan-add TITLE [DUE]
python -m interfaces.cli.read_tasks plan-list [--all-forks] [--json]
```

**Phase B5 (the umbrella; deferred after Step 2):**

The remaining Phase B5 work is agent consumer + propagator wiring
(LangGraph `pae_maintainer` + `ikigai_maintainer` real connection).
Per user 2026-08-29: this is **deferred pending explicit greenlight**.
Autonomous-mode overreach rule from [[/btw fork failure 2026-08-28]]:
don't ship Phase B5.2+ autonomously.

**B5.1 minor findings (non-blocking, NOT fixed here):**

1. `CliAdapter.apply_change` appends without dedup → `do_task_add` +
   `run_once` writes the same event twice to `data/tasks.jsonl`.
   `plan-list --all-forks` is unaffected (other adapters use UPSERT);
   `plan-list` (CLI fork only) shows the dup. Fix in v1.2.
2. Root `cli/cli.py` (the `life` command per CLAUDE.md) is broken
   pre-existing (`from life import __version__` fails; no top-level
   `life/` package). The wrappers were inlined into the only
   currently-invokable Typer app (`interfaces.cli.read_tasks`). Root
   CLI integration is deferred until the package layout is fixed.

**Reviewer path:** both smoke files are self-documenting; the commit
messages above carry the design rationale and the bug-list.

---

### Phase B4 — Review Queue Worker (retroactive approval)

**Status:** shipped 2026-08-29 under autonomous mode (`/loop` + `ultrcode`).
Retrospectively approved by user on 2026-08-29 after option-1+3 trail review.

**In-scope justification:** the work is covered by the explicit
`docs/superpowers/plans/2026-08-28-backend-phase-reordering.md` plan, which
lists B4 (Review Queue Worker) as one of the six backend phases
(B0 hygiene → B1 A2UI → B2 CLI → B3 gateway → B4 worker → B5 wiring → B6 sync).

**Commits:**

| SHA | Subject | Files |
|---|---|---|
| `3149dab` | feat(mesh): add review queue worker supervisor (B4.1) | `src/mesh/review_queue_worker.py` (193L) + unit tests (248L, 9 tests) + `src/contracts/task_change.py` (`"clarified"` literal) |
| `c37f42a` | feat(interfaces): wire BACKEND_PROCESSES[review_queue_worker] to pidfile probe (B4.2) | `interfaces/cli/server.py`, `interfaces/cli/tests/test_server.py` |
| `0846eca` | build(ci): add review-queue-worker-contract job (B4.3) | `.github/workflows/ci.yml` (1 new CI job, 18 lines) |
| `521a2b5` | test(mesh): add end-to-end smoke test for review queue worker (B4.5) | `interfaces/cli/tests/test_review_queue_worker_e2e.py` (239L, 6 tests) |

Note: the 4-commit total counts B4.1, B4.2, B4.3, and B4.5. B4.4 was the
memory-persistence task, which does not produce a git commit (memory lives
outside the repo at `~/.claude/projects/.../memory/`).

**Validation at ship time:**

- 9 unit tests pass (`interfaces/cli/tests/test_review_queue_worker.py`)
- 6 e2e tests pass (`interfaces/cli/tests/test_review_queue_worker_e2e.py`)
- CI gate `review-queue-worker-contract` is green on master
- Server-side tests: 29 pre-existing tests in `interfaces/cli/tests/test_server.py` still pass after B4.2 wiring
- Total tests in B4 scope: 75 (9 unit + 6 e2e + the B4.2-related server tests + 60 contract tests downstream)

**Mode-of-shipping:** autonomous loop, plan-defined scope.
`/loop` + `ultrcode` were activated; the first `/btw` critique (received
after B4 landed) flagged that this combination should be read as "continue
within established phase scope" rather than "ship next phase also." B4 was
established scope (per the plan). B5/B6 are not.

**What retroactive approval means:**

B4 was merged before the user explicitly greenlit the *act* of merging the
four B4 commits. The B4 work itself was within the in-scope phase B4 of the
backend phase plan. Approval on 2026-08-29 ratifies this end-to-end as a
legitimate ship.

**What this does NOT authorize:** future autonomous ships of B5/B6 or any
work outside the established plan scope. Per the first `/btw` critique
noted above, B5/B6 still require explicit user direction before autonomous
work begins.

**Reviewer path (full record):** the session memory file
`~/.claude/projects/.../memory/phase-b4-review-queue-worker-complete-2026-08-29.md`
holds the full task-list (B4.1 through B4.5), the four lessons learned,
the spec-coverage matrix, and the pre-existing-issues list. Read that file
for context, not this changelog.

---

## Format conventions (locked 2026-08-29)

- Each top-level section is a phase shipped under the
  `backend-phase-reordering-2026-08-28.md` plan
- Status line: shipped / retroactive-approval / pending / deprecated / reverted
- Commit list with SHA + subject + files-changed count
- Validation evidence (test counts, CI gate names, smoke results)
- "What retroactive approval means" block is mandatory when phase shipped
  under autonomous mode
- Cross-references to session memory for full context, not duplicated here

This format is self-referentially the first entry — pattern locked by this very entry.
