# Incident Response Runbook — IKIGAI / Algorithmic Life OS

**Date:** 2026-08-27
**Scope:** 13 silent-failure modes surfaced by the IKIGAI Error Code Catalog (`code-docs/diagnostic/2026-08-27-error-catalog.md`)
**Audience:** Operator (matheus), on-call agent (Claude Code session)
**Authority:** This runbook is the canonical response procedure for the failure modes it covers. When in doubt, follow the runbook before improvising.

---

## §0 Purpose

This runbook codifies response procedures for **13 silent-failure modes** identified by
the 2026-08-27 error-code scan (`exceptions.py` registry, MCP `server.py`, agent `tools.py`,
observability `error_capture.py`). All 13 share a single hazard class: **the failure is
reported (or not reported) in a way that the agent loop, the CLI envelope, or the
operator cannot reliably distinguish from a successful path.**

The 13 modes, with their canonical error codes and primary hazard pattern:

| # | Mode | Code | Hazard pattern (from catalog §13) |
|---|------|------|------------------------------------|
| INC-01 | MCP server connection refused | (transport) | Pattern 4 — substring sniffing / silent fallthrough |
| INC-02 | `_MCP_SESSION_CACHE` stale | (transport) | Pattern 1 — silent swallow |
| INC-03 | Schema drift (markdown vs SQLite) | `ERR_DRIFT_001` (dead) | Hybrid drift-as-data vs drift-as-error |
| INC-04 | UEID validation failure | `ERR_ID_001` (dead) | Parallel uncoded validators |
| INC-05 | State machine transition blocked | `ERR_STATE_001/002` (dead) | `TransitionError` shadows coded exception |
| INC-06 | Hysteresis violation | `ERR_REGIME_001` (dead, swallowed) | Deliberate `# Warn but allow` pass |
| INC-07 | Sync engine exception swallowed | `ERR_SYNC_001` (dead) | `except Exception: continue` / `except Exception as e: text = json.dumps({"error": str(e)})` |
| INC-08 | CLI subprocess timeout | (transport) | Three `RuntimeError` templates from `_mcp_call_v1`, no codes |
| INC-09 | SQLite lock contention | (uncoded) | No circuit-breaker at SQLite layer |
| INC-10 | LangGraph checkpointer corruption | (uncoded) | `sqlite3.connect` / `pickle.loads` unguarded in `server.py:390-428` |
| INC-11 | Missing env var | (uncoded) | Hardcoded paths in `tools.py:638-640, 729-733, 910-912` |
| INC-12 | Frontmatter parse error | `ERR_IO_001` (LIVE) | `except MarkdownParseError: continue` in `markdown_db.py:196, 244` |
| INC-13 | Pydantic `ValidationError` silent coercion | `ERR_VAL_001` (dead) | `PlanEntity(extra="allow")` + ~61 uncoded sites; name collides with Pydantic |

For each mode, §2–§14 below prescribe: **Symptom**, **Likely root cause**, **Diagnostic commands**, **Remediation**, **Escalation**, **Recovery verification**.

**Pre-flight (before any incident response):**
1. Confirm cwd is the repo root: `cd "C:\Users\mathe\code_space\life-oss\life"`
2. Confirm the observability layer is collecting: `python -m ikigai.cli.app health`
3. Note the run ID from `data/session-*.md` (most recent) for the postmortem (§16)

---

## §1 Severity classification

Severity is decided by **blast radius** (what is now broken) and **detectability** (how long until the operator notices). Use the matrix below; do not invent custom severities.

### SEV-1 — Critical (system won't start, or silent data corruption)

- **Criteria:** Agent loop is unusable; a vault↔SQLite split is widening; checkpoint is unreadable.
- **Response time:** Immediate (within 15 min of detection).
- **Examples:** INC-01 (MCP down + agent loop stalls), INC-03 (drift >5 min, no reconcile ran), INC-10 (checkpoint pickle raises), INC-12 (frontmatter loop dropping entities from `index_dump()`).

### SEV-2 — High (functional but wrong)

- **Criteria:** Tool returns a value, but the value is wrong and the agent loop does not detect the wrongness.
- **Response time:** Within 2 hours.
- **Examples:** INC-02 (cache returns stale graph state), INC-04 (malformed UEID silently decomposes to `""`), INC-05 (transition silently fails, state unchanged), INC-07 (sync reports success while write failed), INC-08 (MCP timeout, agent retries 3× then surfaces stale data), INC-13 (Pydantic coerces unknown frontmatter keys).

### SEV-3 — Medium (degraded but visible)

- **Criteria:** Tool returns an error code; operator must take action before next session.
- **Response time:** Same business day.
- **Examples:** INC-06 (hysteresis violation logged, allow-listed by override), INC-09 (SQLite locked briefly, eventually unblocks), INC-11 (missing env var caught at next boot).

### Severity escalation rule

If a SEV-2 incident persists across **two consecutive daily runs** without remediation, escalate to SEV-1. The runbook's "Escalation" field for each incident is the contact path for SEV-1 only; SEV-2/3 can be deferred to the next planning cycle.

---

## §2 Runbook INC-01: MCP server connection refused

### Symptom
- Agent tool returns `⚠️ MCP error: ...` or hangs and times out after `timeout` seconds.
- CLI tool emits `{"error": str(e)}` with the `RuntimeError` template `MCP server error (exit {returncode}): {err}` (catalog §6, `tools.py:539`).
- Repeated calls produce the same error — server is not coming back on its own.
- The agent loop is **stuck**: it cannot advance past the MCP-dependent step.

### Likely root cause
1. The downstream MCP server (taskdog, tuiboard, solverforge-calendar) crashed or was never started.
2. `_TASKDOG_CLI` Windows path used on Linux host (catalog §1 C5: `tools.py:910-912`).
3. `~/.claude/.mcp.json` does not register the `ikigai-maintainer-mcp` server (catalog §2 S-C2).
4. Subprocess was started without `subprocess.PIPE` causing stdio deadlock.

