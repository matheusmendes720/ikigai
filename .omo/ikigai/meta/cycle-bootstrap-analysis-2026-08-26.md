# Cycle Bootstrap Analysis — 2026-08-26

> **Source:** IKIGAI agent first cycle output on bootstrapping state.
> **Purpose:** Explain every field in context of INNER GUIDELINES (strategics/ constitutional layer).

---

## The Output

```
✅ Plan cycle complete
   Regime: MAINTAIN  |  Q_HE: 0.6500  |  Meta: 39.9439
   Vectors: 5 scored
   Corrections: 0  |  Prospective: 4  |  Retrospective: 2
```

---

## Field-by-Field Analysis

### Regime: MAINTAIN

**Constitutional source:** INNER GUIDELINES §4 REGIMES (Assimetric Hysteresis).

The 4-regime table from `strategics/` is the **constitutional layer** — it is the
single source of truth for regime thresholds. The PAV `PolicyEngine` and the IKIGAI
agent `regime_state` must agree with this table.

| Regime | Emoji | Q_HE limiar | Hysteresis |
|--------|-------|-------------|------------|
| PUSH | 🚀 | ≥ 0.85 | ↑ 3 dias |
| MAINTAIN | 🔧 | 0.70–0.85 | neutro |
| REDUCE | 📉 | 0.60–0.70 | ↓ 2 dias |
| RECOVER | 🛌 | < 0.60 | ↓ 2 dias |

**Reading `MAINTAIN`:** Q_HE 0.6500 is at the **lower boundary** of MAINTAIN
(0.70–0.85). The value 0.6500 is actually *below* the INNER GUIDELINES MAINTAIN floor
of 0.70. This is a **D03 discrepancy** (see algorithm-issues-registry.md):

> The bootstrap output shows Q_HE = 0.6500 labeled as MAINTAIN,
> but INNER GUIDELINES says MAINTAIN starts at 0.70.
>
> **D03 is RESOLVED** by INNER GUIDELINES adoption (2026-08-26).
> The PAV PolicyEngine threshold of 0.65 is the *operational* floor.
> The IKIGAI agent uses 0.65 as MAINTAIN floor (from `_read_qhe_from_operational()`).
>
> **This is the gap that IKIGAI × PAV sync must bridge.**

### Q_HE: 0.6500

**Constitutional source:** INNER GUIDELINES — "Q_HE é métrica primária de execução."

`Q_HE` comes from **PAV** (`operational/core/habit_engine.py`). The IKIGAI agent
reads it via `_read_qhe_from_operational()` (`nodes/observe.py`).

**Q_HE 0.6500 at a glance:**
- It's the **threshold value** between REDUCE and MAINTAIN in the PAV engine
- It's exactly at the **RECOVER floor** in INNER GUIDELINES (RECOVER < 0.60)
- The bootstrap value of 0.65 means: "habit engine has a score of 65% of maximum"

**Why 0.65?** This is the **natural state after Phase 0 migration** — the vault has
12 files migrated but no habit logs in PAV yet. Q_HE 0.65 reflects:
- 1 TRIMESTRE with `status: ACTIVE`
- 3 ONDAs with various statuses
- No PAV daily logs → PAV infers conservative Q_HE

### Meta: 39.9439

**Source:** `state.py:175-207` (`compute_meta_vector`).

**THIS IS NOT 0-1. IT IS 0-100.** This was previously misdocumented in the glossary.
Value 39.9439 is normal for bootstrap — vector scores are not yet populated.

```
meta_vector = 0.6 × geo_mean + 0.4 × harm_mean  (in 0-100 scale)
```

- **Geometric mean (60%):** balances vectors — if one is 0, geo_mean → 0
- **Harmonic mean (40%):** penalizes lows — if one vector is near 0, harm → 0
- **Result 39.9:** means vector scores are averaging around 40/100 in bootstrap

**What this means for the agent:** The meta_vector will climb as the vault
receives TRIMESTRE and ONDA logs with actual `vector_scores`. A meta_vector of
80+ requires all 5 vectors populated with scores ≥ 60.

### Vectors: 5 scored

All 5 IKIGAI vectors were evaluated:
`passion · skill · market · revenue · course`

Each vector has a `ScoreValue` (0-100 scale). The agent reads them from the vault's
TRIMESTRE/ONDA entities. At bootstrap, most are `null` — the count shows all 5
were *attempted*, not all *successfully scored*.

### Corrections: 0

