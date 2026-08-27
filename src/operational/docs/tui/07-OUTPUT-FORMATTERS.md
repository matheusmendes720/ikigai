# 07 — Output Formatters

> Every command in the `operational` CLI supports `--json`. The dispatch is centralized: each controller checks the `--json` flag (or the `json_output` context var) and prints via one of three formatters in `src/operational/cli/formatters/base.py`. The three formats are designed for three consumers: **JSON for piping to `jq`**, **markdown for human-readable reports and embedding in PR descriptions**, and **table for human eyes in the terminal**. The formatters are pure functions — they take Python data, return a string, and never touch the console.

## The 3 output formats

### `format_as_json` — pretty-printed JSON

**Defined in:** `cli/formatters/base.py:11-13`.

```python
def format_as_json(data: Any, *, indent: int = 2) -> str:
    """Dump data as JSON, handling Pydantic models and datetimes."""
    return json.dumps(data, indent=indent, default=_json_fallback)
```

The fallback at `base.py:16-22` handles two cases the default `json.dumps` does not:

- `BaseModel` → `obj.model_dump(mode="json")` (Pydantic v2, mode=json ensures datetimes become ISO strings).
- `datetime` / `date` → `obj.isoformat()`.

Anything else raises `TypeError` with a clear message. This is intentional: silently swallowing unknown types hides bugs.

**Example:**

```python
format_as_json({"date": "2026-06-08", "energy": 8, "focus": 9, "sleep_hours": 7.2})
```

```json
{
  "date": "2026-06-08",
  "energy": 8,
  "focus": 9,
  "sleep_hours": 7.2
}
```

### `format_as_table` — plain `|`-separated text

**Defined in:** `cli/formatters/base.py:25-45`.

```python
def format_as_table(
    headers: list[str],
    rows: list[list[str]],
    *,
    sep: str = " | ",
) -> str
```

Builds a 3-line minimum output: header, separator (`-` repeated to header width), then one row per `rows` entry. Cells are coerced to `str`; `None` becomes `""`. The separator width matches the **header** width, not the cell width — long cells overflow on the right.

**Example:**

```python
format_as_table(
    ["Métrica", "Valor"],
    [
        ["Energia", "8/10"],
        ["Foco",    "9/10"],
        ["Sono",    "7.2h"],
    ],
)
```

```text
Métrica | Valor
--------|------
Energia | 8/10
Foco | 9/10
Sono | 7.2h
```

This is plain text — no Rich, no box characters, no colors. It is meant for piping into `column -t` or `less`. For a Rich-styled table inside the dashboard, use `metric_table` from `cli/renderers.py:406` instead.

### `format_as_markdown` — fenced code block

**Defined in:** `cli/formatters/base.py:48-50`.

```python
def format_as_markdown(text: str) -> str:
    """Wrap text in a Markdown code block (for terminal output)."""
    return f"```\n{text}\n```"
```

This is a one-liner: it wraps the input in a fenced code block. It does **not** generate a real Markdown table from structured data. If you need a Markdown table, build the pipe-syntax string yourself and pass it to `format_as_markdown` (or just print the raw string — the wrapper is decorative).

**Example:**

```python
format_as_markdown("Sono: 7.2h\nFoco: 9/10")
```

````markdown
```
Sono: 7.2h
Foco: 9/10
```
````

## The `--json` flag

Every Typer command accepts `--json`. The flag is a Boolean (`bool = False`) and is wired into a `typer.Option`:

```python
@app.command()
def daily(
    date: str = typer.Option(None, "--date", "-d"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    ...
```

There are two naming conventions in the codebase:

- `json_output` (used by most commands) — explicit, easy to grep.
- `--json` (the actual CLI flag) — short, intuitive, but `json` is a Python builtin so the parameter is renamed.

Controllers then dispatch:

```python
if json_output:
    print(format_as_json(snapshot.model_dump(mode="json")))
else:
    build_daily_report(snapshot)  # uses console.print() with Rich panels
```

The home menu (`cli/home.py`) does not expose the `--json` flag in the workflow flows — JSON is the power-user path. The reports submenu (`home.py:321-331`) does include JSON options explicitly:

```python
("3", "Relatório diário — JSON", ["report", "daily", "--json"]),
("5", "Relatório semanal — JSON", ["report", "weekly", "--json"]),
("7", "Dashboard JSON", ["state", "show", "--json"]),
```

## When to use which — decision tree

```text
Where is the output going?
│
├─ Piped to jq, awk, or another script?
│  └─ Use format_as_json
│
├─ Embedded in a PR description, GitHub comment, or report?
│  └─ Use format_as_markdown (or build a real Markdown table by hand)
│
├─ Shown to a human in a 120-col terminal?
│  └─ Use the Rich panels / tables (no formatter; controllers call console.print)
│
└─ Shown to a human in a narrow terminal or piped to less?
   └─ Use format_as_table (pipe to `column -t` for alignment)
```

The default for every command is the **Rich panel output** (no formatter call). `--json` switches to `format_as_json`. The `format_as_table` and `format_as_markdown` are exposed for callers that want to embed or pipe the structured data.

## Examples — same data in 3 formats

Given this Python dict:

```python
data = {
    "date": "2026-06-08",
    "tipo_dia": "HARDCORE",
    "metrics": {
        "energy": 8,
        "focus": 9,
        "sleep_hours": 7.2,
    },
    "quadrant": "Q1",
    "recommendation": "Manter ritmo. Monitorar fadiga.",
}
```

### JSON

```python
print(format_as_json(data))
```

```json
{
  "date": "2026-06-08",
  "tipo_dia": "HARDCORE",
  "metrics": {
    "energy": 8,
    "focus": 9,
    "sleep_hours": 7.2
  },
  "quadrant": "Q1",
  "recommendation": "Manter ritmo. Monitorar fadiga."
}
```

### Markdown

```python
text = "| Field | Value |\n|---|---|\n" + "\n".join(
    f"| {k} | {v} |" for k, v in data.items()
)
print(format_as_markdown(text))
```

````markdown
```
| Field | Value |
|---|---|
| date | 2026-06-08 |
| tipo_dia | HARDCORE |
| metrics | {'energy': 8, 'focus': 9, 'sleep_hours': 7.2} |
| quadrant | Q1 |
| recommendation | Manter ritmo. Monitorar fadiga. |
```
````

### Table (plain text)

```python
print(format_as_table(
    ["Field", "Value"],
    [[k, str(v)] for k, v in data.items()],
))
```

```text
Field | Value
-------|------
date | 2026-06-08
tipo_dia | HARDCORE
metrics | {'energy': 8, 'focus': 9, 'sleep_hours': 7.2}
quadrant | Q1
recommendation | Manter ritmo. Monitorar fadiga.
```

### Rich Table (for the dashboard, no formatter)

For the in-terminal dashboard, controllers do not call a formatter — they call `metric_table` from `cli/renderers.py:406` directly:

```python
console.print(metric_table(
    "Métricas do Dia",
    [
        ("Energia",         "8/10",  "ok"),
        ("Foco",            "9/10",  "ok"),
        ("Sono",            "7.2h",  "ok"),
        ("Quadrante",       "Q1",    "ok"),
    ],
    title_color="primary",
))
```

This produces a boxed, colored, severity-aware table that is the dashboard's primary surface. See `02-COMPONENT-CATALOG.md` and `03-LAYOUT-GRID-SYSTEM.md` for the full layout grammar.
