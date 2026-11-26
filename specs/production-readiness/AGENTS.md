# AGENTS.md — `specs/production-readiness/`

**Score 9 — distinct domain: the plan of record.** What the product promises,
how far it actually is, and the ordered plan that closes the gap.

## OVERVIEW
Three documents, one per level of the planning tree, all in PT-BR.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| What the product promises | `PRODUCT.md` | invariants `B1`–`B10`, each with today's measured state |
| What the suite proves — and what it does not | `PRODUCT.md` §3.3 | read before claiming readiness |
| How far from daily production the system is | `PRODUCT.md` §4 | the distance, measured |
| The plan that closes the gap | `TECH.md` | stack, inventory with reasons, day zero, steps with a falsifiable PASS |
| What runs in which order | `ROADMAP.md` | the BRD→PRD→SPEC→ADR→TECH→Tasks tree, the graph, the gates `G1`–`G5` |
| The holes in the planning tree | `ROADMAP.md` §1 | the BRD, the pre-cut specs, the tasks, the missing ADRs |
| The ADR the plan still owes | `ROADMAP.md` §1.4 | `ADR-038` is reserved for the single-player store |

## CONVENTIONS
- **One document per level of the tree.** `PRODUCT.md` holds behaviour, `TECH.md`
  the implementation plan, `ROADMAP.md` the sequence. A plan references
  behaviour by its invariant number (`B2`) instead of restating it.
- **The state column is a measurement, not a wish.** `PRODUCT.md` marks every
  invariant `provado` / `parcial` / `não provado` and cites the file and line
  that proves it.
- **Measured facts carry their date** ("medido na caixa, 2026-11-10"). A
  measurement without a date is a claim.
- **Every step carries a falsifiable PASS.** A step without one is an intention.
- **Negative results are kept.** A gate that failed, and the reason it failed,
  stays in the document.
- **PT-BR.** These three documents are written in Portuguese; the harness
  subtree is English.

## ANTI-PATTERNS
- **Never publish a plan as if it were a contract.** `PRODUCT.md` says what the
  product does; the validation lives in `TECH.md`.
- **Never read the ROADMAP as a live dependency.** It names `sys_ikigai/`,
  `src/mesh/` and `interfaces-cli` as what the cut removed — none of them are
  in the published tree.
- **Never skip a gate.** G1 (the store accepts the schema) precedes G2 (the
  prose lands) precedes G3 (the harness runs a real routine); no client before
  the data layer.
- **Never call the product ready because a suite is green.** A suite that did
  not run is not a passing suite, and `PRODUCT.md` §3.3 names what the suite
  does not prove.
- **Never invent a milestone id.** Take the next free id from the tracker, not
  from the previous directory name.
