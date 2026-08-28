# Backend Audit — IKIGAi / PAV System — 2026-08-27

**Source:** Brainstorming session, `/ultracode /brainstorming`
**Phase:** 1 (Backend Scan — Internal system → MCP bridge)
**Scan depth:** Forensic + trade-offs (user-confirmed)
**Status:** ✅ Exploration complete — all 4 agents returned

---

## 1. Layer Map (5 layers)

```
┌─ LAYER 5: INTERFACES
│   • interfaces/cli/ (read_tasks.py, 206L, lê tasks.jsonl que não existe)
│   • interfaces/tui/ (README-only, 44L)
│   • 3 forks (tuiboard TS, taskdog Py, solverforge-calendar Rust) — cada um com seu MCP server
│
├─ LAYER 4: MCP BRIDGE  ←  2 servers ortogonais + 3 fork servers
│   • ikigai MCP (Python, stdio) — 10 tools, ZERO gaps
│   • mcp-gateway (FastAPI HTTP→stdio) — rotas só pros 3 forks, ZERO refs a ikigai
│   • 3 fork MCP servers: tuiboard-mcp.ts, taskdog-mcp, solverforge-calendar-mcp.rs
│   • gateway config STALE paths (apps/ → life-oss/interfaces/) → crash on start_all()
│   • Deep Agent já tem 10 tool wrappers ligando direto aos 3 forks
│
├─ LAYER 3: AGENT LAYER
│   • Deep Agent (deepagents_harness) — 18 tools, MiniMax proxy LLM (base_url=api.minimax.io)
│   • ikigai_maintainer LangGraph — 8 nodes, REAL
│   • pae_maintainer LangGraph — 5 nodes, REAL (wraps run_pae_cycle)
│   • 4 LangGraph factories — STUB DISPATCHERS (3-lambda vazio)
│   • langgraph_entry.py:27 path quebrado (life-ops/ikigai/src não existe)
│
├─ LAYER 2: KERNEL (PAV operational)
│   • 29 entities (CLAUDE.md diz 15) — pomodoro 7 states (CLAUDE.md diz 8)
│   • 5 mutable + 24 frozen; todos `extra="forbid"`
│   • PolicyEngine 4-state FSM canonical (827L) + STUB paralelo (119L)
│   • HabitEngine Q_HE real (665L): H(t) = 1-e^(-λs), Q_HE = H_avg · E/E_max · (1+η·S_bonus)
│   • Persistence: JSON-blob single-table + 3 migrations
│   • __main__.py:9 imports operational.cli.app (NÃO EXISTE)
│   • 1137-line orphan test file (tests/core/test_services.py)
│
└─ LAYER 1: STORAGE / DATA
    • data/vibe_ops.db — 19 tabelas, schema ok, ZERO rows
    • data/vibe_mesh.db — 0 bytes placeholder
    • data/chroma_db/ — 1 collection, 0 embeddings
    • data/tasks.jsonl — MISSING
    • data/feedback.jsonl — MISSING
    • data/sync_log.jsonl — MISSING
    • data/boulder.json — STALE (2026-06-30, Sisyphus-Junior era, refs .omo/plans/)
    • data/session-ses_*.md — 1.2MB session leftovers (2026-08-26, 2026-08-27)
```

---

## 2. Breakage Inventory (14 items, ranked by severity)

| # | Issue | File:Line | Severity | Impact |
|---|-------|-----------|----------|--------|
| 1 | gateway config STALE paths | `apps/mcp-gateway/config/gateways.yaml:4,9,14` | HIGH | gateway crashes on `start_all()` |
| 2 | langgraph_entry.py broken path | `vibe-ops/src/langgraph_entry.py:27` | HIGH | `make_ikigai_graph` fails at import |
| 3 | PAV __main__.py broken import | `operational/packages/core/src/operational/__main__.py:9` | HIGH | `python -m operational` won't run |
| 4 | tasks.jsonl MISSING (no producer) | `data/tasks.jsonl` | HIGH | CLI returns empty; pipeline broken |
| 5 | vibe_ops.db schema OK but 0 rows | `data/vibe_ops.db` (19 tables) | HIGH | Sensor returns nothing → Adjuster operates on no signal |
| 6 | 4 LangGraph stub dispatchers | `vibe-ops/src/langgraph_entry.py:189,193,197,201` | MED | declared graphs that do nothing |
| 7 | dual PolicyEngine (canonical + stub) | `vibe-ops/src/pipeline/policy_engine.py:3` | MED | drift risk; daily_loop OK, sync_engine broken |
| 8 | local `schemas.pydantic_v2` masquerading as canonical | `vibe-ops/src/schemas/pydantic_v2.py` (49L) | MED | daily_loop + sync_engine import local stub |
| 9 | 1137-line orphan test file | `tests/core/test_services.py` | MED | broken test, clutters test count |
| 10 | contracts/metrics.py → ikigai (circular dep) | `src/contracts/metrics.py:21` | MED | contracts → ikigai breaks layer rule |
| 11 | 3 empty 0-byte files | `pipeline/study_manager.py`, `pipeline/code_review_sync.py`, `storage/vector_store.py` | LOW | dead code cruft |
| 12 | CLAUDE.md entity/state counts WRONG | `life/CLAUDE.md` | LOW | docs say 15 entities, actually 29 |
| 13 | session transcripts ~1.2MB in data/ | `data/session-ses_*.md` | LOW | runtime data dir polluted |
| 14 | boulder.json stale + dead paths | `data/boulder.json` | LOW | refs `.omo/plans/` pre-reorg, agentic-markdown-system worktree gone |

