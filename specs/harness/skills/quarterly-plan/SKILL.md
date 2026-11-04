---
name: quarterly-plan
description: Use when the quarterly cycle runs or the owner asks for the next quarter. Writes a `plano` artifact with its `fase` rows, `okr` objectives and `onda` waves, and runs the Teste de Fogo against the quarter that closed.
---

# Quarterly plan

Closes a quarter with the Teste de Fogo, then opens the next one as a `plano` with its phases, objectives and waves.

## Conceptual source

`strategics/Modelagem Operacional.md` defines the five levels and the cycles. `strategics/Planejamento (Estratégico e Tático).md` defines the quarterly planning, the 5x3x3 proportion and the Teste de Fogo. `strategics/Desempenho Subjacente.md` defines the three-month consolidation this feeds. The Correção do Trajeto is what a failed Teste de Fogo triggers.

## Contract

Trigger:    The quarterly cycle runs, or the owner asks for the next quarter.
Inputs:     The dreams in force, the last quarter's review, the objectives and indicators that closed, and the Teste de Fogo result.
Outputs:    A `plano` artifact for the quarter, its `fase` rows, its `okr` objectives, its `onda` waves, and the uid of each.
Steps:
1. Search for the dreams in force: `search_artifacts` with `kinds=(sonho,)`.
2. Search for the verdict and the decisions of the closing quarter: `search_artifacts` with `kinds=(revisao, desc)` and the closing quarter.
3. Search for what closed and what did not: `search_artifacts` with `kinds=(okr, kpi)` and the closing quarter.
4. Run the Teste de Fogo against the closing quarter. A verdict that is not PASS opens the Correção do Trajeto: the correction is written before the new plan.
5. Write the `plano` with `upsert_artifact`, with its plan tier and its quarter. Set the quarter on every artifact that belongs to it.
6. Write the `fase` rows of the plan, the `okr` objectives with their key results and targets, and the `onda` waves of the quarter.
7. Link them: `PARENT_OF` from the plan to its phases, the phases to the waves, the waves to the tasks; `DERIVES_FROM` when a wave comes from an objective.
8. Report the plan uid, the uids of the phases, objectives and waves, the Teste de Fogo verdict, and the tools that ran.

Invariants:
- The plan is a new artifact. The closing quarter's plan is never edited.
- The Teste de Fogo verdict is computed from the store, not asserted.
- A failed verdict produces a Correção do Trajeto before a new plan.
- Hierarchy is expressed as relations, never as duplicated fields.

Done when:
- the plan, its phases, its objectives and its waves exist and are linked,
- the Teste de Fogo verdict is reported with the evidence it was computed from,
- and the report names every uid it wrote.
