# Life-OSS Constitution

> **The principles that every tick of the loop is checked against.**
> Update only by human decision. This file gates every milestone.

## Core Principles (in order of priority)

### 1. Correctness > Speed
- A test that fails is a feature, not a bug
- Never skip `pytest` to "save time" — the test is the safety net
- A wrong implementation committed is worse than no implementation

### 2. Reversibility > Cleverness
- Every change must be revertable in < 5 minutes
- No "clever" code that no one understands
- If you can't explain it in 3 sentences, simplify it
- **No defensive code for impossible states** (Ronacher's warning)

### 3. Composition > Inheritance
- Prefer `from src.mesh.adapters import CliAdapter` over reimplementing
- New code uses existing contracts (`UEID`, `Task`, `TaskChange`)
- Reuse: Pydantic v2 frozen models, FastMCP patterns, LangGraph graph factory

### 4. Tests are the contract
- New feature → new test (in same commit)
- Bug fix → regression test (in same commit)
- Refactor → existing tests must pass
- Coverage threshold: 85% (enforced in `pytest.ini`)

### 5. State on disk, not in conversation
- Every state transition writes to a file (markdown, JSON, SQLite)
- Never depend on the agent's "remembering" — read from `.claude/loop/`
- `.swarm/memory.db` is the cross-session memory layer

### 6. Multi-package boundaries are sacred
- `src/operational/` (uv workspace) — PAV kernel
- `src/ikigai/` (Poetry) — IKIGAI meta-brain
- `src/life_tatics/` (no manifest) — Time-Tactics
- `src/mesh/` (uv root) — Phase 3 v1 data mesh
- `src/contracts/` (uv root) — Pydantic v2 shared contracts
- `vibe-ops/` (uv) — Cybernetic engine
- Root `life` CLI — Typer hub
- **Do NOT cross-import between these without explicit human approval.**

### 7. Spec-driven, not vibe-driven
- Every implementation traces back to `specs/*/SPEC.md` or `centrals/*`
- `AGENTS.md` and `CLAUDE.md` are the source of truth for operational rules
- Updates to either require human review (no agent self-edit)

## Anti-Patterns (FORBIDDEN)

### ❌ Defensive code for impossible states
```python
# WRONG
def process_task(task: Task) -> None:
    if task is None:  # task is non-nullable, this is impossible
        raise ValueError("task is None")
    ...
```

### ❌ Re-implementing existing contracts
```python
# WRONG — UEID is already in src/contracts
class TaskID(NamedTuple):
    cluster: str
    entity: str
    ...
```

### ❌ Skipping tests to ship faster
```python
# WRONG — commit with "WIP" or "TODO: test"
def calculate_metric(data):
    # TODO: add test
    return data.sum() / data.count()
```

### ❌ Modifying AGENTS.md/CLAUDE.md without human
The agent CAN read these, but CANNOT modify them. The hill-climb loop can PROPOSE updates, but a human merges.

## Gate Process (every tick)

Before marking a milestone as PASS, the verifier checks:

1. ✅ All deterministic gates pass (`pytest -x`, `ruff check .`, `mypy .`)
2. ✅ Verifier JSON scores meet threshold (avg ≥ 4.0, no score < 3)
3. ✅ No constitution violation (none of the anti-patterns above)
4. ✅ Commit is atomic and revertable
5. ✅ Spec acceptance criteria are met (per `specs/*/SPEC.md`)

If ANY fails → FAIL or NEEDS_FIX.

## How to amend this file

1. Propose the change in a new `progress.md` entry as `CONSTITUTION_PROPOSAL`
2. Wait for human review
3. Human edits the file directly
4. Future ticks gate against the new constitution