### Diagnostic commands
```bash
# 1. Which MCP servers are configured?
cat ~/.claude/.mcp.json | jq '.mcpServers | keys'

# 2. Is the downstream binary on PATH?
which taskdog 2>/dev/null || ls "C:\Users\mathe\code_space\apps\dev-tools\taskdog\"

# 3. Can the agent reach the server manually?
taskdog --help 2>&1 | head -5

# 4. Inspect the most recent agent log for the exact exit code
grep -A2 "MCP server error" life-ops/ikigai/data/logs/agent.log | tail -20

# 5. Confirm stdio pipe is set (catalog: missing pipe → deadlock)
grep -nE "subprocess\.(Popen|run)" life-ops/ikigai/src/agents/tools.py | head -20
```

### Remediation
1. **Restart the downstream server** (taskdog, tuiboard, solverforge) using the worktree's documented start script. If the script is missing, fall back to direct invocation: `python -m taskdog.server` or equivalent.
2. **Verify `.mcp.json`** — add the missing server entry, restart the agent session.
3. **If Windows-path-on-Linux**: set `TASKDOG_CLI_OVERRIDE` env var to the Linux binary path (see §11).
4. **Disable the call temporarily** (less risk than stalling): wrap the tool call in a try/except in the harness and return a structured `{"ok": false, "error": {"code": "ERR_SYNC_001", "message": "MCP down"}}` placeholder so the loop can continue.

### Escalation
- SEV-1: agent loop is the primary interface. Ping the user immediately via terminal notification (`PushNotification`); do not wait for next planning cycle.
- File a diagnostic note in `data/matheus/ikigai_state/incidents/INC-01-YYYY-MM-DD.md`.

### Recovery verification
- Agent tool returns a non-error value within 3 calls.
- `python -m ikigai.cli.app health` reports all 8 MCP tools reachable.
- Re-run a representative plan cycle end-to-end; checkpoint is updated.

---

## §3 Runbook INC-02: `_MCP_SESSION_CACHE` stale

### Symptom
- MCP tool returns a successful response, but the response reflects state from **before** a known recent write.
- Two consecutive calls to the same tool produce identical payloads when state should have changed.
- Catalog: `_MCP_SESSION_CACHE` never invalidated on `RuntimeError` / timeout / process exit (catalog §2 S-H2, `tools.py:550`).

### Likely root cause
1. The cache key was not invalidated after a write tool succeeded but a downstream sync failed.
2. The subprocess for the MCP server was restarted but the cache survived in module-level state.
3. The circuit-breaker reset (`_mcp_call_v1`) closed but the cache was not flushed.

### Diagnostic commands
```bash
# 1. Find the cache definition
grep -nE "_MCP_SESSION_CACHE" life-ops/ikigai/src/agents/tools.py

# 2. Find every mutation site (writes that should invalidate)
grep -nE "(_MCP_SESSION_CACHE|ikigai_(plan_cycle|sync_vault|checkpoint)|write_text|upsert)" \
  life-ops/ikigai/src/agents/tools.py | head -40

# 3. Confirm runtime cache state (add a debug print if absent)
#    In a Python REPL with the module loaded:
python -c "from life_ops.ikigai.src.agents import tools; print(len(tools._MCP_SESSION_CACHE))"

# 4. Check whether the cache has a TTL
grep -nE "(time\.time|ttl|expires|invalidat)" life-ops/ikigai/src/agents/tools.py | head -20
```

### Remediation
1. **Flush the cache** at the next tool entry: `tools._MCP_SESSION_CACHE.clear()` (one-liner from a REPL or a `-m` flag in the CLI).
2. **Apply the canonical fix** (catalog §2 S-H2): add `tools._MCP_SESSION_CACHE.clear()` in the `except RuntimeError:` block of `_mcp_call_v1` and in the success path after any write tool (`ikigai_plan_cycle`, `ikigai_sync_vault`, `ikigai_checkpoint`).
3. **For the immediate incident**: re-run the read; the second call (post-flush) should reflect the latest state.

### Escalation
- SEV-2 (functional but wrong) unless the stale value was used to make a planning decision — in that case, escalate to SEV-1 and pause any auto-applied corrections.
- Cross-link the cache-stale write to the originating tool call so the postmortem (§16) can audit downstream decisions.

### Recovery verification
- Two consecutive reads of the affected tool produce different payloads after a write.
- `_MCP_SESSION_CACHE` is empty between calls when no read has happened in the last 60s.
- A deliberate stale-cache probe (write → read with `time.sleep(0.1)`) returns fresh data after the fix.

---

## §4 Runbook INC-03: Schema drift (markdown vs SQLite)

### Symptom
- `triagem.md` (written by `propagation/triagem.py`) shows `drift_kind ∈ {missing_sqlite, drift_detected}` for one or more entities.
- 5-minute threshold tripped: catalog §7 `app.py:481` hardcodes `> 300` seconds.
- Operator notices a markdown file edited but the SQLite row unchanged (or vice versa).

### Likely root cause
1. **Split-brain schema** (catalog §2 S-C1, master diagnostic C2): the canonical 24-col `plan_entities` table is never written to; the runtime 11-col table is.
2. A markdown write failed at the atomic-rename step (catalog §9 `ERR_IO_002`), leaving the `.tmp` file and a stale SQLite row.
3. SQLite write succeeded but markdown write failed (the two destinations are not transactional).

