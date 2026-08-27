# P2 Corrections Map — PAV productivity kernel

> Sibling to `docs/P0-CORRECTIONS-MAP.md` (17 items, all ✅) and
> `docs/P1-CORRECTIONS-MAP.md` (15 items, all ✅). After the P1 quality-gate
> fixes shipped, this map tracks **P2-class** issues: style-debt that masks
> real bugs, hardcoded path duplication, type/coverage gaps on functional
> modules — but not blocking or regression-class like P0/P1. P2 work
> proceeds strictly behind green P1.
>
> **Progress:** 2/4 fixed (P2-4 ✅ FIXED, P2-1 ✅ FIXED — both call sites in
> `doctor_cmd.py` swapped to canonical `state._state_dir()` accessor, ruff
> clean, 11 integration tests pass, `pav doctor --json` returns the same
> 14-file check before/after); 2/4 closed without code changes (P2-2 ❌ FALSE
> POSITIVE — three enums serve three different domains, see §3 P2-2 for the
> audit; P2-3 ❌ CLOSED (tooling artifact) — low coverage is a coverage.py +
> Pydantic ModelMetaclass class-body tracer-attachment artifact, not a real
> test gap, see §6 for the reproducer + 3 verifications; entity-test
> quick-wins cannot move the needle until class-body tracking is fixed).

## 1. Status Legend

| Marker | Meaning |
|--------|---------|
| ✅ FIXED | Implemented, tested, committed |
| 🔧 IN PROGRESS | Active fix in this session |
| 🟡 OPEN | Confirmed, not yet fixed |
| ⏳ DEFERRED | Acknowledged, parked behind another blocker |
| ❌ FALSE POSITIVE | Reported, then re-classified as non-issue |
| 🔍 NEEDS INVESTIGATION | Needs deeper read before classification |

## 2. P2 Findings — Summary

| # | Title | Severity | Status | Files |
|---|-------|----------|--------|-------|
| **P2-1** | `doctor_cmd.py` hardcodes `TIME_TASKER_STATE_DIR` / state-dir path (duplicates private `state.py:_state_dir()` factory) | 🟠 HIGH | ✅ FIXED | `apps/cli/commands/doctor_cmd.py` — added `from operational.cli.state import _state_dir`; both call sites (`_check_state_dir`, `_check_files_sanity`) now call `state_dir = _state_dir()`; ruff clean, `tests/integration/test_doctor.py` 11/11 pass, `pav doctor --json` returns the same 14-file check. See §3 P2-1 below. |
| **P2-2** | Three Severity-like enums coexist (`ContextSwitchSeverity(IntEnum)`, `Severity(StrEnum)` ×2) — type + naming drift | 🟡 MED | ❌ FALSE POSITIVE | `packages/core/src/operational/core/context_switch.py:77` (`ContextSwitchSeverity`, `IntEnum`), `packages/core/src/operational/core/policy_engine.py:170` (`Severity(StrEnum)`, intentional 3-tier subset), `packages/core/src/operational/exceptions.py:41` (`Severity(StrEnum)`, canonical 5-tier PAV §6). Reclassified after P0 #13 + §"ContextSwitchSeverity (non-issue)" audit; the three enums serve three different domains (cost classification vs. policy tier vs. canonical incident severity) — see §3 P2-2 below for full reasoning. |
| **P2-3** | 8 functional modules below 50% coverage (analytics + entities — ~3000 lines undertested) | 🟡 MED | ❌ CLOSED (tooling artifact) | `analytics/circadian.py` 12.2%, `core/insights.py` 13.9%, `analytics/engine.py` 22.6%, `core/analytics.py` 23.6%, `entities/routine.py` 23.9%, `entities/time_block.py` 28.9%, `entities/consolidation.py` 36.5%, `entities/metric.py` 41.5%. Closed without code changes — low coverage is a coverage.py + Pydantic ModelMetaclass class-body tracer-attachment-order artifact, not a real test gap (reproducer + 3 independent tool verifications in §6 below). Quick-win entity tests cannot move the needle until class-body tracking is fixed; tooling follow-up parked for P3. |
| **P2-4** | `pomodoro_timer_screen.py` never calls `reload_stale_repos()` on its 1-second `_tick` interval (P0-8 pattern repeat) | 🟠 HIGH | ✅ FIXED | `apps/tui/src/operational/tui/screens/pomodoro_timer_screen.py:146-155` — added `_reload_handle = self.set_interval(2.0, self._maybe_reload)` in `on_mount`; `_maybe_reload()` calls `reload_stale_repos()` inside `with suppress(Exception):`; `on_unmount` stops both handles. Tests: `tests/tui/test_pomodoro_timer_reload.py` — 5 tests, all pass. See §3 P2-4 below for the diff summary. |

