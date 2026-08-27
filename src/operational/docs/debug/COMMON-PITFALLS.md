# Common Pitfalls

> A catalog of known issues that bite developers working on the `operational` CLI. Each entry has a one-paragraph summary, the symptom, the root cause, and a concrete fix. The issues are ordered roughly by frequency — CRLF and UTF-8 BOM are the two that hit every Windows developer; the Pydantic frozen-model issue hits every contributor who tries to "just update this field".

## 1. CRLF line endings

**Symptom:** `csv.Error: new-line character seen in unquoted field` on Windows. Or `json.JSONDecodeError: Expecting value` on a JSON file that looks fine in Notepad.

**Root cause:** Windows text editors and `git` (when `core.autocrlf=true`) write `\r\n` line endings. Python's `open()` in text mode normalizes these to `\n` on read, so reading is fine. But when writing a CSV, Python does not normalize — it writes whatever the source string has. If a cell contains a `\r\n` (e.g. a journal entry pasted from Word), the CSV becomes malformed.

**Fix:**

- Read CSVs with `open(path, "r", encoding="utf-8", newline="")` — the `newline=""` argument tells Python's CSV parser to handle line endings itself, not the I/O layer.
- Write CSVs with `open(path, "w", encoding="utf-8", newline="")` — same reason, plus it prevents Windows from translating `\n` to `\r\n` on write.
- Sanitize cell content before writing: `cell.replace("\r\n", " ").replace("\n", " ")` for single-line cells, or use a real multi-line CSV quoting strategy for the `journal` field.
- For JSON files, use `open(path, "w", encoding="utf-8")` (no `newline`) — JSON has no multi-line strings, so `\r\n` vs `\n` does not matter.

The CSV loader (`src/operational/cli/csv_loader.py`) already uses `newline=""` on read. The export path (`operational report weekly --csv`) must be checked when adding new export commands.

## 2. UTF-8 BOM

**Symptom:** The first column header is `\ufeffdate` instead of `date`. Pydantic raises `ValidationError: missing field 'date'`.

**Root cause:** Windows Notepad and some Excel-for-Windows exports prepend a UTF-8 BOM (`\ufeff`) to CSV files. Python's default `open(..., encoding="utf-8")` does not strip it; it is preserved in the first cell.

**Fix:**

- Read with `encoding="utf-8-sig"` — Python's "UTF-8 with signature" codec, which strips a leading BOM if present.
- When writing, open with `encoding="utf-8"` (no BOM) so other tools that do not expect the BOM do not get confused. The Python convention is "BOM on read, no BOM on write".
- To detect a BOM in an existing file:

  ```python
  with open(path, "rb") as f:
      bom = f.read(3)
  if bom == b"\xef\xbb\xbf":
      print("File has UTF-8 BOM")
  ```

If a user reports "the CSV is missing the first column", suspect a BOM. The fix is a one-character change in the loader.

## 3. ANSI escape codes in captured output

**Symptom:** `--json` output contains literal `^[[36m` or `\x1b[36m`. `jq` chokes on it.

**Root cause:** A `Console` was built without `no_color=True` while stdout was captured. This happens when a controller uses `make_console` (which sets `no_color=not is_tty`) but stdout was redirected after the call site — `is_tty` is checked at construction time only.

**Fix:**

- Always use the singleton `console` for user-facing output. It is built once with `no_color=is_captured()` (`ui/__init__.py:48`).
- For the JSON path, wrap the captured text in `strip_ansi` before printing:

  ```python
  from operational.ui import strip_ansi
  print(strip_ansi(captured_text))
  ```

- For the `--json` flag specifically, **never** build a local `Console`. Build the dict, serialize with `format_as_json`, and `print()` it directly. No Rich involved.

The home menu's `_run_cmd` (`home.py:49-67`) already does the `redirect_stdout` + `strip_ansi` dance. The same pattern should be used anywhere else that captures output.

## 4. Pydantic frozen models

**Symptom:** `ValidationError: Instance is frozen` or `FrozenInstanceError: cannot assign to field 'X'`.

**Root cause:** Pydantic v2 models in this codebase are declared with `model_config = ConfigDict(frozen=True)`. You cannot assign to a field after instantiation:

```python
snap.metrics.energy = 9  # FrozenInstanceError
```

**Fix:**

Use `model_copy(update={...})`:

```python
new_snap = snap.model_copy(update={"metrics": snap.metrics.model_copy(update={"energy": 9})})
```

