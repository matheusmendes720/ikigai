---
name: M65-lifeconfig-defaults-real-paths
description: Replace fictitious ROOT/system/* submodules with real repo paths
owner: matheus-mendes
status: DONE
milestone: M65
estimated_cost_usd: 0.20
constitution_refs:
  - correctness_over_speed
  - state_on_disk_not_conversation
---

# M65 — LifeConfig defaults point at real repo paths

## Context

M64's `pip install -e .` validation revealed that running
`life submodules` produced output like:

    job_offers: <ROOT>/system/raise_data/job-offers
    leitura:    <ROOT>/system/knowledge/leitura
    ...

None of those paths exist in the live repo (verified 2026-09-18):
`life/system/raise_data/...` does not appear under the project root.
The defaults were left over from an even older pre-reorg era.

## What changed (M65)

`life/cli/config.py` — two surgical edits:

1. `ROOT = Path(__file__).resolve().parent.parent` →
   `ROOT = Path(__file__).resolve().parents[2]` (the original
   `.parent.parent` walked up too few levels under the M60 layout
   `life/cli/config.py` — `parents[2]` correctly reaches the repo root).

2. `DEFAULT_SUBMODULES` updated from 5 fictitious `system/...` paths
   to 5 real repo dirs:
   - `interfaces_cli` → `interfaces/cli`
   - `interfaces_tui` → `interfaces/tui`
   - `taskwarrior`    → `taskwarrior`
   - `strategics`     → `strategics`
   - `specs`          → `specs`

## Acceptance

- [x] `life submodules` lists 5 real repo paths, all `ref=<latest commit>`
- [x] `life config-show` shows correct `root: <repo>`, `submodules: {... real ...}`
- [x] `life --help` still RC=0
- [x] Drift net + chat invariants: 39/39 PASS (no regressions)
- [x] `ROOT` resolution works in BOTH:
  - `python -m life.cli submodules` (via PYTHONPATH=.)
  - packaged-install `life submodules` (via pip entry point)

## Why this matters

After M64 we confirmed the install path works. But the user-facing
default UX still pointed at dead air. M65 makes `life submodules`
informative out-of-the-box — operators see 5 real subs immediately,
not 5 phantom ones.
