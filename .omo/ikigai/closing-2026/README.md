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