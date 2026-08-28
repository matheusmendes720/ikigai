# Phase 2 — Reverse-Engineering: interfaces/cli (native, Typer-based, v0.1.0)

**Date:** 2026-08-28
**Source:** `interfaces/cli/read_tasks.py` (206 LOC) + `interfaces/cli/pyproject.toml` (10 LOC)
**Status:** Single-file, single-package, standalone Typer CLI
**Companion:** Phase 1 audit `docs/diagnostics/2026-08-28-phase1-audit/{00..05}*.md`

---

## Command inventory

Three subcommands registered on `app = typer.Typer(...)` at `interfaces/cli/read_tasks.py:23`:

| Command | Decorator | Lines | Args | Purpose |
|---------|-----------|-------|------|---------|
| `list`  | `@app.command()` | `read_tasks.py:66-102` | `--horizon/-h`, `--done/-d`, `--json`, `--limit/-n` (default 50) | Read + filter + render tasks |
| `done`  | `@app.command()` | `read_tasks.py:105-154` | `task_id` (Arg, first 8 chars of record uuid) | Mark task done + append feedback |
| `stats` | `@app.command()` | `read_tasks.py:157-202` | none | Total / done / pending / by-horizon / by-priority |

Notes on signatures:

- `list` is the ONLY command with a `--json` flag (`read_tasks.py:72`). Per global convention `--json everywhere` (CLAUDE.md root, "Global Conventions" table), `done` and `stats` are non-conformant.
- `done` takes a positional `task_id: str` (line 107) and matches on `task["id"][:8]` (line 130) — i.e., the truncated 8-char uuid written by `_write_tasks_to_data` (`server.py:309`).
- `stats` has no filters — it always re-scans the entire JSONL file (line 170).

Rich Table rendering is the default for `list` and `stats`; `done` prints a single green check line.

---

## JSON output format

Only `list --json` produces JSON. Output is the literal array of task dicts sliced to `tasks[:limit]`:

```json
[
  {
    "id": "a1b2c3d4",
    "written_at": "2026-08-28T14:30:00.000000",
    "source": "deep_agent",
    "title": "Wire canonical path resolution",
    "description": "PR-1 from priority matrix",
    "horizon": "this_week",
    "priority": "high",
    "project_id": "PROJ-01",
    "estimated_minutes": 90,
    "done": false,
    "done_at": null,
    "ueid": "tsk:wire-path:abc12345:0f",
    "vector": "operations",
    "due": "2026-08-30"
  }
]
```

Field set (14 fields) is produced by `_write_tasks_to_data` at `src/ikigai/src/mcp_server/server.py:308-323`. The CLI does NOT extend the schema on read; whatever is in the line is returned verbatim (except non-JSOND loads, which are silently skipped at `read_tasks.py:54-55`).

`done` writes a SEPARATE, NARROWER record to `feedback.jsonl` (`read_tasks.py:145-152`):

```json
{"id": "a1b2c3d4", "action": "done", "date": "2026-08-28", "source": "interface_cli"}
```

Only 4 fields; no back-reference to the original task record (no `ueid`, no `title`, no `project_id`). This is sufficient for a join key but loses semantic context — see Trade-offs.

`stats --json`: NOT IMPLEMENTED. The command renders Rich Tables only (`read_tasks.py:187-202`); no machine-readable alternative exists.

---

## Filter logic

Filter handling is centralized in `_read_tasks(horizon, done)` at `read_tasks.py:37-63`:

- `horizon` (line 56-57): strict equality on `task.get("horizon") != horizon`. No partial match, no `in` semantics. Valid values are the producer-side enum (`today`, `this_week`, `onda`, `sprint`, etc.).
- `done` (line 58-59): strict equality on `task.get("done") != done`. `None` disables the filter.
- Limit (line 73, 79, 93): applied at display, NOT in `_read_tasks`. The full filtered set is loaded into memory before truncation. This means a 100k-task JSONL still pays the parse cost even with `--limit 10`.

Filter combinations: AND-semantics (both must match). OR, NOT, or fuzzy match are not supported. Empty/missing files return `[]` early (`read_tasks.py:42-43`); JSON-decode errors are swallowed per-line (`read_tasks.py:53-55`).

