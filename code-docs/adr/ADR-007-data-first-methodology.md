# ADR-007 — Data-First Methodology

> **STATUS CLARIFICATION (2026-08-29):** The "5+ manual logs per workflow" rule in §Decision.2 and §Implementation Rules.1 is **observation depth** (observe a workflow this many times before designing code for it), NOT a release gate. The methodology's purpose is to ensure specs are grounded in observed behavior, not to gate IKIGAi/algorithm work behind a counter.
>
> The actual gate for algorithm/IKIGAi work is **system readiness** — backend + data + agent layers must be functional before algorithm code is written. This is the canonical framework per `~/.claude/projects/C--Users-mathe-code-space-life-oss-life/memory/algorithm-gate-system-readiness-not-sonho-2026-08-29.md` and was reaffirmed by user on 2026-08-29 in response to the "5 SONHO logs gate" propagated misconception.
>
> **Downstream impact:** Any doc that frames ADR-007 as a "5 SONHO logs gate" (e.g., `docs/design-system/53-adr-007-data-first-gate.md`, references in `10-`, `16-`, `17-`, `18-`, `19-` design-system files) is using the wrong framing. The deferral rule still applies (algorithms still wait), but the reason is system readiness, not a SONHO counter.

**Status:** Accepted
**Date:** 2026-07-02
**Deciders:** human (Matheus) + agent swarm
**Consulted:** `.omo/drafts/ikigai-as-dom-on-planning-engine.md`, `.omo/drafts/agentic-markdown-system-completion.md`
**Informed:** future engineering agents
**Scope:** methodology pivot governing all new feature work for closing 2026 (Jul–Dec)

---

## Status

Accepted (2026-07-02). Supersedes the implicit "design-from-math-first" working mode that drove PAV kernel development through 2026-Q2. The PAV codebase in `life-ops/operational/` remains in place as a reference implementation but is no longer the primary surface area for new features.

---

## Context

The PAV productivity kernel (`life-ops/operational/`) was built top-down: starting from clean-room algebraic theories — `H(t) = 1 − e^(−λ·streak)` for habit consistency, `E = R·(1 − H(t))` for energy required, a 4-state PolicyEngine FSM with hysteresis, and a multi-factor Q_HE composite — and then constructing UI, persistence, and commands around those formulas.

The result is a system with the following observed characteristics:

- **9 TUI screens** are implemented, but daily actual usage is **1–2 screens** (`dashboard` for a glance, `journal` for a one-line log).
- **14 `_PersistentRepo` instances** back the persistence layer, but only **~4 are touched in real daily flows** (habit, journal, energy, sleep).
- **2,518 tests** are written against formulas that the user rarely needs to invoke; coverage is high, but coverage of what the user actually does each day is low.
- The **Q_HE composite** is mathematically defensible, but the daily interaction that produces it is "log a habit," which takes ~3 seconds. The composite is computed for an audience of one, in a context where the user overrides the regime manually anyway.
- The **regime FSM with hysteresis** is correct in the limit, but in practice the user adjusts pace through willpower rather than waiting for state transitions to update.
- The root cause is consistent: **we designed from abstract math theories without grounding in observed daily behavior.** The formulas were specified first, validated as code second, and adopted by behavior last — and behavior never matched.

This ADR changes that order.

---

## Decision

We pivot to a **data-first methodology** for the closing half of 2026. The rules are:

1. The **human manually fills 9 templates** in `vibe-ops/planning/_templates_periodos_v2/` (Sonho, Trimestral, Onda, Semanal, Diário, Quarterly Planning, Quarterly Review, Sprint Kickoff, Sprint Retrospective), using `.omo/ikigai/closing-2026/` as the personal container for the 2026 closing arc.
2. **Code emerges from patterns observed across 5+ manual logs per workflow.** No new entity types, fields, or relations are added until the manual logs show they recur in real use.
3. **All new feature proposals require a "manual work-around" demonstration.** The proposer must show: (a) the template or note structure they used to work around the absence of the feature, (b) the friction they hit, (c) the proposed automation in terms of that friction.
4. **The PAV kernel stays in the codebase** as a reference implementation of the math — useful for future agents that need to reason about formulas — but is **not the primary surface** for daily work during this period.
5. The nine manual templates, the manual review cadence (sonho → trimestral → onda → semanal → diário), and the human override of policy decisions are the canonical inputs. Any software that consumes them is downstream of these artifacts.

The closing-2026 container (`.omo/ikigai/closing-2026/`) is the authoritative time-box for evaluation: at the end of 2026 we either have learned enough to resume feature work, or we have learned that the methodology itself needs revision (see Roll-back criteria).

---

## Consequences

### Positive

- **Specs grounded in real use.** Templates that survived 5+ manual fills are the ones that earn code. No more speculative entity types.
- **Less over-engineering.** We stop building features the user does not reach for. The codebase shrinks toward what is used, not what is provable.
- **More maintainable.** A code surface that is small, opinionated, and aligned with observed behavior is easier for future agents to inherit.
- **User owns the data.** The Markdown vault is the SoT. Any tool that reads or writes it is replaceable. The user's behavior is the contract; the code conforms to it.
- **Honest evaluation surface.** Templates produce artifacts that can be diffed, audited, and replayed. Code that is "the algorithm" cannot.

### Negative

