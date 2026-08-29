# Algorithm Attribution Decisions — Pending Adjudication

**Date:** 2026-08-29
**Status:** PENDING — awaiting user adjudication per attribution report
**Source:** `docs/architecture/2026-08-29-attribution-report.md` §4
**Spec:** `docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md`

---

These 5 decisions are captured here for future adjudication. **No
algorithm code changes** are tied to any of them. Each DEC has a
recommendation but the recommendation is **not yet binding**.

---

## DEC-01 — Sync frequency IKIGAI ↔ PAV

**Question:** How often should the IKIGAI agent pull fresh PAV state
(habit streaks, Q_HE, regime) into its planning context?

**Options:**
- **A:** Daily + `--sync-now` (explicit on-demand trigger)
- **B:** A cada hábito (every habit event triggers sync)
- **C:** On-demand only (no schedule, manual trigger)

**Recommendation:** **A** (Daily + `--sync-now`)

**Rationale:**
- Daily gives the agent fresh context for the next planning cycle
  without flooding PAV with read requests
- `--sync-now` allows operator override when telemetry shows stale data
- B would over-trigger (every habit logged = MCP call)
- C would leave the agent blind unless operator remembers to sync

**Blocker:** none

---

## DEC-02 — Bridge mechanism (PAV → IKIGAI)

**Question:** How does PAV state (habits, Q_HE, regime) cross into the
IKIGAI agent's working context?

**Options:**
- **A:** PAV writes directly to vault
- **B:** MCP via vault-journal (Phase 6b desenho)
- **C:** IKIGAI reads PAV store directly

**Recommendation:** **B** (MCP via vault-journal)

**Rationale:**
- A would violate vault write invariant (§7 of attribution report) —
  PAV is not a vault writer
- C couples the deep agent to PAV's storage format — bad for
  portability if PAV evolves
- B reuses the existing `vault_write` MCP tool, keeps the single
  writer invariant, and the vault-journal pattern is already designed
  in Phase 6b

**Blocker:** Phase 6b desenho (vault-journal pattern needs to be
specified in a future design doc)

---

## DEC-03 — Linkage hábito ↔ entregável

**Question:** How does a PAV Habit link to an IKIGAI Deliverable?

**Options:**
- **A:** Tag IKIGAI (Deliverable.frontmatter.tags contains "habit-ueid")
- **B:** PAV `Habit.ikigai_ueid` field (FK to Deliverable.ueid)
- **C:** Híbrido (tag for fast query + FK for canonical link)

**Recommendation:** **C** (Híbrido)

**Rationale:**
- Tag (A) is fast for grep/MOC queries but is stringly-typed
- FK (B) is canonical but requires schema change to PAV
- Hybrid (C) gets query speed of tag + canonical integrity of FK
  without forcing PAV schema change in this design

**Blocker:** none (PAV schema change is independent of this DEC)

---

## DEC-04 — Native CLI/TUI B2 gerencia PAV?

**Question:** Should the native server-management CLI (B2) include
PAV process management?

**Options:**
- **A:** Sim (B2 manages all backend processes including PAV)
- **B:** Não (B2 explicitly excludes PAV)
- **C:** Só quando PAV reviver (B2 only adds PAV management after
  PAV is revived from desativado)

**Recommendation:** **C** (Só quando PAV reviver)

**Rationale:**
- PAV is desativado per [[legacy-pav-ui-era-2026-08-28]] and
  [[pav-as-ikigai-subsystem-2026-08-28]]
- B2 currently manages IKIGAI backend services only — adding PAV
  management code is YAGNI until PAV revives
- C is the YAGNI minimum: when PAV revives, add the management then

**Blocker:** PAV desativado (DEC resolves when PAV revival happens)

---

## DEC-05 — Deep agent boundaries

**Question:** What can the IKIGAI deep agent do with respect to PAV
and other backend services?

**Question decomposed:**
- Lê PAV store? → **Sim** (via MCP or vault-journal per DEC-02)
- Escreve vault? → **Sim, mas via `vault_write` MCP tool only** (per
  attribution report §7 invariant)
- Invoca B5 agent consumer? → **Sim** (produtor natural — IKIGAI is
  the deep agent that produces TaskChanges for B5 to validate and
  propagate)

**Recommendation:** as decomposed above

**Blocker:** none

---

## Adjudication process

When user is ready to adjudicate:

1. Open this file
2. For each DEC, mark the chosen option with `[x]`
3. Note any rationale that supersedes the recommendation
4. Commit the adjudication
5. If adjudication requires code changes, file a new design doc
   (separate from this attribution design)
6. Memory: update or supersede `algorithm-attribution-decisions-2026-08-29.md`

**No algorithm code change is bound to these DECs.** Even if all 5
DECs are adjudicated, the revival criteria in the spec still gate
when algorithm code actually revives.

---

## Related

- Attribution report §4: `docs/architecture/2026-08-29-attribution-report.md`
- Spec: `docs/superpowers/specs/2026-08-29-algorithm-attribution-design.md`
- Locked decisions: master-branch-carro-chefe-2026-08-28,
  pav-as-ikigai-subsystem-2026-08-28,
  algorithm-gate-system-readiness-not-sonho-2026-08-29
