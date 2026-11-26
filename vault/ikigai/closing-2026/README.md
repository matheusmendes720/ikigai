# Closing 2026 — Personal Plan Container

This is where the human drops their personal plans for closing 2026.

**No code will read or write these files in v1.** The human owns them and edits them
manually during weekly checkpoints.

## Scope

| Section | Period | Weeks | Ondas |
|---------|--------|-------|-------|
| `01-q3-2026/` | 2026-07-06 → 2026-09-27 | 13 | 2–3 |
| `02-q4-2026/` | 2026-10-05 → 2026-12-20 | 13 | 2–3 |
| `99-archive/` | 2026-H1 | — | closed/abandoned |

## Folder pattern

Each quarter follows the same 5-stage scaffold:

```
NN-quarter/
├── 00-sonho/                  — the dream / north-star this quarter is serving
├── 01-plano-trimestral/       — quarterly plan (one file)
├── 02-onda-N/                 — wave(s) inside the quarter (2 or 3)
├── 03-revisões-semanais/      — 13 weekly reviews
└── 04-relatórios-diários/     — ~66 daily reports
```

## Methodology

This is the deliverable target of the **data-first methodology**:

1. Drop the dream in `00-sonho/`.
2. Flesh out the quarter in `01-plano-trimestral/`.
3. Slice the quarter into ondas in `02-onda-N/`.
4. Each onda spawns ~13 weekly reviews and ~66 daily reports.
5. Weekly reviews feed back into the onda; ondas feed back into the quarterly plan;
   the quarterly plan feeds back into the sonho.

## Ownership

The human is the sole writer. No CLI, no automation, no LLM writes into this tree in v1.

---

## Cadence actually adopted (2026-11-23) — the scaffold above is the original target

> **This section is appended, not substituted.** The scaffold above describes the
> method as it was designed: 13 weekly reviews and ~66 daily reports per quarter.
> That target was never met, and the reason was measured — not laziness, but
> shape: the production runs in bursts (704 commits in 5 weeks, then 7 weeks at
> zero), and a daily routine against that shape produces either 7 empty notes or
> none at all.
>
> **The Correction of the Trajectory C1 (2026-11-08) replaced it.** The unit of
> record is now **the burst**:

| Trigger | Record | Where |
|---|---|---|
| Week with commits > 0 | one `revisao`, written at the week's close | `NN-quarter/03-revisões-semanais/YYYY-Www.md` |
| Week with 0 commits | **one line inside the next review** — and no file | idem |
| Burst (>100 commits in a week) | the week's review **is** the record; it is not split into dailies | idem |
| Wave close | the wave's PASS, with the evidence | `NN-quarter/02-onda-N/` |
| Quarter close | the Teste de Fogo, with the fixed denominator | `decisions/` |

> **There is no mandatory daily routine.** There was, and it produced 3 records in
> 60 working days.

### What the tree contains, as of 2026-11-23

| Quarter | Reviews | Waves | Dreams | Daily reports |
|---|---:|---:|---:|---:|
| `01-q3-2026/` | **5** (W35–W39 — the 5 weeks with commits; the 7 weeks at zero are the consolidated review's table) | **3** | **1** (retrospective, labelled as such) | 3 (of ~60) |
| `02-q4-2026/` | **7** (W40, W41, W42, W44, W45, W46, W47; W43 has 0 commits and is one line inside W44) | **3** | **1** | 0 |

> **The two scaffold READMEs below still say "13 weekly reviews" and "~66 daily
> reports"** — they were written before C1 and they are not edited. Each one
> carries an appended section saying what the adopted cadence produced.

*Appended 2026-11-23. The sections above are untouched.*