- **Delays visible feature work.** Six months of "just fill the templates" before any new UI shows up. That is the price.
- **Requires user discipline to log manually for 6 months.** No tooling will gently remind, no score will reward, no FSM will suggest. The user's own attention is the engine.
- **UI may feel underbaked.** When agents do resume feature work, the surfaces will be smaller than PAV in 2026-Q2. That is intentional.
- **Risk of drift between manual log and any code that reads it.** If the manual format changes mid-wave, downstream tooling breaks. Mitigated by the "templates are immutable once in use" rule below.

### Neutral

- The **existing PAV kernel stays in code** as a reference implementation. It is not deprecated, not removed, but it is not the surface we are learning from.
- The `_PersistentRepo` instances, the TUI screens, and the test suite remain available for future agents who need to reason about the math or migrate behavior into a smaller surface.
- Any agent that opens `life-ops/operational/` during this period should treat it as a corpus to read from, not a system to extend.

---

## Alternatives Considered

### A1 — Continue top-down design with better prioritization

**Description.** Keep the PAV methodology: design from formulas, ship features, improve prioritization via sharper user stories and tighter sprint scoping.

**Rejected because.** Still speculative. Better prioritization does not change the fact that the inputs (real daily behavior) are not yet observed at sufficient volume to justify the output (algorithmic UX). We would be picking better targets from a list we built before we had evidence.

### A2 — Buy an off-the-shelf OKR/tracker tool

**Description.** Replace the PAV kernel with a commercial product (e.g., a SaaS OKR tracker, a habit app with a public API). Stop maintaining personal productivity software.

**Rejected because.** Loses the algorithmic core. The IKIGAi methodology, the 5-vector scoring, the regime FSM, and the cybernetic loop are the long-term differentiators of this system. A commercial tool cannot host them, and replacing them with a generic OKR tracker collapses the system into a category it was designed to exceed.

### A3 — Hybrid: design templates + algorithmic engine, but no UI yet

**Description.** Keep the PAV kernel math and persistence, expose only the templates, and defer any new TUI work. The user interacts with templates; the kernel runs offline as a scoring layer that can later be wired in.

**Partially adopted as v0.5 path.** The data-first methodology assumes a pure-template period first (this ADR). A3 is the natural follow-on: once 5+ manual logs per workflow accumulate, the templates themselves can drive the algorithmic engine, and a thin UI can be re-introduced only for the friction points the templates reveal. A3 is on the roadmap but is **not** the current step.

---

## Implementation Rules

These rules govern all feature proposals during the closing 2026 arc. They are the operational form of this decision.

1. **No new entity types** until observed in 5+ manual logs of the same workflow.
2. **No new CLI commands** until observed in 3+ manual workflows (i.e., 3+ different template types reference the same operation pattern).
3. **No new templates** until seen as a gap during a real review. The nine templates in `_templates_periodos_v2/` are the working set; additions require an explicit review-time observation.
4. **All proposals require a "manual work-around"** alongside: the artifact (Markdown note, filled template section, spreadsheet) that the user built to cope with the missing feature, plus a one-paragraph framing of the friction it caused.
5. **Templates are immutable once in use.** A template that has been filled and consumed by a downstream artifact cannot be edited. Refactors happen **between cohorts** (between waves), not mid-wave.

---

## Roll-back criteria

This decision is reversible. The two checkpoints are:

- **6 months** (after the 2026 closing arc): if we have fewer than **10 fully-filled templates manually**, the data-first premise has failed to generate evidence — reconsider whether the methodology was the right frame, or whether the user needed a different scaffolding.
- **3 months** (mid-arc): if the user reports **"too much manual work"** as a recurring friction in reviews, revisit the verification rules (especially the 5+ logs threshold) and consider lowering them or introducing assist tooling sooner than originally planned.

Either signal triggers a re-evaluation, not an automatic reversion. The decision can also be reaffirmed explicitly at each checkpoint.

---

## Related Decisions

- **Open decision set (D1–D4):** `.omo/drafts/ikigai-as-dom-on-planning-engine.md` — proposes planning-with-files as the DOM layer for IKIGAi contracts. The data-first methodology is a precondition: we cannot evaluate IKIGAi-as-DOM until we have manual artifacts in volume.
- **Behavioral rules for future agents:** `.omo/ikigai/meta/agents.md` — governs how agents should treat the PAV kernel, the templates, and the manual logs during this period.
- **Socratic scaffold:** `.omo/ikigai/meta/socratic-interview.md` — the 7-question scaffold used during reviews to surface whether a feature proposal has the manual work-around it requires.
- **ADRs that remain authoritative (do not modify as part of this pivot):** ADR-001 through ADR-006 — none of them are invalidated by data-first; they describe math and architecture that the closing-2026 arc now uses as reference, not as directives.

---

## Notes

- The PAV kernel was not wrong — the formulas are correct. The mistake was building features around them before the user's behavior was understood. This ADR corrects the order, not the mathematics.
- A v0.5 spec (templates + engine, no new UI) is the natural next step but is out of scope for this decision. A3 above sketches the shape; a future ADR will own the specifics once the 5+ logs threshold is met for at least one workflow.
- The `.omo/ikigai/closing-2026/` container is a personal artifact directory, not part of the public vault. It exists to keep the manual logs isolated from the template originals during this period.
- Future agents reading this ADR: if a feature proposal arrives without a manual work-around, route it back through `.omo/ikigai/meta/socratic-interview.md` before implementation. The proposal is not ready.

---

*ADR-007 — Accepted — 2026-07-02 — human + agent swarm — data-first methodology pivot for closing 2026*
