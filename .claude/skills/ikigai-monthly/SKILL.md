---
name: monthly-review
description: Use when the monthly cycle runs or the owner asks how the objectives are tracking. Writes a `desc` artifact recording the decision taken against the objectives, with the gap between each KPI target and actual.
---

# Monthly review

Compares the objectives against the results and writes the decision that follows as a `desc` artifact.

## Conceptual source

`strategics/Hierarquia de Objetivos.md` defines the monthly, dream-oriented review, and `strategics/Desempenho Subjacente.md` defines the three-month consolidation it feeds.

## Contract

Trigger:    The monthly cycle runs, or the owner asks how the objectives are tracking.
Inputs:     The objectives of the quarter, the KPIs with their targets, the actuals read from the weeklies, and the decisions already recorded.
Outputs:    A `desc` artifact against the objectives with its uid, and the gap between target and actual per indicator.
Steps:
1. Search for the objectives: `search_artifacts` with `kinds=(okr,)` and the quarter.
2. Search for the indicators with their targets and periods: `search_artifacts` with `kinds=(kpi,)` and the quarter.
3. Search for the weeklies that carry the actuals: `search_artifacts` with `kinds=(revisao,)` and the quarter.
4. Search for the decisions already recorded: `search_artifacts` with `kinds=(desc,)` and the quarter.
5. Read each indicator and each objective with `get_artifact` at depth 0. The target, the actual and the period are stated in the artifact's frontmatter, and the search returns the identity of a hit, not its body (ADR-046) — the gap is computed over what the artifact SAYS.
6. Compare each indicator's `actual` against its `target` and compute the gap. The values are Decimal, never float: a KPI that loses precision is a wrong KPI.
7. Write the decision with `upsert_artifact`. A `desc` records a decision and why it was taken, so the body states what the gap means and what is being decided about it. The write carries the edges to the objectives and the indicators the decision speaks about: each edge starts at the decision, so the decision and its edges land together.
8. Report the decision uid, the gap per indicator and the tools that ran.

Invariants:
- The comparison is arithmetic over the store. There is no LLM in the gap.
- A `desc` states the rationale. A decision without a rationale is not a decision.
- The prior monthly decision is never rewritten.

When to ask the owner:
- The GAP is computed, but what the gap MEANS is a decision. Ask with `ask` and wait for the answer before writing the `desc`: the rationale is the owner's, and a rationale invented from a number is not a rationale.
- An indicator has no actual, and the weeklies do not say whether that is a miss or a gap in the record. Ask which it is.
- Everything else is settled by the arithmetic. Do not ask to confirm a gap you already computed.

Done when:
- the decision exists at its uid with the gap per indicator,
- and the report names the uid, the gaps and the tools that ran.