### Diagnostic commands
```bash
# 1. Read the drift ledger
cat life-ops/ikigai/data/matheus/ikigai_state/triagem.md | tail -40

# 2. Compare mtime vs SQLite mtime_for()
python -c "
import sqlite3, os
from pathlib import Path
con = sqlite3.connect(os.path.expanduser('~/.ikigai/plan_entities.db'))
md = Path('life-ops/ikigai/data/matheus/dream-2026.md')
print('md mtime:', md.stat().st_mtime)
row = con.execute('SELECT mtime FROM plan_entities WHERE slug = ?', ('dream-2026',)).fetchone()
print('sqlite mtime:', row[0] if row else 'missing')
"

# 3. Check the .tmp leftovers from atomic-rename failures
find life-ops/ikigai -name "*.tmp" -mmin -60

# 4. Confirm which schema is canonical
grep -nE "CREATE TABLE|CREATE TABLE IF NOT EXISTS" \
  life-ops/ikigai/src/ikigai/propagation/sqlite_adapter.py | head -10
```

### Remediation
1. **For one-off drift**: run `python -m ikigai.cli.app reconcile --prefer markdown` (or `--prefer sqlite`) — but **read the warning first**: catalog §12 ERR_CLI_501 (`--prefer sqlite not yet implemented`).
2. **For split-brain schema**: this is the canonical S-C1 fix from the master diagnostic. Reconcile runtime writers (`commit.py:58-118` + `server.py:347-357`) to the 24-col canonical schema. Run `scripts/migrate_plan_entities.py` (commit `eeac3aa`) to backfill.
3. **For `.tmp` leftovers**: clean up manually; the writer does not unlink on failure (catalog §9 ERR_IO_002 fix).

### Escalation
- SEV-1 if drift >24h and any agent tool has consumed the stale state.
- SEV-2 otherwise. Log to `data/matheus/ikigai_state/incidents/INC-03-YYYY-MM-DD.md`.

### Recovery verification
- `triagem.md` shows zero `drift_detected` entries after a fresh run.
- A test round-trip (write markdown → trigger reconcile → read SQLite) matches.
- The 24-col schema is the single source of truth: `SELECT name FROM sqlite_master WHERE type='table' AND name='plan_entities'` returns the canonical columns only.

---

## §5 Runbook INC-04: UEID validation failure

### Symptom
- `ikigai_decompose` returns `{"dream": {}, "objectives": [], ...}` for a dream that should have content (catalog §12 tool 4).
- Agent tool returns `"⚠️ Could not decompose UEID: {e}"` (`tools.py:237`).
- `_slug_from_ueid` returns `""` (catalog §1 `server.py:111-114`).
- No error reaches the operator — the failure is silent.

### Likely root cause
1. The UEID string does not match the canonical 5-part format: `<namespace>:<entity_type>:<slug>:<uuid_short>:<content_hash_short>` (catalog §1).
2. Two parallel validators are bypassed: `types.py:51` raises bare `ValueError`, `entities/ueid.py:11-17` raises `pydantic_core.ValidationError`.
3. `InvalidUEIDError` (catalog §1, `exceptions.py:28`) is **declared but never raised**.

### Diagnostic commands
```bash
# 1. Try to parse the suspect UEID manually
python -c "
import sys; sys.path.insert(0, 'life-ops/ikigai/src')
from ikigai.types import UEID
UEID('DREAM:dream-2026:abc:deadbeef:cafe1234')
"

# 2. Find every UEID consumer
grep -rnE "(_slug_from_ueid|_decompose_ueid|UEID\()" life-ops/ikigai/src/

# 3. Confirm the dead code path
grep -nE "raise InvalidUEIDError" life-ops/ikigai/src/ -r
# Expected: zero matches (catalog §15.4)

# 4. Inspect the parallel validators
sed -n '40,55p' life-ops/ikigai/src/ikigai/types.py
sed -n '1,20p' life-ops/ikigai/src/ikigai/entities/ueid.py
```

### Remediation
1. **For one-off**: re-issue the UEID with the correct 5-part format.
2. **For systematic**: apply catalog §1 fix — import `InvalidUEIDError` in both `types.py` and `entities/ueid.py`; promote `ValueError` → `InvalidUEIDError`; add `except InvalidUEIDError` to consumer tools (`server.py:111-114, 136, 158` and `tools.py:237`).
3. **For LLM-emitted UEIDs**: tighten the agent prompt to require the 5-part format; emit `InvalidUEIDError` and surface as `{"error": {"code": "ERR_ID_001", ...}}`.

### Escalation
- SEV-2 unless a planning decision was made on the silent decomposition — escalate to SEV-1.
- The decomposition returning empty data is the most insidious form: log every occurrence to `data/matheus/ikigai_state/ueid_failures.log`.

### Recovery verification
- `ikigai_decompose` returns the full subtree for the corrected UEID.
- The malformed UEID now surfaces an `InvalidUEIDError` with code `ERR_ID_001`.
- `grep -rnE "raise InvalidUEIDError" life-ops/ikigai/src/` returns ≥1 match after the fix.

---

## §6 Runbook INC-05: State machine transition blocked

### Symptom
- A `task_sm` / `project_sm` / `objective_sm` transition returns `⚠️ No transition from 'X' → 'Y'` or is silently dropped.
- Catalog §5: `_sm_base.py:71` raises uncoded `TransitionError`; `_sm_base.py:67` raises bare `ValueError` for unknown targets.
- The agent loop continues but the entity state is unchanged — no diagnostic reaches the operator.

### Likely root cause
1. The requested target state is not in the allowed-transition graph for the entity.
2. A guard condition blocked the transition (catalog §5 `ERR_STATE_002`).
3. The 8 state machines (`dream_sm`, `goal_sm`, `objective_sm`, `project_sm`, `task_sm`, `deliverable_sm`, `routine_sm`, `habit_sm`) all share the same `_sm_base.py` and the same uncoded behavior.