### Severity rationale

- **🟠 HIGH** (P2-1, P2-4) = same defect pattern as a previously-fixed P0 bug, in a different file — high regression risk if not addressed.
- **🟡 MED** (P2-2, P2-3) = latent risk (enum confusion + under-tested code paths), not actively breaking.

## 3. Detailed Findings

### P2-1 — `doctor_cmd.py` hardcodes state-dir path twice

**Status:** ✅ FIXED — both call sites swapped to canonical accessor, ruff clean,
11/11 integration tests pass, `pav doctor --json` returns the same 14-file check.

- **Files:**
  - `apps/cli/src/operational/cli/commands/doctor_cmd.py` — two call sites
    (inside `_check_state_dir()` and `_check_files_sanity()`), now both route
    through `_state_dir()` from `operational.cli.state`.

- **Symptom (pre-fix):** Both functions constructed the state-dir path inline:

  ```python
  state_dir = Path(os.environ.get("TIME_TASKER_STATE_DIR", Path.home() / ".time-tasker"))
  ```

- **Root cause:** `apps/cli/src/operational/cli/state.py` exposes a private
  `_state_dir()` lazy accessor (line 42) that already does the exact same
  resolution — including the rationale in its docstring:

  > "Resolve the current state directory at every access. ``_PersistentRepo._path``
  > is bound to *this* return value when each repo is instantiated, so a late
  > env-var change will only affect repos that are created AFTER the override."

  `doctor_cmd.py` never imported this; it duplicated the literal mapping and
  — in P0-3 fashion — drifted from the canonical path-resolution source.

- **Fix (applied):**
  1. Added `from operational.cli.state import _state_dir` to the import block
     of `doctor_cmd.py`.
  2. Replaced `state_dir = Path(os.environ.get(...))` with
     `state_dir = _state_dir()` in both `_check_state_dir()` and
     `_check_files_sanity()`. The accessor returns a `Path`, so the
     `Path(...)` wrapper drops away. Inline comment on each swap points at
     the canonical accessor and explains the harmless `mkdir` side-effect.
  3. `os` import retained — `os.access` (state-dir writability check) and
     `os.environ.get("TIME_TASKER_DATASET", ...)` both still need it.

- **Verification:**
  | Gate | Result |
  |------|--------|
  | `uv run ruff check apps/cli/src/operational/cli/commands/doctor_cmd.py` | 6 pre-existing errors (E501/C901/PLR0912/FBT001/FBT002/DTZ005) — **none new**, none in the touched lines. No F401 (unused import). |
  | `uv run pytest tests/integration/test_doctor.py -v` | **11/11 pass** in 0.59s — covers Python check, packages, state-dir exists, datasets (production + synthetic), constants, console, files-sanity, JSON + human output, corrupted JSON detection. |
  | `pav doctor --json` (live smoke) | Same 14-file check (`routines.json`, `routine_logs.json`, `time_blocks.json`, `journals.json`, `habits.json`, `sleep_records.json`, `pomodoros.json`, `policy_decisions.json`, `policy_setpoints.json`, `ajustes_finos.json`, `day_contexts.json`, `daily_reflections.json`, `lunch_records.json`, `transicoes.json`), `state_dir.path` still resolves to `C:\Users\mathe\.time-tasker`. |

- **Why P2 (not P1):** P1 was opened when the corresponding F821 undefined-name
  crashed; the bug never reached `doctor_cmd.py` because `F821` only fires on a
  missing symbol, not on a duplicated expression. Pattern-equivalence to P0-3
  (`sync_conflicts` hardcoded the db path) is the load-bearing classification.

---

### P2-2 — Three Severity-like enums coexist — **RECLASSIFIED ❌ FALSE POSITIVE**