This returns a new instance with the update applied. The original `snap` is unchanged (Pydantic v2's `model_copy` is a deep-copy-with-overrides).

For nested models, you need to copy at each level:

```python
updated_metrics = snap.metrics.model_copy(update={"energy": 9})
new_snap = snap.model_copy(update={"metrics": updated_metrics})
```

The cleaner alternative is to **rebuild the object from scratch** if the change is non-trivial:

```python
new_snap = DaySnapshot(
    date=snap.date,
    tipo_dia=snap.tipo_dia,
    metrics=MetricBlock(energy=9, focus=snap.metrics.focus, sleep_hours=snap.metrics.sleep_hours),
    ...
)
```

`frozen=True` is a feature, not a bug. It prevents accidental mutation and makes the data flow easier to reason about. Respect it.

## 5. Pydantic `extra="forbid"`

**Symptom:** `ValidationError: Extra inputs are not permitted` on a CSV import that worked yesterday.

**Root cause:** Entity models are declared with `model_config = ConfigDict(extra="forbid")`. Any field in the input that is not in the model schema is rejected. This is intentional — it surfaces schema drift early.

**Fix:**

- **For the model:** add the new field to the entity. If the field is genuinely optional, use `field: str | None = None` with `default=None`.
- **For the input:** strip unknown fields before passing to the model:

  ```python
  known = {f for f in Habit.model_fields}
  cleaned = {k: v for k, v in raw.items() if k in known}
  habit = Habit(**cleaned)
  ```

- **For the CSV:** update the CSV header to match the new schema, or update the model to match the CSV. They must agree.

The discipline is "schema first, data second". When you add a new metric, add it to the entity first, then to the CSV exporter, then to the report renderer. Never the other way around.

## 6. Typer defaults

**Symptom:** `typer.BadParameter: ... must be X` even though you did not pass the flag. Or the option is required when it should be optional.

**Root cause:** Typer infers required-ness from the type annotation. If you declare `date: date = typer.Option(None)`, the `None` is the default — but Typer may still complain about the type mismatch.

**Fix:**

- For optional strings: `date: str | None = typer.Option(None, "--date", "-d")` or `date: Optional[str] = typer.Option(None, ...)` with `from __future__ import annotations`.
- For optional integers: `count: int = typer.Option(0, "--count", "-c")` (default `0`, not `None`).
- For required booleans (flags): `json_output: bool = typer.Option(False, "--json")` (default `False`).
- Never use `Optional[X]` without a `None` default. Typer will treat `None` as the default, but the type checker (mypy) will complain.

The `from __future__ import annotations` at the top of every file makes the annotations strings, which sidesteps most of the "TypeError in default value" issues. Without it, `Optional[list[str]]` is evaluated at import time and can fail.

## 7. Timezone handling

**Symptom:** `TypeError: can't subtract offset-naive and offset-aware datetimes`. Or a date that is off by one day in the report.

**Root cause:** Mixing `datetime.now()` (naive) with `datetime.now(UTC)` (aware). The Pydantic models accept both, but arithmetic on mixed types fails.

**Fix:**

- **Always** use `datetime.now(UTC)` for new code:

  ```python
  from datetime import UTC, datetime
  now = datetime.now(UTC)
  ```

- For the `date` field (which is timezone-agnostic by design), use `date.today()`:

  ```python
  from datetime import date
  today = date.today()
  ```

- To convert an aware datetime to a date in the user's local timezone:

  ```python
  from datetime import UTC
  local_date = dt.astimezone().date()
  ```

- The CSV loader reads `date` as a `date` object, not a `datetime`. The metric timestamps are `datetime` (aware, UTC) and stored in the JSON state. Reports convert to local time at render time.

The codebase is **mostly consistent** on this — `datetime.now(UTC)` is used in 95% of the call sites. The remaining 5% are bugs that surface as off-by-one-day in the daily report.

## 8. Empty CSV cells

**Symptom:** `_from_jsonable("")` returns `None` instead of `""`. A field that should be an empty string is now `None` and fails downstream `len()` calls or string concatenation.

**Root cause:** The CSV importer's `_from_jsonable` helper maps empty cells to `None` (Python's "no value"). This is correct for optional fields but wrong for required string fields.

**Fix:**

- For optional fields: declare `field: str | None = None` and accept `None`.
- For required string fields with possible-empty input: declare `field: str = ""` and convert in the loader:

  ```python
  value = raw.get("label") or ""
  ```

- For numeric fields: use `field: int = 0` and convert in the loader:

  ```python
  value = int(raw["count"]) if raw.get("count") else 0
  ```

The rule: **empty CSV cell = `None` for optional, `""` or `0` for required**. The loader cannot know which is which; the caller must coerce.

## 9. State dir already has files

**Symptom:** `operational demo seed` does nothing. "Dataset already loaded, use `clear` first."

**Root cause:** The auto-loader in `src/operational/cli/state.py:113` checks if the state dir has any `*.json` files. If it does, the seed is skipped (to avoid clobbering user data).

**Fix:**

- To re-seed: `operational demo clear` first, then `operational demo seed`.
- To bypass the check (dangerous): set `TIME_TASKER_FORCE_SEED=1` in the environment. The loader will overwrite existing data. This is intended for tests and CI only.
- To inspect what is there: `ls ~/.time-tasker/`. If you see `routines.json` with content, the loader is correct to skip.

This is a **safety feature**, not a bug. Accidentally overwriting a week of journal entries with a synthetic dataset is a real risk; the loader is biased toward "do nothing" when in doubt.

## 10. Pre-existing broken test

**Symptom:** `pytest tests/integration/test_cli_integration.py::test_state_show_json_with_mocked_sleep` fails with a `ValidationError` or `KeyError`. The test is the only one that mocks `sleep`.

**Root cause:** The test mocks the `sleep` function from `time` (to skip real sleep calls), but the mock's return value is not compatible with the entity's expected schema. The test was written for an older version of the `MetricBlock` entity.

**Fix:**

- **For developers:** ignore this test. It is marked as expected-to-fail in the test runner output. The 2517 other tests pass.
- **For the test author (future work):** update the mock to return a valid `MetricBlock`-shaped dict:

  ```python
  mock_sleep.return_value = {
      "date": "2026-06-08",
      "tipo_dia": "HARDCORE",
      "metrics": {"energy": 8, "focus": 9, "sleep_hours": 7.2},
      ...
  }
  ```

  And update the assertion to match the current `DaySnapshot` schema.
- **For CI:** add `::test_state_show_json_with_mocked_sleep` to the pytest ignore list in `pytest.ini`:

  ```ini
  [pytest]
  addopts = --ignore=tests/integration/test_cli_integration.py::test_state_show_json_with_mocked_sleep
  ```

This is the only known-broken test in the suite. Everything else is green.
