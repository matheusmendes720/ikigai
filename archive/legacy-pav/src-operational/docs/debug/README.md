# Debug Layer — Master Index

> This folder contains the **subatomic debugging** recipes for the `operational` CLI. The TUI side of debugging (visual symptoms: ANSI leaks, broken box characters, table width, etc.) lives in `../tui/08-DEBUGGING-CHECKLIST.md`. This folder covers the Python-level debugging: how to inspect entity state, recover from state corruption, profile performance, and trap exceptions. The two indexes are complementary: the TUI checklist is keyed on *visual symptoms*, this one is keyed on *runtime behavior*.

## Common bugs and their fixes

| Bug | Symptom | Where to look | Fix |
|-----|---------|---------------|-----|
| CRLF in CSV | `csv.Error: new-line character seen in unquoted field` | `docs/debug/COMMON-PITFALLS.md` § 1 | Read with `newline=""`, write with `open(..., "w", newline="", encoding="utf-8")` |
| UTF-8 BOM | First column header is `\ufeffdate` | `docs/debug/COMMON-PITFALLS.md` § 2 | Open with `encoding="utf-8-sig"` |
| ANSI leak in JSON | `jq` chokes on `^[[36m` | `docs/tui/08-DEBUGGING-CHECKLIST.md` § 1 | `strip_ansi` before printing |
| `ValidationError` on import | CSV column missing | `docs/debug/COMMON-PITFALLS.md` § 4 | Check the `extra="forbid"` rules in the entity |
| `FrozenInstanceError` | Tried to mutate a Pydantic frozen model | `docs/debug/COMMON-PITFALLS.md` § 3 | `model.model_copy(update={...})` |
| `typer.BadParameter` | Wrong type for an option | `docs/debug/COMMON-PITFALLS.md` § 5 | Add `Optional[X]` and `None` default |
| Naive datetime crash | `TypeError: can't subtract offset-naive and offset-aware` | `docs/debug/COMMON-PITFALLS.md` § 6 | Use `datetime.now(UTC)` everywhere |
| Empty CSV cell | `_from_jsonable("")` returns `None` | `docs/debug/COMMON-PITFALLS.md` § 7 | Default to `None` in the model |

Full catalog: `COMMON-PITFALLS.md`.

## Where to find logs

The runtime log is at `logs/crash_report.log` (sibling of `docs/`). It is written by `ui/logging_setup.py` and contains:

- Python `logging` records from all `operational.*` modules.
- Rich tracebacks captured by `log_error(exc)`.
- `console.print_exception()` output for handled errors.

The log is **append-only** and **rotated manually** (no logrotate config). To start fresh:

```bash
# PowerShell
Remove-Item logs\crash_report.log
```

```bash
# Bash / WSL
rm logs/crash_report.log
```

The next run will recreate it. There is no log-level filter — every record is captured. If the file grows too large, grep for the timestamp range you care about.

## The doctor command

The CLI ships with a self-diagnosis command:

```bash
operational doctor doctor
```

Implemented in `src/operational/cli/commands/doctor_cmd.py`. It checks:

1. **Python version** — `sys.version_info`, must be ≥ 3.10.
2. **Rich version** — must be ≥ 13.0.
3. **Pydantic version** — must be v2.
4. **Typer version** — must be ≥ 0.12.
5. **State directory** — `$TIME_TASKER_STATE_DIR` (default `~/.time-tasker/`) must exist and be writable.
6. **Active dataset** — `TIME_TASKER_DATASET` env var, must be one of `production`, `synthetic`, `golden`.
7. **Built-in CSV availability** — `docs/synthetic.csv`, `docs/golden.csv` must exist and be parseable.
8. **State file integrity** — each `*.json` in the state dir must parse as JSON and pass its Pydantic schema.
9. **Console singleton** — verifies `is_captured()` and `no_color` are consistent.
10. **PATH for `task` (Taskwarrior)** — not strictly required, but reported.

Run the doctor first when something is off. The output is a checklist with `OK` / `WARN` / `FAIL` per item.

## State inspection

The state lives in `~/.time-tasker/` (overridable via `TIME_TASKER_STATE_DIR`):

```bash
# PowerShell
dir $env:USERPROFILE\.time-tasker\

# Bash / WSL
ls -la ~/.time-tasker/
```

Typical contents:

```text
~/.time-tasker/
├── routines.json
├── blocks.json
├── journals.json
├── habits.json
├── metrics.json
├── policies.json
└── decisions.json
```

Each file is a list of entity records (Pydantic models serialized to JSON). The repositories in `src/operational/persistence/` read these files on every command — there is no in-memory cache, so editing a file with a text editor and re-running the command will pick up the change.

To inspect a single file:

```bash
cat ~/.time-tasker/routines.json | python -m json.tool
```

To count entities:

```bash
cat ~/.time-tasker/routines.json | python -c "import json,sys; print(len(json.load(sys.stdin)))"
```

To clear all state:

```bash
# PowerShell
Remove-Item $env:USERPROFILE\.time-tasker\*.json

# Bash / WSL
rm ~/.time-tasker/*.json
```

Then re-seed with:

```bash
operational demo seed
```

## Python debugger basics

The CLI is standard Python 3.10+ code. You can use the built-in `breakpoint()` (which drops into `pdb` by default) anywhere in the source.

```python
# src/operational/cli/commands/state_cmd.py:240
def state_show():
    snap = build_snapshot()
    breakpoint()  # drops into pdb
    console.print(snap)
```

In `pdb`:

```text
(Pdb) p snap
DaySnapshot(date=date(2026, 6, 8), tipo_dia=TipoDia.HARDCORE, ...)
(Pdb) l .
(Pdb) n  # next line
(Pdb) s  # step into
(Pdb) c  # continue
(Pdb) pp snap.metrics  # pretty-print
```

For a richer experience, set `PYTHONBREAKPOINT=ipdb.set_trace` (or `pudb.set_trace`) in the environment before running the command. The `breakpoint()` call sites do not need to change.

For more recipes (state inspection, profiling, state recovery), see `DEBUGGING-GUIDE.md`.

## Reading order

1. `COMMON-PITFALLS.md` — start here when an error message is unfamiliar. The catalog covers ~10 known issues with their fixes.
2. `DEBUGGING-GUIDE.md` — the long-form guide with step-by-step recipes (breakpoints, profiling, recovery).

For TUI-specific (visual) issues, see `../tui/08-DEBUGGING-CHECKLIST.md`.
