# Interpretability Contract — Design Plan

**Date:** 2026-11-25
**Status:** draft
**Anchor:** ADR-037 D2 ("one DOM, N projections") · `strategics/Hierarquia de Objetivos.md:157-163`
**Companion:** `2026-11-25-observability-infrastructure.md`

---

## 1. The problem

The agent speaks in kinds and UEIDs. The owner thinks in 5 levels:
Sonhos→Objetivos→Metas→Tarefas→Atividades. A census of the owner's outputs
shows `fas:b3:957f…` and `kinds=(plano, onda, okr, kpi)` — internal machinery,
never once naming the strategic vocabulary. The weekly-review skill writes a
`revisao` artifact and reports "counts per class" in kinds. The daily-note
reports tool receipts. The converse skill is closest — it answers in prose —
but even it names UEIDs inline without translating them.

**This is not a data problem.** The DOM has the right structure for the store.
But the agent's response contract — what every output says and in what
vocabulary — was never designed. The current contract is the tool receipt.

## 2. The mapping: 10 DOM kinds → 5 strategics levels

The mapping is NOT 1:1. Several DOM kinds are evidence, not entities at a
strategic level. The mapping groups kinds by their strategic function:

| DOM kind | Strategics level | Rationale |
|---|---|---|
| `sonho` | **Sonho** (6–12 meses) | Direct — the kind IS the level |
| `plano`, `onda`, `okr` | **Objetivo** (15 dias) | The plan, the wave and the OKR are the three forms an objective takes in the DOM: quarterly framing, 15-day cycle, and measurable sub-goal |
| `fase` | **Objetivo** (15 dias) | A phase is a row inside a plan — it is part of the objective's articulation, not a separate entity |
| `revisao`, `kpi` | **Meta** (semana) | The weekly review and the indicator are the two instruments of the weekly meta: the qualitative (review) and the quantitative (KPI) |
| `tarefa` | **Tarefa** (5 dias) | Direct — the kind IS the level |
| `nota` | **Atividade** (diário) | Direct — the daily note IS the activity level |
| `desc` | **Evidência** (cross-level) | A decision is evidence ABOUT a level, not an entity AT a level — it attaches to whichever strategic entity it decides about |

**Why `desc` is evidência, not a level.** A decision ("archive PAV kernel") is
always ABOUT something — a dream, a plan, a wave. It is a fact that qualifies
its target, not a thing that stands alone. The mapping treats it as evidence
that the renderer attaches to the entity it relates to, via the `REFERENCES`
edges already in the store.

**Why `fase` is Objetivo, not a separate level.** A phase is the rows inside a
quarterly plan — `Planejamento (Estratégico e Tático).md` calls them "macro
fases." They exist AT the quarterly granularity, as the decomposition of a
plan. Rendering a `fase` as a standalone entity without its parent `plano`
would lose the quarter context that gives it meaning.

## 3. The response contract

Every agent output that reports on the store follows a template with four
required sections and one optional one. The template is a **contract on the
skill**, not on the DOM — the DOM stays exactly as it is.

### Required sections

**1. Strategic chain** — one line per entity, naming the full chain:

```
**Sonho**: [nome do sonho] — Q4-2026 → Objetivo: [plano / onda / okr] → Meta: W47 — [status]
```

The chain is read from `parent_uid` edges: the note's parent is the task, the
task's parent is the meta, the meta's parent is the objective, the objective's
parent is the dream. The query walks the graph; the renderer collapses it into
one line.

**2. Temporal range** — one line situating the fact in its cycle:

```
**Janela:** Q4-2026 · W47 (17–23 Nov) · 3 de 5 dias úteis
```

The quarter comes from the artifact's `quarter` field. The week is derived
from `created_at`. The "N de M dias" is arithmetic over the notes that
reference this task.

**3. Strategic lens** — one word per entity: `#estratégico`, `#tático`, or
`#operacional`, per `Análise (Tático e Operacional).md`:

| Level | Lens |
|---|---|
| Sonho | `#estratégico` |
| Objetivo | `#estratégico` (quarter) / `#tático` (wave) |
| Meta / Tarefa | `#tático` |
| Atividade | `#operacional` |

The lens is NOT stored in the DOM. It is derived from the level, by the
renderer, at output time. A level that maps to two lenses (Objetivo) splits by
temporal scope: quarterly → estratégico, 15-day → tático.

**4. Next concrete action** — one line per entity, with estimated cost:

```
**Próxima ação:** reescrever a fase B3 com o escopo novo · ~15 min · antes da W48
```

The action is what the entity's body says is the next step. The cost is the
owner's own estimate from the prose. The deadline is the end of the current
cycle. When the prose does not state a next action, the renderer says
"aberto — a prosa não nomeia o próximo passo."

### Optional section