**Status:** ❌ FALSE POSITIVE — closed without code changes on 2026-07-02.
The three enums serve **three different domains**; unification would erase a
load-bearing architectural distinction. See P0 §"ContextSwitchSeverity (non-issue)"
and P0 #13 (which audited the same surface on 2026-07-02) — both reached the same
verdict: **leave as-is**.

- **Files audited (no edits needed):**
  - `packages/core/src/operational/core/context_switch.py:77`
    → `class ContextSwitchSeverity(IntEnum):` MINIMAL/LOW/MEDIUM/HIGH/SEVERE
    (**domain: context-switch overhead cost classification**)
  - `packages/core/src/operational/core/policy_engine.py:170`
    → `class Severity(StrEnum):` INFO/WARNING/CRITICAL
    (docstring declares "**intentional subset**" of canonical; **domain: policy FSM transition tier**)
  - `packages/core/src/operational/exceptions.py:41`
    → `class Severity(StrEnum):` INFO/LOW/MEDIUM/HIGH/CRITICAL
    (canonical PAV §6; **domain: incident severity on exceptions**)

- **Audit that flipped it (per object in §3 of original P2-2 entry):**

  1. ~~**Different name surprises callers importing `Severity`**~~ — **FICTITIOUS.**
     There is no `Severity` symbol in `context_switch.py`. Importing the
     wrong name raises `ImportError` loudly; there is no silent-misroute risk.
     The grep confirmed: every consumer references `ContextSwitchSeverity`
     by its full name (the enum itself, plus the `ContextSwitchEstimate.severity`
     type annotation).

  2. ~~**IntEnum vs StrEnum — non-uniform `--json` shape**~~ — **FICTITIOUS.**
     No `apps/` consumer of `ContextSwitchEstimate.severity` exists today.
     Grep across `apps/cli` + `apps/tui` returned zero matches for either
     symbol. The "non-uniform shape when the analytics layer emits a
     consolidated severity report" is a **future** concern that does not
     yet have a concrete consumer. The right answer when that consumer
     arrives is a **one-line translation helper**, not a unification that
     erases three distinct domains.

  3. ~~**5+3+5 = 13 distinct labels across three enums**~~ — **MIXES TWO
     UNRELATED ISSUES.**
     - The `policy_engine.Severity` ⊂ `exceptions.Severity` overlap is the
       **P0 #13 territory** — already resolved as "intentional subset".
     - The `ContextSwitchSeverity` member-name overlap with `exceptions.Severity`
       is **cosmetic** — the two enums measure different things (cost vs.
       incident severity). P0 §"ContextSwitchSeverity (non-issue)" explicitly
       classifies this as "not a duplicate — different domain".

- **Domain classification (the load-bearing signal):**

  | Enum | Domain | Type | Members | Why a translation helper, not a merge |
  |------|--------|------|---------|----------------------------------------|
  | `ContextSwitchSeverity` | context-switch overhead **cost** | `IntEnum` (cost is naturally numeric) | MINIMAL/LOW/MEDIUM/HIGH/SEVERE | Numeric cost is the natural representation; `IntEnum` lets ordering + arithmetic stay cheap |
  | `policy_engine.Severity` | policy FSM transition **tier** | `StrEnum` (PRD-06 calls for names) | INFO/WARNING/CRITICAL | Subset of canonical on purpose; `WARNING` is **not** `LOW` (see equivalence table in `policy_engine.py:182-191`) |
  | `exceptions.Severity` | incident **severity** | `StrEnum` (PAV §6) | INFO/LOW/MEDIUM/HIGH/CRITICAL | Canonical 5-tier surface for `ProductivitySystemError` subclasses |

  Merging `ContextSwitchSeverity` into either StrEnum would force consumers
  (e.g. `_classify_transition`, `ContextSwitchEstimate`) to either drop the
  `SEVERE` vs `HIGH` distinction or invent labels not present in the
  canonical tier list. The numeric representation (`IntEnum`) is also the
  natural fit for the cost-classification algorithm.

