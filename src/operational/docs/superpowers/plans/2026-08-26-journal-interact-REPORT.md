# Journal Interact — Implementation Report

> **Feature:** `pav journal interact` — L2 questionary session for systematic daily time input
> **Plan:** `2026-08-26-journal-interact-questionary.md`
> **Branch:** `gitbutler/workspace` → `master`
> **Commits:** `b0ec0a0` → `210bed2` (5 commits, all approved)
> **Date:** 2026-08-26

---

## Executive Summary

Added `pav journal interact` — a systematic, guided daily journal session that collects sleep times, time blocks with start/end pairs, pomodoro rounds, energy/focus/mood ratings, and free-form narrative notes, then upserts all corresponding PAV entities in one command. The feature introduces zero breaking changes: existing `journal create` and `journal list` are regression-tested and fully preserved.

**Quality gate:** Final review by Senior Code Reviewer (opus) — Ready to merge. No Critical or Important issues.

---

## What Was Built

### New Files (4)

| File | Lines | Purpose |
|---|---|---|
| `packages/core/src/operational/input_validation.py` | 82 | Pure-stdlib HH:MM validators (shared CLI/TUI) |
| `apps/cli/src/operational/cli/commands/journal_interact_cmd.py` | 321 | L2 questionary session — 5 sections, thin Typer controller |
| `tests/integration/test_journal_interact.py` | 190 | 7 integration tests with monkeypatched questionary |
| `tests/unit/test_input_validation.py` | ~65 | 9 unit tests for HH:MM validators |
| `packages/core/src/operational/meta/factories.py` | +57 | `make_routine_log` factory added |

### Modified Files (2)

| File | Change | Purpose |
|---|---|---|
| `apps/cli/pyproject.toml` | +1 line | Added `questionary>=2.0` dependency |
| `apps/cli/src/operational/cli/app.py` | +30/−3 | Registered `journal interact` under `journal` typer |

---

## Architecture

```
packages/core/src/operational/
├── input_validation.py          # NEW — pure stdlib, shared CLI/TUI
│   ├── HHMMValidationError      # custom ValueError subclass
│   ├── parse_HHMM(value: str) → tuple[int, int]       # parse only
│   ├── validate_HHMM(value: str) → time                 # parse + range-check
│   └── validate_block_times(start, end) → (start, end, minutes)
│
└── meta/factories.py           # MODIFIED — +make_routine_log
    └── make_routine_log(routine_id, date, period, routine_type, text, ...)

apps/cli/src/operational/cli/
├── commands/journal_interact_cmd.py   # NEW — thin Typer controller
│   ├── _ask_hhmm(prompt, default) → time        # retry loop with validation
│   ├── _ask_block(prompt, default) → (start, end, minutes)
│   ├── _infer_period_from_time(t) → Period      # MANHA/TARDE/NOITE
│   └── interact(target_date, json_output)       # 5-section session
│
└── app.py                    # MODIFIED — journal_interact_cmd merged under journal
```

**Global constraints verified end-to-end:**
- ✅ Thin Typer controller — no business logic in `journal_interact_cmd.py`
- ✅ All time validation via `input_validation.py` (no raw `time.strptime`)
- ✅ All entity construction via `meta/factories.py` factories
- ✅ All writes via `_PersistentRepo` singletons from `cli/state.py`
- ✅ No framework imports in `packages/core/` — `input_validation.py` imports only `datetime.time`
- ✅ `journal create` / `journal list` regression-tested (2 dedicated tests)
- ✅ `journal interact` registered as `journal interact` subcommand
- ✅ 7 integration tests covering happy path, JSON flag, minimal input, invalid date, empty answers, L1 preservation

---

## The 5-Section Session

```
pav journal interact [--date YYYY-MM-DD] [--json]

1/5 ⏰ Sleep
   Wake-up time (HH:MM)       → validate_HHMM → SleepRecord
   Sleep onset time (HH:MM)
   Sleep quality (1-10)

2/5 🕐 Time Blocks  [loop — press Enter to finish]
   Block label (e.g. "Morning Focus", "Lunch Pause")
   Start and end (HH:MM - HH:MM) → validate_HHMM + validate_block_times
   [repeat]

3/5 🍅 Pomodoros
   Rounds completed today (0-12)

4/5 ⚡ Metrics
   Energy (1-10)
   Focus (1-10)
   Mood morning (1-5)
   Mood evening (1-5)

5/5 📝 Notes
   Free-form narrative (appended to JournalEntry.entry_text)
```

