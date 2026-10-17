---
name: M193-paperclip-stacks-comparison
description: Paperclip 8-stacks matrix — life-oss hybrid of F1+F3+F6+F8; skips F2/F4/F5/F7.
status: DONE
owner: loop-orchestrator
created: 2026-10-12
constitution_refs:
  - composition_over_inheritance
  - state_on_disk_not_conversation
  - tests_are_the_contract
estimated_cost_usd: 0.00
---

# M193 — Paperclip 8-stacks comparison matrix

**Status:** DONE
**Date:** 2026-10-12
**Author:** matheus-mendes (with Claude Code assist)
**Source docs:**
- [meta-analysis-loop-engineering-stacks.md](../../../../Other%20computers/My%20Laptop/notas_estudo/3_indice/harness_engineering/meta-analysis-loop-engineering-stacks.md)
  (Section 3 has the 8-family × 7-criteria matrix)
- [paperclip-orchestrator-specs.md](../../../../Other%20computers/My%20Laptop/notas_estudo/3_indice/harness_engineering/paperclip-orchestrator-specs.md) §9.3
  (migration path Phase 1)
- `.claude/loop/roadmap.md`, `.claude/loop/constitution.md`, `specs/M169-paperclip/SPEC.md`

---

## TL;DR

life-oss is a **hybrid** of Families 3 (TheBotCompany state machine) +
6 (Osmani 6 building blocks) + 1 (Ralph bash loop) + 8 (SDD constitution +
spec) + 5 (LangChain 4 loops, partial via M192/ADR-026 hill-climbing
Loop 4). It does **NOT** use Families 2 (Karpathy single-metric),
4 (AOrchestra dynamic sub-agent delegation), or 7 (Gas Town parallel
merge queue), and explicitly chooses **custom-over-hybrid** for
vendor-freedom reasons (avoiding LangSmith vendor lock-in, keeping the
loop infra under our own control). This SPEC is a research artifact —
side-by-side comparison + decision rationale — not an implementation
task. Drift net impact: +1 invariant (the matrix table itself).

---

## 1. The 8 families table (life-oss status marked ✅/❌)

Reproduced from the meta-analysis doc §3 with the `life-oss` column appended:

| Capability | Ralph | Karpathy | TheBotCo | AOrchestra | LangChain | Osmani | Gas Town | SDD | **life-oss** |
|---|---|---|---|---|---|---|---|---|---|
| **Multi-agent org chart** | ❌ none | ❌ none | ✅ 3 managers | ✅ dynamic | ✅ LangGraph | ⚪ neutral | ✅ 30 parallel | ❌ none | **n/a** (single-purpose loop-tick + canonical-paperclip M190) |
| **State in DB** | ❌ files | ✅ git | ⚪ partial | ❌ context | ✅ traces | ✅ files | ✅ Beads | ✅ md | **✅ SqliteSaver** (`data/paperclip.db`, `.swarm/langgraph_checkpoint.db`) |
| **Budget governance** | ❌ none | ❌ none | ⚪ cycle budget | ❌ none | ✅ LangSmith | ⚪ recommend | ❌ none | ❌ none | **✅ 3-tier** (M173 cost + M175 wall-clock + M176 risk) |
| **Goal alignment** | ❌ none | ❌ none | ✅ roadmap | ❌ none | depends | ⚪ neutral | ❌ none | ✅ spec→plan | **✅ cascade via roadmap** (`.claude/loop/roadmap.md` → goal cascade via M192) |
| **Audit log** | ❌ none | ✅ git | ⚪ partial | ❌ none | ✅ traces | ❌ none | ⚪ partial | ❌ none | **✅ progress.md** + M183 JSON RunRecord persistence |
| **UI** | ❌ none | ❌ none | ❌ none | ❌ none | ✅ Studio | ❌ none | ✅ basic | ❌ none | **✅ FastAPI dashboard** (M178) + ntfy.sh (M8) |
| **Stars (Oct 2026)** | 21.7k | 66k+ (1m) | n/a (paper) | n/a (paper) | 41k+145k | n/a (essay) | 16k | 115-126k | **n/a (custom)** |
| **HIL pattern** | ❌ | ❌ | ❌ | ❌ | ✅ langgraph | ⚪ neutral | ⚪ partial | ⚪ partial | **✅ langgraph_sdk.interrupt()** (M169 first in repo) |
| **Worktree isolation** | ❌ | ❌ | ⚪ recommend | ⚪ recommend | ⚪ recommend | ✅ one block | ✅ merge queue | ⚪ neutral | **✅ scripts/worktree-helper.sh** (M6, Windows-safe M24.1/M178) |
| **Drift-net invariants** | ⚪ n/a | ⚪ n/a | ⚪ n/a | ⚪ n/a | ⚪ n/a | ⚪ n/a | ⚪ n/a | ⚪ n/a | **76 invariants** (canonical_scope + drift_invariants + drift_extended_invariants + paperclip_drift) |

