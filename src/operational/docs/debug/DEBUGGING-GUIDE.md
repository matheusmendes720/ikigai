# Debugging Guide

> The `operational` CLI is plain Python 3.10+ — there is no custom debugger, no hidden hooks, no compile step. The full Python ecosystem (`pdb`, `cProfile`, `tracemalloc`, `logging`) works out of the box. This guide collects the recipes that the codebase's own development loop relies on: setting breakpoints, inspecting entity state, trapping exceptions, profiling, and recovering from state corruption. Each section is a self-contained recipe with copy-paste commands.

## Setup breakpoints

Python 3.7+ has the `breakpoint()` builtin. Insert it anywhere:

```python
# src/operational/cli/commands/state_cmd.py (around line 240)
def state_show(json_output: bool = False) -> None:
    snap = build_snapshot()
    breakpoint()  # drops into pdb
    if json_output:
        print(format_as_json(snap.model_dump(mode="json")))
    else:
        render_dashboard(snap)
```

Run:

```bash
operational state show
```

The process stops at `breakpoint()` and you are in `pdb`:

```text
> /path/to/state_cmd.py(244)state_show()
-> if json_output:
(Pdb) p snap.date
datetime.date(2026, 6, 8)
(Pdb) pp snap.metrics
MetricBlock(energy=8, focus=9, sleep_hours=7.2)
(Pdb) n  # next line
(Pdb) s  # step into render_dashboard
(Pdb) c  # continue
```

For a richer UI, set `PYTHONBREAKPOINT`:

```bash
PYTHONBREAKPOINT=ipdb.set_trace operational state show
```

Or for `pudb` (terminal UI debugger):

```bash
PYTHONBREAKPOINT=pudb.set_trace operational state show
```

The `breakpoint()` calls do not need to be removed for production — they cost ~1µs per call when not triggered. Strip them only before a release commit if you want a clean diff.

## Inspecting entity state

Repositories are at `src/operational/persistence/`. Each one has a `list()` method that returns a list of Pydantic model instances. To inspect the live state from inside a breakpoint:

```python
# In a breakpoint inside state_cmd.py
from operational.persistence.routine_repo import RoutineRepository
repo = RoutineRepository()
routines = repo.list()
p routines  # [<Routine name='Acordar' ...>, <Routine name='Shutdown' ...>]
p len(routines)  # 2
p routines[0].model_dump()  # full dict
```

The repositories are stateless (no in-memory cache), so `repo.list()` always reads from `~/.time-tasker/*.json` fresh.

For a quick one-liner from the shell:

```bash
operational routine list --json | python -m json.tool | head -30
```

This gives you the full JSON dump of all routines, formatted for inspection.

## Inspecting JSON state

The state files are pretty-printed JSON. To inspect one without booting the CLI:

```bash
# Bash / WSL
cat ~/.time-tasker/routines.json | python -m json.tool
```

```powershell
# PowerShell
Get-Content $env:USERPROFILE\.time-tasker\routines.json | python -m json.tool
```

To query a specific field across all records:

```bash
cat ~/.time-tasker/routines.json | python -c "
import json, sys
data = json.load(sys.stdin)
for r in data:
    print(f\"{r['name']:30s}  {r['period']:8s}  {r['type']}\")
"
```

To check schema validity of every file in the state dir:

```bash
for f in ~/.time-tasker/*.json; do
    echo "--- $f ---"
    python -c "
import json
from operational.persistence.${f%.json}_repo import ${f%.json^}Repository
data = json.load(open('$f'))
repo = ${f%.json^}Repository()
for d in data:
    repo._validate(d)  # raises ValidationError on bad data
print('  OK')
"
done
```

(Adjust the repository class names to match — see `src/operational/persistence/` for the exact list.)

## Inspecting CSV data

The two built-in datasets live in `docs/synthetic.csv` and `docs/golden.csv`. To peek at them:

```bash
# Bash / WSL
head -5 docs/golden.csv
```