**Output entities per session:**
- `SleepRecord` (if quality 1-10)
- `TimeBlock` (one per labeled block)
- `PomodoroRound` (count only — timer is a separate TUI screen)
- `JournalEntry` (periods_covered inferred from block-start hours + wake time)
- `RoutineLog` (one per time block — ties block back to a routine pattern)

---

## Validation Design

```
parse_HHMM("05:30")   → (5, 30)     # pure parsing, raises HHMMValidationError on bad format
validate_HHMM("05:30") → time(5, 30)  # parse + range check (0-23h, 0-59m)

validate_block_times(time(5,0), time(8,30))
  → (time(5,0), time(8,30), 210)   # raises ValueError if end <= start
```

`HHMMValidationError` is a custom subclass of `ValueError` with a human-readable `.args[0]` — used to distinguish format errors (should retry) from cancelled input (should exit).

---

## Test Strategy

**Challenge:** `CliRunner.invoke(input="...")` pipes to stdin, but `questionary` reads from `prompt_toolkit`'s Vt100 terminal — the two don't connect in a headless test environment.

**Solution:** `_patch_questionary_ask` monkeypatches `questionary.Question.ask` with a callable that returns pre-programmed answers, bypassing prompt_toolkit entirely:

```python
def _patch_questionary_ask(answers: list[str]):
    def fake_ask(self):
        return answers.pop(0) if answers else None
    monkeypatch.setattr("questionary.Question.ask", fake_ask)
```

**Test isolation:** `conftest.py` exports `TIME_TASKER_STATE_DIR` to a tmp dir **before** importing the app (state is read at module-load). The autouse `_isolated_state` fixture clears all 15 repos before and after every test.

**7 tests:**
| Test | Scenario |
|---|---|
| `test_journal_interact_creates_all_entities` | Full session, all 5 sections answered |
| `test_journal_interact_with_minimal_input` | Empty block loop, default values |
| `test_journal_interact_json_flag_returns_valid_payload` | `--json` flag emits parseable JSON |
| `test_journal_interact_invalid_date_exits_with_error` | Bad `--date` format → exit 1 |
| `test_journal_interact_empty_answers_do_not_crash` | Empty input throughout → graceful exit |
| `test_journal_create_still_works` | Regression: `journal create` intact |
| `test_journal_list_still_works` | Regression: `journal list` intact |

---

## Commit History

| Commit | Description | Review |
|---|---|---|
| `b0ec0a0` | feat(core): add input_validation module with HHMM validators | Approved (Task 1) |
| `dfc1e53` | fix(core): align validate_block_times error message to brief spec | Approved (Task 1 fix) |
| `d214e83` | feat: add questionary>=2.0 dependency + make_routine_log factory | Approved (Task 2) |
| `6d134c6` | feat(cli): add journal interact L2 command with questionary | Approved (Task 3) |
| `210bed2` | fix: remove dead _now_naive helper and stale path comment | Post-review cleanup |

---

## Open Minor Items (Non-Blocking)

These were identified in the final review and are tracked for future cleanup:

1. **`_infer_period_from_time`** — duplicated hour→Period logic (should derive from `Period.default_start_hour`/`default_end_hour` rather than hardcoding 3-7/8-17/18-2 windows)
2. **`block_id` round-trip test** — `make_routine_log` exposes 6 optional kwargs but only one default-args test exists
3. **`pav journal --help` smoke test** — would assert `interact` is listed as a subcommand
4. **`routine_type` selection** — always writes `RoutineType.CORE` even for Lunch Pause blocks (transition)
5. **`routine_id` is fabricated** — synthesizes `rou_interact_<date>` per day with no backing `Routine` entity

None of these are blockers for merge.

---

## How to Use

```bash
cd life-ops/operational

# Interactive session (today)
pav journal interact

# Interactive session (specific date)
pav journal interact --date 2026-08-25

# JSON output (for scripting / piping to other tools)
pav journal interact --date 2026-08-25 --json
```

Sample `--json` output:
```json
{
  "journal_id": "jrn_<hex>",
  "date": "2026-08-25",
  "sleep": { "bedtime": "23:00", "wake": "06:00", "quality_score": 7 },
  "blocks": [
    { "id": "blk_<hex>", "label": "Morning Focus", "start": "06:00", "end": "08:30", "duration_minutes": 150, "period": "MANHA" }
  ],
  "pomodoros": 4,
  "energia": 7,
  "foco": 8,
  "humor_morning": 4,
  "humor_evening": 3,
  "note_preview": "Good deep work session..."
}
```