Key:
- ✅ = life-oss has this capability
- ❌ = life-oss explicitly does NOT have this (by design or scope gate)
- ⚪ = optional/neutral, life-oss status depends on choices made during M-{N}
- n/a = not applicable to this comparison axis

The matrix shows life-oss is **strongest** on state-on-disk, drift
invariants, and audit log (categories where the project's CLAUDE.md
"Append-only" + "State on disk, not in conversation" principles
naturally lend themselves to richer tooling). It is **weakest** on
multi-agent org charts (Family 1/4/7 territory) — but that's an
intentional trade-off for solo-dev simplicity (Family 7's 30
parallel agents would be overkill).

---

## 2. Family assignment (where life-oss sits on the 8-family map)

For each of the 8 families, one-sentence definition + life-oss
adoption note:

### 1. Ralph (Bash + completion promise) — ✅ adopted
**Definition:** Bash while-loop that re-runs a prompt until
`<promise>DONE</promise>` appears in the output.
**Adoption:** `bash .claude/loop/loop-tick.sh` is the canonical Ralph-style
bash loop. The 2 SEPARATE daemons (5/5 + invoke-skill) per `daemon-manager.sh list`
plus the M174 `scripts/paperclip-spawner.sh` entry point are all Ralph descendants.
Logs at `.claude/loop/logs/spawner.log`.

### 2. Karpathy (1 objective metric) — ❌ not applicable
**Definition:** while-true loop on a 630-line Python file that optimizes
1 objective metric (e.g. `val_bpb`) via git-committed iterations.
**Adoption:** ❌ explicitly skipped — life-oss is multi-metric (3 gates
per M173/M175/M176 + 9 v2 graph nodes + heartbeat). Reducing to 1 metric
would lose the planner-only scope guaranteed by ADR-013.

### 3. TheBotCompany (state machine) — ✅ partial
**Definition:** 3-phase state machine (Strategy → Execution → Verification)
with persistent roadmap + issue tracker + cycle budget; Apollo is the
independent verifier.
**Adoption:** ✅ partial — `.claude/agents/loop/orchestrator.md` runs
exactly this 3-phase pattern (read state → decide next task → dispatch
worker → verify → persist). Cycle budget = `MAX_GAP_LOOPS=5` (M169)
+ `MAX_IMPLEMENT_ITERS=3` (M169) + daily cost cap ($10 default).
**Differs:** Apollo is a separate LLM in the paper; life-oss uses the
same Claude session differentiated by `verifier.md` agent markdown
(cheaper, but loses independent verifier).

### 4. AOrchestra (dynamic sub-agent delegation) — ⏳ planned in M191
**Definition:** Orchestrator with ONLY 2 actions (`delegate_task` +
`complete`); sub-agents created ON-THE-FLY with fresh prompts.
**Adoption:** ⏳ not yet active — `paperclip_dynamic_workflows` skeleton
exists per M191 SPEC, but no on-the-fly sub-agent creation in production.
Deliberate choice — dynamic creation is risky; we prefer deterministic
agent slots per role (`claude.py`, `pi.py`, `omo.py`, `openclaw.py`,
`mcode.py`, `hermes.py` in M169 §6).