### Diagnostic commands
```bash
# 1. Inspect the state machine base
sed -n '1,80p' life-ops/ikigai/src/ikigai/state_machines/_sm_base.py

# 2. Find every consumer that catches TransitionError
grep -rnE "except TransitionError" life-ops/ikigai/src/
# Expected: zero matches (catalog §5)

# 3. List the 8 state machines
ls life-ops/ikigai/src/ikigai/state_machines/

# 4. Reproduce the failed transition
python -c "
import sys; sys.path.insert(0, 'life-ops/ikigai/src')
from ikigai.state_machines.task_sm import TaskStateMachine
sm = TaskStateMachine(current_state='TODO')
sm.transition('DONE')
"
```

### Remediation
1. **For one-off**: pick a valid intermediate state (e.g. `TODO → IN_PROGRESS → DONE`); re-attempt.
2. **For systematic**: apply catalog §5 fix — make `TransitionError` a subclass of `InvalidStateTransitionError`, or move `TransitionError` into `exceptions.py` and re-export. Add a `GuardConditionFailedError` subclass.
3. **For guard blocks**: surface the guard name in the error message so the operator can fix the guard, not the transition.

### Escalation
- SEV-2 unless a status update was lost (e.g. DONE never recorded → metrics stay wrong) → SEV-1.
- Cross-link the entity UEID + attempted transition to the postmortem.

### Recovery verification
- Valid transitions complete and persist to SQLite.
- Invalid transitions now raise `InvalidStateTransitionError` with code `ERR_STATE_001`.
- Guard-blocked transitions raise `GuardConditionFailedError` with code `ERR_STATE_002`.
- The 8 state machines are all exercised by a smoke test that covers one valid + one invalid + one guard-blocked path each.

---

## §7 Runbook INC-06: Hysteresis violation

### Symptom
- A regime sub-vector is in `PUSH` while its parent vector is in `RECOVER`. The violation is **deliberately allowed** (catalog §3, `entities/regime.py:79-93`, comment `# Warn but allow (override possible)`).
- `is_hysteresis_active` is carried as plain LangGraph state (`tools.py:281`, `server.py:326`) — never raised as an error.
- The agent's downstream decisions assume the violation was intentional; this is wrong while `src/ikigai/override/` is an empty directory.

### Likely root cause
1. A child vector scored well before its parent recovered — legitimate `PUSH` on a `RECOVER` parent.
2. The override subsystem (`src/ikigai/override/`) that would record the intentional pass is not yet implemented (catalog §8).
3. `RegimeHysteresisViolationError` (catalog §3, `exceptions.py:58`) is declared but the raise site is gated on `enabled=True` — currently `False`.

### Diagnostic commands
```bash
# 1. Find the coherence check
sed -n '70,100p' life-ops/ikigai/src/ikigai/entities/regime.py

# 2. Inspect the override directory (should be empty per catalog §8)
ls life-ops/ikigai/src/ikigai/override/

# 3. Find every consumer of is_hysteresis_active
grep -rnE "is_hysteresis_active" life-ops/ikigai/src/

# 4. Reproduce the violation
python -c "
import sys; sys.path.insert(0, 'life-ops/ikigai/src')
from ikigai.entities.regime import RegimeGraph
g = RegimeGraph(parent='RECOVER', sub='PUSH')
g._coherence_check()
"
```

### Remediation
1. **For one-off**: treat as informational; the override subsystem is intentionally a no-op until implemented.
2. **For systematic**: apply catalog §3 fix — add `enabled=True` toggle to `_coherence_check`. When the override subsystem lands, raise `RegimeHysteresisViolationError` unless an override record applies.
3. **For now**: log the violation explicitly so postmortem can confirm intent. Add an `assert violation_passed_intentionally` log line to `_coherence_check`.

### Escalation
- SEV-3 (degraded but visible). The silent pass is by design until override lands; do not escalate unless the downstream decision was made without operator awareness.

### Recovery verification
- The violation is logged to the observability layer (`error_capture.py`).
- After the override subsystem lands, the violation is recorded in the override log AND surfaces as `RegimeHysteresisViolationError` when no override exists.
- Regime scoring remains stable across a 5-day window — no `PUSH → RECOVER → PUSH` thrashing.

---

## §8 Runbook INC-07: Sync engine exception swallowed

### Symptom
- `ikigai_sync_vault` reports success but the vault write did not happen.
- CLI reconcile (`app.py:450, :494`) silently drops failed entities from the count — the operator sees a success message with a missing delta.
- The MCP path (`server.py:499`) returns `{"error": str(e)}` but **untyped** — agent cannot distinguish a transport failure from a parse failure.

### Likely root cause
1. `agents/tools.py:389` — `log_file.write_text(...)` is unguarded. `OSError` escapes raw (catalog §6).
2. `cli/app.py:450, :494` — `except Exception: continue` silently drops entities.
3. `mcp_server/server.py:499` — `except Exception as e: text = json.dumps({"error": str(e)})` collapses all failures.

### Diagnostic commands
```bash
# 1. The four swallow sites (catalog §6)
grep -nE "except Exception.*continue|except Exception.*pass|except Exception as e.*json\.dumps" \
  life-ops/ikigai/src/ikigai/mcp_server/server.py \
  life-ops/ikigai/src/ikigai/agents/tools.py \
  life-ops/ikigai/src/ikigai/cli/app.py

# 2. Confirm the dropped-entity count
grep -nE "reconcile|dropped|fail" life-ops/ikigai/src/ikigai/cli/app.py | head -20

# 3. Look for orphan log files (sync claimed success but file is missing)
find life-ops/ikigai/data/matheus/ikigai_state -name "cycle-*.md" | wc -l

# 4. Compare the count against the planning cycle that produced them
python -c "
import sqlite3, os
con = sqlite3.connect(os.path.expanduser('~/.ikigai/plan_entities.db'))
print(con.execute('SELECT COUNT(*) FROM plan_entities').fetchone())
"
```

