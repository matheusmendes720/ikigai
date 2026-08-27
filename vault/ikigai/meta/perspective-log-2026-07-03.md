# Perspective Log — 2026-07-03 — IKIGAi Vector Weight Mechanism

> **Session goal.** User chose Option C (defer) for the IKIGAi vector weight mechanism
> question. Three options + trade-offs + migration paths captured here for the code-first
> phase (post-5+ SONHOs).

---

## The question (the user's own meta-reflection)

SONHO template `00-sonho.md` carries 5 IKIGAi vectors (P, S, M, R, C) with equal weights
(0.20 each, Σ = 1.0). For real-world SONHOs, certain vectors will dominate:

- *"Get a remote job"* → **Revenue** dominates (proposed 0.40)
- *"Learn guitar"* → **Course** dominates
- *"Reduce stress"* → **Passion** dominates

User reflection (verbatim, 2026-07-03):
> *"se nao deveria adicionar um sonho pricipal, para manobrar os pesos afim de concentrar
> uma hierquia mais ordenada tornando o maior peso do ikigai vector, aquilo que tange a
> vida financeira/professional"*

Translation: "should I add a principal SONHO, to maneuver the weights in order to
concentrate a more ordered hierarchy, making the highest IKIGAi vector weight touch the
financial/professional life."

**This is structurally significant** — it touches the SONHO schema, the propagation to
TRIM/ONDA/SEMANA/DIA, and the IKIGAi vector scoring in `core/ikigai_scorer.py`.

---

## 3 options + trade-offs

### Option A — Add `principal_vector` field

```yaml
principal_vector: revenue              # single dominant (rank-1)
vector_weights:                        # asymmetric distribution
  R: 0.40
  S: 0.25
  M: 0.20
  C: 0.10
  P: 0.05
```

**Pros:**
- Explicit — schema forces declaration of dominance + distribution
- Tooling reads `principal_vector` for ranking/filtering (no argmax inference)
- Clean propagation: if Revenue is principal, the ONDA can target Revenue-boosting tasks
- Self-documenting: a reader sees intent instantly

**Cons:**
- Refactor Protocol required (template edit, possibly back-propagation)
- Adds 2 fields to schema (more cognitive load at fill time)
- Implicit hierarchy: `principal_vector` is RANK, `vector_weights` is DISTRIBUTION —
  could conflict if not aligned
- Risk: principal_vector hard-coded as enum (P|S|M|R|C) loses future flexibility

**Migration cost:** ~8 template edits + persona re-run + ADR-008 + 1 code refactor in
`core/ikigai_scorer.py` + back-propagation test (TRIM inherits from SONHO)

### Option B — Asymmetric weights, no principal field

```yaml
vector_weights:                        # Σ must = 1.0, free distribution
  R: 0.40
  S: 0.25
  M: 0.20
  C: 0.10
  P: 0.05
```

**Pros:**
- No new field — schema already supports asymmetric YAML
- Maximum flexibility (any vector can dominate)
- Simpler to fill (just weights, no separate ranking)
- One source of truth (weights carry both distribution AND ranking via argmax)

**Cons:**
- Tooling can't easily identify "the principal vector" without `argmax(vector_weights)`
- 5 weights to declare vs 1 principal + 5 weights (more numbers to think about)
- Less explicit about intent (reader has to scan all 5 to find dominance)
- Validation needed: Σ must = 1.0 (schema constraint)

**Migration cost:** ~3 doc edits (template example + persona re-run + ADR-008)
+ 1 code refactor (validator + scorer read weights)

### Option C — Defer until 5+ SONHO logs (CURRENT CHOICE)

```yaml
# SONHO has equal weights implicitly (P=0.20, S=0.20, M=0.20, R=0.20, C=0.20)
# Asymmetry emerges from practice, not from schema
# Revisit after 5+ real SONHOs with explicit user reflection
```

**Pros:**
- ADR-007 data-first — code emerges from practice, not theory
- Zero migration cost now (no schema change)
- After 5 logs: empirical evidence of whether asymmetry is the norm or exception
- Avoids premature design (YAGNI)

**Cons:**
- Real SONHOs with Revenue=0.40 intent will have to "fake" equal weights
- Q5 SIGNALS computation becomes ambiguous (which vector matters?)
- IKIGAi vector scoring loses signal (everything looks equally important)
- The user must hold the asymmetry in their head, not the template

