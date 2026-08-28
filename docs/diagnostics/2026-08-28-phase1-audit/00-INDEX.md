# Phase 1 Backend Forensic Audit — INDEX

**Date:** 2026-08-28
**Source synthesis:** `docs/diagnostics/2026-08-28-ultracode-verified.md` (workflow `wf_776c74d3-689`, 10 agents, 665K tokens, 198 tool calls)
**Original audit:** `docs/diagnostics/2026-08-27-backend-audit/00-INDEX.md`
**Mode:** Ultracode (per user opt-in 2026-08-27)
**Scope:** Forensic + open questions only. No design proposals, no patch plans, no trade-off resolution.

---

## File map

| # | File | Contents |
|---|------|----------|
| 1 | `01-verified.md` | 8 audit items — verdicts (7 CONFIRMED + 1 FALSE), evidence, audit corrections |
| 2 | `02-critic-gaps.md` | 10 NEW gaps (P0×4, P1×4, P2×2) NOT in original audit |
| 3 | `03-priority-matrix.md` | Top 5 priority items by fanout and cost |
| 4 | `04-sequencing.md` | 8-step sequencing with rationale, deps, effort |
| 5 | `05-open-questions.md` | 10 open questions carried forward to Phase 3 brainstorm |

---

## Headline findings (one line each)

- **B-07 FALSE** — `schemas.pydantic_v2` is data models only; canonical PolicyEngine has evaluate() signature mismatch with `daily_loop.py:33` call site (real bug more severe than audit claim)
- **8 items audited, 7 CONFIRMED** with 3 audit corrections (B-04 nuance "producer exists, never invoked"; B-05 PRAGMA user_version=0 not 4; B-08 line count 942 not 1137)
- **10 critic gaps found** that original audit missed entirely: 4 P0 (orphan worktrees ~200M, langgraph stubs CRASH on invocation, mcp_config.json Windows-unrunnable, root CLI architectural lie), 4 P1, 2 P2
- **P1 priority** (canonical path resolution) unblocks 6 entry points (langgraph_entry.py:25-27, mcp_server/server.py:289, gateways.yaml:4,9,14, operational/__main__.py:9) — highest fanout, lowest cost
- **8-step sequencing** with Step 0 = path fixes BEFORE Phase 3 brainstorm (synthesis recommendation); Step 8 = hygiene sweep last
- **10 open questions** for Phase 3: storage topology (blocks everything), contracts naming, tasks.jsonl role, data-first gate interpretation, federation, MiniMax proxy, UEID join key, MCP transports, 4 stub workflows, mcp-gateway orphan

---

## Cross-references

- Agent reports (original): `docs/diagnostics/2026-08-27-backend-audit/{01-04}-agent-*.md`
- Workflow journal: `C:\Users\mathe\.claude\projects\C--Users-mathe-code-space-life-oss-life\2248628b-662f-4735-b7ea-26387a8ea0ff\workflows\scripts\verify-backend-audit-2026-08-27-wf_776c74d3-689.js`
- Full synthesis: `docs/diagnostics/2026-08-28-ultracode-verified.md`
- Total tokens used: 665,423
- Total tool calls: 198