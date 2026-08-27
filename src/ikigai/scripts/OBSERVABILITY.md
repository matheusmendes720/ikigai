# IKIGAI Observability — Setup, Errors, and Notes

Single source of truth for the OpenTelemetry + LangSmith + Langfuse wiring that
backs the IKIGAI deep-agent harness. Touched by every change to:

- `src/observability/` — init + error-capture helpers.
- `src/agents/deepagents_harness.py` — calls `init_tracing()` at module load.
- `src/agents/ikigai_maintainer/graph.py` — calls `init_tracing()` at module load.

## What it does

- One OpenTelemetry SDK, two OTLP exporters (LangSmith + Langfuse).
- Auto-instrumentation for `langchain`, `requests`, `sqlite3`, `logging`.
- Manual spans around `ikigai.make_agent`, `ikigai.graph.compile`, and
  `ikigai.run_chat.error` so the LLM call graph is observable end-to-end.
- `@observed_tool(name)` decorator that captures `UnicodeDecodeError` and
  `FileNotFoundError` as span attributes — the two error classes the dcode
  TUI hits in practice.

## First-time setup

1. **Rotate the leaked LangSmith key.** The previous key
   `REMOVE_ME_PENDING_SECRET_INPUT was logged in
   `~/.claude/history.jsonl:2497`. Generate a new one at
   <https://smith.langchain.com/settings/api-keys> and revoke the old one.

2. **Populate `.env`.** Copy `.env.example` to `.env` and fill in:

   - `LANGSMITH_API_KEY` — the rotated key from step 1.
   - `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` — from
     <https://cloud.langfuse.com/settings/project>.

   `.env` is in `.gitignore` — never commit it.

3. **Mirror `LANGSMITH_API_KEY` into WSL** so dcode traces from the WSL
   TUI reach the same project:

   ```bash
   wsl.exe -d Ubuntu -- bash -c "echo 'export LANGSMITH_API_KEY=lsv2_pt_REPLACE_ME' >> ~/.bashrc"
   ```

4. **Install OTel deps.** From project root:

   ```bash
   poetry install
   ```

5. **Verify both backends received a smoke trace.** Run, within the same
   minute:

   ```bash
   python scripts/repro_byd_db_error.py   # or repro_ops_dir_error.py
   python scripts/verify_traces.py        # within 5 min
   ```

   `verify_traces.py` asserts at least one run hit LangSmith and at least one
   trace hit Langfuse in the last 5 minutes.

## How to add a new tool to the trace

```python
from observability import observed_tool

@observed_tool("ikigai.<stable-name>")
def my_tool(arg: str) -> str:
    ...
```

The decorator wraps the function with an OTel span, binds arg names to
`tool.arg.*` attributes, and tags the span with `error.class` on
`UnicodeDecodeError` / `FileNotFoundError`. Anything else is still
`record_exception()`'d but not specifically labelled.

## Project invariant tension

The repo's "Fully local — SQLite + filesystem only" rule conflicts with
SaaS observability. **Acknowledged exception**: observability data egress is
opt-in for the explicit purpose of harness improvement (the user's stated
goal). If the env vars are absent, `init_tracing()` silently skips the
exporters and the host application still runs.

## Weekly review ritual

Pick a fixed time each week. Run both reproducers, then open both
dashboards. For each new error class that appears:

1. Add the class to `error_capture.py:observed_tool` with a span attribute
   and a `error.hint` string that points at the fix.
2. If the failure is reproducible, add a `scripts/repro_*.py` so the next
   review can re-verify it's still fixed.
3. If the failure is in deepagents (built-in `read_file`), write a
   workaround tool in `src/agents/tools.py` and switch the agent to it.

## Files in this setup

| File | Purpose |
|---|---|
| `.env.example` | Template for `.env` (committed). |
| `.gitignore` | Excludes `.env`, `.langgraph_api/`, Python artifacts. |
| `pyproject.toml` | OTel deps in `[tool.poetry.dependencies]`. |
| `src/observability/__init__.py` | Public surface: `init_tracing`, `get_tracer`, `shutdown_tracing`, `observed_tool`. |
| `src/observability/otel_init.py` | Single `init_tracing()` — configures both exporters. |
| `src/observability/error_capture.py` | `@observed_tool(name)` decorator. |
| `src/agents/deepagents_harness.py` | Module-load init + manual span on `_make_agent` + error span in `run_chat`. |
| `src/agents/ikigai_maintainer/graph.py` | Module-load init + manual span on `make_ikigai_graph`. |
| `scripts/repro_byd_db_error.py` | Reproducer for the SQLite-as-text failure. |
| `scripts/repro_ops_dir_error.py` | Reproducer for the missing-file failure. |
| `scripts/verify_traces.py` | End-to-end backend verification. |
| `scripts/OBSERVABILITY.md` | This file. |