**5. Semiotic subtext** — when the data carries a tension the numbers alone
don't surface. The converse skill already does this well ("a parte feia não é o
bookkeeping — é que só uma fase tem hipótese de fechar"). The other skills
include it when the classification (done/partly/not started/dropped) reveals a
pattern worth naming. This is the agent's judgment, not a template slot.

### What gets HIDDEN

UEIDs, revision numbers, tool names, and `duration_ms` move to an optional
"detalhe técnico" block — collapsible, or at the end of the message, folded
under `(📋)`. The owner taps to expand if they want the receipt. The default
view is the 5 levels, in their vocabulary.

## 4. Where each piece lives

| Piece | Where | What changes |
|---|---|---|
| **Kind→level mapping** | `specs/harness/router.md` §4 (new section) | A table, `rules that hold across every role` |
| **Response template** | `specs/harness/SKILL-SPECS.md` (new `§Response Contract`) | The four required sections, with examples |
| **Skill "Report" step** | `.pi/skills/*/SKILL.md` — the final step of each skill | Replaces "Report the uid, counts per class, tools" with "Render per the response contract" |
| **Strategic chain (graph walk)** | The agent reads `parent_uid` edges at query time | The query already filters; the chain adds one `get_artifact` per parent |
| **Lens derivation** | The renderer, in the agent's output step | Logic in the skill: `if level == "Sonho": lens = "#estratégico"` |
| **Bot renderers** | `src/bot/main.py:_render_routine` | Adds the collapsible `(📋)` block; passes through the rich Markdown |
| **Strategics prose** | `strategics/Hierarquia de Objetivos.md` | No change — it IS the canonical vocabulary, already written |
| **DOM** | `src/contracts/dom.py` · `dom_kinds.py` | **No change.** The mapping lives outside the contracts. |

## 5. Migration path

The migration is a rewrite of skill output steps, not of data structures. It
can be done one skill at a time, with no flag day.

**Step 1: Add the kind→level table to router.md.** One section, 10 rows. Anchors
the vocabulary for every skill that follows.

**Step 2: Rewrite weekly-review "Report" step (step 7).** The review already
classifies each planned item; adding the strategic chain per item is one extra
`get_artifact` per parent_uid. The counts change from "3 done, 1 partly" to "3
done, 1 partly — dos 4 objetivos do Q4-2026, 3 estão no prazo."

**Step 3: Rewrite daily-note "Report" step (step 6).** Same pattern: each task
classified gets its chain. The note already carries EVIDENCES edges; the chain
reads the task's parent to name the meta.

**Step 4: Rewrite converse grounding (step 2).** When the agent cites a uid, it
also names the chain: "o **Sonho BYD** → **Objetivo: caso de 4 cenários** →
**Meta W47: revisão da simulação** diz que…"

**Step 5: Add the collapsible receipt to `_render_routine`.** The bot already
sends rich Markdown; the receipt goes into a `<details>` block at the end.

**What breaks if we don't do this:** Nothing breaks in the data plane. The store
keeps working. The agent keeps producing outputs. But the owner continues to
see UEIDs and kinds instead of their own vocabulary — and the gap between "o
sistema funciona" and "eu consigo LER o que ele produz" stays open. That gap is
the one documented in `PRODUCT.md` §0.1.

## 6. Falsifiable PASS

**PASS 1 — vocabulary guard.** A test reads every skill's `SKILL.md` and
asserts that the "Report" / "Output" step names at least one of the 5
strategics levels (`Sonho`, `Objetivo`, `Meta`, `Tarefa`, `Atividade`) and
does NOT name any DOM kind (`sonho`, `plano`, `onda`, `fase`, `revisao`,
`nota`, `kpi`, `desc`, `okr`, `tarefa`) in the user-facing output instructions.

**PASS 2 — renderer guard.** A test calls `_render_routine` with a mock agent
output that includes a UEID and asserts the output does NOT contain a UEID.
The pattern is **imported from `src.contracts.common._UEID_PATTERN`** — the ONE
canonical source (ADR-014) — never re-typed here. (The earlier draft regex
`[a-z]{3}:[a-f0-9]{8}:[a-f0-9]{16}` was wrong: it dropped the slug segment and
fixed the namespace at 3 chars; the canonical namespace is `{2,8}` and the form
is `type:slug:uuid:hash`.)

**Falsification for PASS 1:** Add `kinds=(plano, onda)` to a skill's output
instructions → the guard fails and points to the skill.

**Falsification for PASS 2:** Include a raw UEID in the mock output → the guard
fails and names the UEID.

## 7. What this is NOT

- **Not a second DOM.** The store keeps kinds. The mapping is a projection, not
  a schema change. ADR-037 D2 holds.
- **Not an LLM responsibility.** The mapping is a fixed table, applied by the
  renderer, zero model tokens spent on it. The count is arithmetic; the mapping
  is a lookup.
