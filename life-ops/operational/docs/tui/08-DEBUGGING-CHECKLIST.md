# 08 — Debugging Checklist

> This is the "why does my dashboard look weird?" recipe book. Each entry is a symptom, the most likely cause, and a fix. For deeper debug recipes (breakpoints, profiling, state recovery), see `docs/debug/DEBUGGING-GUIDE.md`. The two documents are complementary: this one is keyed on **visual symptoms**, the other is keyed on **Python-level debugging techniques**.

## 1. ANSI escape codes leaking

**Symptom:** You see literal text like `[36m╭─[0m` or `^[[1;36m⚡[0m` in the output.

**Cause:** A `Console` was built without `no_color=True` while stdout was captured (pipe, `StringIO`, opencode tool, CI runner). Rich emits escape codes that the captured buffer sees as raw text.

**Fix:**

- For code that uses the singleton — `from operational.ui import console` — the singleton is built with `no_color=is_captured()` (`ui/__init__.py:48`). If you see this leak, check that the module is importing the singleton, not building its own `Console`.
- For code that builds a local `Console` (e.g. via `make_console` in `cli/renderers.py:37`), the factory already detects TTY and sets `no_color=not is_tty`. Verify the call site is using `make_console` and not a raw `Console()` constructor.
- If the leak is in output captured by the home menu's `redirect_stdout` (`home.py:59`), the `_run_cmd` cleanup at `home.py:61` already calls `strip_ansi` (`ui/__init__.py:67-73`). If the leak survives, the regex at `ui/__init__.py:32` may be too narrow — extend it.

**Defensive recipe:**

```python
from operational.ui import strip_ansi
text = strip_ansi(captured_stdout)
print(text, end="")
```

## 2. Box characters not rendering

**Symptom:** You see `?` boxes, `â”‚` (mojibake), or `╭` rendered as `â”œ` in Windows terminals.

**Cause:** The terminal does not have a Unicode-capable font, or the codepage is not UTF-8.

**Fix:**

- **Windows 10+ Terminal / Windows Terminal:** set `safe_box=False` (already set on the singleton at `ui/__init__.py:53`) and ensure the terminal uses a Unicode font like Cascadia Code, Consolas, or Cascadia Mono.
- **Old `cmd.exe`:** run `chcp 65001` before invoking `operational` to switch to UTF-8 codepage. Or use Windows Terminal instead.
- **SSH session to a Linux box:** check `locale` — if it is not `en_US.UTF-8` or similar, set `LANG=C.UTF-8` before connecting.
- **CI runner (GitHub Actions, etc.):** the default `ubuntu-latest` image is UTF-8 and supports Unicode. If you see box-character issues in CI, the runner is using a stripped-down image — install `fonts-noto-color-emoji` and a Unicode mono font.

If you must support a no-Unicode terminal, set `safe_box=True` on the console. The box characters degrade to ASCII (`+`, `-`, `|`) and the dashboard becomes less pretty but still readable.

## 3. Text wrapping in middle of word

**Symptom:** A label like `Produtividade` is split across two lines as `Produt-\nividade`, or a numeric value `8.5h` becomes `8.\n5h`.

**Cause:** The column does not have `no_wrap=True`, so Rich's word-wrap algorithm decided to break the token.

**Fix:**

- For **`Table.grid` columns:** `grid.add_column(no_wrap=True)`. Apply to every column that contains short tokens (numbers, axis labels, codes, statuses).
- For **`Table` (non-grid) columns:** same — `t.add_column("Métrica", no_wrap=True)`.
- For **`Text` content inside a `Panel`:** the panel's `width=` argument controls wrap. Set `width=` to at least the longest token's character count, or use `overflow="fold"` to make Rich hard-wrap (still no mid-word breaks) instead of soft-wrap.

The `cartesian_plane` renderer (`ui/components.py:241-275`) is the gold standard — every one of its ~20 columns has `no_wrap=True` to guarantee the plane never deforms.

## 4. Table too wide

**Symptom:** A 3-KPI row stretches to 200 columns wide on a wide terminal, with whitespace between the panels. Or a table's right edge is clipped on a narrow terminal.

**Cause:** `expand=True` (the default) tells Rich to stretch the table to the full terminal width. For grids that compose panels of fixed width, this is wrong.

**Fix:**

- **`Table.grid(expand=False)`** for KPI rows and any panel-composing layout.
- **`Table(expand=False, ...)`** for data tables when the row count is small.
- For inner tables inside a grid cell, set their `width=` to match the column's `min_width=` so the grid does not have to expand to fit.

The cartesian plane is a `Table.grid(expand=False, padding=(0, 0))` (`ui/components.py:271`); the daily report composes it inside a `section_panel` of fixed width.

## 5. Colors not showing

**Symptom:** All output is monochrome — no green, red, or yellow. The Unicode characters and box drawing are fine.

**Cause:** The terminal does not support colors, or the `no_color` flag is set, or `color_system` resolved to `None`.

**Fix:**

