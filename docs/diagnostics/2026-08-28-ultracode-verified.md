# Ultracode Workflow Results — Verified Backend Audit

**Date:** 2026-08-28
**Source:** Workflow `wf_776c74d3-689` (10 agents, 665K tokens, 198 tool calls)
**Scope:** Adversarially verify 8 HIGH-severity breakage items + completeness critic + synthesis
**Mode:** Ultracode (per user opt-in 2026-08-27)

---

## 1. Verified Status — 8 Items

| ID | Claim | Verdict | Evidence |
|----|-------|---------|----------|
| B-01 | gateway STALE paths | ✅ **CONFIRMED** | `apps/mcp-gateway/config/gateways.yaml:4,9,14` point to `code_space/apps/...` (MISSING). Fix: update 3 cwd paths to `life-oss/interfaces/...`. Note: gateway is OUTSIDE life/ tree (sibling at `code_space/apps/`). |
| B-02 | langgraph_entry.py:27 broken path | ✅ **CONFIRMED** | `IKIGAI_SRC = Path(__file__).parent.parent.parent / "life-ops" / "ikigai" / "src"` — `life-ops/` no longer exists. ikigai moved to `src/ikigai/src/`. langgraph.json:6 wires this graph. |
| B-03 | PAV `__main__.py:9` broken import | ✅ **CONFIRMED** | `from operational.cli.app import app` — `operational.cli` package deleted per 2026-08-26 PAV migration. `python -m operational` raises ModuleNotFoundError. Audit path was off by 1 level (file is at `src/operational/packages/core/src/operational/__main__.py`). |
| B-04 | tasks.jsonl MISSING | ✅ **CONFIRMED** | File absent. **Correction:** producer EXISTS (`daily_consolidator.py:108, 408 lines`) but was never invoked. Audit's "(no producer)" is imprecise; real cause is "producer never invoked". |
| B-05 | vibe_ops.db 0 rows | ✅ **CONFIRMED** | 19 tables, all empty. **Nuance:** `PRAGMA user_version` returns 0 (not 4 — schema v4 is an audit inference). Code opens CWD-relative `./vibe_ops.db` (not `data/`); pae_maintainer references non-existent tables `pae_state`, `period_reports`. |
| B-06 | 4 LangGraph stub dispatchers | ✅ **CONFIRMED** | `langgraph_entry.py:189,193,197,201` — 3-lambda shells. **More severe:** these CRASH on invocation (FileNotFoundError before lambdas run, see critic gap #2). |
| B-07 | dual PolicyEngine wired in parallel | ❌ **FALSE** | Misidentified `schemas.pydantic_v2` (data models, not engine). daily_loop wires ONE engine. **Real bug found:** canonical `evaluate()` signature mismatch with `daily_loop.py:33` call site (positional arg drift: passes `dict` for `QHEMetrics`, `PolicyDecision` for `int`, `date` for `EnergyLevel`). Stub is DEAD CODE (only ref is `main.py:86` unused import + scratch dir). |
| B-08 | 1137-line orphan test file | ✅ **CONFIRMED** | **Correction:** file is 942 lines (not 1137). Imports `operational.cli.services` and `operational.cli.state` (both DO NOT EXIST). Cannot be collected by pytest. |

**Summary:** 7 of 8 CONFIRMED, 1 FALSE (B-07 was a misidentification; the real bug found is more severe — signature drift).

---

## 2. NEW Gaps Found by Critic (10 items, not in original audit)

### P0 — Critical

1. **Orphan worktrees bloating repo (~200M)**
   - `src/ikigai/.claude/worktrees/data-model-unification` (111M)
   - `src/ikikigai/.claude/worktrees/observability-backend-tracing` (86M)
   - NOT in `git worktree list` (only master/eager-engine/quiet-comet)
   - Contain duplicates of `vibe-ops/src/contracts/sync_contract_v1.py`, `life-ops/ikigai/src/agents/ikigai_maintainer/`, `.agents/skills/`, `.claude/skills/`
   - Ships as plain files, bloat repo + confuse grep

2. **4 LangGraph stub dispatchers CRASH on invocation**
   - `langgraph_entry.py:159-167 _load_workflow_yaml` builds path `Path(__file__).parent / ".claude" / "skills" / "quarterly-planner" / "workflows"`
   - Resolves to `vibe-ops/src/.claude/skills/...` — DOES NOT EXIST
   - Actual workflows live at `<root>/.claude/skills/quarterly-planner/workflows/`
   - FileNotFoundError before lambdas run — `langgraph dev` would crash on instantiation

3. **`src/ikigai/mcp_config.json` Windows-unrunnable**
   - WSL2 paths `/mnt/c/Users/mathe/code_space/...`
   - References pre-reorg `life-ops/ikigai` cwd (line 6)
   - `home-flytwist/.bun/bin/bun` (DIFFERENT USER's $HOME, line 11)
   - Pre-reorg fork paths `apps/kanban/tuiboard`, `apps/dev-tools/taskdog`
   - More critical than gateway gateways.yaml because it's the client config Claude/agents consume

4. **Root CLI architectural lie**
   - CLAUDE.md claims: `python -m life.cli daily run` triggers subprocess → vibe-ops daily loop
   - Reality: `handlers/daily.py:21` invokes ITSELF recursively: `python -m life.cli task today`
   - Zero calls into vibe-ops/cybernetic_engine/daily_loop/sync_engine
   - Layering lie: root CLI is decoupled from cybernetic engine

### P1 — High

5. **IKIGAi scoring silent fallback cascade**
   - Audit caught B3 (`_compute_passion_score` returns `q_he*100` at `score_vectors.py:96`)
   - Missed: parallel hardcoding of other 4 vectors:
     - `_compute_skill_score` (line 122) returns `50.0`
     - `_compute_market_score` (line 153) returns `40.0`
     - `_compute_revenue_score` (line 186) returns `30.0`
     - `_compute_course_score` (line 204) returns `60.0`
   - All gated on `data/matheus/projects/` (DOES NOT EXIST) and `~/.ikigai/senai_attendance.json` (line 196)
   - **Effective IKIGAi 5-vector score: `[q_he*100, 50, 40, 30, 60]`** — 4 of 5 vectors are pure constants

6. **langgraph checkpoint import likely runtime crash**
   - `src/ikigai/src/agents/ikigai_maintainer/graph.py:10`: `from langgraph.checkpoint.sqlite import SqliteSaver`
   - This is the langgraph<0.2 path. Current langgraph>=0.4 uses `langgraph-checkpoint-sqlite` package
   - `pyproject.toml:17` declares `langgraph-checkpoint-sqlite = ^3.1` but no import uses that namespace
   - HIGH risk if `make_ikigai_graph` is invoked (langgraph.json:12 declares it)

7. **Vibe-ops contracts / parallel local contracts (3x drift risk)**
   - Audit identified `vibe-ops/src/schemas/pydantic_v2.py` (48L)
   - Missed ENTIRE second parallel contracts module: `vibe-ops/src/contracts/`
     - `sync_contract_v1.py` (1606B) — imported by `vibe-ops/src/middleware/sync_engine.py:8`
     - `roadmap_sync_v1.py` (2135B)
   - So 3 local stub-contracts modules in vibe-ops, none the canonical `src/contracts/`

8. **interfaces/cli broken entry-point script**
   - `interfaces/cli/pyproject.toml:9` declares `life-tasks = "read_tasks:app"` script entry
   - `interfaces/cli/` has NO `__init__.py`
   - No `[tool.hatch.build.targets.wheel]` to specify package discovery
   - `pip install -e .` would either fail OR produce install where `life-tasks` not on PATH
   - CLAUDE.md only invokes CLI as `python -m ...`, never via script — likely never tested

### P2 — Medium

9. **Ikigai graph routing / dead code ×7**
   - Audit said "routing functions `_route_after_*` (lines 139-146) — only `_route_after_observe` is used"
   - Reality: `graph.py:50-88` defines 7 routing functions
   - 6 are pure dead code (~40 LOC)
   - Agent-1's "6 conditional edges" claim was false — only entry-point is conditional

10. **Data layer / uninspected session leftovers**
    - Audit noted `data/session-ses_*.md` (~1.2MB) but missed:
      - `data/2026-08-26-184318-preciso-encaixar-o-pav-system-no-cusersmathe.txt` (69KB)
      - `data/2026-08-27-113757-this-session-is-being-continued-from-a-previous-c.txt` (72KB)
      - Both PII-level (paths to user code, conversation patterns)
    - `vault/run-continuation/ses_*.json` (4 files × 223B) — uninspected

---

## 3. Synthesis — Priority Matrix

| Rank | Item | Unblocks | Reason |
|------|------|----------|--------|
| P1 | Canonical path resolution: one `repo_root()` helper + declared datastore registry. Fixes `langgraph_entry.py:25-27`, `mcp_server/server.py:289`, `gateways.yaml:4,9,14`, `operational/__main__.py:9` | 6 | Highest fanout, lowest cost. Unblocks all 6 LangGraph graphs, MCP-to-CLI tasks.jsonl handoff, gateway start_all() to 3 forks, daily_consolidator writes, `python -m operational`, checkpoint/plan_entities addressing. Nothing downstream observable until this lands. |
| P2 | Contracts unification: resolve `contracts` namespace collision. `src/contracts/{common,task,planning,metrics}.py` (0 importers) vs `vibe-ops/src/contracts/` (2 importers) vs `vibe-ops/src/schemas/pydantic_v2.py` (3 importers) + circular dep `src/contracts/metrics.py:21` | 5 | This IS the data mesh substrate. Unblocks single tasks.jsonl schema for 3 writers, retirement of local pydantic_v2 stub, shared PolicyDecision/QHEMetrics shapes, UEID join-key decision, CI gate. Two packages named `contracts` is root cause audit rated only MED. |
| P3 | Seed the sensor: populate `data/vibe_ops.db` habit_states + study_sessions (19 tables, 0 rows) consumed at `cybernetics/daily_loop.py:70` | 4 | SENSOR stage reads nothing → ADJUSTER acts on no signal → Target-Sensor-Adjuster loop is decorative. Unblocks SENSOR, ADJUSTER, B3 real-passion fix, end-to-end daily-loop validation. Precondition for judging whether mesh design works on real rows. |
| P4 | langgraph_entry.py import repair (lines 25-27, 32) + 4 stub dispatcher decision at lines 189-202 | 2 | Verified dead: `ModuleNotFoundError: No module named 'pae_maintainer'` on import. All 6 registered graphs fail. Restores 2 real graphs (pae_maintainer 5-node, ikigai_maintainer 8-node). Forces implement-or-delete call on 4 stubs. Depends on P1. |
| P5 | Single PolicyEngine: collapse `pipeline/policy_engine.py` (118L stub) into canonical. Also fix daily_loop.py:33 call site signature drift | 2 | Two engines producing regime decisions = live drift risk. daily_loop.py:7 uses canonical while main.py:86 imports stub — `run-daily` and `status` could disagree on same day. Gated by P2 (need shared PolicyDecision shape). |

---

## 4. Sequencing (8 steps)

| Step | Action | Rationale |
|------|--------|-----------|
| **0** | Land P1 quick-win path fixes (~1 day): gateways.yaml:4,9,14 + langgraph_entry.py:25-27 + server.py:289 + operational/__main__.py:9 | Cannot design data mesh against system whose entry points fail at import. Converts audit guesses into observations. |
| **1** | Freeze datastore census as brainstorm input: 3 roots, 7 stores, enumerated with owners | Brings OQ-1 (storage topology) and OQ-3 (is tasks.jsonl interchange or transitional) as explicit decisions |
| **2** | Resolve `contracts` namespace collision | First irreversible design act: whichever package wins becomes mesh's schema authority |
| **3** | Migrate 3 tasks.jsonl writers onto winning contract (de facto already agree on 14 field names) | Cheaper than it looks — convergence exists |
| **4** | Retire `vibe-ops/src/schemas/pydantic_v2.py` (48L), repoint 3 importers | Removes last parallel shape definition |
| **5** | Single PolicyEngine (P5) — now safe because Step 4 gave both engines one PolicyDecision shape | |
| **6** | Seed sensor (P3), then fix B3 passion scoring | Deliberately after contracts: seeding into unowned schema means migrating rows twice |
| **7** | Repair langgraph_entry imports fully (P4) + take 4-stub decision + mcp-gateway orphan merge-or-discard | Decision-gated, not effort-gated |
| **8** | Hygiene sweep: session leftovers, boulder.json, orphan tests, CLAUDE.md counts, CI matrix additions | Last because none of it blocks anything, but CI additions stop next contracts layer from silently reaching zero importers |

---

## 5. Quick Wins vs Deep Work

### Quick Wins (1-day or less)

1. `gateways.yaml:4,9,14` — repoint cwd to `C:/Users/mathe/code_space/life-oss/interfaces/{tuiboard,taskdog,solverforge-calendar}` (3-line edit)
2. `langgraph_entry.py:25-27` — `VIBE_OPS_SRC` to `Path(__file__).parent`, `PAE_SRC` to that `/agents`, `IKIGAI_SRC` to `src/ikigai/src` (3-line edit)
3. `mcp_server/server.py:289` — add one `.parent` so repo_root lands on `life/` not `life/src/` (1-line edit, ends tasks.jsonl split-brain with `read_tasks.py:28` and `daily_consolidator.py:45`)
4. `operational/__main__.py:9` — delete `__main__.py` or point at real entry; drop dangling `"cli_app"` from `__init__.py:358` `__all__`
5. Delete 3 zero-byte files: `vibe-ops/src/pipeline/study_manager.py`, `pipeline/code_review_sync.py`, `storage/vector_store.py`
6. Move `data/session-ses_0e68.md` (766KB), `session-ses_118c.md` (330KB), 2 dated `.txt` transcripts (~142KB) to `logs/` and gitignore
7. Quarantine `data/boulder.json` (stale since 2026-06-30, points at `.omo/plans/` which was renamed to `vault/`)
8. Delete or xfail 2 orphan test files: `tests/core/test_services.py` (942L, imports `operational.cli.services`) and `tests/e2e/test_cli_workflow.py` (66L). Also remove empty `tests/{tui,ui,property}/` and `tests/unit/cli/`
9. CLAUDE.md factual corrections: entity count 15→29, pomodoro states 8→7, "NO pomodoro engine between time blocks" → implemented as PomodoroPlugin
10. `ci.yml:56-65` — add `src/contracts` and `interfaces/cli` to quality-gates matrix

### Deep Work

- **Contracts unification (3-5 days)** — decide `contracts` owner, migrate 3 tasks.jsonl writers, 3 schemas.pydantic_v2 importers, break circular dep `metrics.py:21`
- **Datastore registry (2-3 days)** — collapse 3 storage roots (`life/data/`, `life/src/data/`, `~/.ikigai/`) into one declared registry. Cover `plan_entities.db`, `ikigai_checkpoints.db`, `operational.SqliteRepository`
- **Sensor data pipeline (3-4 days)** — populate + keep populating `vibe_ops.db` habit_states/study_sessions, rewire `score_vectors.py:_compute_passion_score` and `observe.py:_read_qhe_from_operational` off hardcoded 0.65
- **Single PolicyEngine (2 days)** — fold 118L stub into 827L canonical FSM, repoint `main.py:86`, re-test regime agreement between `daily_loop` and `status` subcommand. ALSO fix `daily_loop.py:33` signature drift
- **4 LangGraph stub dispatchers (2 days or 1 hour)** — implement or deregister; depends on user answer
- **mcp-gateway orphan worktree (1-2 days)** — ~1600 lines in `feat/data-model-unification`, never merged; merge-or-discard call

---

## 6. Open Questions (carry forward to Phase 3 brainstorm)

1. **STORAGE TOPOLOGY** (blocks everything): is `~/.ikigai/` (user-home, survives repo moves, invisible to git) or `life/data/` (repo-local, versionable, diffable) the canonical root? Right now you have both plus a phantom third.

2. **CONTRACTS NAMING**: which package owns the name `contracts` — `src/contracts/` (typed Pydantic, 0 importers, declared canonical in CLAUDE.md) or `vibe-ops/src/contracts/` (YAML, 2 real importers, actually load-bearing)? Or are these two different layers (schema models vs sync/wire contracts) needing distinct names?

3. **Is tasks.jsonl THE MESH INTERCHANGE, OR A BRIDGE?** Three processes appending to one flat file with no reconciliation, no locking, no compaction story.

4. **DATA-FIRST GATE**: memory says no new code until 5+ manual logs prove workflow. Does repairing paths + unifying contracts count as "new code" or prerequisite plumbing?

5. **FEDERATION VS SINGLE SOURCE**: does `vibe_ops.db` stay analytic/mesh store with operational SQLite as write master (federated, two schemas), or collapse into one store?

6. **MiniMax PROXY** — intended or accidental? `deepagents_harness.py` points `ChatAnthropic` at `base_url=api.minimax.io` with model `MiniMax-M2.7-highspeed`.

7. **UEID JOIN KEY**: keep two formats (contracts `^[a-z][a-z0-9]{2,30}_...` underscore vs ikigai `namespace:type:slug:uuid:hash`) or unify? tasks.jsonl carries `ueid` written by both sides — mesh has no reliable join key.

8. **TWO MCP TRANSPORTS**: keep deliberate decoupling (ikigai stdio for AI kernel, gateway HTTP for 3 user-view forks) or unify? Note Deep Agent already bridges to all 3 forks directly via 10 wrappers at `agents/tools.py:930-953`.

9. **4 STUB WORKFLOWS**: are `quarterly_replan`, `test_de_fogo_rollup`, `correction_protocol`, `dream_falsification` planned capabilities (implement) or abandoned ideas (deregister)?

10. **mcp-gateway ORPHAN**: merge or discard ~1600 lines in `feat/data-model-unification`? Unmerged since 2026-08-26.

---

## 7. Cross-References

- Original audit: `docs/diagnostics/2026-08-27-backend-audit/00-INDEX.md`
- Agent reports: `docs/diagnostics/2026-08-27-backend-audit/{01-04}-agent-*.md`
- Workflow script: `C:\Users\mathe\.claude\projects\C--Users-mathe-code-space-life-oss-life\2248628b-662f-4735-b7ea-26387a8ea0ff\workflows\scripts\verify-backend-audit-2026-08-27-wf_776c74d3-689.js`
- Workflow journal: `C:\Users\mathe\.claude\projects\C--Users-mathe-code-space-life-oss-life\2248628b-662f-4735-b7ea-26387a8ea0ff\subagents\workflows\wf_776c74d3-689\journal.jsonl`
- Total tokens used: 665,423
- Total tool calls: 198
