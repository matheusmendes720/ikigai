# Router - the dispatch table for cloud agents

**Status:** specification (2026-11-02)
**Scope:** how an agent operating the published repository finds its prompt, its skill and its cadence.
**Anchor:** [ADR-037](../../code-docs/adr/ADR-037-data-layer-canonical-turn.md)
**Companion:** [SYSTEM-PROMPTS.md](./SYSTEM-PROMPTS.md) · [SKILL-SPECS.md](./SKILL-SPECS.md)

This is the entry point. An agent that reads only this file knows where everything else is.

There is exactly one source for each kind of artifact, and this table points at it:

| What | Where it lives |
|------|----------------|
| The system prompts, one per role | `specs/harness/SYSTEM-PROMPTS.md` |
| The skill contracts, one per routine | `specs/harness/SKILL-SPECS.md` |
| The portable projection of the runtime skills | `specs/harness/skills/<id>/SKILL.md` |
| The conceptual material | `strategics/`, indexed by `strategics/00-ÍNDICE-PROGRESSIVO.md` |
| The domain model and the schema | `src/contracts/` |

The portable skills are a projection, not a second source. When they and `SKILL-SPECS.md` disagree, `SKILL-SPECS.md` wins and the projection is the stale copy.

---

## 1. Reading order for a cold agent

1. `AGENTS.md` at the repository root, then the `AGENTS.md` of the subtree you are about to touch.
2. `code-docs/adr/ADR-037-data-layer-canonical-turn.md` — the scope you work in.
3. `code-docs/adr/ADR-013-canonical-scope-discipline.md` — what the agent layer may not do.
4. `specs/harness/router.md` — this file.
5. The prompt for your role, from `specs/harness/SYSTEM-PROMPTS.md`.
6. `strategics/00-ÍNDICE-PROGRESSIVO.md` — when your role needs the conceptual vocabulary.

Stop there. The skills are read when the routine starts, not before.

---

## 2. Roles

| Role | Bootstrapping prompt | Skills it may run | Cadence |
|------|---------------------|-------------------|---------|
| Orientation | 1 - Repo orientation and canonical scope | none | once, first turn |
| Writer | 2 - Writing to the store | `store-write` | on demand |
| Reader | 3 - Reading from the store | `store-read` | on demand |
| Ingestor | 4 - Vault ingestion | `vault-sync` | when the prose changes |
| Planner | 5 - Planning cycle over the DOM | `store-write`, `store-read` | on demand |
| Cadence runner | 6 - Cadence routines | `daily-note`, `weekly-review`, `monthly-review`, `quarterly-plan` | by the cycle |
| Maintainer | 7 - Contract and drift discipline | `contract-change-drift-test`, `ci-green-gate` | before a push |
| Releaser | 8 - Security hygiene, then `release-deploy` | `release-deploy` | on a deploy |

The three engineering skills — `contract-change-drift-test`, `ci-green-gate` and `release-deploy` — are defined in `SKILL-SPECS.md` only. They act on the repository rather than on the store, so they have no portable projection under `skills/`.

An agent may hold more than one role. A cadence runner reads and writes; that is expected.

---

## 3. Cadences

| Routine | Skill | Produces | Conceptual source in `strategics/` |
|---------|-------|----------|-----------------------------------|
| Daily | `daily-note` | `nota` | `Análise (Tático e Operacional).md` — daily blocks and daily report |
| Weekly | `weekly-review` | `revisao` | `Desempenho Subjacente.md` — five-day consolidation; `Hierarquia de Objetivos.md` — the review template |
| Monthly | `monthly-review` | `desc` | `Hierarquia de Objetivos.md` — the monthly review; `Desempenho Subjacente.md` — the quarterly consolidation |
| Quarterly | `quarterly-plan` | `plano` with `fase`, `okr`, `onda` | `Modelagem Operacional.md` — the levels and cycles; `Planejamento (Estratégico e Tático).md` — the planning, the 5x3x3 proportion, the Teste de Fogo |

The proportion behind the cadence: five days of execution, three weeks of analysis, three months of planning. The 45-day `onda` is the cycle; the 180-day macro-phase is the quarter.

---

## 4. Rules that hold across every role

| Rule | Where it is enforced |
|------|---------------------|
| Contracts are Pydantic v2, frozen, extra forbidden. Import a model, never redefine one. | `src/contracts/dom.py`, `src/contracts/dom_kinds.py` |
| The UEID pattern has exactly one source. Never hand-build an identifier. | `src/contracts/common.py` |
| One writer per store. The agent never writes SQL. | `src/services/artifacts.py`, `src/transport/mcp_server.py` |
| A stale `expected_revision` is a conflict. Never force the write. | `src/services/artifacts.py` |
| Every write carries a non-empty `idempotency_key` and a `client_id`. | `src/services/artifacts.py` |
| The vault is append-only. The cloud agent writes to the store, not to markdown. | `src/services/sync.py` |
| Hierarchy is relations, not duplicated fields. | `src/contracts/dom.py` |
| Drift tests are append-only. Never delete one, never weaken one. | `src/ikigai/tests/` |
| No secret, token or connection string in a tracked file, an artifact or a log line. | `src/contracts/store.py` names the variable |
| A suite that did not run is not a passing suite. | `src/ikigai/tests/` |

---

## 5. Failures you will actually hit

| Failure | What it means | What to do |
|---------|---------------|------------|
| `CONFLICT` | Another client wrote first. The `expected_revision` you sent is stale. | Call `get_artifact`, read the current revision, decide whether your change still applies, reapply with the new revision. Report both attempts. Never force. |
| `NOT_FOUND` | No artifact with that uid, or the store has no row for it. | Search for it instead of guessing. Report that it does not exist. Do not reconstruct it from a neighbour. |
| `FORBIDDEN` | The row level security policy rejected the read or the write. The `client_id` does not match the claim the policy compares. | Check the `client_id` you are sending. Report it. Do not attempt to reach the row by another route. |
| `VALIDATION` | The payload broke the contract: a missing body on a prose kind, a missing `metric` on a `kpi`, a malformed uid, an empty `idempotency_key`. | Read the error, fix the payload, retry. The contract is not negotiable. |
| The store is unreachable | The connection failed. There is no local fallback for canonical state. | Report it as a system error with the context. Do not write to the filesystem instead. |
| A skill says a command does not exist | The routine needs something the tree does not have yet. | Report the gap with the file that should carry it. Do not invent the command. |

---

## 6. What is not published

The previous scope is not in the published tree and must not be created: the operator CLI, the fork mesh, the local vector store, the legacy entity model with its state machines, the legacy harness, and the legacy runtime contracts under `sys_ikigai/`. If a routine appears to need one of them, that is a gap in the routine, not a reason to resurrect the surface.

The contracts under `src/contracts/` ARE published — both the unified DOM and the plan hierarchy the vault prose is written against. The DOM's kinds carry `plan_tier` and `ikigai_vectors`, so the two families share a vocabulary and cutting either would break the other.

There is no algorithmic layer in the published tree yet. The hysteresis, the regime and the policy math come after every architectural layer is stable. The DOM is shaped to receive them: `kpi` carries `target`, `actual` and `direction`, `okr` carries `kr_target`, `kr_actual` and `kr_progress`, `desc` carries `rationale` and `outcome`.