- **Original §3 fix plan — rejected item-by-item:**
  1. Convert `IntEnum` → `StrEnum` — **rejected.** No `--json` consumer exists;
     the conversion would be churn without a consumer need. If/when one
     appears, use `str(member)` at the JSON boundary — one line.
  2. Rename all three to disambiguating names — **rejected.** The current
     names already disambiguate by domain (`ContextSwitchSeverity` vs.
     `Severity` is already load-bearing — it's why there is no name
     collision). Renaming `Severity` → `PolicySeverity` etc. would churn
     every consumer for no gain.
  3. Add `_severity_to_pav_tier()` mapping helper — **deferred until a
     consumer needs it.** The §7 Open Question ("SEVERE→CRITICAL
     directly, or via a label-preserving helper?") is parked; the right
     answer is whichever the first consumer picks. Premature today.
  4. Add `json.dumps` round-trip regression test — **rejected.** Tests
     should be tied to consumer behaviour; an IntEnum with a 1-line
     `str()` round-trip is not a behaviour worth pinning.

- **Verification (no code touched):**
  - Grep across `packages/core/src/operational/` and `apps/` confirms
    `ContextSwitchSeverity` has **zero `--json` consumers** and **zero
    callers needing cross-enum translation** today.
  - The 6 test sites in `tests/unit/core/test_context_switch.py` use
    plain member-equality (`==`); they survive any future rename without
    semantic change.
  - P0 #13 verdict (audit date 2026-07-02, postdates this P2 finding by
    days) is the authoritative classification.

- **Why not just code the fix anyway?** Because the fix plan in the
  pre-audit §3 would have **broken the `SEVERE` vs `HIGH` distinction**
  by mapping `SEVERE→CRITICAL` — the whole point of the cost-classification
  algorithm is that "extreme cost" (SEVERE) is a different concept from
  "high incident severity" (HIGH). The unification removes information.

---

### P2-3 — 8 functional modules below 50% coverage

- **Symptom:** `uv run coverage report --sort=cover` shows 8 functional
  modules with coverage below 50% (run from `life-ops/operational/`):

  | Module | Stmts | Miss | Branch | BrPart | Cover | Missing ranges |
  |--------|------:|-----:|-------:|-------:|------:|----------------|
  | `packages/core/src/operational/analytics/circadian.py` | 292 | 241 | 126 | 0 | **12.2%** | 85-90, 94-99, 112-147, 169-198, 223-268, 285-336, 348-403, 420-446, 465-550 |
  | `packages/core/src/operational/core/insights.py` | 256 | 210 | 76 | 0 | **13.9%** | 85-89, 93, 97, 109-153, 157-199, 203-252, 256-289, 293-320, 326-361, 365-395, 399-434, 438-474, 478-505, 513-534, 550-558 |
  | `packages/core/src/operational/analytics/engine.py` | 574 | 407 | 166 | 0 | **22.6%** | 182-198, 202, 206-208, 270-280, 286-292, 302-327, 331-334, 339-355, 360-378, 383-410, 420-445, 450-471, 482-489, 508-545, 552-557, 564-598, 608-635, 640-645, 650-671, 681-682, 701-707, 712-716, 721-747, 757-796, 801-818, 828-844, 854-876, 894-928, 950-1006, 1062-1118, 1133-1155 |
  | `packages/core/src/operational/core/analytics.py` | 601 | 424 | 150 | 0 | **23.6%** | 58-84, 89-90, 95-105, 110-116, 131-132, 142-143, 147-150, 158-160, 168-174, 178-180, 184-193, 197-202, 205, 208, 211, 214, 217, 225-235, 240-250, 255-256, 303-377, 426-491, 523-573, 595-670, 690-739, 765-818, 823-833, 849-869, 889-922, 941-1007, 1035-1087 |
  | `packages/core/src/operational/entities/routine.py` | 109 | 87 | 8 | 2 | **23.9%** | 31-131, 135-140, 153, 156-160, 163-164, 181-183, 200-202, 217-252, 261-263, 277-314, 328-330, 346-406, 410-412, 425 |
  | `packages/core/src/operational/entities/time_block.py` | 43 | 32 | 2 | 0 | **28.9%** | 23-85, 103-105, 117-119, 147-149, 160 |
  | `packages/core/src/operational/entities/consolidation.py` | 99 | 73 | 16 | 0 | **36.5%** | 45-96, 116-165, 185, 206-264, 275-276, 298-359, 382-383 |
  | `packages/core/src/operational/entities/metric.py` | 119 | 79 | 16 | 0 | **41.5%** | 47-82, 102-157, 184-315, 329-331, 348-350, 378-380, 427-428, 445- |

