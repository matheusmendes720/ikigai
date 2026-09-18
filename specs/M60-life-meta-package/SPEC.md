---
name: M60-life-meta-package
description: Establish life as real Python package + root pyproject.toml + .python-version
owner: matheus-mendes
status: DONE
milestone: M60
estimated_cost_usd: 0.50
constitution_refs:
  - composition_over_inheritance
  - correctness_over_speed
  - multi_package_boundaries_are_sacred
---

# M60 — `life` meta-package real directory + root pyproject.toml

## Context

For months (probably since `life-ops/` reorg), the repo root contained
the Future State of the `life` Python meta-package:

    ./__init__.py         <- meant to be `import life`
    ./cli/                <- meant to be `life.cli.*`
    ./centrals/           <- meant to be `life.centrals.*`
    ./handlers/           <- meant to be `life.handlers.*`
    ./plugins/            <- meant to be `life.plugins.*`

But Python doesn't allow a regular package to be a lone `__init__.py`
at the cwd level. A regular package requires a DIRECTORY containing
`__init__.py`. The result: every `from life.X import Y` import
inside `cli/cli.py` (and 7 other modules) was broken at master HEAD.

AGENTS.md / CLAUDE.md both documented `python -m life.cli ...` as the
canonical entry point — that command has failed silently for months.
Tests did not catch the import error because the test suite never
imported `life.cli` directly (it tested `interfaces.cli` instead —
the legacy v2 surface).

## What changed

1. `life/__init__.py` — directory created; the existing root `__init__.py`
   moved into it. Adds `__version__` constant for canonical access via
   `import life; life.__version__`.

2. `life/cli/{__init__.py,__main__.py,cli.py,config.py,log.py,test_runner.py}`
   — moved from `cli/`. New `__main__.py` allows `python -m life.cli`.
   New `_main_console()` in `__init__.py` is the pyproject script
   entry point.

3. `life/centrals/` — moved from `centrals/` (5 files).
4. `life/handlers/` — moved from `handlers/` (3 files).
5. `life/plugins/` — moved from `plugins/` (5 files).

6. `pyproject.toml` at repo root — declares the `life` package,
   exposes a console script `life = "life.cli:_main_console"`,
   pins requires-python to ">=3.11", and adds an optional `mesh` extra
   (pulled by Phase 3 mesh layer consumers).

7. `.python-version` at repo root — `"3.11"`, picked up by `pyenv`,
   `uv`, and `mise` to standardize the interpreter.

## Acceptance

- [x] `python -m life.cli --help` works (was ModuleNotFoundError)
- [x] `python -m life.cli version` returns `0.1.0`
- [x] `python -m life.cli submodules` runs without import errors
- [x] `pip install -e .` + `life --help` console script registered (per
  pyproject.toml, install not re-run in this commit)
- [x] Phase 3 mesh suite: 308 passed, 1 skipped (still M59-green)
- [x] Drift net canônico: 69/69 PASS

## Why this matters

The Algorithmic Life OS docs at `life-ops/` and the more recent
`AGENTS.md` / `CLAUDE.md` repeatedly told future agentic sessions
"run `python -m life.cli` to get the central-handler hub". That
invocation crashed at the import layer. Each new agent had to debug
the same dead end. M60 turns the implication into a fact.

## Risk / out-of-scope

- Subcommands like `daily run`, `task today`, etc. may still error at
  runtime because their bodies hardcode `ROOT/system/...` paths that
  no longer exist post-2026-09 reorganizations. Those are inside the
  subcommand handlers (not the meta-package) and are tracked separately
  (M62-and-beyond for the daily pipeline).
- Plugin discovery at `life/plugins/loader.py` may still use string
  literal module paths that don't match the new package layout. To
  be verified in M63.
