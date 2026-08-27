# IKIGAi Backend — Full Deep-Dive Report

> **Generated**: 2026-08-26
> **Scope**: Vault ↔ taskdog ↔ tuiboard ↔ solverforge ↔ MCP gateway ↔ deep-agent harness
> **Severity**: 🔴 CRITICAL · 🟠 HIGH · 🟡 MEDIUM · 🔵 INFO

---

## Executive Summary

The IKIGAi system has **19 distinct issues** across 4 severity levels. The core finding: the vault and LangGraph infrastructure are well-designed and structurally sound, but the **MCP gateway, harness, and environment bootstrapping have critical misconfigurations that prevent the system from running at full capacity**.

Vault canonical state (1 active dream, 1 objective, 3 projects, 9 deliverables) is correctly stored in `life-ops/ikigai/data/matheus/`. taskdog has 4 aligned ikigai-tagged tasks. tuiboard has a working board for BYD Camacari CV work. solverforge has never been seeded.

---

## Severity Map

| Severity | Count | Description |
|---|---|---|
| 🔴 CRITICAL | 5 | System doesn't start — missing env, missing deps, wrong paths |
| 🟠 HIGH | 6 | Functional but wrong/misaligned |
| 🟡 MEDIUM | 5 | Works but with edge-case bugs |
| 🔵 INFO | 3 | Design notes / future risks |

---

## 🔴 CRITICAL Issues

### C1. Missing Python Environment — IKIGAi MCP Server Unreachable

**File**: `mcp_config.json:4`, `start_mcp_gateway.sh:35`

```json
"command": "/tmp/ikigai-test/bin/python",   // DOES NOT EXIST
```

```bash
IKIGAI_PYTHON="/tmp/ikigai-test/bin/python"  # start_mcp_gateway.sh
```

`/tmp/ikigai-test/bin/python` does **not exist**. The IKIGAi project has no `.venv`, no `poetry.lock`, and no active virtual environment at that path. The MCP server **cannot start** via:
- Claude Code's `mcp_config.json`
- The `start_mcp_gateway.sh ikigai` command

**Fix**: Either create the env at `/tmp/ikigai-test/` or switch `mcp_config.json` to use `poetry run python run_mcp_server.py`.

---

### C2. `~/.ikigai/` Directory Missing — All Checkpoint Tools Fail

**File**: `src/mcp_server/server.py:95-96`, `src/agents/tools.py:20-21`

Both the MCP server and the deep-agent harness expect:
- `~/.ikigai/ikigai_checkpoints.db`
- `~/.ikigai/plan_entities.db`

But `~/.ikigai/` **does not exist** at all. Any call to `ikigai_checkpoint`, `ikigai_plan_cycle`, or `ikigai_sync_vault` will fail at the `mkdir` or `sqlite3.connect` step. The `ikigai_plan_cycle` tool catches the exception non-fatally but silently loses the cycle output.

**Fix**: Create `~/.ikigai/` directory before first run. Note that `tools.py:_get_checkpoint_path()` creates the parent directory, but `server.py` does **not** create the parent directory before connecting.

---

### C3. Missing Python Dependencies — Import Failures on Cold Start

**Files**: `src/mcp_server/server.py`, `src/agents/tools.py`

```
ModuleNotFoundError: No module named 'frontmatter'
ModuleNotFoundError: No module named 'langchain_core'
```

The IKIGAi project uses Poetry but `poetry.lock` is missing (or never generated) and no `.venv` exists. Even if the Python path were corrected, imports would fail immediately.

**Fix**: Run `poetry install` to create the venv and install all dependencies. Alternatively, add a `requirements.txt` for `uv sync`.

---

### C4. `_read_entity` Function Name Collision — Server Silent Death

**File**: `src/mcp_server/server.py:207-239`

Two functions with the **same name** are defined in the same scope:

```python
def _read_plan_entity(cycle_id: str) -> dict[str, Any]:  # line 207
    plan_db = Path.home() / ".ikigai" / "plan_entities.db"
    ...

def _read_entity(table: str) -> dict[str, Any]:           # line 224
    path = Path.home() / ".ikigai" / "plan_entities.db"
    ...
```