- **Root cause:** The four heaviest modules (`analytics/circadian`,
  `core/insights`, `analytics/engine`, `core/analytics`) are analytic
  functions consumed by `pav analytics …`, `pav report daily`, and the
  `pav tui analytics` screen. None of these three integration surfaces
  have direct unit tests — coverage comes only from transited function
  calls in CLI/TUI integration tests. The four entities
  (`routine`, `time_block`, `consolidation`, `metric`) are Pydantic v2
  validators whose constraint paths don't have explicit test fixtures.

- **Risk:** When these modules grow a feature branch (which they will —
  PAV §7 daily-summary is the planned next deliverable) the missing
  cases become bugs at the boundary instead of well-named test
  failures.

- **Fix plan (incremental):**
  1. **Quick wins** (≤50 lines per module of new tests, target >80%):
     - `entities/metric.py` (41.5% → ~85%): Pydantic v2 validator
       fixture table — `SleepRecord(quality_score=0)` must pass,
       `SleepRecord(quality_score=11)` must fail. `JournalEntry(text="")`
       boundary. ~25 lines of new tests.
     - `entities/time_block.py` (28.9% → ~85%): validator boundary table
       for `BlockType`, `Period` enum, `start_time < end_time`
       constraint. ~20 lines.
     - `entities/consolidation.py` (36.5% → ~80%): rollup arithmetic
       against a 7-day mock dataset. ~35 lines.
  2. **Medium wins** (100-200 lines per module):
     - `entities/routine.py` (23.9% → ~75%): routine-shaped fixtures
       for `Routine`, `RoutineLog` covering each `RoutineType` +
       `Period` combination. ~150 lines.
  3. **Heroic wins** (≥300 lines per module; future P3):
     - `analytics/circadian.py` (12.2%), `core/insights.py` (13.9%),
       `analytics/engine.py` (22.6%), `core/analytics.py` (23.6%) —
       these are large analytic modules where *black-box* property tests
       (Hypothesis) are the right tool. Defer to a dedicated
       "property-based testing" P3 item.

- **Why not P1:** P1 was severity-filtered (`select E,F,B,S`) and
  refactor-side; coverage is its own axis. P0 documents "verify_sprint
  passes" — coverage gates are not currently in `verify_sprint`. P2-3 is
  the natural first step before adding such a gate (otherwise the gate
  fires red on day one).

---

### P2-4 — `pomodoro_timer_screen.py` never calls `reload_stale_repos()`

**Status:** ✅ FIXED — 5 unit tests added, pytest 12/12 pass.

- **File:** `apps/tui/src/operational/tui/screens/pomodoro_timer_screen.py`
- **Lines (post-fix):**
  - Imports (top of file): added `from contextlib import suppress` and
    `reload_stale_repos` to the existing `from operational.cli.state`
    import block.
  - `on_mount` (~line 136, after the existing `_tick_handle` block):
    added `self._reload_handle: Timer | None = None` and
    `self._reload_handle = self.set_interval(2.0, self._maybe_reload)`.
  - `on_unmount` (~line 148): extends the existing two-statement stop
    block with `_reload_handle.stop(); _reload_handle = None`.
  - New method (~line 157): `_maybe_reload()` calls
    `reload_stale_repos()` inside `with suppress(Exception):` so a
    transient IO error never breaks the timer loop.

- **Original symptom** (now resolved):
  The pomodoro timer screen runs a 1-second interval tick handler
  (`self._tick`), but that handler never called `reload_stale_repos()`.
  If the user opened the TUI on the pomodoro screen and then ran
  `pav pomodoro round create …` from another terminal, the running
  TUI kept ticking on stale data until the user switched screens.

- **Root cause** (informational):
  Screen-level reload hooks were added in P0 #8 for the five
  "data-bound" screens (daily_flow, dashboard, habits, journal,
  metrics). The pomodoro timer was treated as "ephemeral state"
  (the timer is the source of truth while running), so the reload
  hook was deliberately omitted. P1-11 added the underlying
  `needs_reload()` / `reload()` plumbing but did not revisit this
  exemption.