---

## 3. Retrospective Claims — Verification Matrix

| ID | Claim | Real Status |
|----|-------|-------------|
| B1 | MCP dispatch gap fixed | ✅ DONE — all 10 tools in `_TOOL_DISPATCH` |
| B2 | ikigai_scorer wrong vectors | ✅ IkigaiScorer delegates to canonical `ikigai.core.scoring.vector_scores` |
| B3 | passion_score method | ❌ STILL BROKEN — `score_vectors.py:_compute_passion_score()` still returns `q_he * 100` |
| B4 | daily_consolidator 0 bytes | ✅ DONE — 327 lines, REAL (`consolidate_from_cycle_state`, `--dry-run` supported) |
| B5 | Policy Engine canonical | ⚠️ PARTIAL — `daily_loop.py:7` uses canonical, but `sync_engine.py:9` + `main.py:86` + stub still in parallel |
| B6 | QHE formulas unified | ✅ DONE |
| B7 | UEID formats | ⏸ DECIDED — keep separate (contracts `_` vs ikigai `:`) |
| B8 | pae_maintainer LangGraph | ✅ REAL — `langgraph_entry.py:74` wraps `pae_maintainer.graph.run_pae_cycle` |
| Q2 | "4 stubs removed" | ❌ FALSE — 4 STUB DISPATCHERS remain (replan, rollup, correction, falsification) |
| Q4 | "unified_router zero refs" | ❌ FALSE — `vibe_cli.py:12,37,94` actively uses it in `hybrid_search` |

---

## 4. Cross-Cutting Findings

1. **2 MCP servers are DECOUPLED by design** — ikigai MCP serves the AI kernel, mcp-gateway serves user-view transport to 3 forks. Zero shared code (verified: `grep ikigai` in `apps/mcp-gateway/` returns empty).
2. **Deep Agent bridges ikigai ↔ 3 forks directly** via 10 tool wrappers in `src/ikigai/src/agents/tools.py:930-953`. The gateway is a SECONDARY transport (HTTP→stdio) for clients that are not Deep Agent.
3. **Pipeline layer is THICK and REAL** (35 .py files, ~8000 LOC). Most "stubs" in retrospective were actually REAL. The actual stub is `pipeline/policy_engine.py:119 lines`.
4. **Storage layer is solid schema-wise** but completely EMPTY (0 rows in `vibe_ops.db`, 0 embeddings in `chroma_db`). The daily-loop has NO sensor signal to act on.
5. **PAV kernel is COMPLETE** (29 entities, 4-state FSM, HabitEngine formulas) but has stale import refs (`__main__.py`, `langgraph_entry.py:27`) that break entry points.
6. **3 retrospective claims were FALSE** (B3, B5 partial, Q2, Q4). Verified by direct code inspection, not trusted prior docs.
7. **3 forks are FULLY WIRED** to Deep Agent as MCP tools — `tuiboard-mcp.ts`, `taskdog-mcp` (Python), `solverforge-calendar-mcp.rs`. Each has parallel `-otel-worktree/` branches for OTel instrumentation.
8. **mcp-gateway orphan** in worktree `feat/data-model-unification` (1600 lines) never merged. Decision pending: merge or discard.
9. **CLAUDE.md is STALE** in many places — entity count (15 vs 29), pomodoro states (8 vs 7), path references.
10. **DEEP AGENT uses MiniMax proxy** (`base_url="https://api.minimax.io/anthropic"`, model `MiniMax-M2.7-highspeed`), not direct Anthropic API.

---

## 5. Agent Reports

| # | Topic | File |
|---|-------|------|
| 1 | ikigai MCP + Deep Agent + LangGraph | [01-agent-ikigai-mcp.md](01-agent-ikigai-mcp.md) |
| 2 | vibe-ops cybernetic engine | [02-agent-vibe-ops.md](02-agent-vibe-ops.md) |
| 3 | PAV operational kernel | [03-agent-pav-kernel.md](03-agent-pav-kernel.md) |
| 4 | mcp-gateway + interfaces + data layer | [04-agent-mcp-interfaces.md](04-agent-mcp-interfaces.md) |

---

## 6. Brainstorming Workflow Status

| Step | Status |
|------|--------|
| 1. Explore project context | ✅ COMPLETE (4 parallel agents) |
| 2. Clarifying questions (one at a time) | 🔄 IN PROGRESS (Q1 answered: "Forensic + trade-offs") |
| 3. Propose 2-3 approaches with trade-offs | ⏳ PENDING |
| 4. Present design sections + approval | ⏳ PENDING |
| 5. Write design spec doc | ⏳ PENDING (`docs/superpowers/specs/2026-08-27-backend-audit-design.md`) |
| 6. Spec self-review (placeholder, internal consistency, scope, ambiguity) | ⏳ PENDING |
| 7. User review of written spec | ⏳ PENDING |
| 8. Invoke writing-plans skill | ⏳ PENDING (terminal state) |

---

## 7. Open Decisions (carry forward to Phase 3)

- QHE canonical: IKIGAI vs operational (already unified per B6, but verify)
- `pae_maintainer` LangGraph stubs in `langgraph.json`: remove or implement?
- UEID format: keep separate or unify?
- MiniMax proxy: intended or accidental?
- mcp-gateway orphan worktree: merge or discard?
- 2 MCP transports (ikigai MCP + gateway): keep both or unify?
- Data mesh schema: single source of truth vs federation?