**Migration cost:** 0 now; revisit when 5+ SONHOs logged

---

## Decision: Option C (defer)

User chose C on 2026-07-03, verbatim:
> *"ainda nao vamos mexer em nada tecnicamente.. vamos loggar tambem essa questao em
> perspectiva & append os trade offs, vantagens de cada uma dessas opcoes na sessao dos
> backlogs de codigos que temos referente a esse aspecto do sistema.... vamos nos manter
> no data-first por enquanto... essa eh maior questao que preciso estruturar o quanto
> antes.. por enquanto esses detalhes algorimos nao faz tanta diferenca enquanto nao
> tivermos o nosso dataset pronto com todos os templates de operacao.... pois o codigo
> deve sempre emergir apartir dos dados!"*

Translation: "let's not touch anything technically yet.. let's log this question in
perspective & append the trade-offs, advantages of each option in the code backlog
session for this system aspect.... let's stay data-first for now... this is the biggest
question I need to structure as soon as possible... for now these algorithm details
don't matter much until we have our dataset ready with all operation templates... because
code should always emerge from data!"

**Why this matters structurally:** The user noted that for the SONHO "get a remote job",
Revenue (R) should carry 0.40 weight (vs 0.20). The current template forces equal weights.
This is the second-highest priority structural question after the IKIGAi v3 schema alignment
(see N01 in `algorithm-issues-registry.md`).

---

## Revisit trigger

After **5+ SONHOs logged** with explicit user reflection on whether asymmetry was the right
call (and what weight they intuitively wanted), open ADR-008 with empirical evidence.

Per-SONHO informal annotation: if user fills a SONHO and explicitly says "this one is
Revenue-heavy", add an `_intent_vector` annotation field (informal, NOT schema) and log the
asymmetry as evidence. Format:

```yaml
_intent_vector: revenue      # informal, not validated, signals user mental model
vector_weights: [equal]      # formal, schema-equal
```

This lets us collect asymmetry evidence WITHOUT touching schema.

---

## Migration path (if Option A chosen later)

1. Edit template `_templates_periodos_v2/00-sonho.md` — add `principal_vector` and asymmetric
   `vector_weights` fields to frontmatter + section 5
2. Re-fill Marina persona `00-sonho_example.md` with weighted values
3. Add new section to `code-docs/ikigai/ikigai-as-dom-on-planning-engine.md` documenting the
   weight semantics
4. Update IKIGAi vector scoring in `life-ops/operational/packages/core/src/operational/core/ikigai_scorer.py`
   (or equivalent) to read new field — fall back to argmax(vector_weights) if principal absent
5. Re-run all 5+ SONHOs through the new scorer
6. Add hysteresis: principal_vector cannot change mid-quarter without ADR
7. ADR-008 documents the schema change + back-propagation test results

**Estimated effort:** 1 session (Refactor Protocol applies)

---

## Migration path (if Option B chosen later)

1. Edit template `_templates_periodos_v2/00-sonho.md` example section to show asymmetric
   weights with Σ=1.0 validation rule
2. Re-fill Marina persona with weighted values
3. Add Σ=1.0 validator to Pydantic schema
4. Update IKIGAi vector scoring to read weights (currently assumes equal)
5. Add helper: `principal = argmax(vector_weights)` if no explicit principal
6. ADR-008 documents the schema change

**Estimated effort:** Half session (Refactor Protocol applies)

---

## Related backlog items

- `.omo/ikigai/meta/algorithm-issues-registry.md` → **N01** (5 vs 4 vectors — README vs
  templates vs code) and **D02** (SCALAR path `life/vibe-ops/src/` vs `life-ops/operational/`)
- `vibe-ops/src/pipeline/SCALAR_DECOMPOSITION_BACKLOG.md` (35 items) — needs search for
  IKIGAi weight entries
- `code-docs/ikigai/ikigai-as-dom-on-planning-engine.md` — mathematical spec (sampled
  earlier; not re-read here)

---

## Files created this session

| Path | Action |
|------|--------|
| `.omo/ikigai/meta/perspective-log-2026-07-03.md` | CREATED — this file |

No edits to other files. No commits. Data-first methodology honored.

---

*Perspective log v1 · 2026-07-03 · IKIGAi Sys-01 · Cluster PLAN · decision deferred,
trade-offs captured, migration paths documented.*