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
1. Search for the work of the period: `search_artifacts` with `{"query": {"kinds": ["tarefa", "fase", "plano"], "quarter": "Q4-2026", "limit": 20}}`. The quarter is spelled `Q4-2026` — quarter-year — and the day in the context gives it. Search WITH it: a search without the quarter returns every plan in the store and has to be paged.
2. Search for what is already recorded today: `search_artifacts` with `{"query": {"kinds": ["nota"], "quarter": "Q4-2026", "limit": 20}}`.
3. Read each task that has evidence with `get_artifact` at depth 1, to see its relations.
4. Classify every task as done, partly done, not started or dropped. Cite the evidence: the note uid, or the relation that proves it. An item with no evidence stays open.
5. Write the note with `upsert_artifact`. The body carries the classification and the evidence. Set the quarter and the note date. The write carries the `EVIDENCES` edges to each task the note speaks about: the edge starts at the note, so the note and the edges that make it evidence land together.
6. Report the note uid, the counts per class, the evidence per class and the tools that ran.

## The day, its quarter and its title

**THE DAY IS IN THE CONTEXT, AND THE CONTEXT WINS.** The routine's context
carries `date` — the day the run names, `YYYY-MM-DD` — and `now`. The note's
day is that `date`. The agent does not derive it from the clock, and it does
not adjust it for the owner's zone: the run hands over the day, and the day
advances once per run. (Measured on the box, 2026-11-11: the cadence run of
01:00:00Z wrote `not:2026-11-11:74dfed05:d6ad7bd8023c5f59` — the note carries
the day the run handed it, and the day before it carried the day before that.)

**WHY THE DAY MATTERS SO MUCH.** The note's uid AND its idempotency key are
both derived from it, and the store swallows a repeated key as `unchanged`
BEFORE it even looks at the body (`ikig.idempotency_keys`, `on conflict do
nothing`). A note whose day repeats is a note that is never written, and
nobody says so. Use the day the run handed you, as it is.

**THE QUARTER IS SPELLED `Q4-2026`** — quarter-year. It comes from the day: Q1
is January to March, Q2 April to June, Q3 July to September, Q4 October to
December, and 2026-11-11 is in **Q4-2026**. (Measured: the manual run of
2026-11-10 searched `quarter: "2026-Q4"` first, got nothing back, and only
`Q4-2026` answered.) The quarter is a FILTER, not a label: the search for the
work of the period carries it, and so does the write.

**THE TITLE IS `Relatório Diário — <day>`** — the shape every daily note in the
store already carries, so the owner recognises tomorrow's note the way he
recognised the last one.

## How the tools are called

**`search_artifacts` TAKES A LIST OF KIND NAMES.** Measured on the box,
2026-11-11: the run of 01:00Z sent `kinds` as an OBJECT — `{"item": "nota"}` —
and the contract refused it:

    query.kinds
      Input should be a valid tuple [type=tuple_type, input_value={'item': 'nota'}, input_type=dict]

Only `kinds` was named: a number written as text is coerced and accepted, so
the refusal was the object, not the quotes. The call that answers is:

```json
{"query": {"kinds": ["tarefa", "fase", "plano"], "quarter": "Q4-2026", "limit": 20}}
```

`kinds` is a LIST OF STRINGS and it goes inside `query`. A search WITHOUT the
quarter returns every plan in the store and has to be paged; the quarter's own
work is one page — measured, that search answers **7 rows** (5 `fase`, 2
`plano`).

**THE UID IS FOUR SEGMENTS, AND THE LAST TWO ARE HEX.** Measured: the first
write of the manual run of 2026-11-10 was REFUSED, because its uid was
`not:2026-11-10:daily:tg2115322359` — `daily` is not hex and `tg2115322359`
is not sixteen hex characters. The uid that answers is
`not:<day>:<8 hex>:<16 hex>`: the day's slug, a uuid segment, and the body's
hash. It is the note's identity for life — every revision of the day keeps it.

**A UID THAT ALREADY EXISTS IS A CONFLICT, NOT AN OVERWRITE.** A create
against an existing uid is refused: "the uid is taken — send expected_revision
to update it". So the day's note is READ first, and it is then revised with
the revision that was read. (The note of 2026-11-09 is at revision 4: a day's
note is revised as the day goes, and it is never silently replaced.)

**THE IDEMPOTENCY KEY NAMES THE INTENT, NOT THE MOMENT.**
`daily-note-<day>-tg<chat>` — the day and the chat, and nothing else. A retry
of the same day has to be recognisable as the same intent: a key that carries
the hour writes the day's note again, and a key that carries nothing but the
moment writes it twice.

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
