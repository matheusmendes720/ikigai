---
name: weekly-review
description: Use when the weekly cycle runs or the owner asks how the plan compares to reality. Writes a `revisao` artifact that classifies each planned item as done, partly done, not started or dropped, each with cited evidence.
---

# Weekly review

Compares the plan against reality for one week and writes the comparison as a `revisao` artifact.

## Conceptual source

`strategics/Desempenho Subjacente.md` defines the five-day consolidation this review consumes, and `strategics/Hierarquia de Objetivos.md` defines the review template and the meta table it feeds.

## Contract

Trigger:    The weekly cycle runs, or the owner asks how the plan compares to reality.
Inputs:     The current plan, the tasks of the period, the notes of the week, and the evidence in the store.
Outputs:    A `revisao` artifact for the week with its uid, and the counts per class.
Steps:
1. Search for what the week was supposed to deliver: `search_artifacts` with `kinds=(plano, onda, okr, kpi)` and the quarter.
2. Search for the tasks of the period: `search_artifacts` with `kinds=(tarefa,)`.
3. Search for the notes of the week: `search_artifacts` with `kinds=(nota,)` and the quarter.
4. Classify each planned item as done, partly done, not started or dropped, and cite the evidence for the classification. An item with no evidence stays open.
5. Write the review with `upsert_artifact`. The body carries the classification and the evidence. Set the quarter.
6. Link the review to what it reviews with `REFERENCES` relations.
7. Report the review uid, the counts per class and the tools that ran.

Invariants:
- The count is arithmetic over the state in the store. There is no LLM in the count.
- The review is a new artifact. The plan is not edited.
- An item with no evidence stays open.
- A stale `expected_revision` is a conflict. Reread and reapply; never force.

Done when:
- the review exists at its uid with the counts,
- every planned item has a class and a piece of evidence,
- and the summary counts match what the tools returned.
