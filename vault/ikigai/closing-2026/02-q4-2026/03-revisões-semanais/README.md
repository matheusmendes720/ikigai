# Weekly Reviews — Q4-2026

## Pattern

One file per ISO week, named `YYYY-Www.md`. Use the template
`vibe-ops/planning/_templates_periodos_v2/04-revisao-semanal.md`.

Each review takes **~30–45 minutes** and is done on Friday afternoon or Sunday evening.

## Week list (Q4-2026)

| File | ISO week | Mon → Sun |
|------|----------|-----------|
| `2026-W41.md` | W41 | 2026-10-05 → 2026-10-11 |
| `2026-W42.md` | W42 | 2026-10-12 → 2026-10-18 |
| `2026-W43.md` | W43 | 2026-10-19 → 2026-10-25 |
| `2026-W44.md` | W44 | 2026-10-26 → 2026-11-01 |
| `2026-W45.md` | W45 | 2026-11-02 → 2026-11-08 |
| `2026-W46.md` | W46 | 2026-11-09 → 2026-11-15 |
| `2026-W47.md` | W47 | 2026-11-16 → 2026-11-22 |
| `2026-W48.md` | W48 | 2026-11-23 → 2026-11-29 |
| `2026-W49.md` | W49 | 2026-11-30 → 2026-12-06 |
| `2026-W50.md` | W50 | 2026-12-07 → 2026-12-13 |
| `2026-W51.md` | W51 | 2026-12-14 → 2026-12-20 |
| `2026-W52.md` | W52 | buffer / year-end close |
| `2026-W53.md` | W53 | (only if ISO W53 exists for 2026) |

**Total: 13 weeks** (12 standard + 1 buffer; W53 included only if ISO 8601 assigns one to 2026).

## Inputs

- The week's `../04-relatórios-diários/*.md` (5 reports).
- The active onda file in `../02-onda-N/`.

## Outputs

- Updated onda state.
- Open items carried into next week's reports.
- Decisions to lock or pivot.
- Year-end retrospective inputs (week 52/53).

---

## What actually exists (appended 2026-11-23)

> The list above is the scaffold's target: 13 files, one per ISO week. The
> **Correction of the Trajectory C1** (2026-11-08) replaced that with "one review
> per week with commits > 0; a week at zero is one line in the next review".

| File | Commits | Status |
|---|---:|---|
| `2026-W40.md` | 30 | written 2026-11-23 |
| `2026-W41.md` | 14 | written 2026-11-23 |
| `2026-W42.md` | 7 | written 2026-11-23 |
| `2026-W43.md` | **0** | **no file** — the empty week is one line inside `2026-W44.md` |
| `2026-W44.md` | 28 | written 2026-11-23 |
| `2026-W45.md` | 69 | written 2026-11-08 (the first review of the quarter — not rewritten) |
| `2026-W46.md` | 142 | written 2026-11-23 |
| `2026-W47.md` | 1 | written 2026-11-23 |

> **7 reviews for the 7 weeks with commits; 0 files for the week at zero.**
> That is C1's PASS, spelled out: *"ao fim de 4 semanas, existe uma revisão por
> cada semana com commits > 0, e zero revisões em semanas a zero"*.
>
> **Note on the elapsed window.** The table in §5 of the plan says
> `Elapsed | W41–W45`. W40 (2026-09-28 → 10-04) has 30 commits and belongs to the
> Q4 by the retrospective plan's own reckoning (`q3-2026-plano-retro.md` §2);
> its review is filed here. **The quarter's elapsed set is W40–W45 — six weeks,
> one more than the table says.**
>
> The measurements come from `git log --date=format:'%G-W%V'`, run on 2026-11-23.

*Appended 2026-11-23.*