# AGENTS.md — `specs/harness/`

**Score 11 — distinct domain: the harness contract.** The contract the external
`pi` harness is written against, plus the seven skill projections it loads.

## OVERVIEW
The dispatch table, the role prompts, the skill contracts, the runtime routing,
and the portable projection of the seven runtime skills.

## STRUCTURE
```
specs/harness/
├── router.md                # the dispatch table — a cold agent's entry point
├── SYSTEM-PROMPTS.md        # 8 role bootstrapping prompts, one per section
├── SKILL-SPECS.md           # 10 skill contracts (7 projected + 3 engineering-only)
├── SESSIONS.md              # runtime, routing table, question tool, channel, panel
├── CHAINED-ROUTINES.md      # router → session → routine → synthesis → HITL
└── skills/<id>/SKILL.md     # the 7 published projections
    daily-note · weekly-review · monthly-review · quarterly-plan
    store-read · store-write · vault-sync
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Find your prompt, your skill, your cadence | `router.md` | the reading order for a cold agent |
| The role you are bootstrapping | `SYSTEM-PROMPTS.md` | 8 roles, one per section |
| The contract of a routine | `SKILL-SPECS.md` | wins over the projection |
| What the harness actually loads | `skills/<id>/SKILL.md` | source of truth; `.pi/skills/` is the copy |
| Routing, the blocking question, the panel | `SESSIONS.md` | the runtime table, the `ask` tool, failing closed |
| The five stages of a run | `CHAINED-ROUTINES.md` | the router is deterministic first, the model second |
| The vocabulary the routine reasons in | `strategics/` (via `router.md` §3) | each skill names its conceptual source |

## CONVENTIONS
- **The projection is the source; `.pi/skills/` is runtime state.** A drift test
  holds the two byte for byte (`src/ikigai/tests/test_drift_invariants.py`), so
  editing a projection is a behaviour change, not a wording change.
- **`SKILL-SPECS.md` wins.** When a projection and the specs disagree, the
  projection is the stale copy.
- **Fixed skill shape**: YAML frontmatter (`name`, `description`), title, an
  optional `## Conceptual source` naming a `strategics/` file, `## Contract`
  with the literal labels `Trigger:` / `Inputs:` / `Outputs:` / `Steps:`, then
  `## Invariants`, then `## Done when:`.
- **Descriptions are trigger-form** — "Use when …". That string is what the
  harness matches on.
- **The context wins over the clock.** The day comes from the run context
  (`date`), never from the system clock or the owner's timezone; it is also
  part of the note's uid and of its idempotency key.
- **The quarter is a filter, spelled quarter-year** (`Q4-2026`) — always search
  with it, or the search returns every plan in the store.
- **The cadence proportion**: five days of execution, three weeks of analysis,
  three months of planning; the `onda` is 45 days, the quarter 180.
- **English in this subtree.** `data-layer/`, `miniapp/` and
  `production-readiness/` are PT-BR.

## ANTI-PATTERNS
- **Never create a projection for the three engineering skills.**
  `contract-change-drift-test`, `ci-green-gate` and `release-deploy` act on the
  repository, not on the store, so they live in `SKILL-SPECS.md` only.
- **Never invent a skill id.** Seven are published; a new routine needs its
  contract in `SKILL-SPECS.md` before it has a projection.
- **Never let a cadence run ask the owner.** Nobody is watching: record what
  the evidence says and name what is missing.
- **Never write SQL from a skill.** Only `src/services/` writes the store.
- **Never read the search as the prose** (ADR-046): `search_artifacts` returns
  identity, `get_artifact` returns the body.
- **Never hand-build a uid.** The pattern has exactly one source,
  `src/contracts/common.py`.