### Remediation
1. **For one-off**: re-run `ikigai_sync_vault` after manually verifying the vault write target directory exists.
2. **For systematic**: apply catalog §6 fix — wrap the three `RuntimeError` templates as distinct `SyncError` subclasses; add `except SyncError` at the four swallow sites; the CLI reconcile loops must log dropped entities rather than silently counting them.
3. **For MCP transport**: replace `text.startswith('{"error"')` (`server.py:505`) with a single `_err()` helper that emits the envelope `{ok: false, error: {code, message}}` and check `is_error` from the helper return.

### Escalation
- SEV-2 if a planning cycle was reported as persisted but the vault write failed. The risk is silent drift (catalog §7) compounded with the swallowed exception.
- SEV-1 if a correction was applied based on the missing sync.

### Recovery verification
- A deliberately failing sync (vault dir unwritable) now returns a `SyncError` with code `ERR_SYNC_001`.
- The CLI reconcile logs the dropped entity count rather than hiding it.
- MCP `_call_tool` returns `{"ok": false, ...}` for the failing call, not `{"error": str(e)}`.

---

## §9 Runbook INC-08: CLI subprocess timeout

### Symptom
- Tool returns `"⚠️ MCP call timed out after {timeout}s: {method}"` (catalog §6, `tools.py:537`).
- Three `RuntimeError` templates from `_mcp_call_v1`: timeout, exit code, JSON-RPC error — all untyped.
- After 3 retries (per `_mcp_call_v1` retry-inner), the circuit-breaker opens and the next call fails fast.

### Likely root cause
1. Downstream server is slow or hung (see INC-01).
2. The default `timeout` is too low for the operation.
3. The circuit-breaker opened from a previous failure and has not closed yet.

### Diagnostic commands
```bash
# 1. Find the timeout template
grep -nE "MCP call timed out after" life-ops/ikigai/src/agents/tools.py

# 2. Confirm the retry/CB state
grep -nE "_mcp_call_v1|circuit_breaker|cb_state" life-ops/ikigai/src/agents/tools.py | head -20

# 3. Inspect the call in isolation
time taskdog list_tasks 2>&1 | head -20

# 4. Check the OTel span for the call
#    (catalog §13: errors are logged as Python type name, not ERR_* code)
grep -E "timeout|MCP call timed out" life-ops/ikigai/data/logs/agent.log | tail -10
```

### Remediation
1. **For one-off**: bump the timeout for that specific call; the retry will pick up the new value.
2. **For systematic**: apply catalog §6 fix — wrap the three `RuntimeError` templates as distinct subclasses (`SyncTimeoutError`, `SyncServerError`, `SyncResponseError`) and emit them from `_mcp_call_v1` rather than bare `RuntimeError`.
3. **For the circuit-breaker**: confirm the CB is closed (`grep` for the state-check site) before retrying. If the CB is open, wait for the cooldown.

### Escalation
- SEV-2 unless the timeout is masking an INC-01 condition (MCP down). Always check INC-01 first.

### Recovery verification
- The retry succeeds within `2 × timeout` seconds.
- The CB state transitions are logged: CLOSED → OPEN → HALF_OPEN → CLOSED.
- After the fix, `_mcp_call_v1` raises `SyncTimeoutError` with code `ERR_SYNC_001` rather than bare `RuntimeError`.

---

## §10 Runbook INC-09: SQLite lock contention

### Symptom
- `sqlite3.OperationalError: database is locked` propagates raw from MCP tool calls (`server.py:390-428` — unguarded `sqlite3.connect`).
- `_read_checkpoint` (`server.py:203`) and `_read_entity` (`:238`) both `except Exception: return {}` — silently default to empty data (catalog §12).
- A vault write succeeds but the SQLite write blocks; the agent loop hangs.

### Likely root cause
1. Two writers (CLI reconcile + agent sync) target the same `~/.ikigai/plan_entities.db` without coordination.
2. A long-running read transaction holds a SHARED lock; the writer waits indefinitely (no `busy_timeout`).
3. SQLite was opened with `isolation_level=None` (autocommit) or default DEFERRED, leaving implicit transactions open.

### Diagnostic commands
```bash
# 1. Confirm the DB file
ls -la ~/.ikigai/plan_entities.db

# 2. Check active connections
#    (Windows: Resource Monitor; POSIX: lsof)
lsof ~/.ikigai/plan_entities.db 2>/dev/null || true

# 3. Confirm busy_timeout is set
grep -nE "busy_timeout|isolation_level" life-ops/ikigai/src/ikigai/propagation/sqlite_adapter.py

# 4. Reproduce: open the DB with two writers
python -c "
import sqlite3, threading, time
def w(i):
    c = sqlite3.connect(os.path.expanduser('~/.ikigai/plan_entities.db'))
    c.execute('BEGIN IMMEDIATE')
    time.sleep(2)
    c.execute('COMMIT')
import os, threading
threading.Thread(target=w, args=(1,)).start()
threading.Thread(target=w, args=(2,)).start()
"

# 5. Inspect WAL mode (write-ahead logging mitigates most contention)
python -c "
import sqlite3, os
c = sqlite3.connect(os.path.expanduser('~/.ikigai/plan_entities.db'))
print(c.execute('PRAGMA journal_mode').fetchone())
"
```

### Remediation
1. **For one-off**: wait 30s and retry; SQLite usually releases the lock within that window.
2. **For systematic**: enable WAL mode (`PRAGMA journal_mode=WAL`) and set `busy_timeout=5000`. Apply at every `sqlite3.connect` site in `sqlite_adapter.py`, `commit.py`, `server.py`.
3. **For long-running reads**: switch to `BEGIN DEFERRED` and use `sqlite3.Connection.set_progress_handler` to detect lock waits.

### Escalation
- SEV-2 if contention is intermittent; SEV-1 if a long-running migration holds the lock and blocks all writes.
- File an incident note to `data/matheus/ikigai_state/incidents/INC-09-YYYY-MM-DD.md`.

### Recovery verification
- Two concurrent writers complete without `OperationalError: database is locked`.
- `PRAGMA journal_mode` returns `wal`.
- The next 5 daily runs show zero lock-contention log lines.

