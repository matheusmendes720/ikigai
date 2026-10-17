---
name: M190-paperclip-canonical-adapter
description: Paperclip canonical HTTP adapter — wraps our LangGraph graph as a paperclipai employee. Phase 1 of migration.
status: DONE
owner: matheus-mendes
created: 2026-10-12
constitution_refs:
  - tests_are_the_contract
  - state_on_disk_not_conversation
  - reversibility_over_cleverness
  - composition_over_inheritance
  - multi_package_boundaries_are_sacred
estimated_cost_usd: 0.00
---

# M190 — Paperclip canonical HTTP adapter (Phase 1)

**Status:** DONE
**Date:** 2026-10-12
**Author:** matheus-mendes (with Claude Code assist)
**Source spec:** [`paperclip-orchestrator-specs.md`](G:\Other computers\My Laptop\notas_estudo\3_indice\harness_engineering\paperclip-orchestrator-specs.md)
§6.4 (HTTP adapter contract) + §9.3 (migration path Phase 1)

---

## TL;DR

M190 is the **first concrete step** of the canonical-Paperclip migration
path described in `paperclip-orchestrator-specs.md` §9.3 ("Don't replace;
augment"). It produces a minimal stdlib HTTP server
(`scripts/paperclip_heartbeat_http.py`, ~50 LOC) that accepts the
canonical Paperclip's HTTP-adapter POST payload and forwards each
heartbeat into our existing M169 `make_paperclip_graph()` LangGraph
factory as a single `graph.ainvoke(...)` call, returning the standard
`RunHandle` shape (`status` + `commit_sha` + `worktreePath`). The
canonical Paperclip becomes the **control plane**; our existing
Paperclip graph becomes the **employee**. Both systems run side-by-side
in Phase 1, so nothing in our internal loop is replaced. Phase 2+ (CTO
agent, Reviewer agent, org chart, goal alignment) is explicitly
out-of-scope for this SPEC.

---

## Why M190 now

The canonical Paperclip platform (`paperclipai/paperclip`, 67k⭐, MIT)
ships an **HTTP adapter** (`adapter_type=http`) that calls any external
endpoint with a standardised heartbeat payload. Per §9.2 of the
orchestrator-specs doc, the canonical insight is:

> *"Paperclip vira o control plane e o seu `loop-tick.sh` vira um
> employee."*

Our M169 `ikigai_paperclip` LangGraph graph is already an "employee" —
it takes a `task_id` + `spec_text`, returns a `commit_sha` and
`worktree_path`. The HTTP wrapper in M190 plugs the gap between
**canonical heartbeat payload** (runId, agentId, context.taskId,
wakeReason, customField) and **our state shape**
(`PaperclipStateDict`: task_id, spec_text, messages, …).

This is **Phase 1** (1 day of work per §9.3): parallel, additive, no
replacement.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Canonical Paperclip  (paperclipai/paperclip — control plane)│
│   - Port 3100                                              │
│   - React UI + Postgres                                    │
│   - 67k⭐ MIT, self-hosted                                 │
│   - Agent registry: "Life-Oss Paperclip" with HTTP adapter │
│                                                             │
│   On heartbeat trigger (timer/assignment/on_demand):        │
│     POST http://localhost:8765/heartbeat                    │
│     Authorization: Bearer <LOOP_TICK_TOKEN>                 │
└──────────────────────────────┬──────────────────────────────┘
                               │  HTTP POST /heartbeat
                               │  payload: { runId, agentId,
                               │             context: {taskId,
                               │             wakeReason, …},
                               │             specText }
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  scripts/paperclip_heartbeat_http.py  (M190, ~50 LOC)       │
│   - stdlib http.server, port 8765                           │
│   - Validates Authorization header against HEARTBEAT_TOKEN  │
│   - Builds PaperclipStateDict from payload                   │
│   - graph.ainvoke(state, config={"configurable":            │
│             {"thread_id": taskId}})                         │
│   - Returns RunHandle shape: status + commit_sha +          │
│     worktreePath                                           │
└──────────────────────────────┬──────────────────────────────┘
                               │  in-process call
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  _build_paperclip_graph(checkpoint_db=…, entry_point=…)    │
│   (src/ikigai/src/agents/paperclip/graph.py)                │
│                                                             │
│   read_spec → spec_analyzer → (gaps? yes) hil_pause → …     │
│                           ↘ (gaps? no) worktree_create → …  │
│     → implement → worktree_commit → merge → cleanup → END   │
└─────────────────────────────────────────────────────────────┘
```

---

## Adapter schema

The **exact JSON** that an operator would paste into the canonical
Paperclip UI when registering our life-oss Paperclip as an agent.
Mirrors §6.4 of the orchestrator-specs doc verbatim (only the URL and
auth header are ours):

```json
{
  "adapterType": "http",
  "adapterConfig": {
    "url": "http://localhost:8765/heartbeat",
    "method": "POST",
    "headers": {
      "Authorization": "Bearer {{LOOP_TICK_TOKEN}}"
    },
    "payloadTemplate": {
      "source": "life-oss-paperclip",
      "customField": "phase-1-migration"
    },
    "timeoutMs": 1800000
  }
}
```

| Field | Value | Rationale |
|---|---|---|
| `adapterType` | `"http"` | The only adapter type that wraps an in-process script (per §6.1) |
| `adapterConfig.url` | `http://localhost:8765/heartbeat` | Default port; overridable via `HEARTBEAT_PORT` env var |
| `adapterConfig.method` | `"POST"` | §6.4 mandates POST |
| `adapterConfig.headers.Authorization` | `Bearer {{LOOP_TICK_TOKEN}}` | Canonical Paperclip resolves `{{LOOP_TICK_TOKEN}}` from the agent's env (set during `paperclip onboard`); our server validates it against the `HEARTBEAT_TOKEN` env var |
| `adapterConfig.payloadTemplate.source` | `"life-oss-paperclip"` | Custom field merged into every heartbeat (per §6.4 "payload merge" rule) |
| `adapterConfig.payloadTemplate.customField` | `"phase-1-migration"` | Tag for the parallel-run audit log |
| `adapterConfig.timeoutMs` | `1800000` (30 min) | Matches our `MAX_GAP_LOOPS` × `MAX_IMPLEMENT_ITERS` worst-case budget (5×60 + 3×600) with headroom |

---

## Endpoint contract

### `POST /heartbeat`

**Request headers**

| Header | Value | Required |
|---|---|---|
| `Content-Type` | `application/json` | yes |
| `Authorization` | `Bearer {HEARTBEAT_TOKEN}` | yes — server returns 401 if missing/invalid |

**Request body** (canonical Paperclip's standard heartbeat payload, per
§6.4 of the orchestrator-specs doc)

```json
{
  "runId": "run-abc123",
  "agentId": "agent-xyz",
  "context": {
    "taskId": "M190-paperclip-canonical-adapter",
    "wakeReason": "scheduled",
    "commentId": null
  },
  "specText": "Add a hello_paperclip() function to src/test_paperclip_target.py …",
  "source": "life-oss-paperclip",
  "customField": "phase-1-migration"
}
```

**Successful response** (HTTP 200)

```json
{
  "status": "succeeded",
  "runId": "run-abc123",
  "commitSha": "a1b2c3d4e5f6",
  "worktreePath": "/path/to/worktree",
  "error": null
}
```

**Error response** (HTTP 4xx/5xx)

| Status | When |
|---|---|
| 400 | Body not valid JSON |
| 401 | `Authorization` header missing or invalid |
| 422 | `taskId` or `specText` missing from payload |
| 500 | Graph raised an exception during invoke |
| 504 | Invoke exceeded server-side timeout |

---

## Field mapping

How canonical Paperclip's heartbeat payload maps onto our
`PaperclipStateDict`:

| Canonical field | Type | Our state field | Notes |
|---|---|---|---|
| `runId` | `str` | (NOT mapped to state; echoed back in response) | Used for tracing only |
| `agentId` | `str` | (NOT mapped to state; logged at server start) | Tracked in audit log |
| `context.taskId` | `str` | `task_id` | Becomes `config["configurable"]["thread_id"]` so the SqliteSaver checkpoints per-task |
| `context.wakeReason` | `str` | (logged; not in state) | Surfaces in dashboard run record |
| `specText` | `str` | `spec_text` | Trimmed + validated by `read_spec_node` |
| `payloadTemplate.source` | `str` | (NOT mapped; logged) | Audit-tag for the parallel-run phase |
| `payloadTemplate.customField` | `str` | (NOT mapped; logged) | Audit-tag for the parallel-run phase |

`PaperclipStateDict` is initialised with these fields plus
`messages=[]` (required by OPEN-3 for Cloud Studio chat detection per
`state.py:85`). All other state fields (`spec_gaps`, `worktree_path`,
`commit_sha`, …) are populated by the graph nodes as the run
progresses.

---

## Phase 1 (parallel run) instructions

These are the concrete, runnable steps to validate the adapter
end-to-end **without replacing** our existing loop-tick. Both systems
run side-by-side; you compare.

### 1. Start the life-oss heartbeat server

```bash
cd "C:\Users\mathe\code_space\life-oss\life"

# Token must match what you'll register in Paperclip in step 2
export HEARTBEAT_TOKEN="dev-token-do-not-use-in-prod"
export HEARTBEAT_PORT=8765

# Background it (or run in a separate terminal)
python scripts/paperclip_heartbeat_http.py
# Logs: "listening on 0.0.0.0:8765, token=<set>"
```

### 2. Install canonical Paperclip locally

```bash
# On a separate machine (or VM) — do NOT co-locate with life-oss:
npx paperclipai@latest onboard --yes
# Creates ~/.paperclip/ + embedded Postgres + starts server on :3100

# In the Paperclip UI (http://localhost:3100), register a new agent:
#   name: "Life-Oss Paperclip"
#   role: "Engineer"
#   adapter_type: "http"
#   adapter_config: (paste the JSON from §"Adapter schema" above)
#   env vars: LOOP_TICK_TOKEN=<same as HEARTBEAT_TOKEN>
```

### 3. Verify both systems run side-by-side

```bash
# Our existing life-oss loop is unaffected — keep running as-is
cd "C:\Users\mathe\code_space\life-oss\life"
bash .claude/loop/loop-tick.sh --dry-run

# From canonical Paperclip, trigger a heartbeat:
#   - Either click "Run now" in the Paperclip UI
#   - Or wait for the timer trigger
# Paperclip will POST to our /heartbeat endpoint; our server invokes
# the graph; the run appears in Paperclip's UI + data/paperclip.db.
```

### 4. Compare & verify

| Check | Where to look |
|---|---|
| Both systems can run on the same task | Paperclip UI run log + `data/paperclip/runs/*.json` |
| Our loop-tick still ticks | `.claude/loop/heartbeat.log` + cost-dashboard |
| Drift net still green | `uv run pytest src/ikigai/tests/test_paperclip_drift.py` (must show 78/78 with the M190 drift test) |
| No data loss | `git log --oneline -n 10` (paperclip auto-commits should still land) |

If anything diverges, abort Phase 1 — neither system replaces the other.

---

## Phase 2+ (out of scope for this SPEC)

Brief mention only — these are the **next** milestones after M190,
each gated on Phase 1 succeeding:

| Phase | Adds | Drift count |
|---|---|---|
| **Phase 2** (1 week) | Add `Reviewer` agent (canonical Paperclip) that picks up our completed tasks and runs verification. Mirrors our current verifier (Haiku). | 79/79 |
| **Phase 3** (2 weeks) | Define company mission (1 sentence) + 3-5 goals. Tasks cascade from goal → issue. | 80/80 |
| **Phase 4** (1 month) | Add 5-10 more agents (CTO, Designer, Researcher, CMO). Import a `companies` template from `github.com/paperclipai/companies`. Set monthly budgets per agent. 7-day unattended operation. | 82/82 |

The **CTO agent** in Phase 2 is the key unlock: it can create tasks for
our `Engineer` agent (which IS our life-oss Paperclip) — that's the
Strategy→Execution state machine the orchestrator-specs doc calls the
"killer feature" of Paperclip. M190 is the prerequisite: without an HTTP
adapter for our existing loop, no Paperclip agent can hand work to us.

---

## Acceptance

- [x] `specs/M190-paperclip-canonical-adapter/SPEC.md` exists with full
      YAML frontmatter
- [x] Adapter schema JSON matches §6.4 of the orchestrator-specs doc
      verbatim (URL + method + headers + payloadTemplate + timeoutMs)
- [x] Endpoint contract documented (request headers + body + success +
      error responses)
- [x] Field mapping table maps every canonical payload field to either
      a `PaperclipStateDict` field or a logged-only audit field
- [x] Phase 1 instructions are runnable end-to-end (4 steps, each
      actionable on its own)
- [x] Phase 2+ explicitly marked out-of-scope
- [x] Risks called out (auth, timeout, error mapping)
- [x] `scripts/paperclip_heartbeat_http.py` exists, ~50 LOC, stdlib
      only, validates auth, builds `PaperclipStateDict`, calls
      `_build_paperclip_graph` + `graph.ainvoke`, returns RunHandle
      shape
- [x] `tests/test_paperclip_heartbeat_http.py` exists, 3 tests: auth
      required, response shape, payload → `read_spec_node` plumbing
- [x] `src/ikigai/tests/test_paperclip_drift.py` has new drift
      invariant `test_paperclip_canonical_http_adapter_exists`
- [x] Drift net: **76 → 77** (+1 for this M190 drift test)
- [x] Full paperclip suite + drift net + ruff all green

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `HEARTBEAT_TOKEN` leaks via env dump or shell history | Medium | High (anyone with the token can POST heartbeats) | Read from env only; never log the value; default `"dev-token-do-not-use-in-prod"` makes accidental prod use noisy; document rotation in `paperclip-spawner.sh` boot notes |
| HTTP timeout mismatch (Paperclip `timeoutMs=1800000` vs our `MAX_GAP_LOOPS * MAX_IMPLEMENT_ITERS` worst case) | Low | Medium (Paperclip may abort our invoke mid-implement) | `timeoutMs=1800000` = 30min covers 5×60 + 3×600 + headroom; tracked in M173 cost gate + M175 wall-clock gate |
| Graph raises an exception that paperclipai expects to be a 200 with `status=failed` | Medium | Medium (Paperclip marks run as `error` instead of `failed` with details) | Server catches exceptions, returns HTTP 200 with `status="failed"` + populated `error` field; only malformed JSON / auth failures return 4xx |
| `read_spec_node` rejects an empty `specText` before reaching implement | Low | Low (Paperclip UI shows a clear error in the run log) | Server returns HTTP 422 with `error="spec_text empty"` so Paperclip UI surfaces it cleanly |
| Concurrent heartbeats collide on `data/paperclip.db` checkpointer | Medium | Medium (SqliteSaver serialises, but two heartbeats on the same `taskId` would conflict) | Each heartbeat gets its own `thread_id` (set to `context.taskId`); different tasks don't collide; identical tasks get queued by Paperclip's `maxConcurrentRuns=1` |
| Canonical Paperclip changes its HTTP adapter shape (breaking change) | Low | High (we'd need to ship a new M-number) | Drift net + integration smoke test catch this within one tick; canonical Paperclip is MIT + slow-moving, low risk in practice |

---

## Lessons (to be added in the closeout)

1. **stdlib `http.server` is enough for Phase 1.** No FastAPI, no
   uvicorn, no ASGI. The whole server is ~50 LOC and has zero external
   deps beyond what `make_paperclip_graph` already pulls. If Phase 2
   needs WebSockets / SSE / multi-route, switch to FastAPI then.
2. **Authorization in 5 LOC.** Constant-time comparison via `hmac`
   would be safer than `==`, but `http.server` doesn't need that for a
   local-only Phase 1 server. Document the upgrade path in Phase 2.
3. **`config["configurable"]["thread_id"] = taskId` is the
   SqliteSaver join key.** Without it, every heartbeat would write to
   the same checkpoint row and `read_spec_node`'s state-validation
   would re-fire on every run. Always thread it.

---

## Deferred (future milestones)

| Wave | Adds | Drift count |
|---|---|---|
| **M190 (this)** | HTTP adapter + 3 unit tests + 1 drift test | 77/77 |
| **M191 (proposed)** | Phase 2: CTO/Reviewer agent registration in canonical Paperclip | 78/78 |
| **M192 (proposed)** | Phase 3: company mission + 3-5 goals in canonical Paperclip | 79/79 |

---

## Critical invariants (mitigations in place)

| Risk | Mitigation |
|---|---|
| Adapter schema drift vs canonical Paperclip | Drift test asserts `POST` + `/heartbeat` + auth validation present in the script source |
| RunHandle shape mismatch vs Paperclip's expectations | Unit test asserts `{status, runId, commitSha, worktreePath, error}` keys are all present |
| `taskId` not propagated to graph | Unit test asserts `read_spec_node` receives the `specText` from the payload (proves end-to-end plumbing) |
| Auth bypass | Server returns 401 without `Authorization` header (unit test asserts) |