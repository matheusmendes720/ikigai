# 03 — Priority Matrix (Top 5)

**Source:** `docs/diagnostics/2026-08-28-ultracode-verified.md` §3
**Notation:** `PR-1` through `PR-5` are PRIORITY ITEMS (top-5 ranked). Distinct from `P0/P1/P2` critic-gap SEVERITY in `02-critic-gaps.md`.

---

## Top 5 Priority Items (ranked by fanout and cost)

| Rank | Item | Unblocks | Reason |
|------|------|----------|--------|
| **PR-1** | Canonical path resolution: one `repo_root()` helper + declared datastore registry | 6 | Highest fanout, lowest cost. Unblocks all 6 LangGraph graphs, MCP-to-CLI `tasks.jsonl` handoff, gateway `start_all()` to 3 forks, `daily_consolidator` writes, `python -m operational`, checkpoint/plan_entities addressing. Nothing downstream observable until this lands. |
| **PR-2** | Contracts unification: resolve `contracts` namespace collision | 5 | This IS the data mesh substrate. Unblocks single `tasks.jsonl` schema for 3 writers, retirement of local `pydantic_v2` stub, shared `PolicyDecision`/`QHEMetrics` shapes, UEID join-key decision, CI gate. Two packages named `contracts` is root cause audit rated only MED. |
| **PR-3** | Seed the sensor: populate `data/vibe_ops.db` `habit_states` + `study_sessions` (19 tables, 0 rows) | 4 | SENSOR stage reads nothing → ADJUSTER acts on no signal → Target-Sensor-Adjuster loop is decorative. Unblocks SENSOR, ADJUSTER, B3 real-passion fix, end-to-end daily-loop validation. Precondition for judging whether mesh design works on real rows. |
| **PR-4** | `langgraph_entry.py` import repair (lines 25-27, 32) + 4 stub dispatcher decision at lines 189-202 | 2 | Verified dead: `ModuleNotFoundError: No module named 'pae_maintainer'` on import. All 6 registered graphs fail. Restores 2 real graphs (`pae_maintainer` 5-node, `ikigai_maintainer` 8-node). Forces implement-or-delete call on 4 stubs. Depends on PR-1. |
| **PR-5** | Single PolicyEngine: collapse `pipeline/policy_engine.py` (118L stub) into canonical. Also fix `daily_loop.py:33` call site signature drift | 2 | Two engines producing regime decisions = live drift risk. `daily_loop.py:7` uses canonical while `main.py:86` imports stub — `run-daily` and `status` could disagree on same day. Gated by PR-2 (need shared `PolicyDecision` shape). |

---

## Dependency graph

```
PR-1 (path resolution)
  ↓
PR-4 (langgraph imports — depends on PR-1)
  ↓
PR-2 (contracts unification)
  ↓
PR-5 (single PolicyEngine — gated by PR-2)
  ↓
PR-3 (seed sensor — needs shared schema from PR-2)
```

---

## What this matrix is NOT

- Not a fix plan (per Q2 scope: no patch plans)
- Not a trade-off resolution (10 open questions separate — see `05-open-questions.md`)
- Not a deadline (no time estimates; sequencing in `04-sequencing.md`)
- Not exhaustive (P6+ items in critic gaps deferred to Phase 3)
- Not severity-ranked (`PR-1` is the top priority, NOT a "severity 1" issue. Severity lives in `02-critic-gaps.md` as P0/P1/P2)