- **Check the terminal:** `echo $TERM` (Linux/Mac) or check the Windows Terminal settings. `xterm`, `xterm-256color`, `alacritty`, and `tmux-256color` all support 256 colors. `dumb` does not.
- **Check the singleton:** the `console` is built with `color_system="auto"` and `no_color=is_captured()` (`ui/__init__.py:47-48`). If `is_captured()` returns `True`, colors are disabled. This is correct behavior when stdout is not a TTY.
- **Force colors:** set `FORCE_COLOR=1` in the environment. The `Console(force_terminal=True)` constructor in `cli/renderers.py:make_console` will respect this via Rich's auto-detection.
- **Disable colors explicitly:** set `NO_COLOR=1`. This is the [no-color.org](https://no-color.org/) standard; Rich respects it.

If you are running in a real TTY and colors are still missing, the terminal's `TERM` variable is probably the issue. Set it to `xterm-256color`.

## 6. Console not found

**Symptom:** `ImportError: cannot import name 'console' from 'operational.ui'` or a circular import error.

**Cause:** Either `operational/ui/__init__.py` failed to import (Rich missing, broken install) or a module tried to import from `operational.ui` inside a `cli/commands/*` module that is imported by `ui/`.

**Fix:**

- Verify `pip show rich` returns a version. If not, `pip install rich>=13.0`.
- The correct import in any module is `from operational.ui import console`. Do not import `from operational.ui.console import console` — there is no such submodule; `ui/__init__.py` *is* the console module.
- For circular imports, restructure: do not put `from operational.cli import ...` inside `ui/components.py` or `ui/daily_report.py`. The `ui/` layer is a leaf; it depends only on `rich`, `operational.enums`, and `operational.cli.console` (which re-exports from `ui`).

## 7. Traceback in captured output

**Symptom:** A `RichTraceback` appears in a `StringIO` buffer or in a `| less` pipe, with `Traceback (most recent call last):` formatted in colored blocks.

**Cause:** The Rich traceback handler (`ui/__init__.py:60-64`) is installed **globally** at import time. It catches *every* uncaught exception, including those raised inside the home menu's `redirect_stdout` block.

**Fix:**

- For unit tests that expect a plain Python traceback, set `PYTHONRichTraceback=0` in the environment, or patch `sys.excepthook` to the original before running the test.
- For a captured `--json` output that must not contain a traceback, wrap the controller in `try/except` and call `format_as_json({"error": str(exc)})` — never let an exception escape the controller when `--json` is set.
- To log a traceback to a file without printing it, use `log_error(exc)` (defined in `ui/logging_setup.py`) and let the user see the clean `error_panel` instead.

## 8. Menu option not responding

**Symptom:** You pick option 7 in the home menu, nothing happens, and the menu redraws.

**Cause:** Missing key in the `_route` dict at `cli/home.py:136-147`, or the handler function raises an uncaught exception that is silently swallowed by `_run_cmd`'s `except Exception` clause.

**Fix:**

- Check that the key is in `_route`. If you added a new option, the key must be a string (`"11"`, not `11`) and the value must be a callable with zero arguments.
- If the handler raises, `_run_cmd` (`home.py:68-75`) prints a `Panel` with the error type and message. Look for that panel above the "Press Enter to continue" prompt.
- For submenus, check that the `_submenu` call passes a list of `(key, label, args)` tuples (`home.py:321-331`). The `args` list is passed to `_run_cmd` as `argv`.

## 9. The "blinking cursor" issue

**Symptom:** A blinking block cursor appears in the middle of a panel or table when running interactively.

**Cause:** Rich does not normally emit cursor escape codes, but Windows Terminal + Python's `input()` can leave the cursor in an odd position. The home menu uses `Prompt.ask` (Rich's wrapper) for input, which handles cursor positioning.

**Fix:**

- Avoid using bare `input()` inside a controller. Use `Prompt.ask` from `rich.prompt` so Rich can position the cursor.
- If the cursor is stuck after the home menu exits, add a final `console.print()` to push the prompt to a new line.
- For Windows-specific issues, set `legacy_windows=False` on the Console (already set on the singleton at `ui/__init__.py:52`).

## 10. How to render a single component to a string

**Symptom:** You want to assert on the output of `kpi_card("Energia", "8")` in a unit test, or you want to log the rendered HTML to a file.

**Fix:** Use Rich's `Console.capture` context manager:

```python
from io import StringIO
from rich.console import Console
from operational.ui.components import kpi_card

buffer = StringIO()
capture_console = Console(file=buffer, width=120, color_system=None)
with capture_console.capture() as cap:
    capture_console.print(kpi_card("Energia", "8", color="ok", icon="⚡"))
rendered = cap.get()
# `rendered` is the ANSI-stripped, ready-to-assert string
assert "Energia" in rendered
assert "8" in rendered
```

For HTML output (e.g. for a web dashboard), use `Console(record=True)` + `export_html()`:

```python
from rich.console import Console
console = Console(record=True, width=120)
console.print(kpi_card("Energia", "8", color="ok", icon="⚡"))
html = console.export_html(inline_styles=True)
```

Both patterns are in the [Rich docs](https://rich.readthedocs.io/en/stable/console.html#capturing-output) and are the recommended way to test renderers.

## Quick reference — file:line

| Symptom | File:line to inspect |
|---------|----------------------|
| ANSI leak | `ui/__init__.py:35-37, 67-73` |
| Box characters | `ui/__init__.py:53` |
| Text wrap | `ui/components.py:271-275` (cartesian_plane columns) |
| Table too wide | `ui/components.py:224, 271` (`expand=False` examples) |
| Colors missing | `ui/__init__.py:47-48` |
| Console import | `ui/__init__.py:43` |
| Traceback | `ui/__init__.py:60-64` |
| Menu routing | `cli/home.py:136-147` |
| `redirect_stdout` | `cli/home.py:49-67` |
| Submenu loop | `cli/home.py:297-318` |
| Output formatters | `cli/formatters/base.py:11-50` |
| Color palette | `ui/components.py:31-44` |
| Severity helpers | `ui/components.py:101-164` |
