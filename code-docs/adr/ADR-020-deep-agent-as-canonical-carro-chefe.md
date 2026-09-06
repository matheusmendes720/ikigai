# ADR-020 — Deep Agent as Canonical Carro-Chefe

**Promoted from memory:** `master-branch-carro-chefe-2026-08-28`

**Status:** Accepted (locked decision — not a proposal)
**Date:** 2026-09-03
**Deciders:** Matheus Mendes + Claude (assistant)
**Scope:** Canonical architecture lock-in — Deep Agent = master, PAV = archived subsystem

---

## Context

The IKIGAI system has had two competing architectural eras. In the legacy era (pre-2026-08-26), the PAV TUI/CLI was the carro-chefe — a build-from-scratch productivity kernel with mathematical auto-performance algorithms baked directly into user-facing terminal interfaces. This era accumulated UI concerns that broke the "pure logic, zero I/O" invariant, had zero consumer demand proven by SONHO logs, and treated PAV/IKIGAI/CLI as competing surfaces.

The current era (post-2026-08-26 pivot) replaces that hypothesis: instead of building bespoke UIs around math algorithms, the architecture treats existing fork applications (tuiboard, taskdog, solverforge-calendar) as user surfaces that consume MCP contracts, and makes the Deep Agent the AI-native backend backbone that bidirectionally syncs those surfaces with the vault markdown source of truth.

This decision locks in the current canonical architecture so it is never re-litigated as an open question.

## Decision

The following are locked as the canonical IKIGAI architecture:

- **Master branch = Deep Agent (carro-chefe).** The Deep Agent is the single authoritative system that bidirectionally syncs all fork surfaces (tuiboard, taskdog, solverforge-calendar) with the vault markdown source of truth. It reads widget state from forks and vault planning content, applies the `./strategics/` constitutional layer, and writes back to both forks and vault.
- **PAV TUI/CLI + math = desativado (archived subsystem).** The PAV UI, CLI, and mathematical algorithm code (`apps/cli`, `apps/tui`, `src/operational/apps/`) are deprecated as the carro-chefe. They remain on disk at `archive/legacy-pav/src-operational/` per ADR-013 scope discipline and `legacy-pav-ui-era-2026-08-28`. Revival is governed by explicit criteria (see Revival Criteria).
- **Vault write invariant.** All writes to vault/ (whether from the Deep Agent, native CLI, or any fork) route through the `vault_write` MCP tool exclusively. No other code path writes to vault/. Enforced at the MCP server layer and at the vault filesystem level. Cross-ref ADR-012 §Vault Write Invariant.
- **Planner-only invariant.** The IKIGAI agent layer operates as a planner exclusively. Mathematical policy, scoring, QHE computation, regime FSM, and heuristic execution are not part of `IKIGAI_TOOLS`. Cross-ref ADR-013 §OUT OF SCOPE.
- **Forks = user views.** tuiboard, taskdog, and solverforge-calendar are fork adapters that surface IKIGAI data to the user. They are consumers of MCP contracts, not independent writers to vault. Cross-ref ADR-012 §Fork-Connection Architecture.

## Consequences

### Positive

- **Canonical carro-chefe.** One system (Deep Agent) is unambiguously the master. All forks sync bidirectionally with vault through it. No ambiguity about which system "owns" the productivity OS.
- **Bidirectional sync.** Deep Agent reads from forks (widget state) and vault (strategic planning), applies `./strategics/` rules, and writes to both — closing the loop between user-facing surfaces and the source of truth.
- **Single source of truth.** vault/ is the canonical source. Forks consume contracts; Deep Agent mediates all writes. No fork can drift the vault out of sync.
- **Clean separation.** PAV math stays archived until explicit demand. `./strategics/` (PT-BR markdown) is the constitutional layer the Deep Agent actually reads — not hard-coded algorithm logic.

### Negative

- **Scoring/heuristics off the critical path.** Q_HE, regime FSM, habit tracking, and all PAV mathematical outputs are archived. They cannot run in the current architecture without revival (see Revival Criteria).
- **Revival requires user adjudication.** PAV revival is not a self-service restore — it requires explicit demand with one of the three triggers satisfied and user approval. This adds friction to any future revival attempt.
- **PAV era docs are stale.** Many ADRs, PDRs, BRDs, and decision logs from the legacy era (pre-2026-08-26) reference PAV TUI/CLI as the carro-chefe. Those docs must be flagged with a `SUPERSEDED` trailer before being used as architectural guidance.

## Revival Criteria

PAV revival is governed by the **Revival Criteria** from `docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md` §Revival Criteria (verbatim):

> An algorithm module may be revived (re-imported by production code, modified, or replaced) only when ONE of the following is true AND user adjudicates:
>
> 1. **Consumer demand:** A backend service or deep agent reads from this module's exports, AND the module produces incorrect/wrong values in real use. Symptom: failed test or operator report.
> 2. **Telemetry pain:** Telemetry from real SONHO/ONDA logs shows the algorithm output diverges from what the user wants. Symptom: measured mismatch in ≥5 consecutive observations.
> 3. **Day-to-day conflict:** User opens a planning cycle and finds the algorithm's behavior conflicts with their actual decision-making. Symptom: user override + complaint in cycle retrospective.
>
> **Negative criterion:** "Algorithm is conceptually interesting" or "Algorithm has clean math" is NOT a revival trigger.

Revival additionally requires updating this ADR to explicitly rescind itself and mark the PAV revival path as accepted.

## Cross-references

- **ADR-012** — Fork-Connection Architecture (`code-docs/adr/ADR-012-fork-connection-architecture.md`): vault_write sole writer invariant, fork adapter pattern, UEID canonical format
- **ADR-013** — Canonical Scope Discipline (`code-docs/adr/ADR-013-canonical-scope-discipline.md`): planner-only invariant, out-of-scope table, PAV desativation
- **algorithm-attribution-design** — (`docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md`): attribution model, revival criteria verbatim, vault write invariant
- **Source memory** — `master-branch-carro-chefe-2026-08-28` (`C:\Users\mathe\.claude\projects\C--Users-mathe-code-space-life-oss-life\memory\master-branch-carro-chefe-2026-08-28.md`): canonical architecture statement (Deep Agent = carro-chefe, PAV desativado)
- **PAV legacy memory** — `legacy-pav-ui-era-2026-08-28` (`C:\Users\mathe\.claude\projects\C--Users-mathe-code-space-life-oss-life\memory\legacy-pav-ui-era-2026-08-28.md`): what was tried in the legacy era, why it was deprecated
