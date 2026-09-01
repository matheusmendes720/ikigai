# 01 — Console Lifecycle

> The `operational` CLI has exactly **one** Rich `Console`. It is created at import time inside `src/operational/ui/__init__.py` and shared by every command, controller, and renderer. There is no other `Console()` constructor in the source tree (the alternative `make_console()` factory in `cli/renderers.py:37` is a **deliberate duplicate** kept for reports that want `force_terminal=True`; new code should import `console` from `operational.ui`).

## The single Console

```python
# src/operational/ui/__init__.py:43-54
console: Console = Console(
    width=CONSOLE_WIDTH,
    soft_wrap=True,
    force_terminal=False,  # let Rich auto-detect; we only force width
    color_system="auto",
    no_color=is_captured(),
    highlight=True,
    markup=True,
    emoji=True,
    legacy_windows=False,
    safe_box=False,  # Use full Unicode box characters (╭─╮ etc)
)
```

Each argument matters:

- **`width=CONSOLE_WIDTH`** (`CONSOLE_WIDTH = 120`, line 31) — the dashboard is designed for 120 columns. Rich will pad short lines and wrap long ones to that exact width, regardless of the host terminal.
- **`soft_wrap=True`** — words are never split mid-syllable. A long label overflows the column rather than producing `Mun-` followed by `chkin`.
- **`force_terminal=False`** — Rich auto-detects the terminal. We do not want to *force* a TTY, because that would emit ANSI codes even when stdout is captured.
- **`color_system="auto"`** — Rich picks `truecolor → 256 → 16 → 8 → none` based on the host.
- **`no_color=is_captured()`** — the single switch that prevents escape codes from leaking. See next section.
- **`highlight=True`** — Rich will syntax-highlight Python reprs and tracebacks.
- **`markup=True`** — `[bold red]...[/bold red]` style strings are interpreted.
- **`emoji=True`** — shortcodes like `:rocket:` and Unicode glyphs render natively.
- **`legacy_windows=False`** — disables the Windows `<10 ANSI fallback, so colors work on modern Windows Terminal.
- **`safe_box=False`** — full Unicode box drawing (`╭─╮ │ ╰─╯`); terminals without a Unicode font must override at the call site.

## `is_captured()`

```python
# src/operational/ui/__init__.py:35-37
def is_captured() -> bool:
    """True if stdout is not a TTY (piped, captured, opencode tool, etc)."""
    return not (sys.stdout is not None and sys.stdout.isatty())
```

Three conditions return `True`:

1. `sys.stdout is None` (extremely rare — embedded Python with no stdout).
2. `sys.stdout` is a pipe (e.g. `operational state show | less`).
3. `sys.stdout` is a `StringIO` (e.g. the home menu's `contextlib.redirect_stdout`).

The function is called **once** at module import, and its return value is baked into the `no_color=` constructor argument. The Console does **not** re-check the TTY status during its lifetime. This is intentional: it makes output deterministic for a given Python process — you cannot accidentally get colors in one command and not the next.

## Why this matters

Without `no_color=is_captured()`, Rich **still emits ANSI escape codes** when `force_terminal` is set or when the output `Console` is told to render to a non-TTY buffer. The escape codes look like literal text in the captured buffer:

```text
[36m╭─[0m[1m[36m ⚡ TIME-TASKER [0m[1m[37m v0.1.0[0m[1m[37m  |  2026-06-08[0m
```

By setting `no_color=True` on the singleton at import time, we get:

- No ANSI codes in the captured buffer.
- Rich falls back to **plain text with Unicode box characters** (because `safe_box=False` is still in effect).
- The home menu's `_run_cmd` (see `05-HOME-MENU.md`) can read the buffer, run `strip_ansi()` for safety, and re-print the cleaned text via the singleton.

## `strip_ansi(text)`

```python
# src/operational/ui/__init__.py:67-73
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from a string.

    Used by the home menu to clean output that was captured from inner
    commands that ran in a different TTY context.
    """
    return _ANSI_ESCAPE_RE.sub("", text)
```

The regex `\x1b\[[0-9;]*[a-zA-Z]` matches a literal `ESC`, `[`, zero or more digits/semicolons, and a final letter. That covers SGR (`\x1b[31m`), cursor moves (`\x1b[2J`), and the private-mode `?` variants (Rich emits some of these for 256-color).

It is **defensive**: even when `no_color=True` is set, a downstream component (e.g. `cli/renderers.py:make_console` builds a console with `force_terminal=True`) can still leak codes into a captured buffer. `strip_ansi` is the safety net.

## Rich traceback

```python
# src/operational/ui/__init__.py:60-64
install_rich_traceback(
    show_locals=True,
    width=CONSOLE_WIDTH,
    max_frames=5,
)
```

`rich.traceback.install` is called **at import time** with these defaults:

- `show_locals=True` — every frame in the traceback shows the local variables in a side panel. This is invaluable for Pydantic validation errors and entity hydration bugs.
- `width=CONSOLE_WIDTH` — the traceback respects the 120-column layout.
- `max_frames=5` — long chains (e.g. a request handler that calls 12 layers) are truncated. Set to `0` for the full chain when debugging.

The traceback is installed globally. There is no way to uninstall it from inside a command; it lives for the process lifetime. To get the *plain* Python traceback (e.g. for a CI log), set `PYTHONRichTraceback=0` or import with `python -X dev` and patch `sys.excepthook` before importing `operational.ui`.

## How to add a new console-using module

There is exactly one import path:

```python
from operational.ui import console
```

That is the entire contract. Do not instantiate `Console()` in your module — you will get a second console that does not share the singleton's `is_captured()` decision, and your output will look fine in a real TTY but leak codes when captured.

If you need a non-singleton console (rare), import `make_console` from `operational.cli.renderers` and document why. Most modules will not need this.

## The console never closes

The console is a singleton; its lifecycle is the Python process lifecycle. There is no `.close()` call, no `atexit` handler, no context manager. The console does not own any file handles (it shares `sys.stdout` / `sys.stderr` with the interpreter), so there is nothing to flush.

If you see "console not found" errors in a downstream module, the cause is almost always a *circular import*: `operational.ui` imports from `rich`, which is heavy; avoid `from operational.cli import ...` inside `ui/`.