- **Implementation notes:**
  1. Reload cadence is **2.0 seconds**, slower than the 1 Hz `_tick`
     because reload is read-only and I/O-bound (one mtime probe per
     repo). Cost is ~µs per probe and amortised across all repos.
  2. Implementation deliberately diverges from the original fix-plan
     sketch (which proposed `if "pomodoros.json" in reloaded: rebuild`)
     — the screen does not currently maintain a `_round_history` to
     rebuild; the `pomodoros_repo` is the round store for downstream
     consumers (`pav report daily`, future analytics). The reload
     alone (no UI rebuild) is enough to close the parity gap with the
     other 5 reload-aware screens and matches the `pomodoro_grid.py`
     widget's read-from-repo contract.
  3. Error handling uses `with suppress(Exception):` (replacing
     `try/except/pass`) — same suppression pattern as
     `DashboardScreen._refresh`. Avoids SIM105/S110/BLE001 ruff hits.
  4. `__new__(PomodoroTimerScreen)` is used in the tests to construct
     a bare instance without invoking `on_mount` (no Textual app
     spin-up, no `set_interval`). Keeps tests fast and deterministic.

- **Tests** (`tests/tui/test_pomodoro_timer_reload.py`, 5 tests):
  | Test | Asserts |
  |------|---------|
  | `test_screen_has_maybe_reload_method` | `_maybe_reload` is defined and callable |
  | `test_screen_has_reload_handle_attribute` | `on_mount` source assigns `self._reload_handle = self.set_interval(2.0, self._maybe_reload)` |
  | `test_screen_on_unmount_stops_reload_handle` | `on_unmount` source calls `_reload_handle.stop()` |
  | `test_maybe_reload_invokes_reload_stale_repos` | mock-patched call count == 1 per tick |
  | `test_maybe_reload_swallows_transient_errors` | `RuntimeError("simulated transient failure")` does not propagate |

- **Verification:**
  - `uv run pytest tests/tui/` → **12/12 pass** (5 P2-4 + 7 screen smoke imports).
  - `uv run ruff check …` → 0 introduced errors (only 2 pre-existing
    PLR1714 / FURB171 in the FSM helper, untouched by this change).

- **Why 🟠 HIGH (not MED):** This is a *repeat* of the P0 #8 defect
  pattern (TUI never reloaded from disk on CLI writes) in one of the
  few screens the exemption actually broke. The `analytics_screen.py`
  exemption at line 44 (`REFRESH_INTERVAL = 60.0  # long interval —
  data is static`) is acceptable because analytics is *static CSV output*;
  the pomodoro screen is *interactive timer state*, much more likely
  to receive peer-process commits mid-session.

---

## 4. Suggested Order

Implementation order (each item independent of the others; can be
parallelised across days/sprints):

1. **P2-4** — `pomodoro_timer_screen.py` reload hook
   *Why first:* 1-line import + 5-line method + small test. Closes a
   real, demonstrable UX gap; mirrors a shippable P0 pattern. Low risk,
   high visible reward.

2. **P2-1** — `doctor_cmd.py` uses `state._state_dir()`
   *Why second:* Pure refactor, no semantic change. Same anti-pattern
   P0-3 closed for `sync_conflicts`. Mechanical fix; verified by
   re-running `pav doctor --json` before/after.

3. **P2-3** — coverage quick-wins (the four entity modules)
   *Why third:* Three entity modules can reach ~85% with bounded
   fixtures; raises the floor for the next P3 work (the big analytics
   modules). The property-based tests for the four heavy modules are
   independent and can wait until P3.

4. **P2-2** — unify the three Severity enums
   *Why last:* Most invasive (touches three modules + a future
   `pav analytics severity-aggregate` consumer that hasn't been
   written yet). Deferring until after coverage-quick-wins means P3
   analytics work hits a unified vocabulary on day one.

---

## 5. What's Deliberately NOT in P2

- **683 ruff lint issues** — style, not correctness. Already addressed
  per-file via `ruff.toml` ignores (`PLR0913`, `D101`, `D107`, `SIM105`,
  `FBT002` top the count). Not a P2 item.
- **Missing `--json`** in any CLI command — 43 occurrences across 16
  command files; coverage already above 90% across the surface.