### 5. LangChain (4 loops) — ✅ partial via M192/ADR-026
**Definition:** 4 stacked loops (Agent → Verification → Event-driven →
Hill-climbing) wrapped around LangGraph + LangSmith.
**Adoption:** ✅ partial — ADR-026 (sub-agent dispatch) gives us Loop 1+2
(Sonnet agent + Sonnet verifier on tier-by-risk per M26). Loop 4
(hill-climbing) runs weekly via `.claude/loop/hill-climb.sh`
(Sundays 02:00, cost_cap $10). Loop 3 (event-driven) implemented as
the M8 ntfy.sh notification channel (event-driven alerts on
FAIL / NEEDS_FIX / BLOCKED / OVERRUN / BUDGET_ABORT / spike_alarm).
**Differs:** Loop 2 verifier uses our own agent markdown, not LangSmith's
RubricMiddleware. Cost tracking via local `cost-dashboard.sh` (M7), not
LangSmith. Reject vendor lock-in.

### 6. Osmani (6 building blocks) — ✅ fully adopted
**Definition:** Loop = implementation-agnostic vocabulary:
**Automations, Worktrees, Skills, Plugins, Sub-agents, Durable state**.
**Adoption:** ✅ fully adopted — all 6 blocks have life-oss equivalents:

| Osmani block | life-oss equivalent |
|---|---|
| Automations | `.claude/loop/loop-tick.sh` + `daemon-manager.sh` cron schedules |
| Worktrees | `scripts/worktree-helper.sh` (M6, Windows-safe M24.1/M178) |
| Skills | `.claude/skills/{ikigai-daily,ikigai-weekly,ikigai-monthly,ikigai-quarterly}/SKILL.md` (M2 + W3.5/W3.6 ikigai-cadence) |
| Plugins | (planned — see M191 dynamic-workflows) |
| Sub-agents | `claude.py` / `pi.py` / `omo.py` / `mcode.py` / `hermes.py` / `openclaw.py` adapters in `paperclip/agents/` (M169-M172) |
| Durable state | `data/paperclip.db` (SqliteSaver) + `.swarm/memory.db` |

### 7. Gas Town (parallel merge queue) — ❌ not adopted
**Definition:** Merge queue + worktree pool + role-based workers;
30 parallel agents; Bors-style bisecting merge; Beads (Dolt-backed)
state.
**Adoption:** ❌ explicitly skipped — 30 parallel agents is overkill for
solo dev. Our `daemon-manager.sh list` shows 10/10 scheduled daemons,
but each daemon is single-purpose (one tick = one task). Per the meta-
analysis §6 (Ronacher critique), high-orchestration overhead is a
known risk; we explicitly chose the **custom-over-hybrid** path to
avoid Dolt installation + bisect complexity.

### 8. SDD (Spec-First) — ✅ adopted
**Definition:** Spec-driven development lifecycle —
**Constitution → Specify → Plan → Tasks → Implement → Converge**.
**Adoption:** ✅ adopted (constitution + spec disciplines).
**Constitution:** `.claude/loop/constitution.md` (7 Core Principles,
human-only edit).
**Specify:** Each milestone has a SPEC.md at `specs/M{n}-{slug}/SPEC.md`
with YAML frontmatter (name, description ≤120 chars, status,
owner, created, constitution_refs).
**Plan:** (out-of-band in life-oss — the orchestrator plan is captured
in the milestone's acceptance criteria + tasks.md per-loop, not as
a separate `plan.md`).
**Tasks:** `.claude/loop/tasks.md` (per-loop pending list).
**Implement:** worker.md agent dispatched to a per-task worktree.
**Converge:** verifier.md agent runs 5-dim review (per M26 tier-by-risk);
FAIL/NEEDS_FIX/BLOCKED/OVERRUN routed via M8 notification channel.
**Differs:** No `/speckit.converge` slash command — convergence is the
verifier agent + drift net. No formal `plan.md` between SPEC and
tasks.md.

**Summary table — life-oss adoption matrix:**