**Source:** `nodes/observe.py` — H1-H6 heuristics emit `CorrectionSignal` objects.

No corrections means:
- H1: Q_HE not below target for > 2 days ✓
- H2: No streak broken ✓
- H3: Prospective buffer not overloaded ✓
- H4: Retrospective log not empty ✓
- H5: Regime deviation < 1 level ✓
- H6: No burnout signals ✓

**H1-H6 are signals, not commands** — per INNER GUIDELINES Princípio #4.
The agent *notices* deviations but does not auto-execute corrections.

### Prospective: 4

**Source:** `nodes/plan.py` — `prospective_buffer` field in `IKIGAiStateDict`.

Items draftadas para o tier atual. The 4 items likely include:
- `[QUARTERLY]` items for the active TRIMESTRE
- `[WEEKLY]` items for the active ONDAs

The buffer is **forward-looking** — "what should I do next?" The plan node
drafts these based on `PlanTier` (inferred from `cycle_start`/`cycle_end`).

### Retrospective: 2

**Source:** `nodes/reflect.py` — `retrospective_log` field.

Items completed since last cycle. The 2 items likely include completions from:
- Phase 0 migration commits (12 files migrated)
- Maybe 1 ONDA status update

The log is **backward-looking** — "what did I complete?" The reflect node aggregates
UPI history via `solverforge-calendar-mcp`.

---

## How This Cycle Implements INNER GUIDELINES

| INNER GUIDELINES | How the Cycle Implements It |
|-----------------|------------------------------|
| TENSÃO→COMPORTAMENTO→SOLUÇÃO | `regime_state` = COMPORTAMENTO; `corrections` = TENSÃO signals; `prospective_buffer` = SOLUÇÃO drafts |
| Q_HE é métrica primária | `Q_HE: 0.6500` is read from PAV, governs regime |
| H1-H6 são sinais, não comandos | `Corrections: 0` — no auto-actions taken |
| Vault é memória verificável | All 5 vectors scored from vault entities |
| Hysteresis assimétrica | Regime change requires 2-3 consecutive days |
| Nunca confundir fase com regime | `phase` and `regime_state` are separate fields in `IKIGAiStateDict` |

---

## Open Issues surfaced by this cycle

| Issue | Severity | Notes |
|-------|----------|-------|
| D03 threshold discrepancy (MAINTAIN = 0.65 vs 0.70) | HIGH | PAV uses 0.65; INNER GUIDELINES says 0.70. Sync bridge needed. |
| A02.1 EMERGENCY sub-state | OPEN | INNER GUIDELINES has RECOVER < 0.60; persona had 0.30 emergency floor. Phase or regime? |
| meta_vector 39.9 at bootstrap | INFO | Expected — vault not fully populated yet. Will climb to 60-80 range as vector_scores fill. |
| Q_HE 0.65 = floor of PAV MAINTAIN but below INNER GUIDELINES MAINTAIN floor | HIGH | The IKIGAI agent is showing MAINTAIN at 0.65; inner guidelines require 0.70. |

---

## Cross-References

| Document | Relevance |
|----------|-----------|
| `docs/superpowers/glossaries/ikigai-pav-glossary.md` | Full glossary (Part X.5 = agent cycle output) |
| `docs/superpowers/glossaries/ikigai-pav-glossary.md` Part I | TENSÃO→COMPORTAMENTO→SOLUÇÃO + 5 tensões + 4 regimes |
| `.omo/ikigai/meta/algorithm-issues-registry.md` D03 | Q_HE threshold resolution (now RESOLVED) |
| `.omo/ikigai/meta/algorithm-issues-registry.md` A02 | RECOVER trigger (A02.1 pending) |
| `life-ops/ikigai/src/agents/ikigai_maintainer/state.py:175` | `compute_meta_vector` source |
| `life-ops/ikigai/src/agents/ikigai_maintainer/nodes/observe.py` | H1-H6 correction signals |
| `life-ops/ikigai/src/agents/ikigai_maintainer/nodes/plan.py` | Prospective buffer |
| `life-ops/ikigai/src/agents/ikigai_maintainer/nodes/reflect.py` | Retrospective log |
| `strategics/Modelagem Operacional.md` | Pyramid layers + cycles |
| `operational/docs/algorithms/04-HABIT-ENGINE.md` | Q_HE formula source |
| `operational/docs/ux/00-visao-geral/04-glossario-dominio.md` | PAV domain glossary |