- **Not a bot-only change.** The skills are the primary target. The bot
  renderer is the last mile.
- **Not a flag day.** Each skill migrates independently. Old outputs still
  work; new outputs are richer.

---

## 8. Drill-down refinements (agent, 2026-11-25)

Refinements after reading the canonical sources (`common.py`, `dom.py`,
`repository.py`, `sync.py`, the skills, and the companion plan). Each closes a
gap that would otherwise make a PASS unfalsifiable or a renderer lie.

### 8.1 The companion's provenance guard rests on a false premise

`2026-11-25-observability-infrastructure.md` §1 claims "`_update` sets
`client_id` too". **It does not.** `repository._update` writes title, body,
body_hash, parent_uid, quarter, status, vault_path, kind, created_at,
updated_at, revision, embedding — but NOT `client_id`. So `artifacts.client_id`
holds the **creator's** id forever, not the last writer's. The companion's
guard `existing.client_id != "vault-sync"` therefore would NOT fire for an
artifact the vault created and a client later edited — exactly the W47 case.

**Resolution adopted for the Q1 fix:** read provenance from
`ikig.artifact_revisions` (append-only, records the correct `client_id` per
write via `_insert_revision`), not from `artifacts.client_id`. A new reader
`ArtifactRepository.last_revision_by_client(uid, client_id)` returns the latest
vault revision; if the file's hash equals that revision's `snapshot.body_hash`,
the vault is unchanged and a divergent store body is a client edit → skip. No
migration, no spine change, no write-path change. The companion's broader
observability scope (correlation_id, wiring refactor, NOTIFY payload) remains a
valid **separate** track — but its guard premise must be corrected first.

### 8.2 Level ≠ Range — `plano` is quarter-scoped

The §2 table labels `plano` as "Objetivo (15 dias)", but `plano` is the
**quarterly** plan (`01-plano-trimestral`). The hierarchy LEVEL (where a thing
sits in the decomposition) and its temporal RANGE (the cycle it spans) are two
axes, and the renderer must state both. `plano` sits at the objective
articulation but spans the quarter; `onda` spans 15 days. The §3 lens table
already splits Objetivo by scope (quarter → estratégico, wave → tático); the
mapping table should carry the range explicitly so a `plano` is never rendered
as a 15-day entity. **Rule:** level comes from the kind→level table; range comes
from the artifact's `quarter` + `created_at`/cycle, never from the level alone.

### 8.3 The strategic chain is bounded, and degrades honestly

The chain walk (§3.1) follows `parent_uid` edges. Two realities:

- **Bound it.** Walk at most 5 hops (the 5 levels), cycle-safe (a `seen` set,
  like `RelationService.traverse`). A graph that points back at itself must
  terminate, not loop.
- **Degrade, don't invent.** `parent_uid` is sparsely populated in the real
  corpus (the W47 outputs show mostly `REFERENCES` edges, not parent chains).
  When a link is missing, the renderer names what it knows and marks the rest
  `sem vínculo` — it never fabricates a parent. The chain's completeness is a
  **data-quality** property, not a renderer guarantee; surfacing `sem vínculo`
  is itself a signal that the hierarchy needs edges written.

### 8.4 Telegram has no native collapsible block

§3.5 proposes a `<details>` fold for the receipt. Telegram Markdown (and
`sendRichMessage`) has **no** `<details>` element. The honest implementations
are: (a) the receipt as a **separate follow-up message**, or (b) a truncated
tail with a `/detalhe <uid>` command that fetches the full receipt on demand.
Pick (b) for the default view (one clean message; the owner pulls the receipt
only when wanted). This is the same rendering surface as the owner's original
interpretation complaint — the receipt must not ride inline by default.

### 8.5 PASS 1 must be case-sensitive and step-scoped

- **Case-sensitive.** The strategic vocabulary is capitalized (`Sonho`,
  `Objetivo`, `Meta`, `Tarefa`, `Atividade`); the DOM kinds are lowercase
  (`sonho`, `plano`, …). `Sonho` ≠ `sonho`. A case-insensitive guard would flag
  the correct vocabulary as a violation.
- **Scope to the output step.** Skills legitimately name kinds in their QUERY
  steps (`search_artifacts kinds=(plano, onda)`). PASS 1 must isolate the
  "Report"/"Output" step (the user-facing instruction), not scan the whole
  SKILL.md — otherwise every skill fails on its own search step.

### 8.6 Sequencing against the fixes

This contract is the **projection** layer; it depends on a trustworthy store.
Order: Q1 provenance guard (stop the clobber) → Q2 kinds filter (unblock the
review queries) → this contract's skill rewrites (the owner can finally READ
the output). The census (§4 of the prior analysis) is the first read-only
proof that the chain + level vocabulary renders against real data.