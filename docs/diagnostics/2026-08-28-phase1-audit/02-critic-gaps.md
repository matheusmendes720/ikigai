# 02 — Critic Gaps (10 Items NOT in Original Audit)

**Source:** `docs/diagnostics/2026-08-28-ultracode-verified.md` §2
**Discovered by:** Completeness critic (workflow `wf_776c74d3-689`)
**Notation:** `P0/P1/P2` here are SEVERITY levels. Distinct from `PR-1` through `PR-5` PRIORITY ITEMS in `03-priority-matrix.md`.
**Notation note:** "Fix category" describes WHAT KIND of fix would address the issue. Per Q2 scope, NO PATCHES are executed.

---

## P0 — Critical

### 1. Orphan worktrees bloating repo (~200M)

- **Files:**
  - `src/ikigai/.claude/worktrees/data-model-unification` (~111M)
  - `src/ikigai/.claude/worktrees/observability-backend-tracing` (~86M)
- **Status:** NOT in `git worktree list` (only master/eager-engine/quiet-comet registered)
- **Contains:** duplicates of `vibe-ops/src/contracts/sync_contract_v1.py`, `life-ops/ikigai/src/agents/ikigai_maintainer/`, `.agents/skills/`, `.claude/skills/`
- **Impact:** Ships as plain files, bloats repo, confuses grep
- **Fix category:** quarantine or delete — NOT implemented

### 2. 4 LangGraph stub dispatchers CRASH on invocation

- **File:** `vibe-ops/src/langgraph_entry.py:159-167 _load_workflow_yaml`
- **Path built:** `Path(__file__).parent / ".claude" / "skills" / "quarterly-planner" / "workflows"`
- **Resolves to:** `vibe-ops/src/.claude/skills/...` — DOES NOT EXIST
- **Actual location:** `<root>/.claude/skills/quarterly-planner/workflows/`
- **Failure:** `FileNotFoundError` BEFORE lambdas run. `langgraph dev` would crash on instantiation
- **Fix category:** decision-gated (implement YAML workflows at correct path, OR deregister 4 graphs)

### 3. `src/ikigai/mcp_config.json` Windows-unrunnable

- **Issues:**
  - WSL2 paths `/mnt/c/Users/mathe/code_space/...`
  - References pre-reorg `life-ops/ikigai` cwd (line 6)
  - `home-flytwist/.bun/bin/bun` — DIFFERENT USER's `$HOME` (line 11)
  - Pre-reorg fork paths `apps/kanban/tuiboard`, `apps/dev-tools/taskdog`
- **Why critical:** This is the CLIENT config Claude/agents consume. More impactful than `gateways.yaml` (which is server-side)
- **Fix category:** rewrite for current Windows paths + new fork locations

### 4. Root CLI architectural lie

- **CLAUDE.md claim:** `python -m life.cli daily run` triggers subprocess → vibe-ops daily loop
- **Reality:** `life/src/life/cli/handlers/daily.py:21` invokes ITSELF recursively: `python -m life.cli task today`. Zero calls into `vibe-ops/cybernetic_engine/daily_loop/sync_engine`
- **Impact:** Layering lie. Root CLI is decoupled from cybernetic engine. Documentation does not match code.
- **Fix category:** documentation correction (CLAUDE.md factual), OR implement actual subprocess wiring

---

## P1 — High

### 5. IKIGAi scoring silent fallback cascade

- **Audit caught:** `_compute_passion_score` returns `q_he*100` at `src/ikigai/src/agents/ikigai_maintainer/nodes/score_vectors.py:96`
- **Missed:** parallel hardcoding of 4 OTHER vectors:
  - `_compute_skill_score` (line 122) → `50.0`
  - `_compute_market_score` (line 153) → `40.0`
  - `_compute_revenue_score` (line 186) → `30.0`
  - `_compute_course_score` (line 204) → `60.0`
- **All gated on:** `data/matheus/projects/` (DOES NOT EXIST) + `~/.ikigai/senai_attendance.json` (line 196)
- **Effective IKIGAi 5-vector score:** `[q_he*100, 50, 40, 30, 60]` — 4 of 5 vectors are pure constants
- **Fix category:** rewire vector functions to read from real sensor data (depends on P3 sensor seeding)

### 6. langgraph checkpoint import likely runtime crash

- **File:** `src/ikigai/src/agents/ikigai_maintainer/graph.py:10`
- **Import:** `from langgraph.checkpoint.sqlite import SqliteSaver`
- **Issue:** This is the `langgraph<0.2` path. Current `langgraph>=0.4` uses `langgraph-checkpoint-sqlite` package
- **pyproject.toml:17** declares `langgraph-checkpoint-sqlite = ^3.1` but no import uses that namespace
- **Risk:** HIGH if `make_ikigai_graph` is invoked (langgraph.json:12 declares it)
- **Fix category:** update import path to match declared dependency

### 7. Vibe-ops contracts / parallel local contracts (3x drift risk)

- **Audit identified:** `vibe-ops/src/schemas/pydantic_v2.py` (48L)
- **Missed:** entire second parallel contracts module at `vibe-ops/src/contracts/`:
  - `sync_contract_v1.py` (1606B) — imported by `vibe-ops/src/middleware/sync_engine.py:8`
  - `roadmap_sync_v1.py` (2135B)
- **Total:** 3 local stub-contracts modules in vibe-ops, NONE the canonical `src/contracts/`
- **Fix category:** consolidation (P2 priority) — see `03-priority-matrix.md`

### 8. `interfaces/cli` broken entry-point script

- **File:** `interfaces/cli/pyproject.toml:9`
- **Declaration:** `life-tasks = "read_tasks:app"` script entry
- **Issues:**
  - `interfaces/cli/` has NO `__init__.py`
  - No `[tool.hatch.build.targets.wheel]` to specify package discovery
  - `pip install -e .` would either fail OR install where `life-tasks` not on PATH
- **Note:** CLAUDE.md only invokes CLI as `python -m ...`, never via script — likely never tested
- **Fix category:** add `__init__.py` + hatch config OR remove script entry

---

## P2 — Medium

### 9. Ikigai graph routing / dead code ×7

- **Audit said:** "routing functions `_route_after_*` (lines 139-146) — only `_route_after_observe` is used"
- **Reality:** `src/ikigai/src/agents/ikigai_maintainer/graph.py:50-88` defines 7 routing functions
- **Status:** 6 are pure dead code (~40 LOC)
- **Audit correction:** Agent-1's "6 conditional edges" claim was false — only entry-point is conditional
- **Fix category:** delete 6 unused routing functions

### 10. Data layer / uninspected session leftovers

- **Audit noted:** `data/session-ses_*.md` (~1.2MB)
- **Missed:**
  - `data/2026-08-26-184318-preciso-encaixar-o-pav-system-no-cusersmathe.txt` (69KB)
  - `data/2026-08-27-113757-this-session-is-being-continued-from-a-previous-c.txt` (72KB)
  - Both PII-level (paths to user code, conversation patterns)
- **Also uninspected:** `vault/run-continuation/ses_*.json` (4 files × 223B)
- **Fix category:** move to `logs/` and gitignore

---

## Summary

| Severity | Count | Theme |
|----------|-------|-------|
| P0 | 4 | Repo hygiene (worktrees), runtime crashes (stubs, mcp_config), documentation lie |
| P1 | 4 | IKIGAi scoring silent failure, runtime import drift, contracts drift, CLI install drift |
| P2 | 2 | Dead code ×7 routing, PII session leftovers |

**All 10 are NOT in original audit.** Discovery by completeness critic during workflow `wf_776c74d3-689`.