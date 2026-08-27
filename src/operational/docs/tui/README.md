# TUI Layer — Master Index

> The `operational` CLI is a single-process, fully local productivity orchestrator. Its TUI is built entirely on [Rich](https://rich.readthedocs.io/) — **no `prompt_toolkit`, no `textual`, no curses**. Every panel, table, bar, and timeline is a Rich renderable produced by a small set of factory functions. This folder documents that layer: what it is, how it is wired, and how to extend it safely.

## What is the TUI?

The "TUI" here is a **120-column dashboard**, not a full-screen interactive app. There is one Rich `Console` singleton (`src/operational/ui/__init__.py:43`), one home menu (`src/operational/cli/home.py`), and a set of pure-view factory functions in `src/operational/ui/components.py` and `src/operational/cli/renderers.py`. The layout primitives are `Table.grid`, `Panel`, `Text`, and `Group` — never raw string concatenation. This keeps alignment stable across terminals, lets Rich handle Unicode box-drawing, and makes it trivial to swap the whole layer for `--json` output.

The home menu itself is **not** a Textual app. It is a `while True:` loop that prints a numbered `Table` and calls `rich.prompt.Prompt.ask()` to dispatch to in-process Typer commands via `redirect_stdout`. Commands that want to render the dashboard call the same Rich factories and stream output through the same console.

## TUI layer at a glance

| File | Role | Key symbols |
|------|------|-------------|
| `src/operational/ui/__init__.py` | Console singleton | `console`, `CONSOLE_WIDTH`, `is_captured`, `strip_ansi` |
| `src/operational/ui/components.py` | View factories (atomic + composite) | `kpi_card`, `section_panel`, `next_step_panel`, `error_panel`, `pomodoros_grid`, `cartesian_plane`, `progress_bar`, `sparkline`, `severity_text`, color & quadrant dicts |
| `src/operational/ui/daily_report.py` | Daily-report compositors | `build_next_step_panel`, daily composite builder |
| `src/operational/ui/logging_setup.py` | Logging bridge | forwards `logging` records into Rich |
| `src/operational/cli/renderers.py` | Alternative/extended renderers | `make_console`, `metric_table`, `timeline_h`, `next_step`, `input_summary`, `section_header`, `flag_glossary_panel` |
| `src/operational/cli/home.py` | Interactive menu | `MENU_ITEMS`, `home`, `_run_cmd`, workflow flows |
| `src/operational/cli/formatters/base.py` | Non-Rich output | `format_as_json`, `format_as_table`, `format_as_markdown` |

The CLI surface is **12 Typer subcommands + 1 home command** (`src/operational/cli/app.py:38-52`): `routine`, `block`, `journal`, `habit`, `metric`, `policy`, `demo`, `report`, `state`, `reflect`, `lunch`, `doctor`, plus the `home` entry point.

## Layout conventions

- **Width is fixed at 120 columns** (`CONSOLE_WIDTH = 120`, `ui/__init__.py:31`). The console is built with `width=CONSOLE_WIDTH` so layout is predictable regardless of the actual terminal size.
- **Soft wrap is on** (`soft_wrap=True`, `ui/__init__.py:45`) so words are not split mid-syllable when forced past the right margin.
- **No string concatenation for alignment.** If a panel needs a 2- or 3-column KPI row, use `Table.grid(expand=False, padding=(0, 2))` with `no_wrap=True` on each column. See `04-LAYOUT-GRID-SYSTEM.md`.
- **Severity is the only color axis.** Every colored element is tagged with a `severity` (`ok`, `warn`, `crit`, `info`, `muted`, `None`) or a semantic key (`primary`, `sleep`, `hardwork`, …) that maps to `COLORS` in `ui/components.py:31-44`.

## Color palette

11 named colors live in `COLORS` at `ui/components.py:31-44`:

| Key | Rich name | Typical use |
|-----|-----------|-------------|
| `primary` | `cyan` | Headers, section titles |
| `ok` | `bright_green` | Good / completed |
| `warn` | `yellow` | Watch out |
| `crit` | `bold red` | Critical failure |
| `info` | `deep_sky_blue1` | Neutral info |
| `muted` | `grey58` | Footnotes, sub-text |
| `sleep` | `dodger_blue2` | Sleep / EASE |
| `hardwork` | `green3` | Hardwork / CORE |
| `ease` | `magenta` | EASE ritual |
| `energy` | `yellow1` | Energy metric |
| `focus` | `deep_sky_blue1` | Focus metric |
| `transition` | `deep_pink1` | Transition rituals |

(The dict has 12 entries; the **semantic** count used by the spec is 11 plus the `transition` accent.) Day-type and quadrant palettes live alongside — see `04-COLOR-PALETTE.md`.

## Output formatters

Every command supports `--json`. The three formatters in `src/operational/cli/formatters/base.py`:

- `format_as_json(data)` — pretty-printed JSON, with Pydantic models auto-serialized via `model_dump(mode="json")` and datetimes via `isoformat()` (line 11-22).
- `format_as_table(headers, rows)` — plain `|`-separated text (line 25-45). Suitable for piping into `column -t` or `less`.
- `format_as_markdown(text)` — wraps a string in a fenced code block (line 48-50). Lightweight — does not produce a real Markdown table.

See `07-OUTPUT-FORMATTERS.md` for the full dispatch rules and examples.

## TTY detection

`is_captured()` at `ui/__init__.py:35-37` returns `True` whenever `sys.stdout` is `None` or `not sys.stdout.isatty()`. It is read once at module import time and passed to the `Console(..., no_color=is_captured())` constructor (line 48). This is the single switch that prevents ANSI escape codes from leaking when:

- The home menu captures output via `contextlib.redirect_stdout` (`cli/home.py:59`).
- Output is piped to `less`, `tee`, or a file.
- Output is captured by opencode / CI / pytest.

For any captured text that has already been emitted, `strip_ansi(text)` (line 67-73) removes the escape sequences with a regex.

## Debugging checklist

If the dashboard looks wrong, jump to `08-DEBUGGING-CHECKLIST.md` and `docs/debug/DEBUGGING-GUIDE.md`. The most common symptoms and their fixes are:

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `[36m╭─[0m` literal text in output | `is_captured()` not honored | Use `format_as_json` or set `no_color=True` on the inner console |
| Box characters render as `?` | Terminal has no Unicode font | Set `safe_box=True` or use a Unicode-capable terminal |
| Text breaks mid-word | `soft_wrap=False` or `no_wrap=False` | Set `soft_wrap=True` on the console, `no_wrap=True` on the column |
| Table wider than the terminal | `expand=True` on a wide `Table.grid` | Set `expand=False` and explicit `min_width` |
| Menu option does nothing | Missing key in `_route` | Add handler to `routes` dict in `home.py:136` |
| Captured stdout is blank | Inner console used `force_terminal=True` | Wrap the call in `redirect_stdout` and call `strip_ansi` (`home.py:49-67`) |

## Reading order

1. `01-CONSOLE-LIFECYCLE.md` — start here, the Console singleton sets every downstream default.
2. `02-COMPONENT-CATALOG.md` — the factory functions in `ui/components.py`.
3. `03-LAYOUT-GRID-SYSTEM.md` — `Table.grid` patterns used to compose them.
4. `04-COLOR-PALETTE.md` — color, severity, and quadrant vocabulary.
5. `05-HOME-MENU.md` — the interactive dispatcher.
6. `06-INTERACTIVITY.md` — `Prompt.ask`, `Confirm.ask`, `IntPrompt.ask`.
7. `07-OUTPUT-FORMATTERS.md` — `--json` dispatch.
8. `08-DEBUGGING-CHECKLIST.md` — the "why does my dashboard look weird?" recipes.

For deeper debug recipes (breakpoints, profiling, state recovery), see `docs/debug/`.