---

## §11 Runbook INC-10: LangGraph checkpointer corruption

### Symptom
- `ikigai_checkpoint` MCP tool raises out of the handler entirely (catalog §12 tool 7 — `sqlite3.connect` / `pickle.loads` at `:390-428` unguarded).
- One of the 5 ad-hoc strings at `server.py:398, :400, :413, :416, :431` is returned.
- Agent tool `ikigai_checkpoint` (`tools.py:399`) returns `"cycle_id: ?"` placeholders (catalog §12 tool 8 — `:452` `except Exception: data = {}`).

### Likely root cause
1. The checkpoint blob in `~/.ikigai/checkpoints/<cycle_id>.pkl` is corrupt (partial write, schema mismatch).
2. The SQLite table was migrated but old pickles were not re-serialized.
3. A previous run wrote the blob to a different `sqlite3.connect` than the current reader expects.

### Diagnostic commands
```bash
# 1. List the checkpoint blobs
ls -la ~/.ikigai/checkpoints/

# 2. Try to unpickle each one
python -c "
import pickle, os
for f in os.listdir(os.path.expanduser('~/.ikigai/checkpoints/')):
    p = os.path.expanduser(f'~/.ikigai/checkpoints/{f}')
    try:
        pickle.load(open(p, 'rb'))
        print(f, 'OK')
    except Exception as e:
        print(f, 'CORRUPT', e)
"

# 3. Find the unguarded pickle.loads sites
grep -nE "pickle\.(load|loads)" life-ops/ikigai/src/ikigai/mcp_server/server.py

# 4. Inspect the checkpoint table schema
python -c "
import sqlite3, os
c = sqlite3.connect(os.path.expanduser('~/.ikigai/checkpoints.db'))
print(c.execute(\"SELECT sql FROM sqlite_master WHERE type='table'\").fetchall())
"
```

### Remediation
1. **For one corrupt blob**: archive it (`mv cycle-X.pkl cycle-X.pkl.corrupt-$(date +%s)`) and re-run the planning cycle; the next write will create a fresh blob.
2. **For systematic corruption**: re-serialize all checkpoints against the current schema. If the schema changed, this requires a migration step.
3. **For preventive measure**: wrap `pickle.loads` in `try: ... except (pickle.UnpicklingError, EOFError, AttributeError): return None` and emit a structured `{"ok": false, "error": {"code": "ERR_MIGRATE_001", ...}}`.

### Escalation
- SEV-1 if a checkpoint is needed to resume an in-flight planning cycle.
- SEV-2 if checkpoints are read-only at the moment of the incident.

### Recovery verification
- `ikigai_checkpoint` returns a structured payload, not a traceback.
- All archived `*.corrupt` blobs are listed in `data/matheus/ikigai_state/incidents/INC-10-corrupt-archive.md`.
- After the fix, `grep -nE "pickle\.loads" life-ops/ikigai/src/ikigai/mcp_server/server.py` shows the calls are inside a try/except.

---

## §12 Runbook INC-11: Missing env var

### Symptom
- `tools.py:638-640` (`solverforge`), `:729-733` (`tuiboard`), `:910-912` (`taskdog`) raise `FileNotFoundError` because a hardcoded path does not exist (catalog §1 C5, §2 S-H7).
- `taskdog_get_tasks` (catalog §12 tool 12) returns `⚠️ {e}` rather than the structured `FileNotFoundError` branch that `tuiboard_list_boards` does have.
- `MissingEnvVarError` is not declared in the catalog — there is no code to surface this consistently.

### Likely root cause
1. The env var (`TASKDOG_CLI_OVERRIDE`, `TUIBOARD_ROOT`, `SOLVERFORGE_ROOT`) is not set and no default exists.
2. The default path hardcoded in the source no longer matches the host layout (e.g. Windows path on Linux, catalog §1 C5).
3. The `.env` file (if any) was not loaded at module import time.

### Diagnostic commands
```bash
# 1. Inspect all env vars used by the harness
env | grep -iE "taskdog|tuiboard|solverforge|ikigai" | sort

# 2. Find every hardcoded path
grep -nE "(taskdog|tuiboard|solverforge).*\.exe|/mnt/c/|C:\\\\\\\\" \
  life-ops/ikigai/src/agents/tools.py | head -20

# 3. Confirm the canonical env var names (read the README)
grep -rnE "TASKDOG_CLI_OVERRIDE|TUIBOARD_ROOT|SOLVERFORGE_ROOT" \
  life-ops/ikigai/README.md life-ops/ikigai/src/ 2>/dev/null

# 4. Test the binary at the expected location
ls -la /mnt/c/Users/mathe/code_space/apps/dev-tools/taskdog/ 2>/dev/null || echo "MISSING"
```

### Remediation
1. **For one-off**: set the env var in the current shell and re-run. Add it to the project's `.env` (gitignored) and to the agent harness's `init_tracing()` time env load.
2. **For systematic**: apply catalog §2 S-H7 fix — move all hardcoded paths to a config file (`~/.ikigai/config.toml`) or env vars. Fail loudly at module load if any are missing (do not silently degrade).
3. **For Windows/Linux portability**: detect platform via `sys.platform` and pick the appropriate default.

### Escalation
- SEV-3 unless the missing var blocks the primary plan cycle, in which case SEV-2.
- Document the env var requirements in the harness README so future sessions don't re-hit the same gap.

### Recovery verification
- The env var is set and the binary is found.
- A `_check_env()` call at module load returns no missing vars.
- The next 3 agent sessions boot without env-var errors.

---

## §13 Runbook INC-12: Frontmatter parse error

### Symptom
- `MarkdownParseError` is raised (catalog §9, `ERR_IO_001` — the only live code besides `ERR_IO_002`).
- One of 4 raise sites fires:
  - `propagation/markdown_db.py:115` — `OSError` from `path.read_text`
  - `propagation/markdown_db.py:122` — empty/missing frontmatter
  - `propagation/frontmatter.py:145` — no closing `---`
  - `propagation/frontmatter.py:156` — YAML parse error