| Family | Status | life-oss artefacts |
|---|---|---|
| 1. Ralph | ✅ | `loop-tick.sh`, `paperclip-spawner.sh`, invoke-skill daemons |
| 2. Karpathy | ❌ | none (multi-metric is structural) |
| 3. TheBotCo | ✅ | orchestrator.md (Strategy→Execute→Verify), cycle budget via M173/M175/M176 |
| 4. AOrchestra | ⏳ | M191 skeleton only; deterministic agents active (M169-M172) |
| 5. LangChain | ✅ (partial) | ADR-026 sub-agent dispatch + M3 hill-climb.sh weekly + M8 ntfy.sh events |
| 6. Osmani | ✅ (full) | All 6 blocks mapped to life-oss artefacts (see table above) |
| 7. Gas Town | ❌ | none; explicit trade-off for solo-dev simplicity |
| 8. SDD | ✅ | constitution.md + specs/M{n}-*/SPEC.md + tasks.md + drift net |

---

## 3. Decision tree (life-oss answers)

Reproduced from the meta-analysis doc §8 with **life-oss's choice
marked at each branch** (✅ = we did this; ❌ = we chose a different
branch):

```
START
  │
  ├─ Tenho 1 métrica objetiva? (val_loss, accuracy, build time)
  │   ├─ SIM → Família 2 (Karpathy)
  │   └─ NÃO ↓                                  ← ✅ life-oss is here
  │
  ├─ É greenfield mecânico? (migração, refactor, dependency update)
  │   ├─ SIM → Família 1 (Ralph) — minimal basta
  │   └─ NÃO ↓                                  ← ✅ life-oss is here
  │
  ├─ É multi-milestone com roadmap? (feature X, Y, Z sequenciadas)
  │   ├─ SIM → Família 3 (TheBotCompany) ou Família 6+1 (Osmani+Ralph)
  │   │         └─ É meu projeto pessoal? → Osmani+Ralph hybrid ✅ (life-oss)
  │   └─ NÃO ↓
  │
  ├─ Preciso de task decomposition dinâmica? (research, descoberta)
  │   ├─ SIM → Família 4 (AOrchestra)
  │   └─ NÃO ↓                                  ← ✅ life-oss is here
  │
  ├─ Time > 10 devs, parallel PRs, código maduro?
  │   ├─ SIM → Família 7 (Gas Town)
  │   └─ NÃO ↓                                  ← ✅ life-oss is here
  │
  ├─ Já uso LangChain / LangGraph stack?
  │   ├─ SIM → Família 5 (LangChain 4 loops) — menor atrito
  │   └─ NÃO ↓                                  ← ❌ life-oss: chose Family 6+1 hybrid + vendor-free LangChain elements
  │
  └─ Spec é tão importante quanto código? (compliance, regulated)
      ├─ SIM → Família 8 (SDD: Spec Kit ou BMAD)
      └─ NÃO → Família 6 (Osmani) como base + custom impl
                                                ← ✅ life-oss: Family 8 (constitution.md spec-first) as well
```

**life-oss trajectory:** stops at the "É meu projeto pessoal?" branch
(Osmani+Ralph hybrid), then ALSO adopts Family 8 (constitution +
SPEC). Resulting stack = **(1) Ralph** (bash loop + completion promise)
+ **(6) Osmani** (6 blocks) + **(3) TheBotCo** (state machine for the
3-phase orchestrator) + **(5) LangChain partial** (Loop 4 hill-climb +
Loop 3 events; reject LangSmith) + **(8) SDD** (constitution + SPEC).

The 3 BRANCHES life-oss SKIPPED: Family 2 (single metric), Family 4
(dynamic sub-agent creation), Family 7 (30 parallel agents).

---

## 4. Why we DON'T adopt each skipped family

### 4.1 Family 2 (Karpathy) — single-metric optimization

**Why skipped:** life-oss has multiple load-bearing metrics, not one:
- **Drift net count** (76 invariants — must not regress)
- **Cost per tick** ($0.02 avg / $10/day cap)
- **Wall-clock per tick** (3600s default per M175)
- **Risk keyword blocking** (18 dangerous keywords per M176)
- **Verification quality score** (5-dim, avg ≥4.0 per M26)
- **9 v2 graph nodes** correctness (per Phase 8.2/8.4)
- **Heartbeat liveness** (M39 watchdog)
- **Drift regression gate** (M115 backtest detector)

Reducing to 1 metric would lose ADR-013 planner-only scope
(PAV math is explicitly archived 2026-08-31) and flatten the
risk-tiered review (M26). The single-metric assumption is a
**structural mismatch** with how life-oss measures its own health.

