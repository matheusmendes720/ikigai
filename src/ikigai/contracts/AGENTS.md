# AGENTS.md — src/ikigai/contracts

## OVERVIEW
Meta-Planner **Proposal contracts** (Plan D Task A.1) — 11 frozen Pydantic v2 models in one file. Earned its file at score 9: only 2 files, but it is the highest-cross-boundary surface in the subtree (151 name references across 21 repo files, 10 external import sites) and a distinct domain from the runtime.

## STRUCTURE
```
src/ikigai/contracts/
├── __init__.py     # docstring only — no re-exports
└── proposal.py     # all 11 models + explicit __all__
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Approval flow | `proposal.py` → `Proposal` | `approval_state` ∈ `pending\|approved\|rejected\|rejected_safety\|partial`; `actor_approving` + `approval_timestamp` are the audit trail |
| One operation | `proposal.py` → `ProposalOperation` | `op_type` ∈ `vault_write\|taskdog_create\|data_tasks_append`; `vault_write` / `taskdog_create` carry the typed payload, the third has no payload field yet |
| Proposed vault write | `proposal.py` → `VaultWriteOp` | `entity_type` ∈ `sonho\|objetivo\|meta\|projeto\|entrega\|tarefa` |
| Proposed taskdog write | `proposal.py` → `TaskdogOp` | `priority` ∈ `H\|M\|L` |
| Intent signal | `proposal.py` → `IntentClassification` | `level` ∈ `high\|medium\|low`, `score` ≥ 0 — keyword-based, no LLM |
| Hierarchy match | `proposal.py` → `HierarchyMatch` / `HierarchyContext` | `sonho` → `objetivo` → `meta` → `projeto` |
| Provenance | `proposal.py` → `Traceability` | `memory_refs`, `folder_reads`, `adrs_consulted` — all three required |
| Execution outcome | `proposal.py` → `ExecutionReport` | `ops_total/completed/failed`, `status` ∈ `ok\|partial\|failed` |
| Consuming executor | `src/agents/v2/nodes/proposal_executor.py` | refuses anything with `approval_state != "approved"`; routes writes through `wrap_vault_write` |
| Producer chain | `src/agents/v2/nodes/meta_plan/` | `classify_intent` → `fetch_context` → `generate_proposal` |

## CONVENTIONS
- **Every model is `model_config = ConfigDict(frozen=True, extra="forbid")`** (ADR-009). Proposals are immutable and reject unknown fields — do not relax this.
- **`__all__` lists all 11 public names explicitly**; import from `src.ikigai.contracts.proposal`, not from `contracts` (that name belongs to the repo-root `src/contracts/` package).
- **The UEID regex is re-declared locally** as `_UEID_REGEX` and enforced by `Proposal._ueid_canonical` — ADR-014 4-part format `^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$`. It is **not** imported from `src/contracts/common.py`; the drift net pins the local copy.
- **`VaultWriteOp` has a field validator** (`_sonho_requires_user`) that refuses `actor_required != "user"` for `entity_type == "sonho"` — the Plan A transition validator.
- **Proposals are proposed, never executed.** `approval_state` starts at `"pending"`; only `execute_proposal` acts, and only after approval.

## ANTI-PATTERNS
- **NEVER** add a `DEFAULT_*` tuning constant here, and never add fields to a frozen model — the drift net and `extra="forbid"` make both a breaking change.
- **NEVER** treat a `Proposal` as an execution order. Skills and meta-plan nodes emit proposals; the executor is the only component that acts, and only on `approved`.
- **NEVER** bypass `Proposal._ueid_canonical` by constructing a proposal with a hand-built id — the 4-part UEID check is the ADR-014 gate.
- **NEVER** reuse the `contracts` import name for this package in new code — it collides with the canonical repo-root `src/contracts/` package.

## NOTES
- The repo-root `src/contracts/` package holds the canonical cross-layer models (`UEID`, `Task`, `TaskChange`, `QHEScore`). This package is **not** a second copy of those — it is the Meta-Planner proposal vocabulary, and it intentionally re-declares the UEID pattern locally.
- `chat/schema.py` validates a **looser** UEID pattern (`^[a-z]{2,10}:…`) and `vault_intent_extract._gen_ueid` emits a **5-part** UEID — both drift away from ADR-014 and are known inconsistencies, not a second standard.