Side-effect on `done`: rewrites the WHOLE file via `path.write_text(...)` (`read_tasks.py:140`). NOT in-place mutation — the entire JSONL is loaded into `updated_lines: list[str]` (`read_tasks.py:116`). This is an O(N) write on every completion and a transient inconsistency window if interrupted between truncate and write (no atomic rename).

---

## Data path

```
read_tasks.py:27-29  _tasks_path()
   │  repo_root = Path(__file__).parent.parent.parent  (3 levels up from interfaces/cli/)
   ▼
repo_root / "data" / "tasks.jsonl"

read_tasks.py:32-34  _feedback_path()
   │  same repo_root resolution
   ▼
repo_root / "data" / "feedback.jsonl"
```

Path math: `interfaces/cli/read_tasks.py` → `interfaces/` → `life/` → repo_root (3 levels). NOTE: this assumes `life/` IS the repo root, which is consistent with the workspace containing `data/`, `vault/`, `vibe-ops/`, etc. at this level.

Write paths:
- `tasks.jsonl` is REWRITTEN on `done` (`read_tasks.py:140` — full-file `write_text`, atomic via single syscall on POSIX, not atomic on Windows due to no `os.replace`).
- `feedback.jsonl` is APPENDED on `done` (`read_tasks.py:151-152`). Parent dir is created with `mkdir(parents=True, exist_ok=True)` at line 144 — defensive against missing `data/`.
- `tasks.jsonl` parent dir is NOT pre-created. If `data/` is missing and a write was ever attempted, it would fail (but `done` doesn't write to `tasks.jsonl`'s parent separately — it relies on `tasks.jsonl` existing first since `read_tasks.py:111` checks `path.exists()`).

Two writers to `tasks.jsonl` exist (verified):
1. `src/ikigai/src/mcp_server/server.py:293-327 _write_tasks_to_data` — MCP tool `ikigai_write_tasks` (registered `server.py:656`). Source = `deep_agent`.
2. `vibe-ops/src/pipeline/daily_consolidator.py:108-... _write_tasks` — entry `consolidate_from_cycle_state` (line 327). Source = `cycle_state` or `vault_bootstrap`.

Both resolve the same path identically; no file-locking; no schema validation. Append-only on producer side; full-rewrite on consumer-side `done`.

---

## Broken script entry

`pyproject.toml:9` declares:

```toml
[project.scripts]
life-tasks = "read_tasks:app"
```

This will NOT WORK because (Phase 1 critic gap #8, `02-critic-gaps.md:82-91`):

1. `interfaces/cli/` has NO `__init__.py`. The entry-point spec `"read_tasks:app"` requires the module `read_tasks` to be importable from a package, which means PEP 328-style or a package marker. Without `__init__.py`, pip's wheel build either fails or treats `read_tasks.py` as a top-level module (not in a package).
2. NO `[tool.hatch.build.targets.wheel]` or `[tool.setuptools]` section declares what to package. Default hatch behavior for a single-`.py` project is to not include it in the wheel.
3. NO `[project.urls]` or README. The package metadata is barebones.

Net effect: `pip install -e .` from `interfaces/cli/` either errors or installs in a state where `life-tasks` is NOT on PATH. The CLI is effectively only invokable as `python interfaces/cli/read_tasks.py [list|done|stats] [opts]` — exactly the form shown in the docstring at `read_tasks.py:6-10`.

Mitigation hint: CLAUDE.md only ever invokes the root CLI as `python -m life.cli ...`; `interfaces/cli` has no documented invocation. So the script-entry bug is latent — it has not been exercised in production.

---

## Producer-consumer gap

**VERIFIED 2026-08-28:**

```
$ ls life/data/tasks.jsonl    → No such file
$ ls life/data/feedback.jsonl → No such file
```

Both files are absent (consistent with Phase 1 finding B-04, `01-verified.md:33-38`).

Two producers exist but are NEVER INVOKED:

| Producer | Entry | Where invoked? | Status |
|----------|-------|----------------|--------|
| `daily_consolidator.py` | `consolidate_from_cycle_state` (line 327) | nowhere — no caller found in repo grep | DEAD |
| `server.py:_write_tasks_to_data` (MCP tool `ikigai_write_tasks`) | MCP server at `ikigai.bat mcp` | server starts on demand; tool would only fire if Deep Agent chose to call it | Never fired in observed sessions |

Implication: every invocation of `life-tasks list` or `life-tasks stats` (or `python read_tasks.py list`) returns immediately with the empty-state path:
- `list`: prints `[dim]No tasks found.[/dim]` (`read_tasks.py:83`)
- `stats`: prints `[dim]No tasks yet.[/dim]` (`read_tasks.py:162`)
- `done <id>`: exits 1 with `[red]No tasks found.[/red]` (`read_tasks.py:112-113`)

The CLI is therefore a UI shell with no data behind it. Two valid paths out (decision deferred per OQ-3 in `05-open-questions.md:27-35`):

- **A) Invoke producer**: `python vibe-ops/src/pipeline/daily_consolidator.py` would seed `tasks.jsonl` from `data/cycle_state.json` (or fall back to `_scan_vault_dirs` at line 345 → `action = "vault_bootstrap"`).
- **B) Retire consumer**: delete `interfaces/cli/` until upstream producer pipeline is wired. Per interfaces-architecture memory (`interfaces-architecture-2026-08-27.md`), interfaces are downstream consumers; building them before the producer is a layering inversion.

