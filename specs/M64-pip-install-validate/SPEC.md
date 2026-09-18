---
name: M64-pip-install-validate
description: Validate life installs cleanly via pip install -e . and the life console script works without PYTHONPATH
owner: matheus-mendes
status: DONE
milestone: M64
estimated_cost_usd: 0.20
constitution_refs:
  - composition_over_inheritance
  - tests_are_the_contract
---

# M64 — Validate `pip install -e .` + console script `life`

## Context

After M60 introduced `pyproject.toml` with `[project.scripts] life =
"life.cli:_main_console"`, the install pathway was never validated
end-to-end. The CLI worked via `python -m life.cli` because the
`pytest.ini` `pythonpath = src` shim, but the documented `pip install
-e .` then `life --help` path was untested.

## What changed (M64)

This milestone validated the install pathway in an isolated venv.
**No source changes**; pure validation.

1. Created ephemeral `uv venv --python 3.11 .venv-test-install` (23MB).
2. Installed project deps with `uv pip install --python <py> <deps>`.
3. Ran `uv pip install --python <py> -e .` from repo root.
4. Verified console script `life.exe` was created at
   `.venv-test-install/Scripts/life.exe`.
5. Ran `life --help`, `life version`, `life submodules`,
   `life config-show`, `life log --path` — all 5 RC=0.
6. Ran `life --help` from `C:\Windows\Temp` (foreign cwd) to
   confirm the install is not cwd-dependent.
7. Cleaned up: `rm -rf .venv-test-install`.

## Acceptance

- [x] `pip install -e .` from repo root succeeds (RC=0) and reports
  `Installed 1 package: life==0.1.0`
- [x] Console script `life` is on PATH (at `.venv-test-install/Scripts/`)
- [x] `life --help` produces the Typer root command listing (RC=0)
- [x] `life version` returns `0.1.0`
- [x] `life submodules` lists configured submodules (with stale
  `life/system/...` paths, see out-of-scope below)
- [x] `life config-show` shows config defaults (including the stale
  ROOT resolution, see out-of-scope)
- [x] `life log --path` returns canonical log path
- [x] `life --help` from arbitrary cwd (`C:\Windows\Temp`) still RC=0
- [x] Drift net + chat invariants still 26+13=39/39 PASS

## Out of scope (M65+ candidate)

- `LifeConfig` defaults hardcode `root` such that the canonical
  submodule paths resolve to `life/system/...` — pre-existing bug,
  pre-M60 era. The config defaults predate the M60 meta-package
  restructure; they live in `life/cli/config.py::DEFAULT_SUBMODULES`
  and friends. M65 candidate: rewrite `cfg.root` resolution to
  walk up from `life.cli.config` until it finds the project root
  (the one containing `pyproject.toml`), then map
  `<root>/<submodule>` for each DEFAULT_SUBMODULE.
- Hardcoded `submodules/job_offers`, `knowledge/leitura`, etc. — these
  were added before the reorg; they do not exist under the live
  `life/` layout. A `.life` sub-toml-driven config would be cleaner
  but is out of M64 scope.