```text
date,tipo_dia,wake_h,bed_h,sleep_h,energy,focus,pomodoros_s1,pomodoros_s2,pomodoros_s3,eat_min,rest_min,pesado,quality
2026-06-02,HARDCORE,4,20,8.0,9,9,4,4,4,15,15,false,9
2026-06-03,CURSO,5,21,8.0,8,8,3,4,3,20,20,false,8
2026-06-04,LIVRE,6,22,8.0,7,7,2,3,2,25,30,false,7
2026-06-05,DESCANSO,7,23,8.0,6,6,1,1,1,30,45,false,6
```

To count rows:

```bash
wc -l docs/golden.csv docs/synthetic.csv
```

To check that a CSV is parseable by the loader (`src/operational/cli/csv_loader.py`):

```bash
python -c "
from operational.cli.csv_loader import load_csv
data = load_csv('docs/golden.csv')
print(f'{len(data)} rows loaded')
print(data[0])
"
```

## Console capture for testing

To render a single component to a string (e.g. for an assertion in a unit test), use `Console.capture`:

```python
import io
from rich.console import Console
from operational.ui.components import kpi_card

def test_kpi_card_contains_title():
    buf = io.StringIO()
    con = Console(file=buf, width=120, color_system=None, force_terminal=False)
    with con.capture() as cap:
        con.print(kpi_card("Energia", "8/10", color="ok", icon="⚡"))
    rendered = cap.get()
    assert "Energia" in rendered
    assert "8/10" in rendered
```

`color_system=None` and `force_terminal=False` together disable ANSI codes. The `width=120` matches the singleton's layout. The output of `cap.get()` is a plain string with no escape codes.

For an HTML export (e.g. for snapshot tests in CI):

```python
from rich.console import Console
con = Console(record=True, width=120)
con.print(kpi_card("Energia", "8/10", color="ok"))
html = con.export_html(inline_styles=True)
# Save to file, diff against golden, etc.
```

## Trapping exceptions

The CLI has two layers of exception handling:

1. **Controllers** wrap their main body in `try/except` and call `error_panel` for the user. Example: `state_cmd.py:240-260`.
2. **The home menu** wraps every `_run_cmd` in `try/except` and prints a `Panel` with the error type and message (`home.py:68-75`).

To add a temporary debug trap inside a controller:

```python
try:
    snap = build_snapshot()
except Exception as e:
    breakpoint()  # inspect the failure
    raise
```

Or to log the exception with full context without breaking the flow:

```python
from operational.ui.logging_setup import log_error
try:
    snap = build_snapshot()
except Exception as e:
    log_error(e, context={"date": str(date.today())})
    console.print(error_panel(
        str(e),
        contexto=f"date={date.today()}",
        hint="Run `operational doctor doctor` for diagnostics.",
    ))
    raise typer.Exit(code=1)
```

`log_error` is defined in `src/operational/ui/logging_setup.py` and writes the full Rich traceback to `logs/crash_report.log`.

## Pydantic validation errors

`pydantic.ValidationError` is the most common error in this codebase. It has an `.errors()` method that returns a list of dicts with `loc`, `msg`, `type`, and `input`:

```python
from pydantic import BaseModel, Field
from operational.entities.habit import Habit, HabitCategory

try:
    Habit(name="X", category="BAD_VALUE", qhe=0.5)
except Exception as e:
    if hasattr(e, "errors"):
        for err in e.errors():
            print(f"{err['loc']}: {err['msg']}  (input={err['input']!r})")
```

Typical output:

```text
('category',): Input should be 'physiological', 'cognitive', 'behavioral'  (input='BAD_VALUE')
```

The `loc` tuple is the path to the field. For nested models, it can be multi-level. The `input` is the actual value that failed validation.

To find which field is the offender quickly, add a `breakpoint()` inside the `except`:

```python
except Exception as e:
    breakpoint()
    raise
```

The `e.errors()` list is in scope and you can inspect each entry.

## The Rich traceback

The Rich traceback handler is installed at import time (`ui/__init__.py:60-64`). It catches *every* uncaught exception and prints a beautiful, colorized traceback with locals (`show_locals=True`).

To read the traceback effectively:

