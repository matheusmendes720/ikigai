---
name: daily-note
description: Use when the daily cycle runs or the owner asks to record the day. Writes a `nota` artifact that classifies each planned task as done, partly done, not started or dropped, each with the evidence that proves it.
---

# Daily note

Records one day in the store as a `nota` artifact, classifying every planned task against the evidence found in the store.

## Conceptual source

`strategics/Análise (Tático e Operacional).md` — the daily blocks and the daily report define what a day is made of: the initial routine, the time blocks, and the closing routine that feeds the records.

## Contract

Trigger:    The daily cycle runs, or the owner asks for the day to be recorded.
Inputs:     The quarter, the tasks planned for the period, the notes already written today, and the evidence in the store.
Outputs:    A `nota` artifact for the day with its uid, and the counts of done, partly done, not started and dropped.
Steps:
1. Search for the tasks of the period: `search_artifacts` with `kinds=(tarefa,)` and the quarter.
2. Search for what is already recorded today: `search_artifacts` with `kinds=(nota,)` and the quarter.
3. Read each task that has evidence with `get_artifact` at depth 1, to see its relations.
4. Classify every task as done, partly done, not started or dropped. Cite the evidence: the note uid, or the relation that proves it. An item with no evidence stays open.
5. Write the note with `upsert_artifact`. The body carries the classification and the evidence. Set the quarter and the note date. The write carries the `EVIDENCES` edges to each task the note speaks about: the edge starts at the note, so the note and the edges that make it evidence land together.
6. Report the note uid, the counts per class, the evidence per class and the tools that ran.

Invariants:
- The note is a new artifact. The previous day's note is never rewritten.
- Every classification cites evidence. A recollection is not evidence.
- The body never contains a secret, a token or a connection string.

Done when:
- the note exists at its uid with the counts and the evidence,
- and the report names the uid, the counts per class and the tools that ran.