The second definition **overwrites** the first. When `ikigai_score` calls `_read_entity("plan_entities")` on line 262, it calls the second function which connects to `plan_entities.db` and issues `SELECT * FROM plan_entities` — but the DB has a table also named `plan_entities`, creating a column conflict. More critically, the second function ignores the `table` argument entirely and always reads from `plan_entities.db`.

This causes `ikigai_score`, `ikigai_regime`, `ikigai_phase`, and `ikigai_corrections` to return empty data when the checkpoint DB is absent.

**Fix**: Rename one of the two functions. Suggested: rename line 224's `_read_entity` to `_read_plan_entity_by_table`.

---

### C5. taskdog CLI Path — Windows Binary on Linux Host

**File**: `src/agents/tools.py:910-912`

```python
_TASKDOG_CLI = str(
    Path.home() / "code_space" / "apps" / "dev-tools" / "taskdog" / ".venv" / "Scripts" / "taskdog.exe"
)
```

The harness points to `taskdog.exe` (Windows) but the environment is Linux WSL2. The actual working binary is:
```
/mnt/c/Users/mathe/code_space/apps/dev-tools/taskdog/.venv/bin/taskdog
```

This means **all taskdog tools in the deep-agent harness fail** with `FileNotFoundError`. The tools return `⚠️ taskdog CLI not found at expected path`.

**Fix**: Make it platform-aware:
```python
import sys
if sys.platform == "win32":
    _TASKDOG_CLI = Path.home() / "code_space" / "apps" / "dev-tools" / "taskdog" / ".venv" / "Scripts" / "taskdog.exe"
else:
    _TASKDOG_CLI = Path("/mnt/c/Users/mathe/code_space/apps/dev-tools/taskdog/.venv/bin/taskdog")
```

---

## 🟠 HIGH Issues

### H1. TUIBOARD Config — Relative Path Not Resolved from Config Dir

**File**: `~/.tuiboard/config.yaml` (original version)

The original config had:
```yaml
boards:
  - path: ../BYD-Camacari-CV.md   # relative to project root, not config dir
```

`tuiboard-mcp.ts` resolves `board_path` relative to **where it was launched from**, not relative to the config file. This caused `board_list` to return `{"boards":[]}` initially.

**Status**: Fixed — config now uses absolute path `/mnt/c/Users/mathe/code_space/apps/kanban/tuiboard/BYD-Camacari-CV.md`. The fix is local to the machine; if the config is regenerated from a template it will revert.

**Fix**: Ensure any config generator always uses absolute paths for `boards[].path`.

---

### H2. Vault Root Mismatch — `tools.py` vs `server.py` vs Actual Vault

| Component | Vault Root Used | Correct Path |
|---|---|---|
| `src/agents/tools.py:21` | `~/.ikigai/vault` | `life-ops/ikigai/data/matheus/` ❌ |
| `src/mcp_server/server.py:109` | `life-ops/ikigai/data/matheus/` | ✅ correct |
| Actual vault location | `life-ops/ikigai/data/matheus/` | — |

