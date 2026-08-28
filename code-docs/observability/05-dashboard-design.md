> **[GRAPH-SEQUENCE MISMATCH — parked 2026-08-28 — see master-branch-carro-chefe-2026-08-28]**
> This spec describes an 8-node graph sequence (\`observe→orient→decide→…\`).
> The current deep-agent canonical architecture (per
> master-branch-carro-chefe-2026-08-28) operates as bidirectional sync
> between forks-prontas widgets ↔ vault local \`.db.markdown\`, not as the
> 8-node OODA-style flow this spec assumes. Per algorithm-decisions-defer-
> 2026-08-28, dashboard design is paused until 5+ manual SONHO logs prove
> the workflow. **Do not cite the 8-node sequence as current.**
>
> The 3 external MCP server OTel infra (tuiboard/taskdog/solverforge-
> calendar) referenced via 1.4 row 4 IS still load-bearing for the
> canonical architecture — that part is kept; the IKIGAI-specific
> dashboards 1.1-1.3 + 1.5-1.6 are parked.

# Observability Dashboard Design

**Spec:** 05-dashboard-design
**Date:** 2026-08-27
**Post-merge state:** After `feat/otel-tracing` lands across IKIGAI + 3 external MCP servers
**Backends:** LangSmith (primary, LLM/agent performance) | Langfuse (secondary, LLM cost + token forensics)
**Span model:** OpenTelemetry over MCP stdio; dual OTLP/HTTP export (`OTEL_ENABLED=true`)
**Companion specs:** 01-server-side-reliability · 02-integration-smoke-test · 03-merge-plan · 04-dissolve-worktree

---

## §0. Sumário

Total: **10 dashboards** (6 LangSmith + 4 Langfuse).

| # | Title | Backend | Primary Owner |
|---|-------|---------|---------------|
| 1.1 | IKIGAI Cycle Health | LangSmith | Agent perf |
| 1.2 | IKIGAI Tool Latency | LangSmith | MCP reliability |
| 1.3 | IKIGAI LangGraph Node Distribution | LangSmith | Graph fan-out |
| 1.4 | External MCP Server Health | LangSmith | Cross-server smoke |
| 1.5 | Circuit Breaker State | LangSmith | Reliability layer |
| 1.6 | Retry Pattern Distribution | LangSmith | Reliability layer |
| 2.1 | Deep Agent Conversations | Langfuse | LLM cost |
| 2.2 | Tool Selection Distribution | Langfuse | Agent routing |
| 2.3 | HITL Interrupt Frequency | Langfuse | Human-in-loop |
| 2.4 | Cost per Cycle | Langfuse | Unit economics |

**Tables used throughout:** `spans`, `gen_ai.usage` (auto-instrumented by LangChain/LangGraph), `tool.duration_ms`, `error.class`, `error.code` (solverforge only).

---

## §1. LangSmith Dashboards (LLM/agent performance — primary)

### 1.1 IKIGAI Cycle Health
- **Purpose:** End-to-end observability of one IKIGAi plan cycle (8-node LangGraph); ties latency + errors + kill-switch to a single `cycle_id`.
- **Data sources:** `ikigai.graph.compile`, `ikigai.make_agent`, the 8 graph-node spans (`observe`→`orient`→`decide`→`plan`→`act`→`verify`→`reflect`→`commit`) emitted by LangChain/LangGraph auto-instrumentor.
- **Queries:**
  - Filter: `service.name = ikigai-maintainer` AND `span.kind = internal`
  - Group by `cycle_id` (from checkpoint thread)
- **Panel layout:**
  - Row 1 (KPI tiles): p50 cycle duration · p99 cycle duration · success rate · active cycles
  - Row 2 (timeline): per-trace waterfall of 8 nodes + child LLM/tool spans
  - Row 3 (errors): stacked bar `error.class` per cycle bucket
  - Row 4 (kill-switch): boolean ribbon — `kill_switch_triggered=true` events with linked trace
- **SLO:** p50 ≤ 30 s · p99 ≤ 90 s · success rate ≥ 99 %

### 1.2 IKIGAI Tool Latency
- **Purpose:** Latency + correctness for the 8 IKIGAi internal tools (and 10 external wrapper tools).
- **Data sources:** `tool.ikigai_score`, `tool.ikigai_regime`, `tool.ikigai_phase`, `tool.ikigai_corrections`, `tool.ikigai_decompose`, `tool.ikigai_plan_cycle`, `tool.ikigai_sync_vault`, `tool.ikigai_checkpoint`.
- **Queries:**
  - Filter: `tool.name starts_with "ikigai_"`
  - Aggregation: count + p50/p95/p99 of `tool.duration_ms`, split by `tool.status` (ok|error)
- **Panel layout:**
  - Row 1 (heatmap): tool × latency percentile matrix
  - Row 2 (timeseries): p95 `tool.duration_ms` per tool, 5-min rolling
  - Row 3 (errors): top `error.class` × tool, ranked by count
  - Row 4 (table): per-tool SLO conformance (SLO floor vs observed)
- **SLO:** p95 ≤ 500 ms reads · ≤ 2 s `ikigai_plan_cycle` · ≤ 200 ms score/regime/phase · success ≥ 99.5 %

### 1.3 IKIGAI LangGraph Node Distribution
- **Purpose:** Detect graph fan-out regressions (one node dominating cycle budget) and unused-node drift.
- **Data sources:** the 8 graph-node spans (`observe`→`commit`) plus `phase` and `phase_iteration` attributes.
- **Queries:**
  - Filter: `service.name = ikigai-maintainer` AND `span.name IN {observe,orient,decide,plan,act,verify,reflect,commit}`
  - Group by `span.name`; aggregate count + median duration + `phase_iteration` distribution
- **Panel layout:**
  - Row 1 (donut): span count share per node (last 1 h)
  - Row 2 (box-plot): per-node duration distribution
  - Row 3 (line): median iterations per `phase` (signals infinite-loop regression when `phase_iteration` > 5)
  - Row 4 (heatmap): node × phase cross-tab of mean duration
- **SLO:** no single node > 60 % of total cycle p95 · `phase_iteration` p99 ≤ 5 · every node fires ≥ 1× per 100 cycles

### 1.4 External MCP Server Health
- **Purpose:** Single-pane SLO dashboard for the 3 external MCP servers (tuiboard / taskdog / solverforge-calendar) plus IKIGAI as the 4th consumer-facing service.
- **Data sources:** `tool.<name>` spans across `tuiboard`, `taskdog.mcp`, `solverforge-calendar`, plus IKIGAI wrap-spans for those tools.
- **Queries:**
  - Filter: `service.name IN {tuiboard, taskdog.mcp, solverforge-calendar, ikigai-maintainer}`
  - Group by `service.name` × `tool.name` × minute bucket
- **Panel layout:**
  - Row 1 (KPI tiles, per server): span volume / error rate / p95 latency / cold-start p95
  - Row 2 (time-series): span volume stacked per server, 5-min buckets
  - Row 3 (heatmap): server × tool × p95 latency matrix (green/yellow/red against per-tool SLO)
  - Row 4 (status): per-server dual-export parity gauge (LangSmith vs Langfuse, ±5 %)
- **SLOs (per server):**
  - tuiboard: `board_list` p95 ≤ 300 ms · write tools ≤ 400 ms · success ≥ 99.5 %
  - taskdog: read p95 ≤ 200 ms · write p95 ≤ 500 ms · success ≥ 99.5 %
  - solverforge: read p95 ≤ 250 ms · `events_create` ≤ 600 ms · `google_sync` ≤ 30 s · success ≥ 99 %

### 1.5 Circuit Breaker State
- **Purpose:** Real-time visibility into the IKIGAI client-side circuit breaker (Task 4 / `87f6ef9`); CB counts logical calls, retry wraps the inner attempt.
- **Data sources:** child spans under MCP call sites in `src/agents/tools.py`; attributes `circuit.state` (closed|open|half_open), `circuit.breaker` (tool name), `circuit.failure_count`.
- **Queries:**
  - Filter: `service.name = ikigai-maintainer` AND `circuit.breaker` is set
  - Group by `circuit.breaker`, last state per 30 s window
- **Panel layout:**
  - Row 1 (status grid): 4×3 grid of (server × tool) cells colored by current CB state (closed=green / half_open=yellow / open=red)
  - Row 2 (time-series): `circuit.failure_count` per tool, last 1 h
  - Row 3 (stacked area): time-in-state share per tool (closed vs half_open vs open)
  - Row 4 (table): recent state transitions with `retry.exhausted` flag and linked trace
- **SLO:** circuit-open rate ≤ 1 % per tool · `circuit.failure_count` never exceeds CB threshold without a state change within 60 s

### 1.6 Retry Pattern Distribution
- **Purpose:** Catch retry-amplification regressions on the IKIGAI reliability layer and per-tool backoff distributions.
- **Data sources:** parent + child retry spans; attributes `retry.attempt`, `retry.exhausted`, backoff delay (ms), final `tool.status`.
- **Queries:**
  - Filter: `service.name = ikigai-maintainer` AND `retry.attempt` is set
  - Group by `tool.name` × `retry.attempt` bucket
- **Panel layout:**
  - Row 1 (stacked bar): retry-attempt histogram (1/2/3/4+) per tool
  - Row 2 (line): retry amplification rate (spans with `retry.attempt > 1` / total), 5-min rolling
  - Row 3 (heatmap): tool × backoff-bucket (0–100 ms / 100–500 ms / 500 ms–2 s / > 2 s)
  - Row 4 (table): top retry exhaustions with `error.class` + linked trace
- **SLO:** retry amplification ≤ 5 % · median retry attempts ≤ 2 · `retry.exhausted = true` rate ≤ 1 % (15 min)

---

## §2. Langfuse Dashboards (LLM cost + token forensics — secondary)

Langfuse receives the same OTel spans as LangSmith plus auto-instrumented LangChain spans with `gen_ai.usage.{input,output}_tokens`. Use Langfuse to attribute tokens to prompts/models and to drill into deep-agent loop cost.

### 2.1 Deep Agent Conversations
- **Purpose:** Trace-by-trace view of every deep-agent invocation; surfaces prompt bloat, model selection, and per-cycle cost.
- **Data sources:** LangChain/LangGraph auto-instrumented spans, manual `ikigai.make_agent` span, LangGraph checkpoint spans.
- **Queries:**
  - Filter: `service.name = ikigai-maintainer` AND `gen_ai.usage.input_tokens > 0`
  - Group by `thread_id` + `model`
- **Panel layout:**
  - Row 1 (KPI tiles): median prompt tokens · median completion tokens · median LLM calls/cycle · median cost/cycle
  - Row 2 (scatter): prompt_tokens × completion_tokens, color = model, point = cycle
  - Row 3 (timeline): stacked LLM calls per cycle (model layer)
  - Row 4 (table): top-10 heaviest cycles with prompt size + cost + linked trace
- **SLO:** median prompt ≤ 8 k tok · median completion ≤ 1 k tok · cost per cycle ≤ $0.10

### 2.2 Tool Selection Distribution
- **Purpose:** Show which tools the agent chooses for which thread and how tool mix shifts over time.
- **Data sources:** `tool.<name>` spans; attributes `tool.name`, `thread_id`, `tool.arg.ueid`, `tool.arg.action`.
- **Queries:**
  - Filter: `service.name = ikigai-maintainer` AND `tool.name` is set
  - Group by `thread_id` × `tool.name`
- **Panel layout:**
  - Row 1 (donut): tool-call share (last 24 h)
  - Row 2 (stacked bar): tool mix per thread (top 20 threads)
  - Row 3 (heatmap): thread × tool matrix (call count)
  - Row 4 (line): entropy of tool mix over time (proxy for planning stability)
- **SLO:** no single tool > 80 % share in any thread with > 10 calls (signals an agent stuck on one tool)

### 2.3 HITL Interrupt Frequency
- **Purpose:** Track human-in-the-loop interrupts (`human_in_the_loop = true`); ensures the agent surfaces decisions to humans rather than acting autonomously.
- **Data sources:** LangGraph interrupt spans + `human_in_the_loop` attribute on parent cycles.
- **Queries:**
  - Filter: `service.name = ikigai-maintainer` AND (`human_in_the_loop = true` OR span name contains `interrupt`)
  - Group by `thread_id` × interrupt reason
- **Panel layout:**
  - Row 1 (KPI tiles): interrupts/cycle · median time-to-resolve · unresolved interrupts
  - Row 2 (stacked bar): interrupt reasons, ranked
  - Row 3 (timeline): interrupts per hour with rollback annotations
  - Row 4 (table): longest unresolved interrupts with linked thread
- **SLO:** ≤ 1 interrupt per cycle median · time-to-resolve p95 ≤ 10 min · zero unresolved > 24 h

### 2.4 Cost per Cycle
- **Purpose:** Unit-economics view — cost per IKIGAI cycle, broken down by model + tool cost center.
- **Data sources:** `gen_ai.usage.*` × per-model price table (configurable) + `tool.duration_ms` for tool-side cost attribution.
- **Queries:**
  - Filter: `service.name = ikigai-maintainer`
  - Aggregation: sum(input_tokens × price_in + output_tokens × price_out) per `cycle_id`
- **Panel layout:**
  - Row 1 (KPI tiles): cost/cycle median · cost/cycle p95 · daily spend · 7-day rolling median
  - Row 2 (stacked area): cost contribution by model over time
  - Row 3 (cost breakdown pie): input vs output vs tool-side cost
  - Row 4 (forecast): 30-day projected spend at current trajectory
- **SLO:** cost/cycle p95 ≤ $0.10 · daily spend ≤ 2× rolling 7-day median · any cycle > 50 LLM calls flagged

---

## §3. Service Level Objectives (consolidated)

| Dashboard | SLO | Floor | Page Threshold |
|-----------|-----|-------|----------------|
| 1.1 Cycle Health | p50 cycle | ≤ 30 s | > 30 s for 15 min |
| 1.1 Cycle Health | p99 cycle | ≤ 90 s | > 90 s for 5 min |
| 1.1 Cycle Health | success rate | ≥ 99 % | < 98 % for 10 min |
| 1.2 Tool Latency | read tools p95 | ≤ 500 ms | > 1 s for 5 min |
| 1.2 Tool Latency | `ikigai_plan_cycle` p95 | ≤ 2 s | > 2 s for 10 min |
| 1.3 Node Distribution | per-node share | ≤ 60 % | > 70 % for 30 min |
| 1.3 Node Distribution | `phase_iteration` p99 | ≤ 5 | > 8 (any) |
| 1.4 External MCP | per-server success | ≥ 99–99.5 % | < 98 % for 10 min |
| 1.4 External MCP | dual-export parity | ±5 % | > 10 % sustained |
| 1.5 Circuit Breaker | open rate per tool | ≤ 1 % | > 5 % for 5 min |
| 1.6 Retry Patterns | amplification | ≤ 5 % | > 10 % for 15 min |
| 1.6 Retry Patterns | `retry.exhausted` | ≤ 1 % | > 2 % for 15 min |
| 2.1 Conversations | median prompt | ≤ 8 k tok | > 32 k p95 |
| 2.1 Conversations | cost per cycle | ≤ $0.10 | > $0.25 any |
| 2.3 HITL | interrupts/cycle | ≤ 1 | > 3 for any thread |
| 2.4 Cost | daily spend | ≤ 2× 7-day median | > 3× any day |

---

## §4. Alert Conditions (Prometheus-style rules)

```yaml
groups:
  - name: ikigai-cycle
    rules:
      - alert: IKIGAI_CycleP99Breach
        expr: histogram_quantile(0.99, sum by (le) (rate(ikigai_cycle_duration_seconds_bucket[5m]))) > 90
        for: 5m
        labels: { severity: page, team: ikigai }
        annotations: { runbook: "1.1 Cycle Health > p99 panel" }
      - alert: IKIGAI_UnicodeDecodeRegression
        expr: rate(ikigai_errors_total{error_class="UnicodeDecodeError"}[1m]) > 0
        for: 0m
        labels: { severity: page }
      - alert: IKIGAI_KillSwitchTriggered
        expr: increase(ikigai_kill_switch_total[1m]) > 0
        for: 0m
        labels: { severity: page }
  - name: mcp-reliability
    rules:
      - alert: CircuitBreakerOpen
        expr: rate(circuit_breaker_state_changes_total{state="open"}[1m]) > 0.166  # 10/min
        for: 0m
        labels: { severity: page }
      - alert: RetryAmplification
        expr: sum(rate(retry_attempts_total{attempt="gt1"}[5m])) / sum(rate(retry_attempts_total[5m])) > 0.05
        for: 15m
        labels: { severity: warn }
      - alert: MutationToolMissingIdempotencyKey
        expr: rate(mutation_spans_total{idempotency_key="absent",retry_attempt="gt1"}[5m]) > 0
        for: 0m
        labels: { severity: page, team: ikigai }
  - name: langfuse-cost
    rules:
      - alert: CostPerCycleP95Breach
        expr: histogram_quantile(0.95, sum by (le) (rate(ikigai_cycle_cost_usd_bucket[15m]))) > 0.25
        for: 15m
        labels: { severity: page }
      - alert: InfiniteToolLoop
        expr: increase(ikigai_llm_calls_per_cycle_total{gt_50="true"}[1m]) > 0
        for: 0m
        labels: { severity: page }
```

Runbook anchors are intentionally minimal — full playbooks live in `code-docs/observability/runbooks/` (not yet created).

---

## §5. Implementation Plan (sprint-by-sprint)

| Sprint | Deliverables | Owner | Exit Criteria |
|--------|-------------|-------|---------------|
| **Sprint 17 (current)** | Spec 05 docs (this file) + LangSmith D1.1 + D1.4 baseline | IKIGAI | Smoke test in CI emits both dashboards |
| **Sprint 18** | D1.2, D1.5, D1.6 + Prom rules in `ikigai-observability-rules.yml` | IKIGAI | All 6 LangSmith dashboards live in LangSmith workspace |
| **Sprint 19** | Langfuse D2.1, D2.4 + per-model price table | IKIGAI + finance | Cost/cycle KPI wired to model pricing |
| **Sprint 20** | D2.2, D2.3 + Langfuse→LangSmith cross-link annotations | IKIGAI | All 10 dashboards visible in shared workspace |
| **Sprint 21** | Runbooks for each alert + on-call rotation | IKIGAI + ops | Every alert has a runbook anchor resolved |

**Hard prerequisites (from earlier specs):**
- Spec 01 reliability layer wired (Spec 01 exit gate)
- Spec 02 smoke test emits spans from all 4 servers (Spec 02 exit gate)
- Spec 03 merge of `feat/otel-tracing` branches complete (Spec 03 exit gate)

**Defer:** D2.2 (Tool Selection Distribution) entropy threshold tuning — needs 30 days of post-merge data to set a meaningful baseline.

---

## §6. Cross-references

**Companion specs (all in `code-docs/observability/`):**
- `01-server-side-reliability.md` — source of SLO floors for circuit breaker + retry
- `02-integration-smoke-test.md` — CI gate that proves dual export works
- `03-merge-plan.md` — merge order across the 4 repos
- `04-dissolve-worktree.md` — worktree cleanup after merge

**Source-of-truth files:**
- IKIGAI OTel init: `C:\Users\mathe\code_space\life-oss\life\life-ops\ikigai\src\observability\otel_init.py`
- IKIGAI error-capture decorator: `C:\Users\mathe\code_space\life-oss\life\life-ops\ikigai\src\observability\error_capture.py`
- IKIGAI tools (18 total — 8 internal + 10 external): `C:\Users\mathe\code_space\life-oss\life\life-ops\ikigai\src\agents\tools.py`
- IKIGAI manual spans: `C:\Users\mathe\code_space\life-oss\life\life-ops\ikigai\src\agents\deepagents_harness.py`
- IKIGAI 8-node graph: `C:\Users\mathe\code_space\life-oss\life\life-ops\ikigai\src\agents\ikigai_maintainer\graph.py`
- Tuiboard OTel init: `C:\Users\mathe\code_space\apps\kanban\tuiboard\src\v3\observability\init.ts`
- Taskdog OTel init: `C:\Users\mathe\code_space\apps\dev-tools\taskdog\packages\taskdog-mcp\src\taskdog_mcp\observability.py`
- Solverforge OTel init: `C:\Users\mathe\code_space\apps\calendar\solverforge-calendar\src\observability.rs`

**Sprint status:** `C:\Users\mathe\code_space\life-oss\life\docs\.sdd-progress.md`

**Naming & attribute conventions:** see `code-docs/observability/00-conventions.md` (TBD — extract from this spec into a conventions file before Sprint 18).

---

## §7. Data Dictionary (attributes referenced across dashboards)

| Attribute | Type | Source | Used in |
|-----------|------|--------|---------|
| `service.name` | string (resource attr) | IKIGAI=`ikigai-maintainer`; tuiboard=`tuiboard`; taskdog=`taskdog.mcp`; solverforge=`solverforge-calendar` | All dashboards |
| `deployment.environment` | string (resource attr) | `IKIGAI_ENV` env (default `local`) | All dashboards |
| `mcp.protocol_version` | string | static per server (`2025-06-18`) | D1.4, D5, D6, D7 |
| `tool.name` | string (span attr) | `@observed_tool` / `withToolSpan` / `@instrumented_tool` / `#[instrument(...)]` | All tool dashboards |
| `tool.duration_ms` | number | auto-emitted by server decorators | D1.2, D1.4, D1.6, D5, D6, D7 |
| `tool.status` | enum | `ok` \| `error` | All tool dashboards |
| `error.class` | string | exception type name (Pythonic) | D1.1, D1.5, D1.6, D2.x, D9, D10 |
| `error.code` | int | rmcp `ErrorCode` enum (solverforge only) | D1.4, D6, D10 |
| `cycle_id` | string | LangGraph checkpoint thread id | D1.1, D2.1, D2.4 |
| `thread_id` | string | LangGraph thread id | D1.5, D2.1, D2.2 |
| `regime_state` | enum | PUSH / MAINTAIN / REDUCE / RECOVER | D1.1 |
| `q_he_score` | number | composite habit/energy metric | D1.1 |
| `phase` | string | graph phase name | D1.1, D1.3 |
| `phase_iteration` | int | loop counter per phase | D1.3 |
| `vector_scores.{passion\|skill\|market\|revenue\|course}` | number | 5 IKIGAI vectors | D1.1 |
| `meta_vector_score` | number | composite of 5 vectors | D1.1 |
| `corrections[*]` | array | correction plan items | D1.1 |
| `is_hysteresis_active` | boolean | policy engine flag | D1.1 |
| `kill_switch_triggered` | boolean | cycle abort flag | D1.1 |
| `human_in_the_loop` | boolean | interrupt attribute | D1.1, D2.3 |
| `model` | string | e.g. `claude-sonnet-4.5` | D2.1, D2.4 |
| `gen_ai.request.model` | string | auto-instrumented by LangChain | D2.1, D2.4 |
| `gen_ai.usage.input_tokens` | int | auto-instrumented | D2.1, D2.4 |
| `gen_ai.usage.output_tokens` | int | auto-instrumented | D2.1, D2.4 |
| `gen_ai.system` | string | `anthropic` / `openai` / ... | D2.1 |
| `checkpoint_db` | string path | SQLite checkpoint location | D1.1 (runbook anchor only) |
| `retry.attempt` | int | IKIGAI reliability layer | D1.5, D1.6, D10, D12 |
| `retry.exhausted` | boolean | IKIGAI reliability layer | D1.5, D1.6, D10 |
| `circuit.state` | enum | `closed` \| `open` \| `half_open` | D1.5, D10 |
| `circuit.breaker` | string | tool name CB guards | D1.5 |
| `circuit.failure_count` | int | running count | D1.5 |
| `cache.invalidated` | boolean | scoped cache invalidation | D1.5 |
| `idempotency_key.present` | boolean | solverforge mutation tools | D12 |
| `db.statement` | string | SQLX-prepared statement | D6 (when SQLX layer attached) |
| `db.duration_ms` | number | SQLX query time | D6 |
| `jsonrpc.method` | string | JSON-RPC envelope | D5 |
| `jsonrpc.id` | string | JSON-RPC envelope | D5 |
| `tool.arg.thread_id` | string | captured arg | D1.2 |
| `tool.arg.ueid` | string | UEID format `<CLUSTER>:<ENTITY>:<ID>` | D1.2, D2.2 |

---

## §8. Dashboard Creation Checklist (per dashboard)

For each dashboard before declaring it "live":

1. **Schema verified:** every attribute used exists in at least one real span from Spec 02 smoke test
2. **Time window defined:** default 5-min rolling, 24-h retention on fast panels, 30-day on slow panels
3. **SLO floor encoded:** green/yellow/red thresholds written as PromQL rules in `observability-rules.yml`
4. **Alert wired:** every page-level breach has a corresponding alert in §4 with `runbook:` annotation
5. **Drill-down link:** each panel links to the underlying LangSmith/Langfuse trace search
6. **Owner assigned:** primary + secondary on-call from §5 sprint table
7. **Docstring in tool:** back-link to this spec under `code-docs/observability/05-dashboard-design.md`
8. **Smoke gate:** `pav smoke observability` (Spec 02) emits at least one sample for every panel

---

## §9. Out of Scope (deferred to later specs)

- **D9+ cross-trace anomaly detection** (e.g. ML-based anomaly scoring) — defer until 90 days of post-merge data
- **D10+ LLM evaluation suites** (correctness scoring of generated plans) — needs evaluation harness spec
- **Solverforge SQLX span layer** — blocked on `tracing-opentelemetry` crate version linkage (Spec 03 sub-task)
- **Per-user dashboard personalization** — single-user system, no need
- **Long-term archival (>30 days)** — confirm with finance before adding cost overhead
- **D2.2 entropy threshold tuning** — needs baseline data (see §5 deferral)

---

## §10. Open Questions

1. **Cost pricing table source of truth** — should per-model prices live in `ikigai.config.toml` or in Langfuse admin? Current plan: ikigai config (kept under version control).
2. **HITL `time-to-resolve`** — does the agent clock start on interrupt emit or on next cycle pickup? Decision needed before Sprint 20.
3. **Dual-export parity alert** — is ±5 % the right band? Could be loosened to ±10 % if solverforge crate-link lag introduces systematic drift.
4. **Spec 02 smoke CI cadence** — every PR vs nightly? Suggest: every PR for unit-level, nightly for the full 4-server matrix.

These are tracked in the companion `.sdd-progress.md` and should be resolved before Sprint 18 starts.
