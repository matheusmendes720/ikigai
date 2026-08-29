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

### Hygiene sweep — gitignore fix (clean slate before B5)

**Status:** shipped 2026-08-29. Closes the dangling alternation-syntax
bug in `.gitignore` keyword patterns; verified with `git check-ignore -v`
against all 15 target files.

**Why:** gitignore does NOT support alternation `/(a|b)` or word-boundary
`\b` in match patterns. The previous patterns
(`/(None|str|int|...)\b` and `/(dict\[|list\[|...)`) were silently inert.
This means root-level files like `None`, `dict[str`, etc. created by
malformed bash redirects (`> None`, `> dict[str`) would NOT be ignored.

**Fix:** switch to one explicit line per keyword (`/None`, `/str`, ...) and
use `*` suffix for type-fragment patterns (`/dict\[*`) so `\[` matches one
literal `[` and `*` matches the rest.

**Verification (post-fix):**
- `git check-ignore -v None str int float bool list dict com formal one` →
  all 10 match their patterns.
- `git check-ignore -v 'dict[str' 'list[int]' 'tuple[date' 'set[str]' 'frozenset[bytes]'`
  → all 5 match their patterns.
- Root-level zero-byte files: 0 (clean).
- Untracked files outside `.claude/`: 0 (clean).

**Commit:** `ea6e4e4` — `fix(gitignore): switch keyword deny-list to
explicit lines (alternation unsupported)`

**Pre-existing hygiene debt (NOT this commit):**
- `ruff check src/`: 1427 errors (mostly F401 unused imports across
  `src/contracts/`) — pre-existing, not regression. Out of scope.
- `pytest --collect-only`: 785 tests collect, 57 collection errors in
  `vibe-ops/scratch/` (broken imports) — pre-existing. Out of scope.

---

## [unreleased] — 2026-08-29

### Phase B5.1 — Graph & agent-loop hardening (infra-only)

**Status:** shipped 2026-08-29. Closes 6 of 14 findings from the B5.0
audit (`docs/superpowers/plans/2026-08-29-phase-b5-graph-agent-loop-audit.md`).
Strict scope fence preserved: 0 lines of math touched (no edits to
scoring/formula/qhe/regime/weight code).

**Findings closed (B5.1.1 → B5.1.6):**

| # | Finding | Fix | Files touched |
|---|---------|-----|---------------|
| F9 | FilesystemBackend scoped to `Path.home()` (full system write access) | Scope to `_FS_ROOT = data/`, allowlist `_VAULT_ROOT = vault/`, `virtual_mode=True` | `deepagents_harness.py` |
| F4 | SqliteSaver connection leak (singleton graph never closed) | Stash `conn` on compiled graph, add `close_graph()`, register `atexit` hook | `graph.py` |
| F13 | Zero retry/timeout at transport layer | `_retry_atomic_write` decorator on `queue.py` (`enqueue`, `ack`); 4 attempts, exponential backoff + jitter, OSError/PermissionError | `src/mesh/queue.py` |
| F3 | No error_node terminal — exceptions crashed the graph | New `nodes/error.py` terminal; `_safe_node()` wrapper around all 8 nodes; conditional edges after every node check `error_type` and route to error_node | `graph.py`, `state.py`, new `nodes/error.py` |
| F10 | Default checkpoint DB at `~/.ikigai/ikigai_checkpoints.db` (Windows-lock risk per `life-ops-ikigai-lock-2026-08-27`) | Default to `<project_root>/data/ikigai_checkpoints.db`; honors `IKIGAI_CHECKPOINT_DB` env override | `graph.py`, `deepagents_harness.py`, `tools.py` |
| F1 | Dual `langgraph.json` (root + `src/ikigai/`); root had broken path `life-ops/ikigai/src` (renamed to `src/ikigai/`) | Fix `vibe-ops/src/langgraph_entry.py` path resolution (`PROJECT_ROOT`, `VIBE_OPS_SRC`, `IKIGAI_SRC`); import via `agents.ikigai_maintainer.graph` (post-reorg path); delete duplicate `src/ikigai/langgraph.json` | `vibe-ops/src/langgraph_entry.py` |