- `markdown_db.py:196` (`query()`) and `:244` (`index_dump()`) silently skip the file — `query()` returns a list with no signal that entities were dropped.

### Likely root cause
1. A vault markdown file was edited outside the harness and has malformed YAML.
2. The file was written by a tool that did not emit the closing `---`.
3. UTF-8 encoding error (catalog §15.7 — `UnicodeDecodeError` is one of two uncoded exceptions in observability).

### Diagnostic commands
```bash
# 1. Find the dropped files (re-run the loop with a count)
python -c "
import sys; sys.path.insert(0, 'life-ops/ikigai/src')
from ikigai.propagation.markdown_db import MarkdownDB
db = MarkdownDB()
dropped = 0
for path in db.vault_root.rglob('*.md'):
    try:
        db.parse_from_markdown(path)
    except Exception as e:
        print(f'DROPPED: {path}: {e}')
        dropped += 1
print(f'Total dropped: {dropped}')
"

# 2. The single surfaced-error site (catalog §9)
grep -nE "ERR_IO_001|MarkdownParseError" life-ops/ikigai/src/ikigai/cli/app.py | head -5

# 3. The silent-skip sites (the hazard)
grep -nE "except MarkdownParseError" life-ops/ikigai/src/ikigai/propagation/markdown_db.py
```

### Remediation
1. **For one-off**: open the file, fix the YAML, save it; the next `query()` call will pick it up.
2. **For systematic**: apply catalog §9 fix — read `e.code` rather than hardcoding `ERR_IO_001` in `app.py:307`; count skipped files in `query()` and `index_dump()` and return the count alongside the list; wire the MCP `_decompose_ueid` except blocks to `MarkdownParseError` and emit `{"error": {"code": "ERR_IO_001", ...}}`.
3. **For MCP path**: catalog §9 — `mcp_server/server.py:136, :158` use `except Exception: pass`. Replace with `except MarkdownParseError as e: return {"error": {"code": e.code, "message": str(e)}}`.

### Escalation
- SEV-1 if `index_dump()` is dropping entities silently (the operator cannot see what is missing).
- SEV-2 for one-off malformed files.

### Recovery verification
- The fixed file is picked up by `query()` and the entity is returned.
- A deliberate malformed file (no closing `---`) now returns a structured error rather than being silently skipped.
- `query()` returns a `dropped_count` field alongside the list.

---

## §14 Runbook INC-13: Pydantic ValidationError silent coercion

### Symptom
- `PlanEntity` accepts unknown frontmatter keys without error (catalog §10: `extra="allow"` at `base.py:38`).
- ~61 uncoded validator sites raise bare `ValueError` or Pydantic `ValidationError`. The IKIGAI `ValidationError` (`exceptions.py:113`) **name collides** with Pydantic's — `from ikigai.exceptions import ValidationError` shadows the Pydantic one.
- The CLI falls through to default `code="ERR_CLI_001"` (`app.py:298`) regardless of the underlying failure.

### Likely root cause
1. An LLM-emitted entity has a typo in a field name and Pydantic silently accepts it (because `extra="allow"`).
2. A status value outside the whitelist (catalog §10 — 6 entities, 11 sites) raises bare `ValueError`.
3. A field range check (e.g. `progress_pct must be in [0, 100]`) raises bare `ValueError` instead of `ERR_VAL_001`.

### Diagnostic commands
```bash
# 1. Confirm the collision hazard
grep -nE "^from ikigai\.exceptions import|^from pydantic import" \
  life-ops/ikigai/src/ikigai/entities/base.py | head -10

# 2. Find every PlanEntity validator
grep -rnE "extra=" life-ops/ikigai/src/ikigai/entities/

# 3. The 61 uncoded sites (catalog §10)
grep -rnE "raise ValueError" life-ops/ikigai/src/ikigai/entities/ | wc -l

# 4. Reproduce a coercion
python -c "
import sys; sys.path.insert(0, 'life-ops/ikigai/src')
from ikigai.entities.base import PlanEntity
e = PlanEntity(slug='test-entity', title='Test', extra_unknown_field='survives')
print('unknown field survived:', hasattr(e, 'extra_unknown_field'))
"
```

### Remediation
1. **For one-off**: fix the entity payload manually; the validator message will name the bad field.
2. **For systematic**: apply catalog §10 fix — rename IKIGAI `ValidationError` to `IKIGAIValidationError` to remove the Pydantic collision; switch `PlanEntity` to `extra="forbid"`; wire `_err()` to catch `IKIGAIValidationError` and emit `code="ERR_VAL_001"`.
3. **For status whitelist**: replace the 11 status-whitelist `ValueError` sites with `raise IKIGAIValidationError(...)` carrying the allowed-list in the message.

### Escalation
- SEV-2 (functional but wrong). The silent coercion is dangerous because downstream code may rely on the unknown field being absent.
- SEV-1 if a planning decision was made on the coerced entity.

### Recovery verification
- An unknown field now raises `IKIGAIValidationError` with code `ERR_VAL_001`.
- The Pydantic `ValidationError` and IKIGAI `IKIGAIValidationError` are no longer confused (verify by `from ikigai.exceptions import IKIGAIValidationError`).
- A full daily run completes with zero silently-coerced entities.

---

## §15 Escalation matrix (who to ping per SEV)

| SEV | Response time | Notification channel | Backup | Operator action |
|-----|---------------|----------------------|--------|-----------------|
| **SEV-1** | <15 min | `PushNotification` (terminal + phone if Remote Control) | GitHub Issue `@emergency` label | Pause agent loop; do not retry; follow runbook §; file postmortem stub |
| **SEV-2** | <2 h | Terminal `PushNotification` | Next planning cycle | Apply remediation; log to `data/matheus/ikigai_state/incidents/INC-NN-YYYY-MM-DD.md` |
| **SEV-3** | Same business day | `data/matheus/ikigai_state/incidents/INC-NN-YYYY-MM-DD.md` | Next planning cycle | Apply remediation; verify per runbook § |

