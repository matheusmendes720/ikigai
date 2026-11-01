# AGENTS.md — `specs/`

**Score 8 (101 tracked files in 100 directories, 98 `SPEC.md`, 53 inbound refs) — created: distinct domain.** The milestone-spec corpus is the least derivable part of the tree: every other directory can be read off its code, this one can only be read off its frontmatter.

## OVERVIEW
`specs/` holds **101 tracked files across 100 directories**: 95 milestone
directories (`specs/M<NNN>-<slug>/`) plus five feature directories whose entry
file is not a milestone spec. 98 files are named `SPEC.md`; the other three are
`data-layer/TECH.md`, `harness/SYSTEM-PROMPTS.md` and `harness/SKILL-SPECS.md`.

A spec here is a *contract* — goal, scope, acceptance — not a plan of record.
The tracker that consumes them is `.claude/loop/{roadmap.md,tasks.md}`; this
directory holds the document, not the state.

Two header contracts coexist. `specs/M*/SPEC.md` opens with YAML frontmatter;
`code-docs/specs/2026-*-spec-*.md` (a different subtree) uses a `>` blockquote
header and has no frontmatter. Never mix them inside one file.

## STRUCTURE
```
specs/
├── M<NNN>-<slug>/SPEC.md   # 95 milestone dirs — one spec each
├── agentic-markdown-system/SPEC.md
├── data-layer/TECH.md            # ADR-037 data-layer tech spec (R1 approved)
├── harness/SYSTEM-PROMPTS.md     # harness prompt set (360 lines, 2026-11-01)
├── harness/SKILL-SPECS.md        # harness skill set (376 lines, 2026-11-01)
├── period-reports-sync/SPEC.md
└── vault-bidirectional-sync/SPEC.md
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Canonical data-layer contract | `data-layer/TECH.md` | ADR-037 anchored; the R1 approval is recorded in its header |
| Harness prompts / skills | `harness/SYSTEM-PROMPTS.md`, `harness/SKILL-SPECS.md` | both written 2026-11-01 against ADR-037 |
| A shipped milestone | `M<NNN>-<slug>/SPEC.md` with `status: DONE` | 83 of the 94 frontmattered specs |
| Work still open | `status: PENDING` | 11 specs; `estimated_cost_usd` is the sizing signal |
| The tracker (not the spec) | `.claude/loop/roadmap.md`, `.claude/loop/tasks.md` | milestone and task ids live there |
| Why a decision was made | `code-docs/adr/ADR-0*.md` | ADR-037 is the current scope decision |

## CONVENTIONS
- **Frontmatter is the machine field.** `specs/M*/SPEC.md` carries `name`,
  `description`, `status`, `owner` and `constitution_refs` — all five on all 94
  frontmattered specs — plus optional `estimated_cost_usd` (67), `milestone`
  (44), `created` (33), `estimated_ticks` (16), `dependencies` (2), `shipped`
  (1). `name` equals the directory slug.
- **Closed vocabularies.** `status` ∈ {DONE, PENDING}; `owner` ∈
  {matheus-mendes, loop-orchestrator}; `constitution_refs` ∈ 7 values
  (`tests_are_the_contract` 82, `state_on_disk_not_conversation` 58,
  `correctness_over_speed` 41, `composition_over_inheritance` 37,
  `reversibility_over_cleverness` 36, `spec_driven_not_vibe_driven` 7,
  `multi_package_boundaries_are_sacred` 6).
- **Seven files carry no frontmatter**: the six feature-directory entries and
  `M159b-minimax-embeddings-probe/SPEC.md`. That is the pattern for a
  non-milestone document, not a missing key to add.
- **Body order** is frontmatter → `> Created / Owner / Status` blockquote →
  `## Goal` → scope and acceptance sections.

## ANTI-PATTERNS
- **Never read a spec's status from the body.** The blockquote repeats it and
  drifts; the frontmatter is the field tooling reads.
- **Never prune a finished milestone.** 83 DONE specs are still in the tree —
  the corpus is kept as history. Retire a document with a successor, not a
  delete.
- **Never invent a milestone number.** The sequence skips freely (M10, M142,
  M159b, M163…); take the next free id from the tracker, not from the previous
  directory name.
- **Never treat a PENDING spec as a live dependency.** Milestone specs are
  historical documents: M142/M143 still name `.claude/loop/mcp_bridge.py`,
  which was removed with the PC-only scope (ADR-037). Read them as a record of
  intent.
- **Never put both header contracts in one file** — a spec is either
  frontmattered (milestone) or blockquoted (feature document).
