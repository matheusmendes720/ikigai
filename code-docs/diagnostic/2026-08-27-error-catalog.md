> **[SUPERSEDED 2026-08-28 — KEEP for ADR; see master-branch-carro-chefe-2026-08-28]**
> Error code catalog at \`src/ikigai/exceptions.py\` registry + raise sites
> remains a valid audit reference, but the surrounding IKIGAI server.py is
> paused per ADR-007 (5+ SONHO logs gate). Catalog content retained for when
> IKIGAI un-pauses; do not extend with new error codes until then.

# IKIGAI Error Code Catalog

**Scan root:** `C:\Users\mathe\code_space\life-oss\life\life-ops\ikigai\`
**Scan date:** 2026-08-27
**Scope:** `src/ikigai/exceptions.py` (registry), `src/ikigai/**` (raise sites), `src/mcp_server/server.py` (8 tools), `src/agents/tools.py` (18 tools), `src/observability/error_capture.py` (parallel taxonomy)

---

## §0 Sumário Executivo

### Headline counts

| Fact | Value |
|------|-------|
| Declared codes (`exceptions.py`) | **18** (1 base + 17 subclasses) |
| Codes actually raised in `src/` | **2** (`ERR_IO_001`, `ERR_IO_002`) |
| Dead codes (declared, never raised) | **15** (83%) |
| Undeclared codes (emitted, absent from registry) | **3** (`ERR_CLI_001`, `ERR_CLI_404`, `ERR_CLI_501`) |
| Coded raise sites | **6** |
| Uncoded raise sites (`ValueError` / `TransitionError`) | **~63** |
| MCP tools emitting a code | **0 of 8** |
| Agent tools emitting a code | **0 of 18** |
| Entity validators emitting a code | **0** |

### Counts by category

| Category | Declared | Live | Dead | Undeclared-live |
|----------|---------:|-----:|-----:|----------------:|
| BASE | 1 | 0 | 1 | 0 |
| ID | 3 | 0 | 3 | 0 |
| SCORE | 2 | 0 | 2 | 0 |
| REGIME | 1 | 0 | 1 | 0 |
| PHASE | 1 | 0 | 1 | 0 |
| STATE | 2 | 0 | 2 | 0 |
| SYNC | 1 | 0 | 1 | 0 |
| DRIFT | 1 | 0 | 1 | 0 |
| OVERRIDE | 1 | 0 | 1 | 0 |
| IO | 2 | **2** | 0 | 0 |
| VAL | 1 | 0 | 1 | 0 |
| MIGRATE | 1 | 0 | 1 | 0 |
| CLI | 0 | 0 | 0 | 3 |
| **Total** | **18** | **2** | **15** | **3** |

### Structural observations

1. **`src/ikigai/errors.py` does not exist** — `exceptions.py` is the sole registry.
2. **`src/ikigai/persistence/` and `src/ikigai/override/` are empty directories** — no code exists to raise `ERR_OVERRIDE_001` or any persistence-layer code.
3. **No code carries a message template.** `IKIGAiError.__init__(message, *, code=None, context=None)` takes message as caller-supplied free-form; subclasses set only `code`. Every "template" in this catalog is the literal f-string at the raise site.
4. **The CLI is the only structured error envelope.** `cli/app.py:69-71` produces `{"ok": false, "error": {"code": ..., "message": ...}}` to stderr + `typer.Exit(code=1)`. MCP and agent tools never use this shape.
5. **`--json everywhere` is met on shape but not on typing.** MCP returns untyped `{"error": str(e)}`; agent returns `⚠️ {e}`. `is_error` is decided by `text.startswith('{"error"')` (`server.py:505`).
6. **A parallel observability taxonomy exists.** `src/observability/error_capture.py` classifies by Python type name, never by `ERR_*` code — the same failure is named two different ways depending on which layer observes it.

---

## §1 Identity Errors (ERR_ID_001..003)

All three ID codes are **dead** — declared but never raised. UEID validation lives in two parallel, uncoded implementations.

### `ERR_ID_001` — `InvalidUEIDError` (`exceptions.py:28`, never raised)

Two parallel validators bypass it. (a) `src/ikigai/types.py:51` — `UEID.__new__` raises bare `ValueError(f"Invalid UEID format: {value!r}. Expected: <namespace>:<entity_type>:<slug>:<uuid_short>:<content_hash_short>")`. (b) `src/ikigai/entities/ueid.py:11-17` — Pydantic `Annotated[str, StringConstraints(pattern=...)]` raises `pydantic_core.ValidationError`. Neither imports `InvalidUEIDError`. The `ValueError` surfaces as Pydantic `ValidationError` through `UEID.__get_pydantic_core_schema__` (`types.py:116`). No tool catches it by type.

**Handling:** MCP `ikigai_decompose` `_slug_from_ueid` (`:111-114`) returns `""` on malformed UEID; `_decompose_ueid` `:136`, `:158` swallow via `except Exception: pass`. Agent `ikigai_decompose` `:237` returns `f"⚠️ Could not decompose UEID: {e}"`.

**Fix:** Import `InvalidUEIDError` in both `types.py` and `entities/ueid.py`. Promote `ValueError` → `InvalidUEIDError` at the format-check site, preserving the message verbatim. Add `except InvalidUEIDError` to consumer tools.

### `ERR_ID_002` — `UEIDCollisionError` (`exceptions.py:32`, never raised)

`SQLiteAdapter.upsert()` (`propagation/sqlite_adapter.py:264`) resolves same-UEID writes by append-only history, never raising. No collision check exists.

**Fix:** Add an explicit collision check if the append-only invariant is relaxed; otherwise document as reserved-future.

### `ERR_ID_003` — `SlugImmutableError` (`exceptions.py:36`, never raised)

`PlanEntity.slug` (`entities/base.py:46`) is a plain `Field(pattern=...)` under `frozen=False, validate_assignment=True` — reassigning a slug re-validates *format* but is permitted. The documented immutability invariant is unenforced.

**Fix:** Convert `PlanEntity` to `frozen=True` (per repo-wide Pydantic v2 strict invariant) or add a `@model_validator(mode="after")` raising `SlugImmutableError` when `slug` is in `model_fields_set` after init.

---

## §2 Score Errors (ERR_SCORE_001..002)

Both SCORE codes are **dead**. There are ~35 uncoded range checks that should carry them.

### `ERR_SCORE_001` — `ScoreRangeError` (`exceptions.py:45`, never raised, ~35 uncoded sites)

**Uncoded sites (all bare `ValueError`):** `types.py:151` `percent must be in [0, 100]`; `types.py:157` `ratio must be in [0, 1]`; `types.py:163` `raw must be in [0, {max_value}]`; `core/scoring/vector_scores.py:27,29` `{name} must be in [0, 100]`; `core/scoring/vector_scores.py:50` `streak_days must be >= 0`; `core/scoring/vector_scores.py:54` `lambda_rate must be >= 0`; `core/scoring/vector_scores.py:56` `revenue_actual must be >= 0`; `core/scoring/vector_scores.py:79,95,97,99,117` range checks; `core/scoring/qhe.py:43,77,85` `{name} must be in [0, 1]` and `weights must sum to 1.0, got {…}`; `core/scoring/meta_vector.py:36,38,40,94` `w_geo must be in [0, 1]`, `w_geo + w_harm must equal 1.0`, `Score must be >= 0`; `core/scoring/rice.py:21,23,25,27` `reach [1,10]`, `impact [0.25,3]`, `confidence [0,1]`, `effort >= 0`; `core/heuristics/weight_ucb.py:35-41` UCB bounds; `core/heuristics/regime.py:43-49` regime bounds; `core/heuristics/phase_pivot.py:101-107` phase pivot bounds.

**Handling:** all raise bare `ValueError`. Agent tools call scoring only via `graph.invoke()` inside `ikigai_plan_cycle`, so a range violation surfaces as untyped `⚠️ {e}` or `{"error": str(e)}`.

**Fix:** Replace each `raise ValueError(...)` with `raise ScoreRangeError(...)` carrying the original message. Add `except ScoreRangeError` to `ikigai_plan_cycle`'s `graph.invoke()` wrapper (`tools.py:309`).

### `ERR_SCORE_002` — `ScoreUnitMismatchError` (`exceptions.py:49`, never raised)

`types.py:174` `Cannot convert {self.unit} to percent` and `types.py:184` `Cannot convert {self.unit} to ratio` raise bare `ValueError`. This is the code's exact intended trigger, unwired.

**Fix:** Replace both with `raise ScoreUnitMismatchError(...)`. The two sites are isolated.

---

## §3 Regime Errors (ERR_REGIME_001)

### `ERR_REGIME_001` — `RegimeHysteresisViolationError` (`exceptions.py:58`, never raised, **deliberately swallowed**)

`RegimeGraph._coherence_check` (`entities/regime.py:79-93`) detects the exact violation — a sub-vector in `PUSH` under a parent in `RECOVER` — and **deliberately passes** (comment at line 90-91: `# Warn but allow (override possible)`). The `except ValueError: continue` at line 87 additionally swallows unparseable sub-vector roots.

**Handling:** `is_hysteresis_active` is carried as plain state in the LangGraph dict (`agents/tools.py:281`, `mcp_server/server.py:326`), never as an error.

**Fix:** Add an `enabled=True` toggle to `_coherence_check`. When the override layer (currently empty `src/ikigai/override/`) lands, raise `RegimeHysteresisViolationError` unless the override record applies. The current silent pass is the right behavior for the empty override subsystem, but should not survive its implementation.

---

## §4 Phase Errors (ERR_PHASE_001)

### `ERR_PHASE_001` — `PhaseConvergenceError` (`exceptions.py:62`, never raised)

`core/heuristics/phase_pivot.py` validates its four inputs with bare `ValueError` (lines 101-107) and reports non-convergence as the boolean `phase_converged` in graph state, not as an exception.

**Handling:** `ikigai_phase` agent tool prints `converged={converged}` (`agents/tools.py:157`); MCP `ikigai_phase` returns `"phase_converged": d.get("phase_converged", False)` (`server.py:286`).

**Fix:** Keep the boolean state in the LangGraph dict (cheap to carry) but additionally raise `PhaseConvergenceError` when a downstream consumer requires convergence as a precondition. Document the boolean + exception pairing in the phase-pivot module docstring.

---

## §5 State Errors (ERR_STATE_001..002)

Both STATE codes are **dead**, shadowed by an uncoded twin (`TransitionError`).

### `ERR_STATE_001` — `InvalidStateTransitionError` (`exceptions.py:71`, never raised)

`src/ikigai/state_machines/_sm_base.py:10` declares `class TransitionError(Exception)` — plain, codeless — and raises it at line 71 with `f"No transition from {self.current_state!r} → {target_state!r}"`. The module comment says it "must not import from sibling modules to avoid circular imports," which is why the coded exception was bypassed.

**Also uncoded:** `_sm_base.py:67` `raise ValueError(f"Unknown state: {target_state!r}")` for an unknown target state.

**Handling:** no `except TransitionError` anywhere. All 8 state machines (`dream_sm`, `goal_sm`, `objective_sm`, `project_sm`, `task_sm`, `deliverable_sm`, `routine_sm`, `habit_sm`) inherit this behavior.

**Fix:** Either (a) make `TransitionError` a subclass of `InvalidStateTransitionError` so existing catches still work, or (b) move `TransitionError` to `exceptions.py` and have `_sm_base.py` re-export it. Option (a) is the smallest change.

### `ERR_STATE_002` — `GuardConditionFailedError` (`exceptions.py:75`, never raised)

`_sm_base.py:77` raises `TransitionError(f"Guard blocked {self.current_state} → {target_state}")` instead.

**Fix:** Add a `GuardConditionFailedError(InvalidStateTransitionError)` subclass and raise it at the guard-block site. Distinguish guard-block (recoverable) from no-transition (structural) in handlers.

---

## §6 Sync Errors (ERR_SYNC_001)

### `ERR_SYNC_001` — `SyncError` (`exceptions.py:84`, never raised)

Both sync paths swallow instead.

| Site | Behavior |
|------|----------|
| `mcp_server/server.py:499` | `ikigai_sync_vault` wraps vault write in `except Exception as e: text = json.dumps({"error": str(e)})` |
| `agents/tools.py:389` | `ikigai_sync_vault` calls `log_file.write_text(...)` with **no try/except** — `OSError` escapes raw |
| `cli/app.py:450, :494` | `except Exception: continue` — silently drops failed entities from reconcile count |

**Related uncoded: MCP transport failures.** `agents/tools.py:537/539/542` and `:619/621/624` raise `RuntimeError` with three templates — `MCP call timed out after {timeout}s: {method}`, `MCP server error (exit {returncode}): {err}`, `MCP error: {response['error']}`. These are the most frequently hit sync failures in the harness and carry no code.

**Fix:** Wrap the three `RuntimeError` templates as distinct `SyncError` subclasses (`SyncTimeoutError`, `SyncServerError`, `SyncResponseError`). Add `except SyncError` at the four swallow sites. The CLI reconcile loops should at minimum log the dropped entity rather than silently counting it.

---

## §7 Drift Errors (ERR_DRIFT_001)

### `ERR_DRIFT_001` — `DriftDetectedError` (`exceptions.py:88`, never raised)

Drift is modeled as *data*, not an error. `cli/app.py:462-491` compares markdown mtime against `SQLiteAdapter.mtime_for()` and appends a `DriftEntry(drift_kind="missing_sqlite" | "drift_detected", decision=...)` to `propagation/triagem.py`, then writes `triagem.md`. The 5-minute threshold is hardcoded at `app.py:481` (`> 300` seconds). `triagem.py` contains zero `raise` and zero `except` — it is a pure recorder.

**Silent misclassification:** `sqlite_adapter.py:257` `except (ValueError, AttributeError): return None` — an unparseable mtime returns `None`, which the CLI then interprets as `missing_sqlite` rather than as corruption.

**Fix:** Either commit to drift-as-data (delete `ERR_DRIFT_001`) or commit to drift-as-error (raise from the triagem writer and remove the silent `None` classification). Hybrid is the worst of both worlds.

---

## §8 Override Errors (ERR_OVERRIDE_001)

### `ERR_OVERRIDE_001` — `OverrideRejectedError` (`exceptions.py:97`, never raised)

`src/ikigai/override/` is an **empty directory** — the subsystem this code serves has not been written. Same for `src/ikigai/persistence/`.

**Fix:** Remove the dead code until the override subsystem lands, or land the subsystem. Carrying a registered error code for a non-existent subsystem is a load-bearing hazard — any tool that catches `OverrideRejectedError` will silently never fire.

---

## §9 IO Errors (ERR_IO_001..002)

The **only two live codes**. Both serve the markdown↔SQLite propagation layer.

### `ERR_IO_001` — `MarkdownParseError` ✅ LIVE (`exceptions.py:106`, 4 raise sites)

| File:line | Message | Context dict | Trigger |
|-----------|---------|--------------|---------|
| `propagation/markdown_db.py:115` | `f"Failed to read markdown file: {e}"` | `{"path": str(path)}` | `OSError` from `path.read_text(encoding="utf-8")` — chained `from e` |
| `propagation/markdown_db.py:122` | `"Empty or missing frontmatter"` | `{"path": str(path)}` | `parse_from_markdown()` returned falsy data |
| `propagation/frontmatter.py:145` | `"Markdown frontmatter missing closing '---'"` | `{"line_count": len(lines)}` | opening `---` found, no closing delimiter |
| `propagation/frontmatter.py:156` | `f"Failed to parse YAML frontmatter: {e}"` | `{"yaml_content_preview": yaml_content[:200]}` | `yaml.YAMLError` — chained `from e` |
| `propagation/frontmatter.py:162` | `"Frontmatter must be a YAML mapping"` | `{"type": type(data).__name__}` | YAML parsed to a non-dict |

**Handling — 3 catch sites, 2 silent:**

| File:line | Behavior |
|-----------|----------|
| `markdown_db.py:196` | `except MarkdownParseError: continue` — `query()` **silently skips** malformed files; returned list gives no signal that entities were dropped |
| `markdown_db.py:244` | `except MarkdownParseError: continue` — `index_dump()` **silently omits** malformed entities from the index |
| `cli/app.py:307` | `except MarkdownParseError as e: _err(str(e), code="ERR_IO_001")` — **the only place in the codebase where a declared code reaches a user surface.** Emits `{"ok": false, "error": {"code": "ERR_IO_001", "message": "..."}}` to stderr, exit 1. Note the code is **hardcoded as a string literal**, not read from `e.code`. |

**Not handled anywhere:** the 8 MCP tools and 18 agent tools never import or catch `MarkdownParseError`. `mcp_server/server.py:136` and `:158` — the two frontmatter reads in `_decompose_ueid` — use `except Exception: pass`, so a malformed dream/objective file vanishes from the decomposition tree with no diagnostic.

**Fix:** (a) read `e.code` instead of hardcoding the string in `app.py:307`; (b) count skipped files in `query()` and `index_dump()` and return the count alongside the list; (c) wire the MCP `_decompose_ueid` except blocks to `MarkdownParseError` and emit `{"error": {"code": "ERR_IO_001", ...}}`.

### `ERR_IO_002` — `MarkdownWriteError` ✅ LIVE (`exceptions.py:110`, 1 raise site)

**Raise site:** `propagation/markdown_db.py:103` — `f"Failed to write markdown file: {e}"`, context `{"path": str(path)}`, chained `from e`. Triggered by `OSError` during the atomic write-then-rename (`tmp_path.write_text(...)` → `tmp_path.replace(path)`, lines 99-101). **Note:** on failure the `.tmp` file is **not cleaned up**.

**Handling:** **zero catch sites.** `ERR_IO_002` propagates uncaught to whatever called `MarkdownDB.write()`. In the CLI that means a raw traceback rather than the `_err()` JSON envelope; in the agent path it hits a bare `except Exception` and degrades to `⚠️ {e}`.

**Fix:** (a) add `try: tmp_path.unlink() except FileNotFoundError: pass` in the except block; (b) wrap the agent `ikigai_sync_vault` `log_file.write_text(...)` (`tools.py:389`) in `except OSError as e: raise MarkdownWriteError(...)`; (c) wire `cli/app.py` to catch and `_err()` it.

---

## §10 Validation Errors (ERR_VAL_001)

### `ERR_VAL_001` — `ValidationError` (`exceptions.py:113`, never raised, ~61 uncoded sites, **name collides with `pydantic.ValidationError`**)

**Naming hazard:** `from ikigai.exceptions import ValidationError` alongside any Pydantic import is a live shadowing hazard. Pydantic's `ValidationError` is what actually fires today.

**Uncoded sites (~61):**

**`entities/base.py` — `PlanEntity` (7 sites):** line 110 `f"Unknown vector root: {root!r} (from {item!r})"` (`_coerce_vector_types` before); line 112 `f"Invalid vector type: {item!r}"`; line 129 `f"Unknown vector key: {k!r}"` (`_coerce_weight_keys` before); line 131 `f"Invalid weight key: {k!r}"`; line 139 `f"Vector weight for {vec} out of range [0, 1.5]: {w}"` (`_validate_weights_range` after); line 148 `"is_placeholder=True requires placeholder_owner"`; line 150 `"claimed_by requires is_placeholder=True"`.

Plus declarative `Field` constraints that raise Pydantic `ValidationError` directly: `slug` (min 2 / max 64 / `^[a-z0-9][a-z0-9_-]*[a-z0-9]$`, line 46), `title` (1-200, line 53), `horizon_days` (`ge=1, le=7300`, line 70).

**`entities/plan/*.py` — status-whitelist validators (6 entities, 11 sites):** all six share the template `f"{Entity}Entity status must be one of {sorted(s.value for s in allowed)}, got {self.status.value}"`:

| File:line | Entity | Allowed statuses |
|-----------|--------|------------------|
| `dream.py:35` | Dream | SEED, ACTIVE, FULFILLED, ABANDONED, ARCHIVED |
| `goal.py:34` | Goal | DRAFT, ACTIVE, PAUSED, ACHIEVED, ABANDONED, ARCHIVED |
| `objective.py:35` | Objective | ACTIVE, IN_PROGRESS, BLOCKED, DONE, ABANDONED |
| `project.py:42` | Project | IN_PROGRESS, PAUSED, BLOCKED, COMPLETED, CANCELLED |
| `deliverable.py:35` | Deliverable | DRAFT, PLANNED, IN_PROGRESS, DONE, CANCELLED |
| `task.py:64` | Task | DRAFT, TODO, IN_PROGRESS, BLOCKED, DONE, CANCELLED |

Field-range companions: `objective.py:40` `progress_pct must be in [0, 100]`; `task.py:69/71/73/75` the four RICE bounds — **duplicating** the identical checks in `core/scoring/rice.py:21-27`, two independent uncoded copies of one rule.

**Silent-pass hazard:** `PlanEntity` sets `extra="allow"` (`base.py:38`) rather than the repo-wide `extra="forbid"` invariant. Unknown frontmatter keys pass silently instead of producing a validation error at all.

**Handling:** the one place a validator failure is translated for a user is `cli/app.py:298` — `except ValueError: _err(f"Invalid entity_type: {entity_type}")`, which falls through to the **default** `code="ERR_CLI_001"`.

**Fix:** (a) rename to `IKIGAIValidationError` to remove the Pydantic collision; (b) switch `PlanEntity` to `extra="forbid"`; (c) wire `_err()` to catch it and emit `code="ERR_VAL_001"`.

---

## §11 Migration Errors (ERR_MIGRATE_001)

### `ERR_MIGRATE_001` — `MigrationError` (`exceptions.py:117`, never raised)

`scripts/migrate_plan_entities.py` (the legacy 11-col → canonical-24 migration, commit `eeac3aa`) does not import `exceptions`. `sqlite_adapter.py` has no schema-version guard.

**Fix:** Add a schema-version guard at the top of `SQLiteAdapter.__init__` that raises `MigrationError` when `PRAGMA user_version` is below the minimum supported version. Import the exception into the migration script and raise on idempotency conflict.

---

## §12 Per-Tool Error Map

### 8 MCP tools (`src/mcp_server/server.py`)

Every tool is dispatched from the single `_call_tool` handler (`server.py:251`). **None emits an error code.** Errors are `json.dumps({"error": ...})` strings, and `is_error` is inferred by **string prefix matching** — `server.py:505`: `is_error = text.startswith('{"error"')`. Any error dict whose first key is not `error`, or any message with leading whitespace, is silently reported as success.

| # | Tool | Error surface | Hidden failure |
|---|------|---------------|----------------|
| 1 | `ikigai_score` | none | `_read_checkpoint` (`:203`) and `_read_entity` (`:238`) both `except Exception: return {}`. Corrupt pickle, missing table, or locked DB indistinguishable from "no data yet" — returns `{"vector_scores": {}, ...}`. Also `round(mv, 4)` at `:267` will `TypeError` uncaught if `meta_vector` is NULL. |
| 2 | `ikigai_regime` | none | same swallow; silently defaults to `"MAINTAIN"` / `days=0` |
| 3 | `ikigai_phase` | none | same swallow; silently defaults to `"BUSCA"` |
| 4 | `ikigai_decompose` | `{"error": "dream_ueid required"}` (`:293`) | Only the missing-arg case is reported. `_decompose_ueid` (`:99`) has **two** `except Exception: pass` blocks (`:136`, `:158`) — every unparseable vault file drops out silently. Nonexistent dream returns `{"dream": {}, "objectives": [], ...}` with **no error**, indistinguishable from an empty dream. No UEID format validation — malformed UEID yields `""` from `_slug_from_ueid` (`:111-114`). |
| 5 | `ikigai_corrections` | none | `:306` `except Exception: corrs = []` — malformed corrections JSON reported as zero corrections |
| 6 | `ikigai_plan_cycle` | `{"error": str(e)}` (`:379-380`) | The one tool that reports failure — but **untyped**: import error, `ValueError` from any of ~61 validators, and graph timeout all collapse to the same shape. Nested `except Exception: pass` at `:367-368` marked `# non-fatal` means the `SQLiteAdapter.upsert()` persistence step can fail while the tool still returns success. |
| 7 | `ikigai_checkpoint` | 5 ad-hoc strings (`:398, :400, :413, :416, :431`) | Five ad-hoc messages, zero codes. `sqlite3.connect` / `pickle.loads` at `:390-428` are **unguarded** — a corrupt checkpoint blob raises out of the MCP handler entirely. |
| 8 | `ikigai_sync_vault` | 3 ad-hoc strings (`:436, :446, :500`) | `_read_plan_entity` (`:220`) `except Exception: return {}`, so a DB read failure is reported as the misleading "run ikigai_plan_cycle first". |

**Fallback for unrecognized name** (`:503`): `text = f"Unknown tool: {name}"` — **plain text, not JSON**, so `is_error` evaluates `False` and an unknown-tool call is returned as **success**.

### 18 agent tools (`src/agents/tools.py`)

`IKIGAI_TOOLS` (`tools.py:1091-1113`), all LangChain `@tool`. **None emits an error code.** Universal idiom: `return f"⚠️ {e}"` — a *success* return carrying a warning glyph, so the LLM cannot distinguish failure from output.

| # | Tool | Line | Error handling | Note |
|---|------|-----:|----------------|------|
| 1 | `ikigai_score` | 68 | none | `_read_checkpoint_data:57` `except Exception: return {}`. Returns `"⚠️ No vector scores found in checkpoint. Run \`plan\` first."` for both empty and corrupt state. |
| 2 | `ikigai_regime` | 100 | none | silently defaults `MAINTAIN` / `qhe=0.65` |
| 3 | `ikigai_phase` | 131 | none | silently defaults `BUSCA` |
| 4 | `ikigai_corrections` | 171 | none | `"✅ No corrections — system is balanced."` on read failure — **a swallowed error reported as a green checkmark** |
| 5 | `ikigai_decompose` | 201 | `:237` `except Exception as e: return f"⚠️ Could not decompose UEID: {e}"` | Imports `mcp_server.server._decompose_ueid`, inherits both `except Exception: pass` blocks |
| 6 | `ikigai_plan_cycle` | 247 | **none** | `graph.invoke()` at `:309` unguarded — any validator `ValueError` propagates raw. Also mutates `sys.path` at `:265`. |
| 7 | `ikigai_sync_vault` | 332 | **none** | `log_file.write_text()` at `:389` unguarded — `OSError` escapes. `MarkdownWriteError`/`ERR_IO_002` is not used despite this being exactly a markdown write. |
| 8 | `ikigai_checkpoint` | 399 | `:452` `except Exception: data = {}`; `:472` `except (TypeError, ValueError): serializable[k] = str(v)` | Unpack failure returns `"cycle_id: ?"` placeholders. Returns `f"Unknown action: {action}"` at `:477` — no marker. `sqlite3.connect` at `:420` unguarded. |
| 9 | `solverforge_list_events` | 644 | 4 branches (`:672, :674, :676, :661`) | Best-structured handler — 4 distinct branches, still zero codes. Hardcoded `.exe` path at `:638`. |
| 10 | `solverforge_create_event` | 681 | 4 branches (`:717, :719, :721, :709`) | |
| 11 | `tuiboard_list_boards` | 737 | `:755, :757, :759` | `RuntimeError` is the `_mcp_call_v1` triple (timeout/exit/JSON-RPC error) flattened into one message |
| 12 | `tuiboard_get_tasks` | 764 | `:802, :804` | **No `FileNotFoundError` branch** — missing `bun` degrades to generic `⚠️ {e}`, unlike tool 11 |
| 13 | `tuiboard_update_task` | 809 | `:861, :863` | Sends `expectedMtimeMs: int(time.time()*1000)` (`:855`) — i.e. *now*, defeating the optimistic-concurrency check. A lost-update conflict is not detectable. |
| 14 | `tuiboard_create_task` | 868 | `:900, :902` | |
| 15 | `taskdog_list_tasks` | 926 | `:972, :974, :976` + `:956` substring sniff | Server-down detection by grepping stderr for English substrings — locale/wording-fragile. Closest thing to error *classification* in the agent layer, and it is string matching. |
| 16 | `taskdog_create_task` | 981 | `:1021, :1023, :1025` + `:1017` substring sniff | |
| 17 | `taskdog_complete_task` | 1030 | `:1047, :1049, :1051` + `:1043` substring sniff — **only 2 substrings** (`"connect"`, `"refused"`), missing `"no connection"` | Inconsistent with tools 15/16/18 |
| 18 | `taskdog_get_task` | 1056 | `:1080, :1082, :1084` + `:1069` substring sniff | Returns `f"Task #{task_id} not found."` at `:1079` with **no marker** — genuine not-found and a parse miss are identical |

### Undeclared CLI codes (3)

Emitted by `cli/app.py` but **absent from `exceptions.py`**, so nothing can import or assert on them:

| Code | Site | Message | Trigger |
|------|------|---------|---------|
| `ERR_CLI_001` | `cli/app.py:67` (default param of `_err`) | caller-supplied | **Catch-all default.** Every `_err()` call without explicit `code=` lands here — e.g. `app.py:299` `f"Invalid entity_type: {entity_type}"`. Distinct failures are indistinguishable to a machine reader. |
| `ERR_CLI_404` | `cli/app.py:304` | `f"Not found: {entity_type}/{slug}"` | `db.find_by_slug()` returned `None` |
| `ERR_CLI_501` | `cli/app.py:455` | `"--prefer sqlite not yet implemented (destructive; use with caution)"` | `reconcile --prefer sqlite` invoked |

`_err()` envelope (`app.py:69-71`): `{"ok": false, "error": {"code": ..., "message": ...}}` to stderr + `typer.Exit(code=1)`.

---

## §13 Error Handling Patterns

The harness exhibits **five** error-handling patterns, none of them code-aware.

### Pattern 1 — Silent swallow (`except Exception: return default`)

**Sites:** ~14 across MCP tools (`:136, :158, :203, :220, :238, :306`) and agent tools (`tools.py:57, :452`).
**Failure mode:** distinct failure modes (missing table, corrupt pickle, locked DB, schema mismatch) collapse to the same default. The agent or client cannot tell "no data yet" from "corruption".
**Fix:** Carry a `warnings: list[str]` in the return value alongside the data; raise at the top-level handler when the default is returned.

### Pattern 2 — String-prefix error detection (`text.startswith('{"error"')`)

**Site:** `server.py:505`.
**Failure mode:** any error dict whose first key is not `error`, or any message with leading whitespace, is silently reported as success. An unknown-tool call (`:503`) returns plain text and is reported as success.
**Fix:** emit the envelope from a single `_err()` helper (parallel to `cli/app.py:69-71`) and check `is_error` from the helper return rather than string-matching.

### Pattern 3 — Warning-glyph success (`return f"⚠️ {e}"`)

**Sites:** ~30 across agent tools.
**Failure mode:** the LLM receives a string starting with `⚠️` and cannot distinguish it from a deliberate warning. The green-checkmark case (`ikigai_corrections`, `tools.py:171`) is the inverse — an error is reported as success.
**Fix:** raise a typed exception that the agent loop catches and translates to a structured `{ok: false, error: {code, message}}` payload, never a return string.

### Pattern 4 — Substring sniffing (`if "connect" in err_output`)

**Sites:** `taskdog_list_tasks:956`, `taskdog_create_task:1017`, `taskdog_complete_task:1043` (2-substring variant), `taskdog_get_task:1069`.
**Failure mode:** locale- and wording-fragile. A taskdog server emitting `Unable to connect` in Spanish or with a different verb is reported as a generic failure, not server-down.
**Fix:** require taskdog to exit with a documented non-zero code for server-down; map codes to typed exceptions.

### Pattern 5 — Retry + circuit-breaker (the exception)

The one tool that does it right is `src/agents/tools.py` `_mcp_call_v1` (post-`87f6ef9`): client-side retry + circuit-breaker + scoped cache invalidation, with CB-outer / retry-inner so the CB counts logical calls (not attempts). Its three `RuntimeError` templates (§6) are the most structured error surface in the harness and still carry no codes.

### Retry / circuit-breaker / logging

**Where retries exist:** only inside `_mcp_call_v1` for MCP transport. No retry at any other layer — markdown read failures, YAML parse errors, validator failures, drift detection, and reconciliation all propagate (or are swallowed) on first attempt.

**Where circuit-breakers exist:** only `_mcp_call_v1`. No CB at the markdown-DB layer (a corrupted vault file gets re-parsed on every query) or at the SQLite layer (a locked DB will block each new attempt).

**Where errors are logged:** nowhere systematically. The observability layer (`src/observability/error_capture.py`) records exceptions as OTel span attributes on the way out, but the original `ERR_*` code is never preserved — `error.class` is the Python type name. Two failures with the same cause but different code-bearing types will be grouped together; two failures with the same code but different Python types will be split.

---

## §14 Cross-references

| Doc | Path | Relevance |
|-----|------|-----------|
| Master System Diagnostic | `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` | Top-level catalog of issues across IKIGAI, PAV, vibe-ops; this file is the error-code companion |
| Risk-Effort Matrix | `code-docs/diagnostic/2026-08-27-risk-effort-matrix.md` | Triage priorities; dead-code removal (15 codes) is low-effort low-risk; wire IO_001/002 to MCP/agent paths is medium |
| Migration Scripts Catalog | `code-docs/diagnostic/2026-08-27-migration-scripts-catalog.md` | `ERR_MIGRATE_001` should be wired into the 11-col → canonical-24 migration |
| Issue Dependencies | `code-docs/diagnostic/2026-08-27-issue-dependencies.md` | Cross-system dependency map |

**Related commits:** `1d9479a` docs(observability): 4 specs for next steps · `87f6ef9` feat(reliability): client-side retry + circuit-breaker + scoped cache invalidation · `0ff111d` refactor(commit, mcp-server): route plan entity writes through `SQLiteAdapter` · `eeac3aa` chore(scripts): `migrate_plan_entities.py` for legacy 11-col DBs.

**Related modules (not yet read for this catalog):** `src/observability/error_capture.py` — parallel taxonomy (Python type names, not `ERR_*` codes) · `scripts/migrate_plan_entities.py` — should wire `ERR_MIGRATE_001` · `src/ikigai/override/` — empty directory; `ERR_OVERRIDE_001` cannot fire until subsystem lands · `src/ikigai/persistence/` — empty directory; no codes to wire.

---

## §15 Verification commands

### 15.1 Confirm declared codes match this catalog

```bash
grep -nE "^class\s+(IKIGAiError|InvalidUEIDError|UEIDCollisionError|SlugImmutableError|ScoreRangeError|ScoreUnitMismatchError|RegimeHysteresisViolationError|PhaseConvergenceError|InvalidStateTransitionError|GuardConditionFailedError|SyncError|DriftDetectedError|OverrideRejectedError|MarkdownParseError|MarkdownWriteError|ValidationError|MigrationError)\b" \
  C:/Users/mathe/code_space/life-oss/life/life-ops/ikigai/src/ikigai/exceptions.py
```

Expected: 18 matches at the line numbers cited in §0 Summary table.

### 15.2 Find all `raise` sites of declared exception classes

```bash
grep -rnE "raise\s+(IKIGAiError|InvalidUEIDError|UEIDCollisionError|SlugImmutableError|ScoreRangeError|ScoreUnitMismatchError|RegimeHysteresisViolationError|PhaseConvergenceError|InvalidStateTransitionError|GuardConditionFailedError|SyncError|DriftDetectedError|OverrideRejectedError|MarkdownParseError|MarkdownWriteError|ValidationError|MigrationError)\b" \
  C:/Users/mathe/code_space/life-oss/life/life-ops/ikigai/src/
```

Expected: 6 matches (4× `MarkdownParseError` + 1× `MarkdownWriteError` + 1× chained-from `ValueError` site).

### 15.3 Confirm undeclared CLI codes are absent from `exceptions.py`

```bash
grep -nE "ERR_CLI_001|ERR_CLI_404|ERR_CLI_501" \
  C:/Users/mathe/code_space/life-oss/life/life-ops/ikigai/src/ikigai/exceptions.py
```

Expected: zero matches.

```bash
grep -rnE "ERR_CLI_001|ERR_CLI_404|ERR_CLI_501" \
  C:/Users/mathe/code_space/life-oss/life/life-ops/ikigai/src/ikigai/cli/
```

Expected: matches at `app.py:67`, `app.py:304`, `app.py:455`.

### 15.4 Confirm dead-code raise-site count

For each dead code in §0, run:

```bash
grep -rnE "raise\s+InvalidUEIDError" C:/Users/mathe/code_space/life-oss/life/life-ops/ikigai/src/
grep -rnE "raise\s+UEIDCollisionError" C:/Users/mathe/code_space/life-oss/life/life-ops/ikigai/src/
# ... repeat for each dead code
```

Expected: zero matches per dead code.

### 15.5 Confirm empty directories

```bash
ls C:/Users/mathe/code_space/life-oss/life/life-ops/ikigai/src/ikigai/persistence/
ls C:/Users/mathe/code_space/life-oss/life/life-ops/ikigai/src/ikigai/override/
```

Expected: both empty (or missing).

### 15.6 Confirm `errors.py` does not exist

```bash
test -f C:/Users/mathe/code_space/life-oss/life/life-ops/ikigai/src/ikigai/errors.py && echo EXISTS || echo MISSING
```

Expected: `MISSING`.

### 15.7 Confirm parallel observability taxonomy

```bash
grep -nE "error\.class\s*=" C:/Users/mathe/code_space/life-oss/life/life-ops/ikigai/src/observability/error_capture.py
```

Expected: 2 matches (UnicodeDecodeError, FileNotFoundError) — neither references any `ERR_*` code.

### 15.8 Confirm `is_error` string-match

```bash
grep -nE "startswith\(\"\{\\\"error" C:/Users/mathe/code_space/life-oss/life/life-ops/ikigai/src/mcp_server/server.py
```

Expected: 1 match at `server.py:505`.

### 15.9 Re-scan after fixes

After wiring any code, re-run §15.2 and §15.4 to confirm:

- Dead-code raise counts move from 0 to ≥1 (where wired).
- Coded-tool counts move from 0 to ≥1 for any tool that adopts `e.code`.

---

*End of catalog. Re-scan after each fix batch; counts in §0 are the canonical state at 2026-08-27.*