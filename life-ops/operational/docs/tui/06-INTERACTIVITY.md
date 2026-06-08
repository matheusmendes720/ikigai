# 06 — Interactivity

> All user input in the `operational` CLI goes through `rich.prompt`. There are no custom input handlers, no async prompts, no `input()` calls, no `click.echo`+`click.prompt` mix. The three prompt classes in active use are `Prompt.ask` (text), `IntPrompt.ask` (integer), and `Confirm.ask` (yes/no). All three are **synchronous** and **blocking** — they read a single line from stdin, optionally re-prompt on invalid input, and return the validated value.

## `Prompt.ask` — text input

`rich.prompt.Prompt.ask` is the workhorse. It prints the prompt, reads a line, optionally validates against a `choices=` list, and returns the trimmed string.

```python
from rich.prompt import Prompt

label = Prompt.ask("Label do bloco da tarde", default="Deep Work — Features")
# User types: "Estudos ENEM"  →  returns "Estudos ENEM"
# User presses Enter         →  returns "Deep Work — Features"
```

**Signature (relevant params):**

```python
Prompt.ask(
    prompt: str | Text,            # the question (supports Rich markup)
    *,
    choices: list[str] | None = None,
    default: Any = ...,
    show_default: bool = True,
    password: bool = False,
    console: Console | None = None,
)
```

Common options used in the home flows (`cli/home.py`):

- `default="..."` — pre-filled value shown after the question. Pressing Enter accepts the default. Used for almost every flow prompt to keep the loop fast.
- `choices=["y", "n"]` — restricts valid input. Re-prompts on invalid input automatically.
- `password=True` — masks input with `*`. Not used in this CLI but available for future secret flags.

## `IntPrompt.ask` — integer input

`rich.prompt.IntPrompt.ask` is identical to `Prompt.ask` but coerces the input to `int` and re-prompts on `ValueError`. Use it whenever the value is a count, an hour, a minute, a score, etc.

```python
from rich.prompt import IntPrompt

e = IntPrompt.ask("Energia agora (1-10)", default=7)
# User types: "8"    →  returns 8 (int)
# User types: "abc"  →  re-prompts
# User presses Enter →  returns 7 (int)
```

**Signature:**

```python
IntPrompt.ask(
    prompt: str | Text,
    *,
    choices: list[int] | None = None,
    default: int = ...,
    show_default: bool = True,
    console: Console | None = None,
)
```

**Not currently used in the home flows** — `_flow_morning` reads hour/minute as `Prompt.ask` and then passes the string to the command (`home.py:170-179`). The command then validates and parses. This is a deliberate choice: keeping the home flows string-based avoids two layers of integer validation. If you are writing a new flow and need a guaranteed-int input, use `IntPrompt.ask` directly.

## `Confirm.ask` — yes/no

`rich.prompt.Confirm.ask` accepts `y`, `yes`, `true`, `1` (returns `True`) or `n`, `no`, `false`, `0` (returns `False`). It is case-insensitive.

```python
from rich.prompt import Confirm

if Confirm.ask("Continuar?", default=True):
    # do the thing
```

**Not currently used in the home flows** — the home flows use `Prompt.ask(..., choices=["y", "n"], default="y")` (see `home.py:166, 200, 228, 365`). This gives the same UX with more control over the prompt text. `Confirm.ask` is the right choice when the prompt is literally a yes/no question with no other context.

## When to use which — decision tree

```text
Need to read a value from the user?
│
├─ Value is a count, hour, score, or any integer?
│  └─ Use IntPrompt.ask
│
├─ Value must be one of a small set of strings?
│  └─ Use Prompt.ask with choices=[...]
│
├─ Value is free-form text with a sensible default?
│  └─ Use Prompt.ask with default="..."
│
└─ Value is a yes/no decision?
   └─ Use Confirm.ask (or Prompt.ask with choices=["y","n"])
```

The home flows mix patterns deliberately:

- `Prompt.ask(..., default="8")` for the sleep quality score (string) — passed to the command as a string.
- `Prompt.ask(..., choices=["y","n"], default="y")` for "Continuar?" decisions.
- `Prompt.ask(..., default="")` for free-form journal text.

## Validation

`Prompt.ask` re-prompts automatically when:

- `choices=[...]` is set and the input is not in the list.
- The input is empty and `default=` is not set.

It does **not** validate types or ranges. If you ask for "Energia (1-10)" and the user types "42", the prompt accepts it. Validation is the **caller's** responsibility, usually by:

- Constraining with `choices=["1","2","3","4","5","6","7","8","9","10"]`.
- Calling `IntPrompt.ask` (catches `ValueError`, re-prompts).
- Parsing in the command and raising a clean error via `error_panel`.

The third pattern is the most common in the home flows. The command (`operational metric energy -e 42`) parses `-e` as an int, raises a clean `typer.BadParameter` if it is out of range, and the home loop catches the exception and shows it via `error_panel`.

## Defaults

`default="value"` is the single most important UX lever in the home flows. The default value is shown after the prompt, and pressing Enter accepts it. Use it for:

- **Pre-filled workflow continuations.** The user is at the dashboard and wants to log a check-in; `IntPrompt.ask("Energia", default=7)` lets them press Enter four times to log the default state.
- **Common labels.** `Prompt.ask("Label do bloco", default="Deep Work — Features")` saves the user from typing the same string every day.
- **Safe fallbacks.** `Prompt.ask("O que deu certo?", default="")` lets the user skip a journal field by pressing Enter.

Do not use `default=...` for fields that must be filled (e.g. a routine name). An empty default for a required field is a footgun.

## Choice prompts

`Prompt.ask(..., choices=[...])` is the menu-prompt primitive. The home loop uses it at the top level:

```python
# home.py:106-110
choice = Prompt.ask(
    "[bold yellow]Choose[/bold yellow]",
    choices=[str(i) for i in range(1, 11)] + ["q"],
    default="5",
)
```

Submenus use the same pattern (`home.py:311-312`):

```python
choices = [str(i + 1) for i in range(len(items))] + ["b"]
choice = Prompt.ask("[bold yellow]Choose[/bold yellow]", choices=choices, default="1")
```

The `"b"` choice is the back-to-main-menu escape hatch for submenus. The `default="1"` means pressing Enter picks the first item.

## Async prompts — not used

`rich.prompt` does have async variants in the Rich library API, but the `operational` CLI does not use them. All prompts are synchronous, blocking, single-line. The reasoning is:

- The CLI is single-threaded; async prompts would require restructuring the entire dispatch loop.
- The home menu is a `while True:` loop that does not benefit from async I/O.
- All inputs are short (a few characters). The blocking cost is negligible.

If you are tempted to add an async prompt, you have probably outgrown the home menu. Move the workflow to a `rich.live` dashboard or a full `textual` app, not a coroutine.