The `ikigai_sync_vault` tool in `tools.py` writes cycle logs to `~/.ikigai/vault/` (which doesn't exist), while `server.py` correctly uses the project-relative vault. The **deep-agent harness** uses `tools.py` version, so vault sync from the agent goes to the wrong place.

**Fix**: Align `tools.py:_VAULT_DIR` to:
```python
_VAULT_DIR = Path(__file__).parent.parent.parent / "data" / "matheus"
```
Or use the same helper as `server.py`.

---

### H3. solverforge — `calendar.db` Never Existed + Wrong Binary Path

**Files**: `src/agents/tools.py:638-640`, `start_mcp_gateway.sh:30-31`

1. `~/.ikigai/vault/calendar.db` does **not exist** — the solverforge calendar has never been seeded.
2. The binary path in `start_mcp_gateway.sh` uses Linux-style `$HOME/code_space/...` which resolves to `/home/flytwist/code_space/...` (Linux home) but the actual code is at `/mnt/c/Users/mathe/code_space/...` (Windows share on WSL2). `start_mcp_gateway.sh status` will always show "Solverforge binary not found" even if the binary is built.

**Fix**: Resolve the WSL2 path mapping for solverforge and seed `calendar.db`.

---

### H4. B1 Blocker — Vault Claims RESOLVED, Interfaces Still Show OPEN

**Files**: `data/matheus/ikigai_state/b1-blocker-resolution.md`, taskdog task `#10`, tuiboard board

The vault has a `b1-blocker-resolution.md` file dated **2026-08-26 21:25** marking B1 (graduation years) as resolved. But:
- taskdog task `#10` `[CRITICAL] Fornecer graduation years — H3 cap` — **PENDING**
- tuiboard `B1 hard block — Graduation years (3 entries × 4 CVs = 12 fields missing)` — **BLOCKED**

The vault state and interface state are **diverged**. The B1 resolution file was written before graduation years were actually provided — the resolution was premature.

**Impact**: CV score is held at 49 (D-band) by the H3 hard rule. Once graduation years are provided, taskdog `#10` and tuiboard B1 can both be closed, and the CV score rises to its projected A-band (86-88).

**Fix**: Either provide the graduation years and close the tasks, or update the vault to reflect that B1 is still open.

---

### H5. Two Separate LangGraph Instances — Checkpoint DBs Not Synced

**Files**: `src/mcp_server/server.py:317` vs `src/agents/tools.py:269`

Both `ikigai_plan_cycle` implementations call `make_ikigai_graph()` independently:

- `server.py:319` does **not pass** a `checkpoint_db` argument → uses default `~/.ikigai/ikigai_checkpoints.db`
- `tools.py:269` explicitly passes `checkpoint_db=_CHECKPOINT_DB` → also `~/.ikigai/ikigai_checkpoints.db`

They converge on the same DB path, but each compiles its own StateGraph with its own SqliteSaver connection. Checkpoints written by one instance are visible to the other, but there's no coordination — if both run concurrently, SqliteSaver's locking should handle it, but this is fragile.

**Fix**: Use the singleton `graph()` from `ikigai_wrapper.py` in both places.

---

### H6. Deep-Agent Harness — Potentially Wrong API Base URL

**File**: `src/agents/deepagents_harness.py:294-303`

```python
base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.minimax.io/anthropic")
model_name = os.environ.get("ANTHROPIC_MODEL", "MiniMax-M2.7-highspeed")
```

The harness defaults to `api.minimax.io/anthropic` for **MiniMax's** API gateway. If `MINIMAX_API_KEY` is not set, it falls back to looking for `ANTHROPIC_API_KEY`. This is a credential routing issue — the model and base URL are mismatched if MiniMax's API is not Anthropic-compatible.

**Fix**: Ensure `MINIMAX_API_KEY` and `MINIMAX_BASE_URL` are properly set in the environment, or verify that MiniMax's API accepts Anthropic-compatible request formats.

---

## 🟡 MEDIUM Issues

### M1. taskdog CLI — Terminal Width Truncates `ikigai` Tag to `ikiga…`

**File**: `tools/vault_taskdog_sync.py`

When `taskdog list` runs in a terminal with < 200 columns, output truncates:
```
Tags: ikiga…
```
Instead of:
```
Tags: ikigai
```

**Root cause**: taskdog CLI uses `$COLUMNS` to decide when to truncate tag display. Standard 80-column terminals cause 6-char truncation (6 chars + `…`).

**Fix (already applied in sync script)**: Set `COLUMNS=200` and `LINES=50` in the subprocess environment before calling taskdog CLI.

**Note**: When calling taskdog via `mcp_config.json` → `taskdog-mcp` (stdio transport), this issue does **not** occur because stdio has no terminal width set. Only direct `subprocess` calls to `taskdog list` need the COLUMNS fix.

---

### M2. taskdog Server — Port `:8000` Must Be Running Before MCP Connects

**File**: `start_mcp_gateway.sh:72-79, 95-108`

The gateway script checks `curl http://127.0.0.1:8000/health` to verify the server is up. The `taskdog-mcp` CLI connects to `http://localhost:8000`. If the server isn't running, all taskdog MCP tools return connection errors.

**Status**: Already handled in gateway script (auto-starts server if not running). But if using `mcp_config.json` directly from Claude Code, the server must be started manually first.

---

### M3. MCP Gateway — `test_all` Uses `grep` on JSON-RPC Output

**File**: `start_mcp_gateway.sh:243-248`

```bash
$IKIGAI_PYTHON "$IKIGAI_ROOT/run_mcp_server.py" 2>&1 | grep -q "ikigai-maintainer"
```

The `test_all` function uses `grep` on JSON-RPC responses to verify servers are responding. This is fragile — if the output format changes, the grep pattern fails silently.

**Fix**: Parse JSON and check for valid `result` field instead.

---

### M4. tuiboard MCP — `configPath` Passed as Empty String

**File**: `src/agents/tools.py:747`

```python
result = _mcp_call_v1(_TUIBOARD_MCP_CMD, "board_list", {"configPath": ""})
```

Passing `configPath: ""` may cause tuiboard to ignore the default config search paths and only use the current working directory. Since we now use absolute paths in the config, this is less critical, but it should either be omitted or set to the actual config directory path.

---

### M5. MCP Gateway — WSL2 Path Mapping Inconsistency

**File**: `start_mcp_gateway.sh:30-31`

```bash
TUIBOARD_ROOT="/mnt/c/Users/mathe/code_space/apps/kanban/tuiboard"      # ✅ correct
SOLVERFORGE_ROOT="$HOME/code_space/apps/calendar/solverforge-calendar"  # ❌ wrong
```

- `TUIBOARD_ROOT` uses the `/mnt/c/...` WSL2 path (correct for Windows-share access)
- `SOLVERFORGE_ROOT` uses `$HOME/code_space/...` (Linux home = `/home/flytwist/code_space/...`) — **incorrect** on WSL2 because the actual code is at `/mnt/c/Users/mathe/code_space/...`

**Fix**: Use the same WSL2 path pattern for `SOLVERFORGE_ROOT`:
```bash
SOLVERFORGE_ROOT="/mnt/c/Users/mathe/code_space/apps/calendar/solverforge-calendar"
```

---

## 🔵 INFO Issues

### I1. LangGraph Singleton — Module-Level State

**File**: `src/agents/ikigai_maintainer/graph.py:163-170`

```python
_graph_instance = None
def graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = make_ikigai_graph(checkpoint_db=db_path)
    return _graph_instance
```

The singleton pattern is fine for production but makes testing and development tricky — the module-level state persists across invocations and can't be reset without restarting the process. The `langgraph.json` `ikigai_maintainer` entry uses `ikigai_wrapper.py:graph` which is the singleton.

---

### I2. `ikigai_plan_cycle` — Non-Fatal DB Write Failure Silently Swallowed

**File**: `src/mcp_server/server.py:367-368`

```python
except Exception:
    pass  # non-fatal
```

The `plan_entities.db` upsert is wrapped in a bare `except Exception: pass`. If the DB write fails (schema mismatch, permission error, disk full), the cycle completes successfully from the agent's perspective but **no data is persisted**. The user gets a success response with no cycle to query later.

**Fix**: At minimum log the error. Better: raise and return an error in the tool result.

---

### I3. `ikigai_score` Fallback — Reads Wrong Table When Checkpoint Empty

**File**: `src/mcp_server/server.py:256-267`

When `_read_checkpoint()` returns empty (no DB), `ikigai_score` falls back to `_read_entity("plan_entities")`. But `_read_entity` (the second definition after the name collision) connects to `plan_entities.db` and issues `SELECT * FROM plan_entities`. The `ikigai_vectors` field name in the upsert (line 363) also doesn't match the individual column names the fallback reads (`passion`, `skill`, etc.).

---

## Summary Table by Component

| Component | Status | Issues |
|---|---|---|
| **Vault** (`data/matheus/`) | ✅ Healthy | H4 (B1 divergence), H2 (sync writes to wrong path) |
| **LangGraph graph** | ✅ Built | H5 (duplicate instances), I1 (singleton state) |
| **MCP server** (`server.py`) | 🔴 Broken | C1 (no env), C2 (no ~/.ikigai/), C3 (no deps), C4 (name collision), I2 (silent failures) |
| **Deep-agent harness** | 🔴 Broken | C1, C2, C3, C5 (wrong taskdog path), H2 (wrong vault root), H6 (API creds) |
| **taskdog MCP** | ✅ Working | M1 (COLUMNS fix needed for CLI), C5 (wrong binary path in harness) |
| **tuiboard MCP** | ✅ Working | H1 (was broken, now fixed with absolute path), M4 (empty configPath) |
| **solverforge** | 🔴 Dead | H3 (no calendar.db, wrong WSL2 paths) |
| **MCP gateway** (`start_mcp_gateway.sh`) | ⚠️ Partial | C1 (wrong ikigai python), M3 (fragile test), M5 (WSL2 path) |
| **mcp_config.json** | 🔴 Dead | C1 (points to non-existent env) |

---

## Vault ↔ Interface State

### Current vault canonical state
- **1 DREAM**: `vaga-remota-2026` (ACTIVE, horizon 547d)
- **1 OBJECTIVE**: `q3-2026-primeira-vaga` (ACTIVE, Q3 2026)
  - KR1: Pipeline BI (30 empresas, 20 msgs, 5 respostas)
  - KR2: Portfolio (1 demo 12min + 1 projeto GitHub)
  - KR3: 1 processo seletivo técnico
  - KR4: Q_HE ≥ 0.65 sustentado
- **3 PROJECTS**: `onda-2026-07-byd-deep-dive` (DONE), `onda-q3-1-pipeline-bi-cold-outreach` (ARCHIVED), `onda-2026-07-salvador-data-pipeline` (ARCHIVED)
- **9 DELIVERABLES**: D1–D4 (BYD stack fit, econometric analysis, cold outreach assets, process tracker), plus 5 others

### taskdog — ✅ Aligned (4 tasks)
| ID | Task | Status |
|---|---|---|
| #7 | `[KR1] Loggar 14 novas outreach no tracker` | PENDING |
| #8 | `[KR2] Gravar demo de 12min para portfolio` | PENDING |
| #9 | `[KR1] Submeter CVs para 11 vagas Tier 1` | PENDING |
| #10 | `[CRITICAL] Fornecer graduation years — H3 cap` | PENDING |

### tuiboard — ✅ Working BYD-Camacari-CV board
| Column | Tasks |
|---|---|
| Done | 7 (CV optimization, patching, ordering, localization, cover letters, scoring) |
| Blocked | 5 (B1 graduation years, B2-α role adjudication, B5 LGPD doc, re-score, score holding) |
| Ready | 1 (Submit to BYD recruiter) |

### solverforge — 🔴 No calendar.db
- `~/.ikigai/vault/calendar.db` does not exist
- solverforge has never been seeded with calendar data

---

## Recommended Priority Order

| Priority | Action | Files |
|---|---|---|
| **P0** | Create `~/.ikigai/` directory | — |
| **P0** | Run `poetry install` to install all dependencies | `pyproject.toml` |
| **P0** | Fix `mcp_config.json` Python path | `mcp_config.json:4` |
| **P1** | Fix `_TASKDOG_CLI` to Linux binary path | `tools.py:910-912` |
| **P1** | Fix `_VAULT_DIR` in `tools.py` | `tools.py:21` |
| **P1** | Fix `_read_entity` name collision | `server.py:224` |
| **P1** | Fix B1 blocker — provide graduation years OR reopen vault record | vault, taskdog, tuiboard |
| **P2** | Fix `SOLVERFORGE_ROOT` WSL2 path in gateway script | `start_mcp_gateway.sh:31` |
| **P2** | Add error logging to non-fatal `except` blocks | `server.py:367` |
| **P3** | Make taskdog path platform-aware | `tools.py:910-912` |
| **P3** | Replace grep-based MCP tests with JSON parsing | `start_mcp_gateway.sh:243-248` |
| **P3** | Use singleton `graph()` in both `server.py` and `tools.py` | `server.py:319`, `tools.py:269` |