---

## Trade-offs

| Choice | Pro | Con |
|--------|-----|-----|
| JSONL for `tasks.jsonl` | Human-readable; append-friendly; no schema migration | No locking (concurrent writers corrupt); no validation (typo'd fields pass through silently); rewrite-on-`done` is O(N) |
| First-8-chars of uuid as task_id | Short, copy-pastable; matches what humans see | Collision risk at scale (1 in 16M); no namespace |
| Feedback as separate `feedback.jsonl` (not in-place update of `tasks.jsonl`) | Audit trail; append-only writes; feedback can be replayed | Loses semantic context (4-field stub only); needs join for full picture |
| Typer (vs Click / argparse) | Subcommand auto-discovery; `--help` per command; type-driven Options | Heavier dep; magic in entry-point resolution (cf. broken script) |
| No `__init__.py` | Lazy single-file CLI; no package overhead | Blocks `[project.scripts]` entry-point; can't be `pip install`-ed |
| `read_tasks.py` writes to `data/` (not `vault/`) | Append-only invariant preserved on vault | Bypasses canonical contracts from `src/contracts/` — silent schema drift risk |
| `stats --json` missing | Forces human eyes; prevents broken pipeline JSON | Violates CLAUDE.md `--json everywhere` convention |

---

## Cross-references

- Phase 1 audit INDEX: `docs/diagnostics/2026-08-28-phase1-audit/00-INDEX.md`
- Phase 1 B-04 (this gap): `docs/diagnostics/2026-08-28-phase1-audit/01-verified.md:33-38`
- Phase 1 critic gap #8 (broken script): `docs/diagnostics/2026-08-28-phase1-audit/02-critic-gaps.md:82-91`
- Phase 1 OQ-3 (tasks.jsonl role): `docs/diagnostics/2026-08-28-phase1-audit/05-open-questions.md:27-35`
- Phase 1 Step 3 (migrate 3 writers): `docs/diagnostics/2026-08-28-phase1-audit/04-sequencing.md:29-34`
- Producer (MCP): `src/ikigai/src/mcp_server/server.py:287-327`
- Producer (cybernetic): `vibe-ops/src/pipeline/daily_consolidator.py:108, 327, 352, 402`
- Adjuster (also reads same path): `vibe-ops/src/cybernetic_engine/middleware/sync_engine.py:8` (via `vibe-ops/src/contracts/sync_contract_v1.py`)
- Layering memory: `~/.claude/projects/.../memory/interfaces-architecture-2026-08-27.md`
- Convention `--json everywhere`: `CLAUDE.md` "Global Conventions" table (project root)

---

DONE 04-interfaces-cli.md: 197 lines
