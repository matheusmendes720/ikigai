---
name: M78-invoke-skill-cli
description: CLI subcommands `life invoke-skill <name>` and `life skill-list`; 5 smoke tests pass
owner: matheus-mendes
status: DONE
milestone: M78
estimated_cost_usd: 0.20
constitution_refs:
  - correctness_over_speed
  - tests_are_the_contract
  - composition_over_inheritance
---

# M78 — invoke-skill CLI surface

## Context

M77 built `invoke_skill()` as a Python function. M78 exposes it via
the CLI so users can run `life invoke-skill ikigai-quarterly` and get
the same end-to-end behavior (manifest load + LLM stub + taskdog
post-processor + review_queue on failure).

## What changed

### interfaces/cli/v2.py

Added two new Typer commands following the existing `register_plan` pattern:

```python
register_invoke_skill(app)   # `life invoke-skill <name>`
register_skill_list(app)      # `life skill-list`
```

`invoke-skill` signature:
- `<name>` (positional, required): skill name like ikigai-daily
- `--entry-point / -e <str>`: override manifest's entry_point
- `--actor / -a <str>`: actor (user|agent|system), default agent

`skill-list` signature: no args. Returns JSON with all 5 skills
(name, description, entry_point, actor, outputs_count, fires_taskdog).

### NEW tests/interfaces/test_invoke_skill_cli.py

5 CLI smoke tests:
1. `invoke-skill --help` exits 0 + shows W3.5/W3.6 description
2. `skill-list` returns 5 skills with ikigai-daily/weekly/monthly/quarterly
3. `skill-list` correctly marks `fires_taskdog: true` for quarterly/weekly, false for daily/monthly
4. `invoke-skill ikigai-daily` runs without taskdog (empty outputs)
5. `invoke-skill ikigai-nonexistent` returns structured error dict

## Acceptance

- [x] tests/interfaces/test_invoke_skill_cli.py : 5/5 PASS
- [x] tests/ root : 318 PASS + 27 SKIP, 0 FAIL (was 313 + 27)
- [x] End-to-end: `life invoke-skill ikigai-daily` returns
       {"skill": "ikigai-daily", "entry_point": "surface_intentions", ...}
- [x] End-to-end: `life skill-list` returns 5 skills with correct
       `fires_taskdog` flags per manifest

## Usage

```bash
# List available skills
life skill-list

# Run a skill
life invoke-skill ikigai-daily --actor agent
IKIGAI_FAKE_LLM=1 life invoke-skill ikigai-quarterly
```

## Out of scope (M79+)

- Wire to cron (auto-fire ikigai-daily at scheduled times)
- `life skill show <name>` (introspect a single manifest)
- Real LLM integration (currently FAKE_LLM=1 stub only)
- Per-skill input validation (manifest `inputs` field)

## Lessons

- Typer `register_*` functions take `app` as parameter (not at module
  top-level) per Plan D Task E.1 circular-import fix. Same pattern
  works for the new commands.
- Lazy `from .invoke_skill import invoke_skill as _invoke_skill`
  inside the function body defers the import until first CLI call.
