# Layer 1: strategics/ Review Findings

**Reviewer:** T-11.2 (Sonnet) — 2026-09-12
**Inputs:**
- `strategics/00-ÍNDICE-PROGRESSIVO.md` (425L)
- `strategics/Planejamento (Estratégico e Tático).md` (603L)
- `strategics/Hierarquia de Objetivos.md` (142L)
- `strategics/Modelagem Operacional.md` (274L)

Out of scope for this review (read but not cross-checked):
- `strategics/Análise (Tático e Operacional).md` (117L)
- `strategics/Desempenho Subjacente.md` (167L)
- `strategics/Integracao_Tatica.md` (142L)
- `strategics/design_system_and_knowledge_tracking.md` (91L)
- `strategics/system_architecture_and_tracking_framework.md` (111L)

---

## Per-Doc Summary

### 1. `00-ÍNDICE-PROGRESSIVO.md` (canonical navigator)
- **Claims:** This is the **exclusive navigation map** for the strategics layer. It self-describes as a "mirror em `time-tasker/strategics/`". It organizes the 6 theory docs into 3 layers (Estratégico / Tático / Operacional), with a relationship topology (Mermaid) and a cross-doc glossary.
- **SONHO count:** No explicit count. Referenced plurally ("Sonhos & Objetivos" as the strategic-layer product, §4.2 row 4).
- **Hierarchy depth:** Mentions "4 Níveis" in the Estratégico layer diagram (§0, ASCII pyramid: `• 4 Níveis`).
- **PAV refs:** Uses the term "PAE" (Plano Anual Estratégico). **No reference to the now-archived PAV kernel** (PAV = Produtividade Algorítmica Visual, archived 2026-08-31 per CLAUDE.md). The docs use PAE, not PAV — these are different concepts but easy to confuse.
- **Date/version:** "Atualizado em: 2026-05-15" + Commit Log 2026-06-30 (planning-with-files v3.1.3).

### 2. `Planejamento (Estratégico e Tático).md`
- **Claims:** The "manual de construção" — expands metrics, advanced protocols, templates, and quality-assurance mechanisms. Dual-frame integration of PAE × Hierarchical Structure. Explicitly section-annotated with `[RECONSTRUCTED]` / `[EXPANDED]` markers, signaling these sections were added later by reconstruction/expansion.
- **SONHO count:** Lists **2 example SONHOS** in §6.1 ("Publicar um livro", "Melhorar saúde física") — these are illustrative, not normative.
- **Hierarchy depth:** **5 níveis** in §1.2.1: SONHOS → OBJETIVOS → METAS → TAREFAS → ATIVIDADES (lines 61–69).
- **PAV refs:** PAE = Plano Anual Estratégico (§1.1.1); 180 dias úteis = Macro-Fase (§2.1.1); ciclos = 45 dias úteis; ondas = 15 dias úteis; Teste de Fogo after 180 dias úteis.
- **Date/version:** **No explicit date, author, or version header.**

### 3. `Hierarquia de Objetivos.md`
- **Claims:** Provides the templates for Revisão Semanal (meta-oriented) and Revisão Mensal (sonho-oriented). Pure template/structure doc.
- **SONHO count:** No explicit count. Used as examples ("Concluir um portfólio", "Melhorar saúde física").
- **Hierarchy depth:** **4 níveis** in §3 (Nível 1: Sonhos, Nível 2: Objetivos, Nível 3: Metas, Nível 4: Tarefas). **No ATIVIDADES level.**
- **PAV refs:** None explicit. No mention of PAE, Q1-Q4, ciclos, or ondas. Pure template doc.
- **Date/version:** Examples dated 22/01/2025 a 28/01/2025. **No document-level date/version.**

