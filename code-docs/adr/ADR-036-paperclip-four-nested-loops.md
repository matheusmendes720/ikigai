# ADR-036 — Paperclip: Adoption of the 4 Nested Loops Framework

> **Status:** ACCEPTED (2026-10-12)
> **Deciders:** matheus + orchestrator (`.claude/agents/loop/orchestrator.md`)
> **Date:** 2026-10-12
> **Wave:** M192 (Paperclip documentation arc)
> **Related:** `specs/M169-paperclip/SPEC.md`, `orchestrator.md §Inspiration`,
> `hill-climb.sh`, `trend-report-loop-engineering-2026.md §3.1`

> **Naming note:** M192 prompt requested `ADR-026-paperclip-four-nested-loops.md`,
> but `ADR-026` is ACCEPTED (Sub-Agent Dispatch Protocol, 2026-09-05). Per
> `code-docs/adr/README.md §Maintenance` ("Numbering — sequential"), the next available
> number is **036**. All references use `ADR-036`.

---

## Context

The **LangChain "4 nested loops" framework** (Sydney Runkle, jul 2026,
"Art of Loop Engineering") is the canonical 2026-h2 taxonomy:

```
┌─────────────────────────────────────────────────────────────┐
│ LOOP 4: Hill-Climbing (analisa traces → reescreve harness) │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ LOOP 3: Event-Driven (cron/webhook → trigger)           │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ LOOP 2: Verification (grader → feedback → retry)    │ │ │
│ │ │ ┌─────────────────────────────────────────────────┐ │ │ │
│ │ │ │ LOOP 1: Agent (think → tool → observe → loop)    │ │ │ │
│ │ │ └─────────────────────────────────────────────────┘ │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

Life-OSS loop engineering (`.claude/loop/`) **already implements all 4 loops in practice**
but documents them implicitly. The orchestrator's "Inspiration" section
(`orchestrator.md:339`) cites the 4-loop stack AND TheBotCompany 3-role state machine
without a canonical mapping. This ADR codifies the mapping. Backwards-compatible,
doc-only, +1 drift test.

---

## Decision

**Life-OSS adopts the LangChain 4 nested loops framework as the primary lens for designing
and reviewing loop improvements.** Every cron / daemon / node maps to exactly one loop.
New loops MUST declare which loop they belong to before acceptance.

### Mapping (life-oss → 4 loops)

#### Loop 1 — Agent (think → tool → observe)

Lives INSIDE each subprocess invocation.

| Surface | Role |
|---|---|
| `paperclip/agents/claude.py` | Claude CLI subprocess — ReAct think→tool→observe inside |
| `paperclip/agents/{pi,mcode,omo,hermes,openclaw}.py` | Future / stub adapters; same shape when active |
| `.claude/agents/loop/{worker,verifier}.md` | Loop-level sub-agents spawned per tick |

**Insight:** separation of Loop 1 and Loop 2 is required — "model is a fairly generous
grader of its own homework" (Osmani).

#### Loop 2 — Verification (grader → feedback → retry)

The autothrottle chain gating every Paperclip run. Maps to M173/M175/M176 + deterministic gates.

| Surface | Role | Drift test |
|---|---|---|
| M173 **CostGate** (`paperclip/policy.py`) | Reject if daily spend > `COST_THRESHOLD_USD` | `test_paperclip_router_importable` |
| M175 **WallClockGate** (`paperclip/policy.py`) | Reject if elapsed > `threshold_seconds` (default 3600s) | `test_paperclip_wall_clock_gate_exists` |
| M176 **RiskGate** (`paperclip/policy.py`) | Reject if spec matches `DEFAULT_RISK_KEYWORDS` (rm -rf, git push --force) — first fail-CLOSED gate | `test_paperclip_risk_gate_exists` |
| Deterministic gates in `verifier.md` (`pytest -x`, `ruff check .`, `mypy .`) | Short-circuit FAIL before LLM-as-judge; deterministic > LLM | (drift net coverage) |
| M26 tier-by-risk (`risk-classifier.md`) | LOW=5min / MEDIUM=10min / HIGH=30min verifier depth | (drift net coverage) |

**Insight:** deterministic gates run FIRST. LLM-as-judge only after gates pass.

#### Loop 3 — Event-Driven (cron / webhook / inbox → trigger)

| Cron / daemon | Role | Cadence |
|---|---|---|
| `loop-tick` | Heartbeat (orchestrator tick) | 60min |
| `cost-dashboard` | Cost reports + spike alarm | 6h |
| `streak-tracker` | Streak observability | daily |
| `daemon-watchdog` | Silent-daemon detection | 30m |
| **M174 paperclip-auto-spawner** | Drains `.claude/loop/inbox/`, dispatches Paperclip runs | 5min |
| 4 invoke-skill crons | IKIGAI daily/weekly/monthly/quarterly | 1440m / 10080m / 43200m / 129600m |

**Insight:** Paperclip M174 is itself Loop 3 — it doesn't do work, it triggers Loop 1 + 2.

#### Loop 4 — Hill-Climbing (analisa traces → reescreve harness)

"First 3 loops automate work. The fourth automates improvement" (Runkle).

| Surface | Role | Trigger |
|---|---|---|
| `.claude/loop/hill-climb.sh` | Pattern-based proposal engine → emits `M-CAND-*` to `roadmap.md` | Weekly (168h), M3 |
| M33 hill-climb v2 | 3-candidate pattern analysis | Same weekly cron |
| M29 signal-discovery | Aggregates progress.md → candidate recommendations | One-shot + weekly refresh |

**Insight:** Loop 4 needs greppable / structured traces. life-OSS traces live in
`.claude/loop/progress.md` (append-only, structured) + `.swarm/memory.db` + `runs/*.jsonl`
(M183 `persist_run` output) — all satisfy the requirement.

### 5-Risks Matrix (Ronacher + Osmani)

| # | Risk | Mitigation | Status |
|:--|:-----|:-----------|:-------|
| 1 | **Cognitive surrender** (defensive code, Ronacher) | `constitution.md` principle 2 + anti-pattern "no defensive code for impossible states"; orchestrator hard-rule #7 | ✅ MITIGATED |
| 2 | **Loop brittleness** | M175 WallClockGate (1h cap) + M173 CostGate + `verifier.md` hard-rule (max 8 sub-agents, $5/tick, 30min wall) | ✅ MITIGATED |
| 3 | **Verifier mis-grades** | Deterministic gates FIRST; LLM-as-judge only after gates; M26 tier-by-risk | ✅ MITIGATED |
| 4 | **HITL fatigue** | M174 auto-spawner (unattended routine); M8 ntfy.sh only on `NEEDS_FIX × max_attempts` + cost spike; 10min cooldown | ⚠️ **PARTIAL** — M180 HIL pause/resume closes the gap (in flight) |
| 5 | **Runaway cost** | M173 CostGate + M7 cost-dashboard.sh (>$10/day exit code 2 alarm) + M175 WallClockGate + verifier.md $5/tick hard-rule | ✅ MITIGATED |

**Net:** 4 of 5 risks fully mitigated by drift-enforced gates; **risk #4 (HITL fatigue)**
is the known gap — M180 HIL work closes it.

---

## Rationale

1. **Canonical vocabulary.** Per `trend-report-loop-engineering-2026.md §3.1`, the 4-loop
   framework is the 2026-h2 consensus (LangChain + Osmani + Runkle).
2. **External alignment.** M169 + Paperclip's evolution mirrors the broader trend
   (paperclipai/paperclip, Karpathy AutoResearch, Huntley Ralph).
3. **Mapping is documentation, not design.** Every cron / daemon / node already exists;
   the change is a 1-file write + 1 drift test.
4. **Drift enforcement matters.** A new loop infrastructure MUST declare its loop
   assignment before acceptance.
5. **5-risks matrix is the durable artifact.** New crons MUST document risk mitigation
   status against it.

---

## Implementation Rules

### (a) Every new cron / daemon / gate declares its loop

SPEC.md files MUST include (when adding Loop 1/2/3/4 surface):

```yaml
loop_assignment: <1|2|3|4>
loop_role: <agent|verification|event-driven|hill-climbing>
mitigates_risk: <1|2|3|4|5>   # from §5-Risks Matrix
```

### (b) The 4 loop names are reserved identifiers

The drift test (`test_paperclip_adr_036_exists`) checks for literal strings `"Loop 1"`,
`"Loop 2"`, `"Loop 3"`, `"Loop 4"`, `"Agent"`, `"Verification"`, `"Event-driven"`,
`"Hill-climbing"` in this file. A rename requires a test amendment.

### (c) Future Paperclip waves MUST update this ADR

New gates / daemons / spawners append rows to the mapping table + risks matrix.
Orchestrator refuses to dispatch workers that don't cite the loop they belong to (per
`constitution.md` principle 7, "Spec-driven, not vibe-driven").

---

## Consequences

### Positive

- **Clear taxonomy** — new contributor reads this ADR, then 4 spec arcs; structure at a glance.
- **Easier onboarding** — external researchers recognize life-oss's loop stack without translation.
- **Drift-enforceable** — future contributor cannot silently remove this ADR without breaking
  `test_paperclip_adr_036_exists` (CI).
- **Backwards-compatible** — no daemon schedule changes, no orchestrator prompt changes,
  no node renames.

### Negative

- **Maintenance overhead** — new crons must update this ADR (§c). At M169 cadence
  (1-2 waves/week), ~5 minutes per wave — acceptable.
- **Vocabulary lock-in** — if LangChain taxonomy evolves (5 loops, sub-loops), ADR goes stale.
  Resolution = supersede with new ADR.
- **HITL fatigue gap documented, not closed** — risk #4 has partial mitigation; M180 closes it.
  Intentional; surfaces the gap.

---

## Alternatives Considered

### Alt A — Adopt `paperclipai/paperclip` as canonical control plane

Replace life-oss loop-tick + paperclip-spawner with canonical Paperclip (67k⭐ MIT).

- **Rejected:** out-of-scope per M169 §"What M169 does NOT do". M169 + M174 chose the
  **custom adapter** path (thin LangGraph graph inside existing stack). Canonical Paperclip
  is **Option C in the M169 migration plan** — destination if/when life-oss graduates from
  "custom loop" to "company-grade orchestrator". Until then, we keep the adapter and adopt
  the 4-loop framework as the conceptual model.

### Alt B — Skip the ADR; rely on orchestrator's "Inspiration" section

- **Rejected:** agent prompt has 8K token budget and shifts focus every tick; ADR is
  long-lived + immutable. Drift-typed ADRs gate against removal.

### Alt C — Use a benchmark taxonomy (MLCommons EVAL, BIG-bench)

- **Rejected:** these are benchmark taxonomies, not loop-engineering taxonomies. The
  4-loop framework is purpose-built for "which cron is which loop?" — category mismatch.

### Alt D — Document ONLY the 5-risks matrix (skip loop mapping)

- **Rejected:** 5 risks = "what could go wrong?"; 4 loops = "what does each part do?".
  Both needed; decoupled loses "which cron mitigates which risk".

---

## Cross-references

### Load-bearing prior ADRs

- **ADR-013** (Accepted 2026-08-31) — canonical scope discipline; principle 7 underpins
  Implementation Rule §a.
- **ADR-026** (Accepted 2026-09-05) — Sub-Agent Dispatch Protocol; W4.4 sub-agent dispatch
  node IS Loop 1.
- **ADR-035** (Accepted 2026-09-21) — Empty-Commit Guard; G4 orchestrator disk-verification
  applies to ALL 4 loops.

### Code / spec references

- `specs/M169-paperclip/SPEC.md` — Paperclip MVP (4th LangGraph graph)
- `specs/M173-paperclip-cost-gate/SPEC.md` — Loop 2, risk #5
- `specs/M175-paperclip-wall-clock-gate/SPEC.md` — Loop 2, risks #2 + #5
- `specs/M176-paperclip-risk-gate/SPEC.md` — Loop 2, risk #1
- `specs/M174-paperclip-auto-spawner/SPEC.md` — Loop 3 trigger
- `specs/M180-paperclip-hil-resume/SPEC.md` — closes risk #4 gap
- `specs/M183-paperclip-state-persistence/SPEC.md` — Loop 4 trace source (`persist_run`)
- External: `G:\Other computers\My Laptop\notas_estudo\3_indice\harness_engineering\trend-report-loop-engineering-2026.md §3.1` (Runkle) + §5 (Ronacher 5 risks)

### Implementation steps (post-acceptance)

1. **M192 entry** — append to `.claude/loop/roadmap.md` (insert before `## Backlog`).
2. **Drift test** — add `test_paperclip_adr_036_exists` to `src/ikigai/tests/test_paperclip_drift.py`.
   Asserts: file at canonical path; 4 loop names + 4 descriptive words; 4 risk names.
3. **README update** — `code-docs/adr/README.md` ADR Index gets a row for ADR-036.
4. **Verify** — `pytest src/ikigai/tests/test_paperclip_drift.py` shows 11 → 12 PASS;
   `ruff check` clean; full drift net green.

---

*ADR-036 — accepted 2026-10-12 — adopts LangChain's 4 nested loops framework as the primary
lens for loop engineering. Maps every existing cron / daemon / gate to one of the 4 loops and
lists the 5 risks matrix (Ronacher + Osmani) with per-risk mitigation status. Drift-enforced
by `test_paperclip_adr_036_exists`.*
