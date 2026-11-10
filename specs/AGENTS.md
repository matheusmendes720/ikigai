# AGENTS.md — `specs/`

**18 tracked files in 11 directories — created: distinct domain.** The specs are the
least derivable part of the tree: every other directory can be read off its code,
this one can only be read off its documents.

## OVERVIEW
`specs/` holds **18 tracked files across 11 directories**: one harness contract
(`harness/`), two feature tech specs (`data-layer/`, `miniapp/`), one planning set
(`production-readiness/`), and the seven skill projections the harness loads
(`harness/skills/`).

A spec here is a *contract* — goal, scope, acceptance — not a plan of record.
The plan of record lives beside the spec it plans (`production-readiness/TECH.md`
and `ROADMAP.md`).

The milestone corpus that used to live here (`specs/M<NNN>-<slug>/`) is
**unpublished, not deleted** (ADR-037 §"publicação independente"). It stays on
the owner's disk and in the git history.

## STRUCTURE
```
specs/
├── AGENTS.md
├── data-layer/TECH.md                 # ADR-037 data-layer tech spec (R1 approved)
├── harness/SYSTEM-PROMPTS.md          # the prompt set, one per role
├── harness/SKILL-SPECS.md             # the skill contracts, one per routine
├── harness/router.md                  # the dispatch table: what lives where
├── harness/skills/<id>/SKILL.md       # 7 projections the harness loads
│   ├── daily-note · weekly-review · monthly-review · quarterly-plan
│   └── store-read · store-write · vault-sync
├── miniapp/TECH.md                    # the panel inside the Telegram (ADR-044)
└── production-readiness/
    ├── PRODUCT.md                     # what the product is, and its measured state
    ├── TECH.md                        # the plan that closes the measured gap
    └── ROADMAP.md                     # the planning tree, the graph, the gates
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **What the product is, and how ready it is** | `production-readiness/PRODUCT.md` | the behaviour invariants `B1`–`B10` and the readiness matrix, measured |
| **How the gap gets closed** | `production-readiness/TECH.md` | the plan, the inventory, the falsifiable PASS of every step |
| **What runs in which order** | `production-readiness/ROADMAP.md` | the BRD→PRD→SPEC→ADR→TECH→Tasks tree, the gates `G1`–`G5` |
| The harness contract | `harness/router.md` | how an agent finds its prompt, its skill and its cadence |
| The prompts, one per role | `harness/SYSTEM-PROMPTS.md` | the roles a cold agent can hold |
| The skill contracts | `harness/SKILL-SPECS.md` | the routines; the three engineering skills have no projection |
| The canonical data-layer contract | `data-layer/TECH.md` | ADR-037 anchored; written before the scope cut |
| The panel inside the Telegram | `miniapp/TECH.md` | the three routes, the credential, and how the proof is read |
| Why a decision was made | `code-docs/adr/ADR-0*.md` | ADR-037 is the current scope decision |

## CONVENTIONS
- **The projection is the source; the copy is runtime state.** `harness/skills/`
  is the source of truth for the routine text, and `.pi/skills/` is the copy the
  harness loads. A drift test holds them byte for byte.
- **`SKILL-SPECS.md` wins.** When the projection and the skill specs disagree,
  the specs are the contract and the projection is the stale copy.
- **The three engineering skills have no projection.** `contract-change-drift-test`,
  `ci-green-gate` and `release-deploy` act on the repository rather than on the
  store, so they live in `SKILL-SPECS.md` only.
- **One document per level of the planning tree.** A `PRODUCT.md` holds behaviour,
  a `TECH.md` holds the implementation plan, a `ROADMAP.md` holds the sequence.
  The plan references the behaviour by its invariant number instead of restating
  it.
- **Every step carries a falsifiable PASS.** A step without one is an intention.

## ANTI-PATTERNS
- **Never let a spec describe a tree the branch does not publish.** This file
  used to describe 101 files across 95 milestone directories and a tracker under
  `.claude/loop/` — none of it published since the scope cut. A cold agent that
  reads a stale spec looks for files that are not there.
- **Never read a milestone spec as a live dependency.** They are historical
  documents: several still name files that ADR-037 unpublished. Read them as a
  record of intent.
- **Never publish a plan as if it were a contract.** A `PRODUCT.md` says what
  the product does; the validation lives in the `TECH.md`. Mixing them makes
  both unusable.
- **Never invent a milestone number.** The sequence skips freely; take the next
  free id from the tracker, not from the previous directory name.
- **Never prune a finished spec.** The corpus is kept as history. Retire a
  document with a successor, not with a delete.