### 4.2 Family 4 (AOrchestra) — dynamic sub-agent creation

**Why skipped:** dynamic sub-agent creation is **risky** for a
solo-dev project. The AOrchestra paper reports 67.6% on GAIA but
inherits a "fresh context, no persistent state" semantic that
conflicts with CLAUDE.md Principle 5 ("State on disk, not in
conversation"). Without persistent state per sub-agent, we lose
debuggability — when a sub-agent fails, we have no run-record to
post-mortem (see M183 fix). Instead, life-oss uses **deterministic
agent slots** per role (`claude.py`, `pi.py`, `omo.py`,
`openclaw.py`, `mcode.py`, `hermes.py` in `paperclip/agents/`),
each a Python file in the repo. The `paperclip_dynamic` skeleton
(M191) is preserved for future use but not wired into production.

### 4.3 Family 5 (LangChain) — vendor lock-in

**Why partially adopted, not fully:** LangSmith is required for the
canonical Loop 4 hill-climbing engine (`langchain.com/blog/the-art-of-loop-engineering`).
Locking cost-tracking into a vendor product contradicts the project's
"fully local" constraint (`SQLite + filesystem only, zero cloud deps`
per CLAUDE.md global conventions). Instead, life-oss:
- Uses LangGraph for the graph engine (open source, MIT) ✅
- Rejects LangSmith for cost-tracking → uses local `cost-dashboard.sh` (M7) ✅
- Rejects `RubricMiddleware` for verification → uses our own
  `verifier.md` agent with 5-dim scoring + tier-by-risk (M26) ✅
- Adopts Loop 4 hill-climb pattern → `hill-climb.sh` weekly (M3) ✅
- Adopts Loop 3 event-driven → `notify.sh` via ntfy.sh (M8) ✅
- Uses Sonnet worker + Sonnet verifier (same model, different
  prompts) instead of maker-checker (different model) — accepts the
  weaker verification to avoid paying for 2 model tiers.

### 4.4 Family 7 (Gas Town) — 30 parallel agents

**Why skipped:** 30 parallel agents would be overkill for the scale
of life-oss. Per `daemon-manager.sh list` (2026-10-12), life-oss runs
**10 daemons** (loop-tick, hill-climb, cost-dashboard, streak-tracker,
daemon-watchdog, paperclip-spawner, invoke-skill-ikigai-daily, weekly,
monthly, quarterly), each single-purpose. Solo-dev project — 1
operator, 1 repo. Gas Town's overhead (Dolt installation, merge queue
infra, Beads state, role-based worker dispatch) would consume more
engineering time than it saves. The **`scripts/worktree-helper.sh`**
and **`paperclip_auto_spawner`** (M174) cover the parallel-PR case
lightly (3-5 concurrent worktrees, not 30) — most milestones run
serial anyway because they share the worktree namespace.

---

## 5. Migration paths

Brief reference to §9.3 of the meta-analysis + §9.3 of
`paperclip-orchestrator-specs.md`:

### Phase 1 — Add canonical Paperclip locally (M190, DONE)

Install canonical Paperclip (`npx paperclipai@latest onboard`)
side-by-side with our existing loop-tick. Register our
**HTTP adapter** (`scripts/paperclip_heartbeat_http.py` ~50 LOC)
as a "Life-Oss Paperclip" employee. Canonical Paperclip becomes
the control plane; our existing graph becomes the worker. Both
run side-by-side; nothing in our internal loop replaced.

### Phase 2 — Add CTO + Reviewer agents (M191+, PENDING)

Add a `CTO` agent in the canonical Paperclip org chart whose job
is to create issues for our `Engineer` agent (which IS our life-oss
Paperclip). Add a `Reviewer` agent that picks up our completed
tasks and runs verification using the same 5-dim rubric as our
local `verifier.md`. This unlocks the Strategy→Execution→Verify
state machine without rebuilding our loop infra.

### Phase 3 — Goal alignment cascade (M192+, PENDING)

Define company mission (1 sentence) + 3-5 goals. Tasks cascade
from goal → issue. Hooks into `.claude/loop/roadmap.md` so the
existing milestone list becomes the audit trail. Aligns with
ADR-026 sub-agent dispatch + LangChain Loop 1 (Agent).