### 4. `Modelagem Operacional.md`
- **Claims:** "O DNA do sistema" — defines the performance pyramid, 4 levels of granularity, and integrated cyclical structure (PAE + Hierarchical). The most foundational doc.
- **SONHO count:** No explicit count. Sonhos = "6 a 12 meses" (§1.2.5).
- **Hierarchy depth:** **4 níveis** in §1 "Organização em Níveis de Granularidade" (lines 115–124): Sonhos → Objetivos → Metas → Tarefas. **No ATIVIDADES level.** Cadence table: Sonhos (Mensal #supervisão), Objetivos (Quinzenal #revisão), Metas (Semanal #relatórios), Tarefas (Diário #narrativa e #to-do).
- **PAV refs:** Heavy PAE usage: PAE = Plano Anual Estratégico; Q1-Q4 = 13 weeks each; ciclo = 45 dias úteis; ondas = 3 semanas; 4 ciclos por Macro-Fase.
- **Date/version:** **No explicit date, author, or version header.**

---

## Cross-Doc Consistency Check

| Topic | `00-ÍNDICE-PROGRESSIVO` | `Planejamento (E&T)` | `Hierarquia de Objetivos` | `Modelagem Operacional` | Consistent? |
|---|---|---|---|---|---|
| **SONHO time horizon** | 6-12 meses (Estratégico layer) | 6-12 meses (§1.2.2) | 6-12 meses (§3.1) | 6-12 meses (§1.2.5) | **Yes** |
| **SONHO count (normative)** | None (plural only) | 2 examples (illustrative) | None | None | **Yes (all silent)** |
| **Hierarchy depth** | 4 Níveis (diagram) | **5 Níveis** (§1.2.1: SONHOS/OBJETIVOS/METAS/TAREFAS/ATIVIDADES) | **4 Níveis** (§3) | **4 Níveis** (§1) | **NO — 4 vs 5** |
| **OBJETIVOS horizon** | 3 meses (E&T doc reference) | 3 meses / Trimestre | 15 dias (quinzenal) — §3.2 | 15 dias (quinzenal) — §1 table | **NO — 3 meses vs 15 dias** |
| **METAS horizon** | Implied 15 dias | 15 dias (§1.2.2) | 7 dias / Semana (§3.3) | Semana (§1 table) | **NO — 15 dias vs Semana** |
| **Macro-Fase / PAE base** | PAE = Q1-Q4 (referenced) | 180 dias úteis = 4 ciclos × 45 (§2.1.1) | (silent) | Q1-Q4 = 13 weeks (§1.1) | **Mismatch — PAE≠Macro-Fase length** |
| **Ciclo base (Hierarchical)** | 45 dias úteis | 45 dias úteis | (silent) | 45 dias úteis | **Yes** |
| **Onda base** | 15 dias úteis (3 weeks) | 15 dias úteis (3 weeks) | (silent) | 3 semanas (15 dias úteis) | **Yes** |
| **PAV refs (algorithmic kernel)** | None | None | None | None | **Yes — all silent on PAV** |
| **PAE refs (annual plan)** | Yes | Yes | None | Yes | **Partial — Hierarquia is silent** |
| **Teste de Fogo** | 180 dias úteis | 180 dias úteis | (silent) | 180 dias úteis (referenced) | **Yes** |
| **Glossary overlap** | "Ciclo (45 dias)" / "Onda" / "PAE" | "Ciclo" / "Onda" / "Teste de Fogo" | (no glossary) | Implicit only | **Partial** |
| **Document date/version stamp** | 2026-05-15 + 2026-06-30 | MISSING | MISSING (only example dates) | MISSING | **NO — only the index is dated** |
| **Central Engine pointer** | Yes (planning-with-files v3.1.3) | Yes | Yes | Yes | **Yes (post-2026-06-30 update)** |

---

## Cross-Doc Concept Drift Observations

These are drift *patterns* worth noting separately from the formal gap list:

1. **Hierarchy depth fork.** `Planejamento (E&T)` is the only doc carrying a 5-level hierarchy (with ATIVIDADES as level 5). The other 3 docs stop at TAREFAS (level 4). `grep -c "ATIVIDADES"` confirms this: 11 hits in `Planejamento (E&T)`, 2 in `Modelagem Operacional` (incidental), 1 in `Análise (T&O)`, 0 in `Hierarquia de Objetivos` and `00-ÍNDICE-PROGRESSIVO`.

2. **OBJETIVOS horizon conflict.** `Planejamento (E&T)` and the index say OBJETIVOS = 3 meses (per quarter). `Modelagem Operacional` and `Hierarquia de Objetivos` say OBJETIVOS = 15 dias (quinzenal). These are **mutually exclusive** horizons — same word, different meaning.

3. **Temporal-model duality is glossed over.** The PAE frame uses Q1-Q4 (calendar, ~13 weeks each). The Hierarchical frame uses 45-business-day ciclos. The docs claim both coexist, but a Q = ~65 business days ≈ 1.44 ciclos of 45. The mapping is never made explicit. The Macro-Fase of "180 dias úteis" = 9 months, not 12, so a single Macro-Fase doesn't equal a PAE year. This is **unresolved dual-base arithmetic** at the core of the framework.

4. **"PAE" vs "PAV" terminological collision.** Strategics uses PAE = Plano Anual Estratégico. The project elsewhere (CLAUDE.md, archived PAV kernel) uses PAV = Produtividade Algorítmica Visual. These are different concepts but the **acronym collision is a real readability hazard** for anyone reading both layers. Strategics docs are silent on PAV (correctly scoped) but provide no disclaimer.

5. **Date/version hygiene.** Only `00-ÍNDICE-PROGRESSIVO` carries a stamp ("2026-05-15"). The 3 other core docs are undated. `[RECONSTRUCTED]` / `[EXPANDED]` markers in `Planejamento (E&T)` (§1.2, §2.2, §3.1, §4.1, §4.2, §5.2) signal later augmentation, but no commit/date attribution. Audit trail is weak.

---

## Provisional Gaps

| # | Severity | Gap | Evidence |
|---|---|---|---|
| **G-L1.1** | **P1** | **Hierarchy depth inconsistent** — `Planejamento (E&T)` declares 5 níveis (incl. ATIVIDADES); the other 3 docs use 4 níveis. Confusing for agents and humans who read multiple docs. | §1.2.1 of `Planejamento (E&T)` (lines 61–69, 5-level tree) vs §1 of `Modelagem Operacional` (lines 115–124, 4-level table) vs §3 of `Hierarquia de Objetivos` (4 níveis) vs §0 ASCII diagram of `00-ÍNDICE-PROGRESSIVO` ("4 Níveis"). |
| **G-L1.2** | **P1** | **OBJETIVOS horizon conflicting** — same word, two distinct time bases (3 meses vs 15 dias). | §1.2.2 of `Planejamento (E&T)` ("3 meses → Trimestre 1, 2, 3, 4") vs §1 table of `Modelagem Operacional` ("Objetivos / 15 dias (quinzenal)") vs §3.2 of `Hierarquia de Objetivos` ("Prazo: 15 dias (revisão quinzenal)"). |
| **G-L1.3** | **P2** | **PAE / PAV acronym collision** — strategics uses PAE (Plano Anual Estratégico); project elsewhere uses PAV (Produtividade Algorítmica Visual, archived 2026-08-31). Strategics docs provide no disclaimer. | `00-ÍNDICE-PROGRESSIVO` + `Planejamento (E&T)` + `Modelagem Operacional` all use PAE freely. CLAUDE.md archives PAV (Produtividade Algorítmica Visual). New readers could confuse them. |
| **G-L1.4** | **P2** | **Dual temporal base (PAE calendar vs Hierarchical business-days) never reconciled** — Macro-Fase = 180 business days ≈ 9 months ≠ 1 PAE year (Q1-Q4 = ~12 months). The docs claim they coexist but provide no mapping. | `Planejamento (E&T)` §2.1.1 ("Macro-Fase: 180 dias úteis / Divisão: 4 Ciclos (45 dias úteis cada)") vs §1.1.1 of `Modelagem Operacional` ("Q1 a Q4 têm duração variada — 13 semanas em média"). 180 BD ≈ 9 months; PAE year ≈ 12 months. |
| **G-L1.5** | **P2** | **METAS horizon inconsistent** — `Planejamento (E&T)` says METAS = 15 dias; `Modelagem Operacional` and `Hierarquia de Objetivos` say METAS = Semana (7 dias). Same word, different cadence. | §1.2.2 of `Planejamento (E&T)` ("METAS (15 dias)") vs §1 table of `Modelagem Operacional` ("Metas / Semana / Semanal #relatórios") vs §3.3 of `Hierarquia de Objetivos` ("Prazo: 7 dias"). |
| **G-L1.6** | **P3** | **3 of 4 core docs have no date / version / author stamp** — only `00-ÍNDICE-PROGRESSIVO` is dated ("2026-05-15"). The other 3 docs are append-only but lack timestamps. Audit trail weak. | File headers of `Planejamento (E&T)`, `Hierarquia de Objetivos`, `Modelagem Operacional` — no frontmatter or version line. |
| **G-L1.7** | **P3** | **[RECONSTRUCTED] / [EXPANDED] markers in `Planejamento (E&T)` lack attribution** — markers signal later augmentation but no commit hash, date, or author. | §1.2 [RECONSTRUCTED], §2.2 [EXPANDED], §3.1 [EXPANDED], §4.1 [EXPANDED], §4.2 [EXPANDED], §5.2 [EXPANDED]. |
| **G-L1.8** | **P3** | **Concept name casing is inconsistent** — SONHOS/OBJETIVOS/METAS/TAREFAS/ATIVIDADES appear in both ALL-CAPS and Title case across docs, sometimes within the same doc. Not a contradiction, but a style hygiene issue. | Compare §1.2.1 of `Planejamento (E&T)` (ALL CAPS) with §1.2.2 of same doc (Title case in the table column header). |
| **G-L1.9** | **P3** | **Glossary fragmentation** — only `00-ÍNDICE-PROGRESSIVO` (§7) and `Planejamento (E&T)` (ANEXO) carry glossaries, with partial overlap. `Hierarquia de Objetivos` and `Modelagem Operacional` have none. | §7 of index + ANEXO of `Planejamento (E&T)` vs absence in the other two. |
| **G-L1.10** | **P3** | **`Hierarquia de Objetivos` is template-only, no framework doctrine** — leaves the OBJETIVOS horizon conflict (G-L1.2) and the METAS horizon conflict (G-L1.5) implicit because it never names a horizon for OBJETIVOS (other than the §3.2 line "15 dias" which directly conflicts with `Planejamento (E&T)`). | §3.2 of `Hierarquia de Objetivos`. |

---

## Out of Scope (recorded for follow-up, NOT gaps)

- The strategics layer treats PAE (Plano Anual Estratégico) as the active doctrine. This is **consistent with attribution** (PAV = Produtividade Algorítmica Visual = different concept = archived). No attribution violation in the strategics docs themselves.
- The `[RECONSTRUCTED]` / `[EXPANDED]` markers show the layer is being actively maintained. The drift is honest, not hidden.
- The 6-doc corpus is internally consistent on the **SONHO time horizon** (6-12 meses), the **Onda base** (15 dias úteis), and the **Ciclo base** (45 dias úteis). Those are the load-bearing invariants that hold across all 4 docs.

---

## Severity Roll-up

- **P0 (attribution violated):** 0
- **P1 (drift detection missing — would block a downstream agent):** 2 (G-L1.1, G-L1.2)
- **P2 (UX / inconsistency):** 3 (G-L1.3, G-L1.4, G-L1.5)
- **P3 (cosmetic):** 5 (G-L1.6 – G-L1.10)

**Total provisional gaps: 10** (0 P0 / 2 P1 / 3 P2 / 5 P3)

**Consistency violations: 5** (hierarchy depth, OBJETIVOS horizon, METAS horizon, dual temporal base, missing date stamps).

---

*Review-only. No code changes. No remediation actions in this spec. Per plan §"Constraints": diagnosis belongs to a future plan.*