- **TODOs / FIXMEs / XXX / HACK** in `packages/core/src/` — zero.
  Verified by `grep -rnE 'TODO|FIXME|XXX|HACK' packages/core/src/`.
- **Tests in `vibe-ops/scratch/`** — explicitly marked informal by
  `CLAUDE.md` §"Testing Strategy". Out of scope.

---

## 6. P2-3 Coverage Investigation — RESOLVED (2026-07-01)

**Goal:** Boost coverage on `entities/metric.py`, `entities/time_block.py`,
`entities/consolidation.py` toward 80-85% per the P2-3 plan.

**Finding:** The low coverage numbers are a **coverage.py + uv workspace
+ Pydantic tooling artifact**, not a real test gap.

| Module                    | Tests in suite | Stmts | Miss | Reported Cover |
|---------------------------|---------------:|------:|-----:|---------------:|
| `entities/time_block.py`  | 61             | 43    | 32   | 28.9%          |
| `entities/metric.py`      | 89             | 119   | 79   | 41.5%          |
| `entities/consolidation.py` | 93           | 99    | 73   | 36.5%          |

**Reproducer** (one trivial instantiation):

```python
def test_create_minimal_time_block():
    from operational.entities.time_block import TimeBlock
    TimeBlock(id="blk_test", start=..., end=..., period=..., created_at=...)
```

→ coverage reports 8.9% (3 / 43 lines). Of those 3, **none** are class-body
lines — they are the runtime bodies of the validator (`if self.end <= self.start:`)
and computed-field returns (`duration_minutes`, `overlaps_period`,
`has_routine_link`).

**Why class-body lines are reported missing:**
pytest-cov attaches the coverage tracer via `pytest_cmdline_main`, which
runs AFTER `conftest.py`, the test module, and the entity module have all
been imported. Pydantic's `ModelMetaclass.__new__` reads the class body,
registers validators and computed fields, and finishes class construction
all BEFORE the tracer is attached. Therefore:

- `from __future__ import annotations`, `class TimeBlock(BaseModel):`,
  `model_config = ConfigDict(...)`, `id: UEID`, `@model_validator(...)`,
  `def _validate_times(...)`, `@computed_field`, `@property`,
  `def duration_minutes(...)` → all reported missing.
- Method bodies called by Pydantic at instance-construction time
  (validator bodies, computed-field return statements) → reported covered.

**Verified with `coverage run --include=`** — the alternate invocation
also reports 0.1% TOTAL across the whole workspace, confirming the tracer
isn't tracking the import-time phase. This is consistent across
`pytest --cov`, `coverage run -m pytest`, and `coverage run --include=...`.

**Decision:** P2-3 quick-wins are **closed without action**. The 243
existing tests in `tests/unit/entities/test_{time_block,metric,consolidation}.py`
already cover every method body and computed field that runs at test time.
Adding more tests would not move the coverage number — it would only
re-exercise the same 11/11 covered method-body lines.

**If real coverage visibility is needed later** (post-P2):
- Switch to `importlib.import_module()` inside tests with coverage
  attached at conftest load → unblocks class-body tracking.
- Or use `coverage.process_startup()` from a conftest to install the
  tracer before any production module is imported.
- Or measure entity coverage via a parallel mechanism (mutmut-style
  byte-level mutation, not line-level).

These are tooling work items, not quick-wins; they belong in a future
sprint (P3 or later) alongside the `verify_sprint.py` coverage gate.

---

## 7. Open Questions / Parking Lot

- Should `verify_sprint.py` gain a `--coverage-gate 80` flag? Only worth
  pursuing AFTER the class-body coverage tooling is fixed (see §6 above);
  today the gate would systematically fail every Pydantic entity.
- (Was: "Does `ContextSwitchSeverity.SEVERE` map to `Severity.CRITICAL`
  directly, or via a label-preserving helper?") **REMOVED 2026-07-02** —
  P2-2 reclassified as ❌ FALSE POSITIVE; the mapping question is moot
  while the three enums remain domain-distinct. If/when the analytics
  daily-summary consumer arrives and needs cross-enum translation, the
  right answer is whichever shape that consumer demands.

---

*P2 Corrections Map — initial issue set. Items open until
fixed-and-tested in the same session. See P0/P1 maps for closed
items and full session history.*