1. **Read top-down.** The deepest frame is the most recent call, but the *cause* is usually a few frames up — in the function that passed the bad value.
2. **Read the locals panel.** Each frame has a side panel with the local variables. Find the `self` or the function arguments; one of them will have the bad value.
3. **Check the `input` field** if it is a Pydantic error. The actual offending value is right there.

To get the *plain* Python traceback (e.g. for a CI log):

```bash
PYTHONRichTraceback=0 operational state show
```

Or set the env var in the test:

```python
import os
os.environ["RichTraceback"] = "0"
# then import operational
```

## Performance profiling

For a one-shot profile of a single command:

```bash
python -c "
import cProfile, pstats
from operational.cli.app import app

profiler = cProfile.Profile()
profiler.enable()
app(args=['state', 'show'], standalone_mode=False)
profiler.disable()

stats = pstats.Stats(profiler).sort_stats('cumulative')
stats.print_stats(20)
"
```

The `print_stats(20)` shows the top 20 functions by cumulative time. Look for:

- `repo.list()` calls — these re-read JSON from disk every time. If they dominate, add a TTL cache.
- `model_dump()` calls — Pydantic v2 is fast, but recursive `model_dump` on large graphs can be slow.
- `cartesian_plane` / `sparkline` / `pomodoros_grid` — these are pure-Python string builders. Should be sub-millisecond.

For a flame graph (requires `flameprof`):

```bash
pip install flameprof
python -c "
import cProfile, pstats
from operational.cli.app import app
profiler = cProfile.Profile()
profiler.enable()
app(args=['state', 'show'], standalone_mode=False)
profiler.disable()
stats = pstats.Stats(profiler).sort_stats('cumulative')
stats.print_stats(50)
" | flameprof > /tmp/operational-flamegraph.html
```

## Memory profiling

For a memory profile of a long-running process:

```python
import tracemalloc
tracemalloc.start()

# ... run the command ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics("lineno")
for stat in top_stats[:10]:
    print(stat)
```

`tracemalloc` tracks every Python allocation. The output is "file:line" + size. Look for:

- Pydantic model creation in tight loops — should be fine, Pydantic v2 uses `__slots__` on its models.
- `format_as_json` on large datasets — the JSON string is materialized all at once. Use `format_as_json(..., indent=None)` for compact output.
- String concatenation in renderers — `Text.append` is the right way; `"a" + "b"` allocates a new string each time.

To find the biggest allocation site at a given moment:

```python
import tracemalloc
tracemalloc.start()
# ... do the suspect work ...
snap = tracemalloc.take_snapshot()
snap.statistics("traceback")[:5]  # top 5 allocation sites by traceback
```

## State corruption recovery

The most common state corruption is a half-written JSON file (e.g. the process was killed mid-write). The repositories handle this gracefully: if a file is missing, they return an empty list. If a file is malformed, the loader raises a `JSONDecodeError` and the command fails with a clean error.

To recover from a corrupted state:

1. **Backup the current state:**

   ```bash
   cp -r ~/.time-tasker/ ~/.time-tasker.backup.$(date +%Y%m%d)
   ```

2. **Identify the corrupt file:**

   ```bash
   for f in ~/.time-tasker/*.json; do
       python -c "import json; json.load(open('$f'))" 2>&1 | grep -q Error && echo "CORRUPT: $f"
   done
   ```

3. **Remove the corrupt file** (or repair it by hand if you know the schema):

   ```bash
   rm ~/.time-tasker/routines.json  # example
   ```

4. **Re-seed from a dataset:**

   ```bash
   TIME_TASKER_DATASET=synthetic operational demo seed
   ```

   This loads the synthetic dataset into the empty state.

5. **Verify:**

   ```bash
   operational doctor doctor
   ```

The state is **always** recoverable because there is no external service backing it. Wiping the directory and re-seeding is a 5-second operation.

For finer control, individual commands accept `--clear` to reset their own data:

```bash
operational routine clear   # clears routines.json only
operational habit clear     # clears habits.json only
```

The `operational demo clear` command wipes all state in one shot (with a confirmation prompt).