**Verification (post-fix):**
- `tests/mesh/test_queue.py` — 7/7 PASS (5 pre-existing + 2 new retry tests)
- `tests/ikigai/test_error_node.py` — 3/3 PASS (graph compiles 9 nodes,
  injected exception routes to error_node, clean run skips error_node)
- Combined: `pytest tests/mesh/test_queue.py tests/ikigai/test_error_node.py`
  → 10/10 PASS
- `ruff check` on new/touched files (queue.py, error.py, graph.py,
  __init__.py): clean (pre-existing ruff debt in langgraph_entry.py
  out of scope)

**What B5.1 did NOT touch (deferred per algorithm gate):**
- 8 LOW/MEDIUM findings (F2, F5, F6, F7, F8, F11, F12, F14) — deferred
  to B5.2/B5.3 unless time permits
- Any algorithm code: `state.py` constants, `score_vectors.py`,
  `heuristics.py`, `balance.py`, `metrics.py` (QHE) — all preserved
  per [[algorithm-gate-system-readiness-not-sonho-2026-08-29]]

**Commits (single batch):** F9 + F4 + F13 + F3 + F10 + F1 + tests + CHANGELOG
landed in one commit per the audit's "batch B5.1 together" guidance.

---

### ADR-007 propagation gap — STATUS banner sweep (27 files)

**Status:** shipped 2026-08-29. Closes the gap after commit `118060e`
(ADR-007 + 53-adr-007-data-first-gate.md + 5 Q3 placeholders). This sweep
applies the same STATUS blockquote pattern to the remaining 27 files
that cite the "5 SONHO logs gate" framing.

**Why:** the user's 2026-08-29 correction was that the "5 SONHO logs gate"
framing is a **propagated misconception** of ADR-007. ADR-007's rule is
**observation depth**, not a release gate. The actual gate for
algorithm/IKIGAi work is **system readiness** (backend + data + agent
functional), independent of the SONHO counter. See
`~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md`
for the canonical clarification.

**Scope:** 27 files / 64 insertions. Pure docs — no code or contract
changes. Append-only invariant preserved (STATUS blockquotes appended at
top of each doc; nothing deleted).

**Files (27):**
- `docs/design-system/*` (18 files): 09, 10-pattern-ueid-tri-key,
  10-modelo-unificado-auto-feedback-estocastico, 12, 13, 14, 15, 16, 17,
  18, 19, 30, 31, 32, 33, 34, 43, 45. File 34 was already SUPERSEDED;
  got a lightweight note rather than the full banner.
- `vault/ikigai/closing-2026/02-q4-2026/*` (5 placeholders): SONHO,
  Plano Trimestral, Onda 1, Onda 2, Onda 3. Mirror Q3 banner pattern.
- 1 each: `docs/superpowers/plans/2026-08-25-ikigai-vault-layers.md`
  (banner appended after existing SUPERSEDED blockquote),
  `docs/auto-performance-os/09-postulado-ikigai-5-vetores.md`,
  `vault/ikigai/meta/algorithm-issues-registry.md`,
  `src/ikigai/data/matheus/ikigai_state/profile-2026-07-03.md`.

**Two banner variants:**
- **ADR-007 propagation note** (default, 22 files): flags "5 SONHO logs
  gate (ADR-007)" as propagated misconception; clarifies actual gate.
- **Q4 placeholder STATUS** (5 files): same shape as Q3 banners.

**Commit:** `48b2c08` — `docs: close ADR-007 propagation gap — STATUS
banners on 27 files`

**Scope-expansion note:** the proposal cited 18 files (13 docs + 5
placeholders). The grep that produced the actual list revealed 27 (full
audit). User had authorized with "ok .. continue"; commit ships the full
sweep rather than partial. Work type identical to proposal (STATUS
banners); only file count differs.

---

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
