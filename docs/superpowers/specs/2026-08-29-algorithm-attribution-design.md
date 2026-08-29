# Algorithm Attribution Design — IKIGAI × PAV × Forks × Deep Agents × Backend

**Date:** 2026-08-29
**Status:** Approved (user greenlit via "sim" after proposal)
**Scope:** Documentation only. **Zero code touched.**

---

## Goal

Codify the attribution model that determines which system owns what,
so the deep agent reads `./strategics/` for business rules instead of
algorithm code, and the 31 catalogued algorithm issues stay archived
until empirical evidence demands revival.

## Architecture (1 paragraph)

The canonical business rules live in `./strategics/` PT-BR markdown
(the constitutional layer). The 4 IKIGAI scoring modules
(`src/ikigai/src/ikigai/core/scoring/{vector_scores,qhe,rice,meta_vector}.py`)
and 6 heuristic modules
(`src/ikigai/src/ikigai/core/heuristics/{regime,cross_priority,opportunity_fit,phase_pivot,skill_velocity,weight_ucb}.py`)
remain on disk but are archived-in-place (not moved, not imported by
production code, not executed). The deep agent reads `./strategics/`
markdown via a `vault_write` MCP tool that enforces append-only as the
single writer invariant. No algorithm code is added, modified, or
removed in this design.

## Tech Stack

N/A — documentation deliverable only.

## Global Constraints (verbatim from proposal)

- **Source of truth for instructions:** `./strategics/` PT-BR markdown
- **Algorithm code status:** archived-in-place per
  [[prioritize-backend-over-algorithm-refinement]] +
  [[algorithm-decisions-defer-2026-08-28]]
- **No code touched:** this design ships docs only
- **Vault write invariant:** all vault writes (deep agent + native
  CLI + forks) go through single `vault_write` MCP tool that enforces
  append-only
- **Algorithm gate respected:** system readiness gate met per
  [[algorithm-gate-system-readiness-not-sonho]] — backend+data+agent
  functional — but [[prioritize-backend-over-algorithm-refinement]]
  says "defer algorithm/template/registry polish until a real consumer
  demands it"

## Revival Criteria (when archived algorithm code revives)

An algorithm module may be revived (re-imported by production code,
modified, or replaced) only when ONE of the following is true AND
user adjudicates:

1. **Consumer demand:** A backend service or deep agent reads from
   this module's exports, AND the module produces incorrect/wrong
   values in real use. Symptom: failed test or operator report.
2. **Telemetry pain:** Telemetry from real SONHO/ONDA logs shows
   the algorithm output diverges from what the user wants. Symptom:
   measured mismatch in ≥5 consecutive observations.
3. **Day-to-day conflict:** User opens a planning cycle and finds the
   algorithm's behavior conflicts with their actual decision-making.
   Symptom: user override + complaint in cycle retrospective.

**Negative criterion:** "Algorithm is conceptually interesting" or
"Algorithm has clean math" is NOT a revival trigger. The
[[algorithm-decisions-defer-2026-08-28]] framework (reversibility +
telemetry + day-to-day conflicts) governs.

## Decisions Pending Adjudication (DEC-01..05)

Per the attribution report §4 — these are captured for future
adjudication, NOT decided in this design:

| DEC | Question | Recommendation | Blocker |
|---|---|---|---|
| **DEC-01** | Sync freq IKIGAI↔PAV | A: Daily + `--sync-now` | none |
| **DEC-02** | Bridge mechanism | B: MCP vault-journal (Phase 6b desenho) | Phase 6b desenho |
| **DEC-03** | Linkage hábito↔entregável | C: Híbrido (tag IKIGAI + PAV Habit.ikigai_ueid FK) | none |
| **DEC-04** | Native CLI/TUI B2 gerencia PAV? | C: Só quando PAV reviver (B2 só IKIGAI backend services) | PAV desativado |
| **DEC-05** | Deep agent boundaries | Lê PAV: sim; escreve vault: via MCP; invoca B5: sim (produtor natural) | none |

DEC-01..05 → moved to `docs/decisions/pending/algorithm-attribution-decisions.md`
for future adjudication. **No algorithm code change.**

## Vault Write Invariant (NEW per peer §7)

> **All vault writes go through `vault_write` MCP tool.**
>
> Whether the writer is a deep agent, the native CLI, or a fork
> (tuiboard, taskdog, solverforge-calendar), the path is the same:
> `vault_write` MCP tool → enforces append-only → emits
> `vault_event.json` for downstream observers (B6 sync daemon, audit).
>
> **Invariant único:** no other code path writes to vault/. This is
> enforceable at the MCP server level (rejects any non-`vault_write`
> write attempt) and at the vault filesystem level (`.gitignore` for
> vault/.db to prevent direct file mutation).

## Out of Scope (deferred)

- ❌ Modifying any algorithm code (scoring/, heuristics/, contracts/metrics.py)
- ❌ Restoring PAV CLI/TUI per [[legacy-pav-ui-era-2026-08-28]]
- ❌ Vector weight tuning — DEC pending per [[user-revenue-weight-preference]]
- ❌ New fork adapters beyond the 4 documented (tuiboard, taskdog,
  solverforge-calendar + native CLI/TUI control plane)
- ❌ Real-time conversation agents (IKIGAi mid-design per
  [[master-branch-carro-chefe-2026-08-28]])
- ❌ Multi-agent swarm (gated on IKIGAi backbone)

## Deliverables (3 artifacts)

1. **This spec** → `docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md`
2. **Attribution report** → `docs/architecture/2026-08-29-attribution-report.md`
   (the file user referenced — §0 mental model through §7 vault invariant)
3. **Memory** → `algorithm-attribution-decisions-2026-08-29.md` capturing
   DEC-01..05 + revival criteria

## Testing (N/A for docs)

No tests added — this design ships documentation only. The
attribution report will be reviewed for accuracy against
`./strategics/` content and the locked decisions in memory.

## Success Criteria

This design succeeds when:
- ✅ Attribution report at `docs/architecture/2026-08-29-attribution-report.md`
  exists and covers §0–§7 per proposal
- ✅ Spec committed to git with this content
- ✅ Memory file + MEMORY.md pointer for DEC-01..05 adjudication
- ✅ Zero algorithm code changed (verified by `git diff` showing only
  .md files added)
- ✅ User reviews and approves this spec before any further work

## Related Memory

- [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] — algorithm
  gate = system readiness (now met)
- [[algorithm-decisions-defer-2026-08-28]] — reversibility + telemetry
  + day-to-day conflicts
- [[prioritize-backend-over-algorithm-refinement]] — backend first,
  algorithm polish later
- [[master-branch-carro-chefe-2026-08-28]] — deep agent as carro-chefe
- [[pav-as-ikigai-subsystem-2026-08-28]] — PAV desativado como subsystem
- [[user-revenue-weight-preference]] — DEC-?? for weight decisions
- [[legacy-pav-ui-era-2026-08-28]] — PAV CLI/TUI abandoned 2026-08-26
- [[interfaces-architecture-2026-08-27]] — forks = user views, native
  = control plane
- [[backend-phase-reordering-2026-08-28]] — Phase B sequencing
