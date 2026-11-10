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

## The planned work is not only `tarefa`

**THE MEASURED FACT (2026-11-10, on the box):** the store holds **0** `tarefa`
artifacts alive — the only two ever written were probes, and both are deleted.
It holds **5** `fase` rows for Q4-2026 (B0–B4, each with its window and its
"Done quando"), **5** `okr`, **7** `kpi` and **1** `revisao`. The daily note of
2026-11-09 — the one that WORKED, revision 4, written through MCP — classified
**the phases and the plan's decision gate**, and it said so in its own §1: the
store had no artifact of the kinds that represent work, so "the planned tasks"
are the B0–B4 phases and the §4.1 gate.

So step 1 is a SEARCH, and it does not end at `tarefa`. Read the work of the
period in the kinds that carry it:

- `tarefa` — the tasks, when they exist. They are the finest grain.
- `fase` — the phase rows, each with its window and its "Done quando" criteria.
- `plano` — the quarter's plan, which opens the decision gates.

**A PHASE IS PLANNED WORK, AND IT IS CLASSIFIED LIKE A TASK.** Its window says
whether it is in scope today; its "Done quando" says what evidence would prove
it done. A phase whose window closed with no evidence is "not started" — the
same class, the same rule, the same citation.

**WHAT AN EMPTY SET MEANS, AND WHAT IT DOES NOT MEAN.** If the search returns
nothing — no `tarefa`, no `fase`, no gate — then the day had no planned work.
That is a FACT ABOUT THE DAY, and it goes IN the note: the note is still
written, it says there was no planned work, and the counts are zero.

**IT IS NOT A REASON TO WRITE NOTHING.** The note of a day with no planned work
is still the record of that day, and the daily cycle is what produces it. A
cycle that ends with no note has produced nothing at all.

**IT IS NOT A REASON TO WRITE A DIFFERENT ARTIFACT.** The routine's output is a
`nota`. A `desc` is the monthly review's output; a `revisao` is the weekly's.
Writing one of those instead of the note is the routine answering a question
nobody asked — measured on the box (2026-11-10), a cadence run that found
itself with nothing to classify wrote **two `desc`** and **no note**, and the
gate that asked for a daily note stayed red. Write the `nota`.

**IT IS NOT A REASON TO INVENT WORK.** Nothing is planned that the store does
not say is planned. A task that was never written is not "not started"; it is
absent, and the note says it is absent.

## Invariants

- The note is a new artifact. The previous day's note is never rewritten.
- **The note is written ONCE PER DAY, and it is written EVERY day.** A run that
  ends without a `nota` has failed its contract, whatever it wrote instead.
- Every classification cites evidence. A recollection is not evidence.
- **A CLASSIFICATION WITH NO EVIDENCE IS "NOT STARTED", NEVER "DONE".** The
  absence of an artifact proves that the store holds no record — it does not
  prove that the work did not happen, and it does not prove that it did. The
  note says the record is missing; it does not convert a missing record into a
  verdict. (Measured on the box, 2026-11-10: with 0 `tarefa` and 0 `fase` alive,
  the store could not tell "not done" from "not recorded" — and the note that
  worked said exactly that.)
- The body never contains a secret, a token or a connection string.

## When to ask the owner

- The evidence for a task points both ways, and the class would change what the day says. Ask with `ask` and wait for the answer; the call blocks, and the answer arrives as the tool result.
- A task was dropped and the store holds no reason. Ask why — the reason is the owner's, not something to infer from a missing note.
- **A routine that runs on its own has no owner to ask.** The daily cycle
  fires at 22:00 with nobody watching: there is no one to answer, and a
  question that waits for an answer holds the run until its ceiling. So a
  cadence run NEVER asks — it records what the evidence says and names what is
  missing. (Measured on the box, 2026-11-09: a monthly review asked eight
  questions and none was answered inside the deadline; the decision was
  recorded as "veto pendente". Asking is a tool of a run the owner started.)
- Everything else is settled by the evidence. Do not ask to confirm what the store already says.

## Done when

- the note exists at its uid with the counts and the evidence,
- **and the note exists even when there was no planned work to classify** —
  in that case it says so, its counts are zero, and it names what was searched,
- and the report names the uid, the counts per class and the tools that ran.
