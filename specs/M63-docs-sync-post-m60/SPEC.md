---
name: M63-docs-sync-post-m60
description: AGENTS.md + CLAUDE.md updated to reflect post-M60 life/ directory + pyproject.toml
owner: matheus-mendes
status: DONE
milestone: M63
estimated_cost_usd: 0.20
constitution_refs:
  - correctness_over_speed
  - state_on_disk_not_conversation
---

# M63 — AGENTS.md + CLAUDE.md sync to post-M60 reality

## Context

After M60 moved the `life` meta-package from "lone root `__init__.py`
+ top-level cli/, centrals/, handlers/, plugins/" into a real
`life/` directory + pyproject.toml, both AGENTS.md and CLAUDE.md
continued to describe the OLD layout. Several specific places:

- AGENTS.md line 26 (file roles table): `cli/, centrals/, handlers/,
  plugins/, __init__.py (root)` — directory paths were at root
- AGENTS.md line 177: "Root `__init__.py` enables `python -m life.cli`"
  — claim that was actively false for months before M60
- AGENTS.md line 377: `cli/cli.py does from life import __version__`
  — actual file is `life/cli/cli.py`
- AGENTS.md line 391: handlers/daily.py — actual file is `life/handlers/daily.py`
- CLAUDE.md "Root Layout (não-src/)": described `python -m life.cli`
  as living in `cli/`, `centrals/`, `handlers/`, `plugins/` at root —
  ALL wrong post-M60

## What changed

### AGENTS.md
- 7 of 8 targeted replacements applied. The remaining 1 (table row
  index) was already correct in spirit and was skipped.
- Key fixes:
  - File roles table now lists `life/cli/`, `life/centrals/`, etc.
  - "Root `__init__.py` enables `python -m life.cli`" replaced
    with explicit M60 restructure note + Python ≥3.11 pin
  - PYTHONPATH pitfall updated to mention `pytest.ini` and
    `pip install -e .` as the canonical ways to populate sys.path

### CLAUDE.md
- "Root Layout (não-src/)" section entirely rewritten to reflect:
  - `life/__init__.py` + `life/cli/`, `life/centrals/`, etc.
  - `pyproject.toml` + `.python-version`
  - `pytest.ini` automatic `pythonpath = src`
  - Legacy `__init__.py` at root marked as NOT a valid package

## Acceptance

- [x] `tests/test_drift_extended_invariants.py` 18/18 PASS
- [x] `tests/test_drift_invariants.py` 7/7 PASS
- [x] `tests/test_drift_state.py` 1/1 PASS
- [x] `tests/test_chat_repl.py` 8/8 PASS
- [x] `tests/test_chat_system.py` 5/5 PASS
- [x] All 8 stale references in AGENTS.md referring to bare root-level
  cli/, centrals/, handlers/, plugins/ as the live location are gone
- [x] CLAUDE.md root-layout section no longer contradicts reality

## Risk / out of scope

- Three mentions of `python -m life.cli` in commands blocks (AGENTS.md
  lines 181-194) are now ACCURATE — they describe the canonical entry
  point, which actually works post-M60.
- CLAUDE.md Turkish section "Typer CLI raiz ..." paragraph still
  claims consistency with `python -m life.cli`. That section was
  untouched here; it is consistent with the new section above.
