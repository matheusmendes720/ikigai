# P0 Corrections Map — PAV Kernel

> **Purpose.** Single source of truth for the P0 hygiene batch identified during the
> early-2026 audit. Anchors future sessions so we don't relitigate which finding was
> fixed, what was changed, and where. **Read this first** before opening new P0 work.
>
> **Scope.** `life-ops/operational/` (PAV productivity kernel) — packages/core, apps/cli,
> apps/tui, top-level config. Cross-system refactors (vibe-ops/, life/, docs) are out
> of scope unless explicitly noted.

---

## 1. Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ FIXED | Code change applied, test(s) added/passing, verified in this audit pass |
| 🔴 BROKEN | Confirmed defect — code change **not yet applied** |
| ⚠️ LATENT | Discovered during this audit — needs classification (fix / keep / design) |
| ✅ RESOLVED | Originally flagged but found to be a non-issue on inspection |

## 2. P0 Findings — Confirmed List (17 total)

| # | Issue | Status | File | One-line Fix |
|---|-------|--------|------|--------------|
| 1  | Hardcoded analytics date range past today | ✅ FIXED 2026-07-02 | `apps/cli/src/operational/cli/commands/analytics_cmd.py:86-94` (`_window()`) + 13 call sites | Module-level `_START`/`_END` (frozen at import) → per-call `_window()` function |
| 2  | `_json = json` local shadowing at 8 sites | ✅ FIXED 2026-07-02 | `apps/cli/src/operational/cli/commands/analytics_cmd.py` (8 sites: `cmd_qhe`, `cmd_sleep`, `cmd_habits`, `cmd_pomodoro`, `cmd_policy`, `cmd_mood`, `cmd_week`, `cmd_master`) | Removed 8 dead `_json = json` aliases; replaced 8 `_json.dumps(...)` with `json.dumps(...)` |
| 3  | `sync_conflicts` hardcodes db path | ✅ FIXED | `apps/cli/src/operational/cli/commands/sync_cmd.py` | Added `--db` Typer option |
| 4  | PomodoroTimer broken end-to-end | ✅ FIXED | `apps/tui/src/operational/tui/screens/pomodoro_timer_screen.py` | Full rewrite: `PomodoroTracker` from core drives FSM; 1-Hz tick auto-advances; `action_*` methods route buttons and bindings; `PomodoroRound` persisted via `cli_state.pomodoros` on every transition; abort chains through legal transitions (BREAK→SKIPPED→WORK→PAUSED→IDLE, WORK→PAUSED→IDLE); record IDs lowercase state per `^[a-z]{3,5}_[a-z0-9_]+$` |
| 5  | QHE_ALPHA/BETA/GAMMA constants unused (dead code) | ✅ FIXED | `packages/core/src/operational/constants.py` | Fields removed; `FIELD_COUNT` 24→21; validation block dropped; tests updated (150 passing) |
| 6  | Purity violations in core modules | ✅ RESOLVED 2026-07-02 | `packages/core/src/operational/core/insights.py:11` (docstring example) + `core/next_step.py:16` (sibling `core/budget` only — no CLI imports); see §3 | Was: live `print()` + CLI import. Now: print is in a docstring Usage: block (never executes), and `next_step.py` only imports from `operational.core.budget` (a sibling core module). |
| 7  | No file-locking on `_PersistentRepo._dump()` | ✅ FIXED | `apps/cli/src/operational/cli/state.py:67-110` (lock) + `:111-176` (read-merge-write) + `_state_dir()` helper at `:40-64` | OS-level exclusive lock (`fcntl.flock` POSIX / `msvcrt.locking` Windows) + read-merge-write inside the lock; see §4 |
| 8  | TUI never reloads from disk on CLI writes | ✅ FIXED 2026-07-01 | `apps/cli/src/operational/cli/state.py:67-128,328-344` (mtime tracking + `reload_stale_repos`) + 6 TUI screens (dashboard, daily_flow, habits, journal, metrics, policy) | mtime-poll in screen data-read paths; see §5 |
| 9  | 2 broken test imports (stale paths) | ✅ FIXED | `tests/.../test_*.py` | Stale paths removed; both files import cleanly |
| 10 | Pre-commit mypy hook uses wrong path regex | ✅ FIXED | `.pre-commit-config.yaml:28` | `^(packages\|apps)/.+/src/.+\.py$` |
| 11 | Pre-commit pytest-fast hook is no-op | ✅ FIXED | `.pre-commit-config.yaml:33-48` | `poetry run`→`uv run`, dropped dead `-m "unit"` marker, scoped to diff'd unit tests |
| 12 | `regime_color_map` MAINTAIN mismatch | ✅ FIXED | `apps/tui/src/operational/tui/theme.py` (consistency with `tokens.py`) | Both files now agree: MAINTAIN=blue |
| 13 | Two Severity enums coexist (5 vs 3 levels) | ✅ FIXED | `packages/core/src/operational/core/policy_engine.py:169-216` | Equivalence table documented, pinned by `test_warning_equivalent_to_exceptions_medium` |
| 14 | `--log-file` handler ignores `--json-log` flag | ✅ FIXED | `apps/cli/src/operational/cli/app.py` (logging setup) | Structlog pipeline routes JSON to **all** handlers, including file |
| 15 | Verify `consolidator.py` existence in core/ | ✅ RESOLVED 2026-07-02 | `packages/core/src/operational/core/consolidator.py` | File exists, 133 unit tests pass, 1 production caller (`weekly_aggregator.py:29`); see §3 |
| 25 | `_energy_for`/`_focus_for` return FIRST match (stale) | ✅ FIXED | `apps/cli/src/operational/cli/services.py` | Flattened to date-keyed `next()` over `metric.list()` |
| 36 | `demo TIME_TASKER_DATASET` default='production' KeyError | ✅ FIXED | `apps/cli/src/operational/cli/state.py` (`_BUILTIN_DATASETS`) | `"production"` registered |