### Phase 4 — Full multi-agent autonomy (PENDING)

Add 5-10 more agents (CTO, Designer, Researcher, CMO). Import a
`companies` template from `github.com/paperclipai/companies`. Set
monthly budgets per agent. Operate 7-day unattended. This is the
end-state of the migration: canonical Paperclip as the only
control plane, our loop-tick becomes a stock "Engineer" employee.

**Reverse direction (if Phase 1 fails):** roll back the HTTP
adapter; canonical Paperclip uninstalled. life-oss retains the
existing custom infra. Per §9.3's "augment, never replace"
principle, no Phase 0 (existing loop) work is at risk from
Phase 1+ work.

---

## 6. Acceptance

- [x] `specs/M193-paperclip-stacks-comparison/SPEC.md` exists with full
      YAML frontmatter (name, description ≤120 chars, status DONE,
      owner, created, constitution_refs)
- [x] The matrix in §1 has ALL 8 families + life-oss column
      (Ralph, Karpathy, TheBotCo, AOrchestra, LangChain, Osmani,
      Gas Town, SDD, life-oss)
- [x] §4 has a 1-paragraph "why not" for each of the 4 skipped families
      (Families 2, 4, 5 partial, 7)
- [x] §3 reproduces the 8-family decision tree with life-oss's answer
      marked at each branch
- [x] §5 references §9.3 of the meta-analysis + §9.3 of the
      orchestrator-specs doc for migration paths
- [x] `src/ikigai/tests/test_paperclip_drift.py` has new test
      `test_paperclip_stacks_comparison_exists` asserting all 8 family
      names appear in the SPEC + life-oss is mentioned
- [x] `.claude/loop/roadmap.md` has the M193 entry with
      `STATUS: DONE`
- [x] Drift net goes 76 → 77 (+1 for the new M193 drift test;
      other commits in parallel may add more, this SPEC contributes +1)

---

## 7. Lessons

1. **Hybrid is a valid answer.** No single family covers the full
   life-oss scope; combining 4 (3, 6, 1, 8) families explicitly is
   architecturally honest and matches the meta-analysis's "Por que
   escolhemos um HYBRID das 4 famílias mais maduras" verdict.

2. **Staying custom = staying vendor-free.** Picking custom over
   Family 5 (LangChain) + Family 7 (Gas Town) preserves CLAUDE.md's
   "fully local" constraint. The cost is writing our own
   cost-dashboard (M7), our own hill-climb (M3), our own notification
   channel (M8); the benefit is no LangSmith bill, no Dolt install,
   no merge queue infra.

3. **Migration to canonical Paperclip is gradual, not rip-replace.**
   The "augment, never replace" principle from §9.3 means Phase 1 is
   additive (canonical Paperclip + existing loop-tick both run); only
   Phase 4+ actually migrates the control plane. M190 is the
   prerequisite — without an HTTP adapter for our existing loop, no
   canonical Paperclip agent can hand work to us.

---

## 8. Related

- [meta-analysis-loop-engineering-stacks.md](../../../../Other%20computers/My%20Laptop/notas_estudo/3_indice/harness_engineering/meta-analysis-loop-engineering-stacks.md)
  — the 8-family × 7-criteria matrix (§3) + decision tree (§8) +
  state-of-the-art one-liners (§9)
- [paperclip-orchestrator-specs.md](../../../../Other%20computers/My%20Laptop/notas_estudo/3_indice/harness_engineering/paperclip-orchestrator-specs.md) §9.3
  — "Don't replace; augment" migration principle
- `specs/M169-paperclip/SPEC.md` — our Paperclip graph v0 (the system
  this SPEC is comparing against the 8 families)
- `specs/M190-paperclip-canonical-adapter/SPEC.md` — Phase 1 of the
  canonical Paperclip migration
- `code-docs/adr/ADR-026-sub-agent-dispatch-protocol.md` — sub-agent
  dispatch (Family 5 LangChain-style)
- `.claude/loop/roadmap.md` — current life-oss loop state (all
  M-numbers referenced)
- `.claude/loop/constitution.md` — the 7 Core Principles that gate
  every milestone
