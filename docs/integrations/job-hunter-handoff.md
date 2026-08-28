# job_hunter ↔ life/ — Pause Handoff (Life-Side Reference)

> **Created:** 2026-08-28
> **Purpose:** Single pointer in `life/` for resuming job_hunter integration work.
> **Status:** Integration is **SPEC-ONLY** — no code, no consumer in `life/` consumes `job_hunter/data/jobs.jsonl` yet.

---

## TL;DR

`job_hunter` paused at **`v0.1.2`** on `main` (13 commits, SL1 + F1–F13). The
PDR §6.3 / §7 / §11 plans for integrating with `life/` are **drafted but not
started** because:
1. `life/` has no reader of `job_hunter/data/jobs.jsonl`
2. Per memory `job-hunter-life-integration-spec-only.md`: "nao tem nada pronto
   por la para ingerirmos de dados"

**To resume integration**, build the consumer side first (in `life/`); then
job_hunter-side producers have a reason to exist.

---

## Where the canonical artifacts live

**In `job_hunter/` (primary workspace):**
| What | Path |
|------|------|
| Handoff (state + resume procedure) | `C:\Users\mathe\code_space\job_hunter\HANDOFF.md` |
| Commit changelog (F1–F13) | `C:\Users\mathe\code_space\job_hunter\CHANGELOG.md` |
| PDR (master spec, with §6.3/§7/§11 SUPERSEDED trailers) | `C:\Users\mathe\code_space\job_hunter\PDR.md` |
| Next-phases specs (SL2/§1, SL3/§2, etc.) | `C:\Users\mathe\code_space\job_hunter\docs\ROADMAP.md` |
| Source code | `C:\Users\mathe\code_space\job_hunter\src\job_hunter\` |
| Tests (1759 lines, 67 cases) | `C:\Users\mathe\code_space\job_hunter\tests\test_cli.py` |
| Runtime data (gitignored) | `C:\Users\mathe\code_space\job_hunter\data\jobs.jsonl` + `*.migrated.jsonl` sidecars |

**In this `life/` workspace:**
| What | Path |
|------|------|
| This file | `life/docs/integrations/job-hunter-handoff.md` |

**In persistent memory:**
| What | Path |
|------|------|
| User acceptance of F1–F13 | `~/.claude/projects/.../memory/job-hunter-f1-f13-accepted-2026-08-28.md` |
| SPEC-ONLY directive | `~/.claude/projects/.../memory/job-hunter-life-integration-spec-only.md` |
| No-auto-apply guardrail | `~/.claude/projects/.../memory/linkedin-no-auto-apply.md` |

---

## What Would "Integration" Look Like?

Per PDR §6.3 / §7 / §11 — these are DRAFTS, not active work:

1. **life/ reads** `job_hunter/data/jobs.jsonl`
2. **life/ produces** `data/tasks.jsonl` (TaskChange mesh) with:
   - "Follow up with <company>" if `last_update > 7 days ago` and `status == applied`
   - "Prepare interview for <company>" if `status == technical` and interview_date is set
3. **life/ feeds** the IKIGAI Market vector with `job_hunter` metrics:
   - `market_score = 0.4·response_rate + 0.3·velocity_norm + 0.2·offer_pipeline + 0.1·source_diversification`
4. **life/ weekly_consolidator** includes job_hunting time allocation:
   - `weekly_allocation = {discovery, applications, follow_ups, interview_prep, sonho_reflection}`

### Why draft-not-implemented

- **Standalone rule** (from `life/CLAUDE.md`): `job_hunter/` imports nothing from `life/`
- **Append-only rule**: integration writes go through `data/review_queue/` mesh, not directly to life/
- **No consumer today**: no `life/` code reads from `job_hunter/`; building the producer end is dead code

---

## Resume Decision Tree

When user comes back:

```
                   ┌─────────────────────────────────────┐
                   │ User returns to job_hunter work     │
                   └────────────────┬────────────────────┘
                                    │
                                    ▼
            ┌───────────────────────────────────────────────┐
            │ Is life/ interested in the integration now?  │
            └───────┬─────────────────────────┬─────────────┘
                    │                         │
                  YES                        NO
                    │                         │
                    ▼                         ▼
    ┌───────────────────────────┐    ┌──────────────────────────┐
    │ Build life/ consumer     │    │ Stay SPEC-ONLY           │
    │ first (mesh reader of    │    │ Resume job_hunter only:  │
    │ jobs.jsonl). Once stable,│    │ §1 SL2 importer OR       │
    │ then job_hunter side     │    │ §2 SL3 metrics           │
    │ becomes §5 in            │    │ (no integration code)    │
    │ job_hunter/ROADMAP.md    │    └──────────────────────────┘
    └───────────────────────────┘
```

---

## Invariants That Cross the Boundary (must be preserved)

These invariants from `life/CLAUDE.md` apply to job_hunter integration when/if it ships:

| Invariant | How job_hunter respects it |
|-----------|-----------------------------|
| UEID 5-part canonical | `_UEID_SALT_V1 = b"jh_v1_2026_08"`, regex `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$` (mirrors `life/src/contracts/common.py`) |
| Pydantic v2 strict (`frozen=True`, `extra="forbid"`) | All `models.py` classes use it |
| Append-only | `data/jobs.jsonl` is append-only; legacy 4-part records preserved in `*.migrated.jsonl` sidecar |
| `--json` everywhere | CLI's `add`/`list`/`update`/`show`/`delete`/`migrate-sidecar` all support `--json` |
| Zero LLM in pipelines | Scoring (when/if implemented) is pure arithmetic per PDR §6.2 — no LLM |
| Fully local | SQLite + filesystem only; `data/` is gitignored |

---

## What is NOT in `life/` Because of This Pause

These would have been the natural additions once integration started, but
per SPEC-ONLY directive they do not exist:

- ❌ `life/src/agents/job_hunter/` (reader agent)
- ❌ `life/src/contracts/job_application.py` (mirror of `job_hunter/models.py`)
- ❌ `life/src/mesh/adapters/job_hunter.py` (mesh fork adapter for job_hunter)
- ❌ `life/data/review_queue/job_hunter/` (review queue for cross-fork writes)
- ❌ `life/interfaces/cli/mesh/job_hunter_show.py` (mesh show for job_hunter UEIDs)
- ❌ `life/data/jobs.jsonl` (consumer-owned copy of job_hunter data)

When **§5 of `job_hunter/docs/ROADMAP.md`** is unblocked, these become the
implementation targets (with cross-workspace branch isolation:
`feat/job-hunter-mesh-adapter` in `life/` + `feat/life-consumer-emitter`
in `job_hunter/`).

---

## Final State Confirmed at Pause (2026-08-28)

From `job_hunter/`:
- `git tag -l 'v0.*'` → `v0.1.0`, `v0.1.1`, `v0.1.2`
- 13 commits in `bbc97f0..d701bc2` range
- 67/67 tests pass
- `ruff check`, `ruff format --check` clean

From `life/` (this workspace):
- 4 SUPERSEDED-trailer commits to docs (data-model-unification-design, ikigai-vault-layers-design, decision-questionnaire ADR-008..011, decision-package appendix ADR-008..011, cross-cutting-triage ADR-008..011)
- No code touched by job_hunter pause cycle
- This pointer file added

---

*Companion file: `job_hunter/HANDOFF.md` (canonical state) + `job_hunter/CHANGELOG.md`
(commit history) + `job_hunter/docs/ROADMAP.md` (next phases). Do not edit this file
without updating those three in lockstep.*