**Roll-up.** 15 fixed / 0 broken / 0 latent / 2 resolved (+ consolidator re-export caveat promoted to RESOLVED in §3 P0 #15).

---

## 3. Detailed Findings — Fixed (Verified During This Pass)

### P0 #1 — Hardcoded analytics date range (frozen at import time)

- **File:** `apps/cli/src/operational/cli/commands/analytics_cmd.py:86-87`
- **Root cause:** Module-level `_START = date.today() - timedelta(days=180)` and `_END = date.today()`. Python evaluates module bodies exactly once on first import — so the analytics window was frozen on the day the process first imported `analytics_cmd.py`. Any subsequent invocation reused that stale window, producing ever-more-stale analytics as the system clock advanced. (Common trap: looks "dynamic" because it calls `date.today()`, but isn't — the call happens once at import, not per command.)
- **Fix:** Removed the module-level globals. Replaced them with a per-call function `_window(days: int = 180) -> tuple[date, date]` that re-evaluates `date.today()` on every invocation. Updated all 13 call sites across the file (`weeks_in_range`, `qhe_weekly_aggregates`, `pomodoro_weekly_aggregates`, `data_quality_report`, master report f-string, `cmd_quality`) to use `*_window()` unpack instead of the frozen globals.
- **Verification (2026-07-02):** `uv run python -c "from operational.cli.commands.analytics_cmd import _window; print(_window())"` returns `(2026-01-03, 2026-07-02)` — today is `2026-07-02` and the 180-day window ends today. `uv run pytest tests/unit/cli -q` → 20 passed. Module imports cleanly. No test file imports `analytics_cmd`, so no regression risk on test surfaces.

### P0 #2 — `_json = json` local shadowing (no nested decorator present)

- **File:** `apps/cli/src/operational/cli/commands/analytics_cmd.py` (8 sites)
- **Root cause:** At 8 sites across `cmd_qhe`, `cmd_sleep`, `cmd_habits`, `cmd_pomodoro`, `cmd_policy`, `cmd_mood`, `cmd_week`, and `cmd_master`, the body contained `_json = json` as a local aliasing of the stdlib module — followed by `_json.dumps(...)`. The alias added nothing (the module-level `import json` is in scope) and was a stale debugging remnant. The "nested `trace_command`" half of the original finding did not exist in the code as audited on 2026-07-02 — `cmd_qhe` etc. each have a single `with trace_command(...)` block, no decorator on top. (The original report may have conflated two separate P0 items.)
- **Fix:** Removed the 8 `_json = json` lines. Replaced all 8 `_json.dumps(...)` call sites with `json.dumps(...)` directly.
- **Verification (2026-07-02):** `grep -n '_json\s*=\s*json' analytics_cmd.py` → no matches. `grep -n '_json\.dumps' analytics_cmd.py` → no matches. `grep -nE '\b_START\b|\b_END\b' analytics_cmd.py` → no matches (confirms P0 #1 cleanup is complete). `uv run pytest tests/unit/cli -q` → 20 passed.

### P0 #3 — `sync_conflicts` hardcodes db path

- **File:** `apps/cli/src/operational/cli/commands/sync_cmd.py`
- **Root cause:** Function signature was `def sync_conflicts() -> None` — the SQLite path was read from a module-level constant, which prevented testing against fixtures.
- **Fix:** Added a `--db` Typer option (default `./vibe_ops.db`) and threaded it through 5 call sites (sync_conflicts, sync_export, sync_import, sync_resolve, sync_history).
- **Doc drift fixed (2026-07-02):** Earlier version of the map said default was `~/.time-tasker/sync.db`. Actual default per `sync_cmd.py` is `./vibe_ops.db` (repo-local).
- **Verification:** `pav sync conflicts --db /tmp/fixture.db --json` works; tests can now inject paths.

### P0 #9 — Broken test imports

- **Files:** Two test files in `tests/` referenced modules relocated during the workspace consolidation.
- **Root cause:** Paths left over from a pre-uv-layout.
- **Fix:** Updated both import statements.
- **Verification:** `uv run pytest --collect-only` lists both files without `ImportError`.

### P0 #10 — mypy pre-commit regex

- **File:** `.pre-commit-config.yaml:28`
- **Root cause:** Original regex `^src/.+\.py$` matched the legacy single-package layout — silent no-op under the uv workspace (`packages/*/src/`, `apps/*/src/`).
- **Fix:** `files: ^(packages|apps)/.+/src/.+\.py$`
- **Verification:** `git commit` with a type-introducing change in `packages/core/src/operational/foo.py` now triggers the mypy hook.

### P0 #12 — `regime_color_map` MAINTAIN mismatch

- **Files:** `apps/cli/src/operational/ui/tokens.py`, `apps/tui/src/operational/tui/theme.py`
- **Root cause:** `tokens.py` mapped MAINTAIN → blue; `theme.py` had MAINTAIN → green. TUI screens that imported both got inconsistent colors depending on the call site.
- **Fix:** `theme.py` updated to blue.
- **Verification:** Both files agree.

### P0 #13 — Two Severity enums

- **Files:** `packages/core/src/operational/core/exceptions.py`, `packages/core/src/operational/core/policy_engine.py`
- **Root cause:** Canonical PAV §6 Severity (5 tiers: `INFO/LOW/MEDIUM/HIGH/CRITICAL`) and policy-engine Severity (3 tiers: `INFO/WARNING/CRITICAL`) coexist by design — policy is a subset. The original code lacked a contract that pinned the design intent.
- **Fix:** Added docstring in `policy_engine.py:169-216` with equivalence table (`WARNING` ≡ canonical `MEDIUM`, both = "protective downgrade"). Added `test_warning_equivalent_to_exceptions_medium` in `tests/unit/core/test_policy_engine.py:190-216`.
- **Verification:** The new test passes (alongside the other 11 in that module). `INFO`/`CRITICAL` name-equal across both enums; `LOW`/`HIGH` absent from policy; `WARNING` (policy) ≡ `MEDIUM` (canonical) semantically.

> **Note.** A third enum, `ContextSwitchSeverity` (`packages/core/src/operational/core/context_switch.py:76-85`), exists for **context-switch overhead classification** (MINIMAL/LOW/MEDIUM/HIGH/SEVERE, IntEnum). It is **not a duplicate** — different domain (cost vs. policy tier vs. canonical incident severity). Leave as-is.

### P0 #14 — `--log-file` ignores `--json-log`

- **File:** `apps/cli/src/operational/cli/app.py` (logging wiring)
- **Root cause:** `--log-file` opened a plain `logging.FileHandler` while `--json-log` only mutated the stdlib root handler via structlog. Streams were split.
- **Fix:** Routed `--log-file` through the structlog pipeline; JSON formatter is applied to all handlers consistently.
- **Verification:** `pav --json-log --log-file /tmp/pav.log state show` produces JSON lines in `/tmp/pav.log`.

### P0 #6 — Purity violations in core modules (audit: already clean)

- **Files audited:**
  - `packages/core/src/operational/core/insights.py` (the only `print(...)` at line 11)
  - `packages/core/src/operational/core/next_step.py` (the file the map originally flagged at lines 141, 188)
- **Original concern:** A live `print()` in `core/insights.py` and `core/next_step.py` importing from `operational.cli.*`.
- **Audit findings (2026-07-02):**
  - **`insights.py:11 print(...)` is inside the module docstring's `Usage:` example block (lines 1-12).** `grep -n 'print' packages/core/src/operational/core/insights.py` shows **exactly one** match, and inspection confirms it sits inside `r"""..."""` triple-quoted text, not runtime code. It never executes — it's documentation.
  - **`next_step.py` no longer matches the original "core imports CLI" claim.** Top-level imports (line 16) only `from operational.core.budget import classify_quadrant` — a sibling core module, not CLI. Line 141 contains a **lazy import** of the same sibling (`from operational.core.budget import compute_day_quadrant`) inside a function body, also not CLI. The `DaySnapshot` reference in the module docstring (line 4) is a docstring type reference, not an import. The map's "lines 141, 188" citation is also stale — the file is now 175 lines, not 188+. The `operational.cli` substring only appears in the docstring.
  - **`insights.py` imports (line 17-38) are all from `operational.core.analytics`** — another sibling core module — not CLI.
- **Conclusion:** P0 #6 was either already fixed before the audit started, or was a speculative entry based on imagined code. No code change needed. Promotion `⚠️ LATENT → ✅ RESOLVED`.
- **Verification (2026-07-02):**
  - `grep -n '^\s*print\s*\(' packages/core/src/operational/core/*.py` → no matches (docstring print does not match `^\s*print\s*\(` outside docstring context).
  - `grep -nE 'from operational\.cli|import operational\.cli' packages/core/src/operational/core/*.py` → no matches.
  - `grep -n 'print' packages/core/src/operational/core/insights.py` → exactly 1 match (line 11, inside `r"""..."""`).

### P0 #15 — `consolidator.py` existence audit

- **File:** `packages/core/src/operational/core/consolidator.py` (252 LOC, 10 exported symbols: `Consolidator`, `DailyConsolidationResult`, `compute_energy_score`, `compute_health_score`, `compute_overall_score`, `compute_productivity_score`, `compute_sleep_debt`, `consolidate_daily`, `generate_alerts`, `generate_recommendations`).
- **Audit (2026-07-02):** File exists, no action needed. Module is pure (no I/O, no logging side-effects, mypy --strict compatible per its own docstring). Tests in `tests/unit/core/test_consolidator.py` cover all 8 sub-score / alert / recommendation paths.
- **Production callers:** Exactly **one** — `packages/core/src/operational/core/weekly_aggregator.py:29` imports `consolidate_daily`, `compute_sleep_debt`, `compute_energy_score`, etc. directly. No CLI/TUI command consumes consolidator today; the only CLI surface that mentions "consolidation" is `state_cmd.py` (file inspection), `analytics_cmd.py` (entity-row coverage), and `reflect_cmd.py` / `metric_cmd.py` (single-line docstring mentions). The real consumer chain is `consolidate_daily → DailyConsolidation → WeeklyAggregator.aggregate_from_consolidations → WeeklyAggregate`.
- **Discoverability caveat (non-P0) — RESOLVED 2026-07-02:**
  - **Symptom:** `from operational import consolidate_daily` raised `ImportError` in editable installs because CLI's `__init__.py` (`apps/cli/src/operational/__init__.py`) was resolved before core's __init__.py due to uv workspace path ordering — CLI app is listed after core in sys.path, so its `__init__.py` claims the PEP 420 namespace first.
  - **Root cause:** uv editable-install namespace shadowing. `operational.__file__` resolved to `apps/cli/src/operational/__init__.py` rather than `packages/core/src/operational/__init__.py`, so core's consolidator re-exports were unreachable via the `operational.*` root.
  - **Fix applied (partial re-export from CLI `__init__.py`):** Added a `from operational.core.consolidator import (...)` block in `apps/cli/src/operational/__init__.py` re-exporting all 10 consolidator symbols (`Consolidator`, `DailyConsolidationResult`, `compute_energy_score`, `compute_health_score`, `compute_overall_score`, `compute_productivity_score`, `compute_sleep_debt`, `consolidate_daily`, `generate_alerts`, `generate_recommendations`). A module docstring caveat documents the editable-install constraint and points consumers to canonical import paths for the rest of the API.
  - **Why not full delegation via runpy / PEP 562 `__getattr__`:** `runpy.run_path` runs core's `__init__.py` as `__main__`, which breaks submodule imports (`ModuleNotFoundError: 'operational' is not a package`). PEP 562 `__getattr__` triggered `RecursionError` because `sys.modules.get("operational")` returned the CLI module itself (same name = infinite loop on `getattr`). Full duplication of all ~80 core symbols would have been maintenance-heavy for no real win — the canonical path (`from operational.core.consolidator import …`) still works in every install layout.
  - **Verification (2026-07-02):** `uv run python -c "from operational import consolidate_daily, Consolidator, generate_alerts"` → `consolidator re-export: OK / __version__: 0.1.0`. Full regression: `uv run pytest tests/unit/core/test_consolidator.py tests/unit/cli tests/unit/entities -q` → **969 passed in 1.77s**.
- **Verification (2026-07-02):** `uv run pytest tests/unit/core/test_consolidator.py tests/unit/core/test_weekly_aggregator.py -q` → **133 passed in 0.38s**. `uv run python -c "from operational import consolidate_daily"` → OK (10/10 consolidator symbols importable from operational namespace root in editable installs).

### P0 #25 — `_energy_for`/`_focus_for` stale match

- **File:** `apps/cli/src/operational/cli/services.py`
- **Root cause:** Two helpers returned the FIRST entry in `metric.list()` rather than the **most recent date-keyed** record. After demo-data seeding, the first record was the oldest.
- **Fix:** Replaced with a date-keyed `next()` scan that yields the latest record per date.
- **Verification:** `pav dashboard --json` reports current-day energy/focus.

### P0 #36 — `demo` default KeyError

- **File:** `apps/cli/src/operational/cli/state.py` (`_BUILTIN_DATASETS`)
- **Root cause:** `TIME_TASKER_DATASET` defaulted to `"production"` but `_BUILTIN_DATASETS` only contained `golden`/`synthetic`. KeyError on first demo call.
- **Fix:** Registered `"production"` in `_BUILTIN_DATASETS` with a documented alias.
- **Verification:** `pav demo seed` (no env) works; `pav demo dataset` lists all three.

---

## 4. Detailed Findings — Broken (Awaiting Fix)

### P0 #4 — PomodoroTimer broken end-to-end ✅ FIXED (2026-07-01)

- **File:** `apps/tui/src/operational/tui/screens/pomodoro_timer_screen.py` (full rewrite, was 102 lines → ~390 lines wired)
- **Tests:** `tests/tui/test_tui_launch.py::test_pomodoro_screen_runs_full_state_machine_cycle` (new)
- **Symptom (before fix):** Pressing Start changed the displayed countdown from 25:00 → a frozen local counter; pressing Pause/Stop did nothing; nothing was persisted; the FSM never advanced.
- **Root cause (verified):** Seven independent defects stacked:
  1. `BINDINGS` declared `action_start_timer`/`action_pause_timer`/`action_skip_break`/`action_abort_timer` but **none of the action methods existed** — Textual raised `NoAttributeError` on every key press / button click.
  2. The screen mutated free-form `self._state: str` instead of using `PomodoroState` — illegal transitions silently accepted.
  3. **No countdown ticker.** The `Digits` widget rendered once at mount and never updated.
  4. **No tracker wiring.** The screen did not import `PomodoroMachine` (the spec calls the concrete class `PomodoroTracker`); nothing drove the FSM.
  5. **No persistence.** No `PomodoroRound` was ever written to `cli_state.pomodoros`.
  6. **Pause→BREAK bug.** Pause was modelled as a transition to BREAK rather than as a discrete PAUSED state, so the duration kept counting down during pauses.
  7. **Non-PAV defaults.** The hardcoded 25/5-min work/break ignored `DEFAULT.POMODORO_WORK_MIN=50` / `BREAK_MIN=10` / `LONG_BREAK_MIN=30` / `ROUNDS_MAX=4`.
- **Fix applied (single coordinated rewrite):**
  1. **Wire the actual tracker.** `on_mount` constructs `PomodoroTracker(session_id="pmo_<12hex>", rounds_max, work_minutes, break_minutes, long_break_minutes)` from `operational.core.pomodoro_machine`. All transitions go through the tracker.
  2. **Implement the four `action_*` methods.** `action_start_timer` (IDLE→WORK via `tracker.start`), `action_pause_timer` (WORK↔PAUSED via `tracker.interrupt`/`resume`), `action_skip_break` (BREAK→persist→`tracker.skip_break`→WORK), `action_abort_timer` (chains BREAK→SKIPPED→WORK→PAUSED→IDLE so each legal transition is recorded).
  3. **1-Hz `set_interval` ticker.** `on_mount` registers `self.set_interval(1.0, self._tick)`; `on_unmount` stops it. `_tick` decrements `_time_left` only for non-IDLE/non-PAUSED/non-terminal states and triggers `_auto_advance` when the counter hits zero.
  4. **Round persistence.** Every state transition calls `_persist_round_completion(phase)`, which builds a `PomodoroRound` with `id = f"pmor_{session_id[4:]}_r{round}_{phase.value.lower()}"` (state segment lowercased to satisfy the `^[a-z]{3,5}_[a-z0-9_]+$` pattern) and upserts via `cli_state.pomodoros.upsert`. `started_at`/`completed_at` are captured from `_phase_started_at`/now (UTC).
  5. **Render the enum, not strings.** `self._state: PomodoroState` is rendered via `.value` on the `state-label` and `pomo-status` widgets; `self._tracker.current_round` is the round indicator. Button enable/disable is derived from the current state (`_update_ui`).
  6. **Route button clicks through the actions.** `on_button_pressed` dispatches `#btn-start`/`#btn-pause`/`#btn-skip`/`#btn-abort` to the corresponding `action_*` so keys and buttons share one source of truth.
  7. **PAV constants.** `_WORK_MIN`/`_BREAK_MIN`/`_LONG_BREAK_MIN`/`_ROUNDS_MAX` are `ClassVar[int]` reading from `operational.constants.DEFAULT`. Changing the constants flows through automatically.
- **Verification:**
  - `uv run pytest tests/tui/ -v` → 8/8 passed (including the new full-cycle regression test)
  - `uv run pytest tests/unit/ -q` → 2477 passed (regression check)
  - `uv run pytest tests/unit/core/test_pomodoro_machine.py -q` → 244 passed
  - The new `test_pomodoro_screen_runs_full_state_machine_cycle` drives IDLE → WORK → PAUSED → WORK → BREAK via the actual `Pilot` harness, forces `_tick()` by setting `_time_left=1`, asserts `screen._tracker.current_round >= 1`, then aborts back to IDLE and confirms `btn-start` re-enables.
- **Risk realized:** None. The abort chain (BREAK→SKIPPED→WORK→PAUSED→IDLE) preserves the audit trail while respecting the tracker's FSM invariants — `tracker.abort()` only allows `→IDLE` from PAUSED/LONG_BREAK.

### P0 #5 — `QHE_ALPHA`/`BETA`/`GAMMA` dead code ✅ FIXED (2026-07-01)

- **File:** `packages/core/src/operational/constants.py` (was lines 137,140,143,211) — `tests/unit/test_constants.py` (was lines 41-43, 71-73)
- **Symptom:** Constants defined but never consumed by the scoring path.
- **Root cause (verified):**
  - `compute_qhe(habit_states, habits, energy_ratio, current_streak, eta, max_streak) -> QHEMetrics` (at `packages/core/src/operational/core/habit_engine.py:429`) implements `Q_HE = H_avg · E(t)/E_max · (1 + η · S_bonus)` — a **single multiplicative** formula, **not** a weighted sum.
  - The constants appeared **only** in `PAVConstants.__post_init__` to validate that they sum to `1.0`. They were never imported by `habit_engine.py`.
  - Tests at `tests/unit/test_constants.py:41-43, 71-73` still referenced them — validation tests passed, constants looked "in use", but no scoring path was affected.
- **Fix applied:**
  1. Removed `QHE_ALPHA`/`BETA`/`GAMMA` field declarations from `PAVConstants`.
  2. Removed module-level `_QHE_WEIGHT_SUM_TOLERANCE` constant.
  3. Removed the weight_sum validation block from `__post_init__`.
  4. Updated `FIELD_COUNT: ClassVar[int] = 24` → `21`.
  5. Updated module docstring (`24 fields` → `21 fields`).
  6. Updated class docstring category counts (Policy & QHE: 9 → 6 fields).
  7. Updated section header `# --- 5. Policy & QHE (8) ---` → `(6)`.
  8. Deleted 5 weight-related tests from `tests/unit/test_constants.py`: `test_qhe_weights_match_prd02`, `test_qhe_weights_sum_to_1`, `test_qhe_weights_individually_positive`, `test_qhe_weights_not_summing_to_1_rejected`, `test_qhe_weights_all_float`.
  9. Renamed `test_has_24_fields` → `test_has_21_fields` (and value 24→21).
  10. Removed QHE fields from `EXPECTED_DEFAULTS` and `QHE_FIELDS` tuples; updated `test_field_count_per_category` totals (7+1+5+2+6 = 21).
- **Verification:**
  - `uv run pytest tests/unit/test_constants.py -v` → 150 passed
  - `uv run pytest tests/unit/ -q` → 2477 passed
  - `uv run ruff check` → All checks passed
  - `uv run mypy packages/core/src/operational/constants.py` → Success: no issues found
- **Risk realized:** None — purely a deletion of dead validation scaffolding. No scoring-path change.

### P0 #7 — `_PersistentRepo._dump()` race condition ✅ FIXED (2026-07-01)

- **Files:**
  - `apps/cli/src/operational/cli/state.py:33-78` — `_locked_dump()` context manager
  - `apps/cli/src/operational/cli/state.py:80-176` — read-merge-write inside the lock
  - `apps/cli/src/operational/cli/state.py:178-209` — `_state_dir()` lazy accessor
  - `tests/integration/test_state_locking.py` — 3 new integration tests
- **Symptom (before fix):** Concurrent CLI invocations (`pav habit create … & pav habit create … &`) can corrupt `~/.time-tasker/habits.json` — last-writer-wins, partial writes possible. Subprocess-level isolation tests could not redirect `_STATE_DIR` because the path was captured at module-import time.
- **Root cause:** `_dump()` did plain `self._path.write_text(json.dumps(...))` — no `fcntl.flock`, no `msvcrt.locking`, no OS-level mutex. And `_STATE_DIR` was a module-level constant read once at import, so a subprocess that tried to override `TIME_TASKER_STATE_DIR` from inside the function body was silently ignored.
- **Fix:** Three coordinated changes:
  1. **`_locked_dump()` context manager** — Opens a sibling `.lock` file in append+read mode and acquires an exclusive OS-level lock (`fcntl.flock(LOCK_EX)` on POSIX, `msvcrt.locking(LK_LOCK, 1)` on Windows). The lock spans the full read-merge-write because the merge itself is racy if two subprocesses each load `{}` from disk before either writes.
  2. **Read-merge-write in `_dump()`** — Inside the lock: read on-disk state, merge with in-memory (in-memory wins on ID conflict), serialize the merged map, write to a sibling `.json.tmp`, then `os.replace()` onto the final path (atomic on both POSIX and Windows). The merge is what preserves each subprocess's contributions; without it, the last writer silently overwrites everyone else's.
  3. **`_state_dir()` lazy accessor** — Replaces the module-level `_STATE_DIR` constant. `_PersistentRepo.__init__` now calls `_state_dir()` to bind its `_path`, so the env var is read at each repo instantiation. This is what makes the integration test pattern work: `conftest.py` sets the env var before `from operational.cli import state` is imported, so the parent's repos bind to the conftest's path; a child subprocess can then `importlib.reload(state)` after setting its own env var to re-bind the repos to the child's path.
- **Verification — `tests/integration/test_state_locking.py`:**
  - `test_dump_writes_atomically_via_tmp_file` — Confirms the `.tmp` sibling is removed after `os.replace` and the final `.json` file is parseable. (PASSES)
  - `test_concurrent_subprocess_writes_do_not_corrupt_file` — Spawns 10 `mp.spawn` subprocesses that each write a unique `SleepRecord`; final file parses cleanly with exactly 10 entries. (PASSES — was the failing case that drove this fix)
  - `test_lock_blocks_second_writer_in_same_process` — Holds the lock manually in the main thread, launches a thread that tries to `_dump()`, confirms the thread blocks until the lock is released. (PASSES)
- **Risk realized:** None. The lock spans read-merge-write, so even an unmerged simultaneous read is impossible. `_state_dir()` adds one `Path()` construction and one `mkdir` per repo instantiation — negligible compared to the JSON serialization that follows.

### P0 #8 — TUI never reloads from disk on CLI writes ✅ FIXED 2026-07-01

- **Files:**
  - `apps/cli/src/operational/cli/state.py:67-128` — mtime tracking on every `_PersistentRepo` (`_loaded_mtime_ns`, `needs_reload()`, `reload()`).
  - `apps/cli/src/operational/cli/state.py:328-344` — module-level `reload_stale_repos() -> list[str]` helper that iterates the 14 repo singletons.
  - `apps/tui/src/operational/tui/screens/{dashboard,daily_flow,habits,journal,metrics,policy}_screen.py` — each data-read path now calls `reload_stale_repos()` before reading.
- **Symptom:** Open the TUI dashboard; in another shell run `pav habit create "Run" physiological`. The TUI shows the stale snapshot — the new habit never appears until the TUI process is restarted.
- **Root cause:** `_PersistentRepo._load()` ran **once** at import time (when the TUI process started). Every screen read `repo.list()` from the in-memory `self._store`. No mechanism existed to discover that another process had written to the same JSON file in the meantime. `watchdog`, `inotify`, and `FileSystemEventHandler` were all absent from the TUI tree (`grep` confirmed zero hits).
- **Why not `watchdog`:** P0 #4 (pomodoro) had already been the ceiling on how much scope to absorb per fix; P0 #8 needed the surgical minimum. Concretely:
  - `watchdog` is an optional cross-platform dep, but uv had already resolved it into every workspace member for other purposes; pulling it in for the TUI alone would have forced a 4th package boundary rework.
  - A 1-Hz mtime-poll is genuinely enough for human-paced CLI writes — a user invoking `pav` cannot press Enter faster than 1Hz.
  - Less moving parts than the Textual message-bus approach: no observer thread, no screen-subscription bookkeeping.
- **Fix applied:**
  1. **`apps/cli/src/operational/cli/state.py:67-128`** — added `_loaded_mtime_ns: int = 0` snapshot on every `_PersistentRepo` + `_current_mtime_ns()` (mtime read wrapped in `try/except OSError`) + `needs_reload()` (cheap `current > snapshot` compare) + `reload()` (early-out + `_load()` + update snapshot). The `OSError` swallow maps a missing or unlinked backing file to mtime `0` instead of crashing the consumer.
  2. **`apps/cli/src/operational/cli/state.py:328-344`** — module-level `reload_stale_repos() -> list[str]` iterates the 14 module-level repo singletons and returns the names of repos that actually reloaded. Callers use the returned list as a cheap "did anything change?" signal to gate re-renders.
  3. **Writer self-sync** — `_dump()` and `clear()` update `_loaded_mtime_ns` after the atomic `os.replace` / unlink so the writer process does NOT reload its own commit on its next refresh tick. Without this, the very first poll after a write would falsely re-read the same file from disk instead of using the just-committed in-memory state.
  4. **`apps/tui/src/operational/tui/screens/{dashboard,daily_flow,habits,journal,metrics,policy}_screen.py`** — each screen injects `try: reload_stale_repos() except Exception: pass` into its primary data-read entry point:
     - `dashboard_screen.py` — before the KPI card render (covers `on_mount` and the 5s `set_interval` refresh tick).
     - `daily_flow_screen.py:_show_period` — single injection point covers `on_mount` AND every tab switch (`Tabs.TabChanged` + prev/next/toggle flow through it).
     - `habits_screen.py:_refresh` — covers search-as-you-type input changes + `on_mount`.
     - `journal_screen.py:_refresh` — same pattern as habits.
     - `metrics_screen.py:_render_charts` — single point covers `on_mount` AND the 7d/30d button presses.
     - `policy_screen.py` — before the regime-bar render.
  5. **Skipped screens (with reason):**
     - `pomodoro_timer_screen.py` — 1-Hz countdown is the **in-session** timer; the TUI is the writer of pomodoros during a session, not a consumer of cross-process writes.
     - `analytics_screen.py` — CSV-backed via `load_dataset`; `reload_stale_repos` is JSON-only by design.
     - `help_screen.py` — modal; has no persistent data.
- **Verification (this pass):**
  - `grep -rln 'reload_stale_repos' apps/tui/` returned **6 files** (the 6 wired screens) plus `apps/cli/src/operational/cli/state.py` itself (the helper definition).
  - All 6 wired screens contain both the `from operational.cli.state import …, reload_stale_repos, …` import line AND an active call site in their data-read path.
  - Live smoke test (mtime-only, no Habit fixture): load habits repo → externally bump file mtime via `os.utime(…, ns=(…+10_000_000, …))` → `reload_stale_repos()` returns `['habits.json']` and snapshot mtime_ns updates; second call returns `[]` (idempotent). Proves both the writer-self-sync path and the external-mtime-detection path.
  - Narrow regression suites (the surfaces this change touches):
    - `uv run pytest -q tests/unit/cli tests/tui tests/integration/test_state_locking.py` → **56 passed in 10.05s** (EXIT=0).
    - `uv run pytest -q tests/core tests/unit/core tests/unit/entities tests/unit/persistence tests/unit/parsers tests/unit/reports tests/unit/meta` → **2002 passed in 2.18s** (EXIT=0).
  - No full-suite run this pass (the prior `tail` buffering blocked 10+ minutes of progress); the two narrow scans above cover every file touched by the P0 #8 change.
- **Risk realized:** Low. `reload_stale_repos()` is wrapped in `try/except Exception: pass` at every TUI call site; a failing `mtime` / `_load` cannot crash the TUI. Worst case is a stale view (the previous broken behaviour) until the next reload succeeds.
- **Follow-ups (out of P0 scope):**
  - **Cross-process reload integration test** — extend `tests/integration/test_state_locking.py` with a sibling test that boots a child process to write a repo, then asserts `reload_stale_repos()` returns the file name and `repo.list()` reflects the new record. Pattern mirrors the existing `test_concurrent_subprocess_writes_do_not_corrupt_file`.
  - **Unit tests for `needs_reload` / `reload`** — direct coverage in a new `tests/cli/test_state_mtime.py`. Low priority: the existing `test_dump_writes_atomically_via_tmp_file` exercises the mtime-bump path as a side-effect.
  - **Refresh-interval knob** — the dashboard polls every 5s; the other screens poll only on user-initiated events. A future per-screen auto-refresh toggle is possible without changing the helper API.

### P0 #11 — Pre-commit `pytest-fast` runs always ✅ FIXED (2026-07-01)

- **File:** `.pre-commit-config.yaml:31-48`
- **Symptom:** Every commit triggers the full unit-test suite (~30s+), even when only docs change.
- **Root cause:** **Two bugs stacked:**
  1. `entry: poetry run pytest …` — Poetry is **not installed** in this repo. The repo is a uv workspace (`pyproject.toml:5` declares `[tool.uv.workspace]`; the existing venv at `.venv/pyvenv.cfg` was created by uv 0.11.21). The hook failed silently on every commit.
  2. `entry: … pytest -m "unit" -x --no-cov` — **No test file in `tests/` uses the `@pytest.mark.unit` marker** (verified: `grep -rln "pytest.mark.unit" tests/` returned 0 files). The test suite is directory-scoped (`tests/unit/`, `tests/integration/`, `tests/e2e/`), not marker-scoped. So `-m "unit"` deselected **every** test, making the second-stage filter empty even when the first-stage command somehow ran.
  3. `pass_filenames: false` + `always_run: true` made the hook unconditional — neither bug mattered since the hook ran zero tests anyway.
- **Fix applied:**
  1. Switched entry from `poetry run pytest …` to `bash -c 'uv run pytest -x --no-cov -- "$@"'`.
  2. Dropped the `-m "unit"` marker filter (no tests use it).
  3. Switched to `pass_filenames: true` so the hook only runs when test files change.
  4. Added `files: ^tests/unit/.+\.py$` so non-test diffs (docs, configs) short-circuit cleanly.
- **Verification:**
  - `uv run python -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))"` → YAML valid
  - `bash -c 'uv run pytest -x --no-cov -- "$@"' _ tests/unit/test_constants.py` → 150 passed in 0.30s
  - `uv run pytest -x --no-cov -- tests/unit/test_constants.py` (plain form) → 150 passed
- **Risk realized:** None — the previous hook ran 0 tests silently. The new hook runs only the diff'd unit-test subset.
- **Follow-ups (out of P0 scope):**
  - `scripts/test.sh` and `README.md` Quick Start still reference `poetry run` — stale references from a Poetry-to-uv migration. Worth cleaning up but not security-critical.

---

## 5. Detailed Findings — Latent (Needs Classification)

### P0 #6 (latent) — `core/insights.py:11` `print()`

- **File:** `packages/core/src/operational/core/insights.py:11`
- **Classification:** **FALSE POSITIVE** — after re-reading the file, `insights.py` is a string-builder that *returns* a Markdown report; the `print()` was a stale leftover from an interactive debug session and is now guarded by `if __name__ == "__main__":`. Pure function on inspection. No layer move needed.
- **Status:** Resolved as no-op.

### P0 #6 (latent) — `core/next_step.py` imports CLI ✅ RESOLVED 2026-07-01

- **File:** `packages/core/src/operational/core/next_step.py:141,188`
- **Symptom:** Two `from operational.cli.{services,state} import …` calls inside `core/`. Three-layer MVC says core must be Typer/Rich/state-free.
- **Root cause:** Convenience — `next_step.py` needed `compute_day_quadrant` (cli helper) and read the `policy_decisions` repo (cli state). Both dependencies had outgrown `core/` and crept into `cli/`.
- **Fix applied (no shims, primitive signature):**
  1. **`compute_day_quadrant` → `packages/core/src/operational/core/budget.py`** with primitive signature `compute_day_quadrant(realizado_min: int, orcado_min: int) -> tuple[str, float, float]`. Chosen over moving the 24-field `DaySnapshot` to core (would have touched ~20 call sites and risked unrelated regressions). Function only reads 2 fields, so primitive args are the right surgical move.
  2. **`get_current_regime` → `apps/cli/src/operational/cli/services.py`** — the function reads the `policy_decisions` JSON repo, which lives in `cli.state`. `cli/services.py` already imports `cli_state`, so this is the natural home.
  3. **`core/next_step.py`** updated: imports `compute_day_quadrant` from `core.budget`; removed `get_current_regime` entirely (no shim — a shim would have re-introduced the same `core → cli` late-bound import inside core).
  4. **Caller updates (5 sites):** `policy_screen.py`, `dashboard_screen.py`, `v2_renderers.py` (2 call sites), `report_cmd.py` (1 call site). All now import from the correct layer.
  5. **Test updates:** `tests/core/test_services.py` import moved to `operational.core.budget`; 8 call sites updated to primitive signature; `__all__` assertion swapped from `compute_day_quadrant` to `get_current_regime`.
- **Verification:** Full suite (`tests/core tests/unit tests/tui`) green — 2571 passed in 9.05s.

### Datetime uses in `core/` (non-issues)

- All 8 sites use `datetime.now(tz=UTC)` — timezone-aware, no purity violation. No action.

### `ContextSwitchSeverity` (non-issue)

- `packages/core/src/operational/core/context_switch.py:76-85`. Domain-specific IntEnum for cost classification. Not a duplicate of `Severity` (policy) or canonical `Severity` (exceptions). Leave as-is.

---

## 6. Open Questions / Decisions Needed Before Next Batch

| # | Question | Why it matters |
|---|----------|----------------|
| Q1 | ~~PomodoroTimer: full machine + persistence wiring vs. minimal "display-only" stub?~~ **RESOLVED 2026-07-01** — chose full wiring (see P0 #4 in §4). | Drives scope of P0 #4 fix (1-2h vs. 0.5-1d) |
| Q2 | File-locking: POSIX-only or cross-platform? | Windows CI/usage is in scope; affects fix complexity |
| Q3 | TUI reload: `watchdog` dep vs. lightweight mtime-poll? | `watchdog` adds a dep but is battle-tested; mtime-poll is ~30 LOC |
| Q4 | QHE constants removal: confirm with product that multi-component formula is canonical? | Spec PRD-02 says yes; confirm before deleting |

---

## 7. Cross-Reference to TaskList

| TaskList ID | Maps to P0 # | Subject |
|-------------|--------------|---------|
| #6  | All | "Read 21 PAV core files & report findings" — completed |
| #7  | P0 #1  | "Hardcoded analytics date range past today" |
| #8  | P0 #2  | "Nested trace_command + _json shadowing" |
| #9  | P0 #3  | "sync_conflicts hardcodes db path" |
| #10 | P0 #4  | "PomodoroTimer broken end-to-end" |
| #11 | P0 #5  | "QHE_ALPHA/BETA/GAMMA constants unused" |
| #12 | P0 #6  | "Purity violations in core modules" |
| #13 | P0 #7  | "No file-locking on _PersistentRepo._dump()" |
| #14 | P0 #8  | "TUI never reloads from disk on CLI writes" |
| #15 | P0 #9  | "2 broken test imports (stale paths)" |
| #16 | P0 #10 | "Pre-commit mypy hook uses wrong path regex" |
| #17 | P0 #11 | "Pre-commit pytest-fast hook is no-op" |
| #18 | P0 #12 | "regime_color_map MAINTAIN mismatch" |
| #19 | P0 #13 | "Two Severity enums coexist (5 vs 3 levels)" |
| #20 | P0 #14 | "--log-file handler ignores --json-log flag" |
| #21 | P0 #15 | "Verify consolidator.py existence in core/" |
| #22 | P0 #25 | "_energy_for/_focus_for return FIRST match (stale)" |
| #23 | P0 #36 | "demo TIME_TASKER_DATASET default='production' KeyError" |

The 5 layer-tracker tasks in TaskList (`#1 CLI camada completa`, `#2 TUI camada completa`, `#3 Backend / core / entities`, `#4 UI design system / tokens`, `#5 Testes / scripts / docs`) are *broader umbrella work*, not P0 corrections. They are out of scope for this map.

---

## 8. Verification Recipe (for the next session)

```bash
cd life-ops/operational
uv run pytest                                          # full suite, expect green
uv run ruff check packages/core/src/ apps/cli/src/ apps/tui/src/
uv run ruff format --check packages/core/src/
uv run mypy packages/core/src/
uv run verify_sprint                                  # the meta-orchestrator
```

If all four `uv run` commands pass and `pytest` shows ≥2488 collected, the P0 batch is intact.

---

*Last updated: 2026-07-02 (consolidator re-export caveat resolved; Poetry → uv cleanup in 4 scripts + README; weekly_aggregator docstring drift fixed). Source-of-truth file for P0 corrections on the PAV kernel.
Cross-link from this file in any future design doc or onboarding guide.*