**On-call rotation:** Single-user system; operator = matheus. Backup = next Claude Code session that picks up the workspace. Use `gh issue list --label emergency` to see open SEV-1s.

**Notification templates:**
- SEV-1: `INC-01 MCP server connection refused — agent loop stalled at step X. Runbook §2 followed. Pausing until acknowledged.`
- SEV-2: `INC-04 UEID validation failure — N entities affected. Runbook §5 in progress. Will resolve by EOD.`
- SEV-3: `INC-06 hysteresis violation — informational, override subsystem pending. No action required.`

---

## §16 Postmortem template

After every SEV-1 and SEV-2 incident, write a postmortem to `data/matheus/ikigai_state/incidents/INC-NN-YYYY-MM-DD-postmortem.md` using this template.

```markdown
# Postmortem: INC-NN (SEV-X) — <short title>

**Date:** YYYY-MM-DD
**Runbook:** §N
**Author:** <operator or agent>
**Status:** 🟡 Draft / ✅ Final

## Summary
One-paragraph description of what happened, who noticed, and what the user-visible impact was.

## Timeline (UTC)
- HH:MM — Event X
- HH:MM — Operator noticed symptom Y
- HH:MM — Runbook §N invoked
- HH:MM — Remediation applied
- HH:MM — Recovery verified

## Root cause
<one paragraph; cite the catalog §NN if applicable>

## What went well
- <list 2-3 things>

## What went wrong
- <list 2-3 things>

## Action items
| # | Action | Owner | Severity | Due |
|---|--------|-------|----------|-----|
| 1 | <fix the systemic issue per catalog §NN> | <owner> | SEV-X | YYYY-MM-DD |
| 2 | <add a regression test> | <owner> | SEV-3 | YYYY-MM-DD |

## Cross-references
- Error catalog: `code-docs/diagnostic/2026-08-27-error-catalog.md` §NN
- Master diagnostic: `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` §NN
- Related runbook: §N (this document)
```

---

## §17 Cross-references

### Primary sources
- `code-docs/diagnostic/2026-08-27-error-catalog.md` — 18 declared codes, 13 silent-failure modes (this runbook's source of truth).
- `code-docs/diagnostic/2026-08-27-master-system-diagnostic.md` — 77 cross-system findings; this runbook addresses the silent-failure subset.
- `code-docs/diagnostic/2026-08-27-migration-scripts-catalog.md` — `scripts/migrate_plan_entities.py` (commit `eeac3aa`) is referenced in INC-03 and INC-10.

### Related specifications
- `code-docs/diagnostic/2026-08-27-pre-merge-checklist.md` — pre-flight before any systemic fix.
- `code-docs/diagnostic/2026-08-27-risk-effort-matrix.md` — triage priorities (dead-code removal is low-effort low-risk; wiring IO_001/002 to MCP/agent is medium).
- `code-docs/diagnostic/2026-08-27-issue-dependencies.md` — cross-issue dependency graph.

### Code locations cited
- `life-ops/ikigai/src/ikigai/exceptions.py` — exception registry (18 classes).
- `life-ops/ikigai/src/mcp_server/server.py` — 8 MCP tools; `is_error` at `:505`; `_decompose_ueid` `:99-160`; `ikigai_checkpoint` `:390-428`.
- `life-ops/ikigai/src/agents/tools.py` — 18 agent tools; `_mcp_call_v1` (post-`87f6ef9`); `_MCP_SESSION_CACHE` `:550`.
- `life-ops/ikigai/src/ikigai/propagation/markdown_db.py` — `query()` `:196`, `index_dump()` `:244`, write `:103`.
- `life-ops/ikigai/src/ikigai/propagation/frontmatter.py` — YAML parse `:145, :156`.
- `life-ops/ikigai/src/ikigai/propagation/sqlite_adapter.py` — `upsert()` `:264`, `mtime_for()` `:257`.
- `life-ops/ikigai/src/ikigai/entities/base.py` — `PlanEntity` `:38, :46, :53, :70`.
- `life-ops/ikigai/src/ikigai/entities/regime.py` — `_coherence_check` `:79-93`.
- `life-ops/ikigai/src/ikigai/state_machines/_sm_base.py` — `TransitionError` `:10, :71`.
- `life-ops/ikigai/src/ikigai/observability/error_capture.py` — parallel taxonomy (Python type names, no `ERR_*` codes).
- `life-ops/ikigai/src/ikigai/cli/app.py` — `_err()` envelope `:69-71`; reconcile `:450, :494`; status check `:298`.

### Related commits
- `87f6ef9` — feat(reliability): client-side retry + circuit-breaker + scoped cache invalidation
- `0ff111d` — refactor(commit, mcp-server): route plan entity writes through `SQLiteAdapter`
- `eeac3aa` — chore(scripts): `migrate_plan_entities.py` for legacy 11-col DBs
- `2c39867` — feat(tuiboard): OTel dual-export (TB-1)
- `600c92b9` — feat(taskdog): OTel dual-export (TD-1)
- `cfbf12b, 064b8c9` — feat(solverforge): OTel dual-export (SF-1)

### Out of scope for this runbook
- INC-NN+ that map to planned-but-not-implemented subsystems (`override/`, `persistence/`) — see §6 of master diagnostic.
- PAV kernel restoration (catalog §3 master diagnostic `P1`) — different runbook needed.
- External MCP server OTel gaps (TB-1, TD-1, SF-1) — fixed in feature branches; not silent failures.

---

*End of runbook. Last reviewed 2026-08-27. Update after each SEV-1 incident; refresh quarterly otherwise.*