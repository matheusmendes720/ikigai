---
name: M180-paperclip-hil-resume
description: Paperclip HIL resume — Command(resume) propagation, audit trail, hil_apply_user_resolution node.
status: DONE
owner: matheus-mendes
created: 2026-10-12
constitution_refs:
  - tests_are_the_contract
  - state_on_disk_not_conversation
  - composition_over_inheritance
estimated_cost_usd: 0.00
---

# M180 — Paperclip HIL Resume (Audit Trail + Graph Topology)

**Status:** DONE
**Date:** 2026-10-12
**Author:** matheus-mendes (with Claude Code assist)

---

## TL;DR

M180 adds an **audit-trail consumer node** between Paperclip's existing
`hil_pause` (which calls `interrupt()`) and `merge_user_resolution` (which
merges the resume payload into `spec_text`). The new node,
`hil_apply_user_resolution`, increments a `hil_resume_count` counter and
stamps an ISO timestamp on every user resume, then writes a structured
system message to the LangGraph `messages` channel describing the payload
(answer length + whether `rewritten_spec` was provided).

The graph grows from 9 → 10 nodes. Drift net grows **72 → 75** (+3: 1
paperclip drift + 2 from pre-existing paperclip drift that was already
in the file as of M180 prep). The `hil_pause_node` itself is unchanged
— M180 adds the receiving end of the `Command(resume=...)` payload.

---

## What changed

```
src/ikigai/src/agents/paperclip/state.py                       # +2 fields
src/ikigai/src/agents/paperclip/nodes/hil_pause.py             # +hil_apply_user_resolution_node
src/ikigai/src/agents/paperclip/graph.py                       # +node, +edge, +routing fn
src/ikigai/src/agents/paperclip/tests/test_hil_pause.py        # +5 tests
src/ikigai/src/agents/paperclip/tests/test_graph_smoke.py      # EXPECTED_NODES 9 -> 10
src/ikigai/tests/test_paperclip_drift.py                       # +1 drift invariant
.claude/loop/roadmap.md                                        # M180 row
specs/M180-paperclip-hil-resume/SPEC.md                         # this file
```

**Total: 4 modified source files + 2 modified test files + 2 new files
(this SPEC + directory). Drift net 72 → 75.**

The `hil_pause_node` itself is unchanged. The fallback
`RuntimeError("PAPERCLIP_HIL_PAUSE: ...")` path is preserved (it's the
load-bearing fallback when `langgraph_sdk` isn't importable). M180 adds
a CONSUMER node for the resume payload — the INTERFACE for resume is
what changed in this milestone.

---

## Architecture decisions

### D16 — New node `hil_apply_user_resolution` sits between `hil_pause` and `merge_user_resolution`

Graph topology (new edges in bold):

```
read_spec → spec_analyzer ⇄ (hil_pause → hil_apply_user_resolution → merge_user_resolution → spec_analyzer)
                       ↘
                        worktree_create → implement ⇄ (test fail → implement)
                                            ↘
                                             worktree_commit → worktree_merge → worktree_cleanup → END
```

Two new edges: `hil_pause → hil_apply_user_resolution` and
`hil_apply_user_resolution → merge_user_resolution`. The new routing
function `_route_after_hil_apply` mirrors `_route_after_hil_pause`:
checks `error_type` (END) or always routes to `merge_user_resolution`.

### D17 — `hil_apply_user_resolution` does NOT touch spec_text

The audit-trail node is intentionally narrow: it bumps counters,
stamps a timestamp, writes a chat-channel message, and sets
`last_step`. It does NOT call `merge_user_resolution_node` or modify
`spec_text`. The actual spec-text merge remains `merge_user_resolution`'s
job. This separation is deliberate — it keeps the audit logic unit-
testable in isolation from the spec-text merge logic, and matches the
fail-CLOSED philosophy of "one node per role, easy to test."

### D18 — Resume count starts at 0, missing → 1

`hil_resume_count` is `NotRequired[int]`. The first call to
`hil_apply_user_resolution_node` reads `state.get("hil_resume_count") or 0`
and writes back `1`. Subsequent calls increment from whatever the prior
value was. Missing field → first resume; this matches the pattern in
`merge_user_resolution_node` for `gap_iteration`.

### D19 — `hil_last_resume_at` is ISO 8601 UTC

Stamped with `datetime.now(UTC).isoformat()` at the moment the node runs.
Future-proofs downstream consumers that need to compute "time since last
resume" without parsing a free-form timestamp.

### D20 — Audit message is structured (not free-form prose)

The `messages` channel gets one structured entry per resume:

```python
{
    "role": "system",
    "content": (
        "paperclip: HIL resume applied at iteration "
            f"{state.get('gap_iteration', '?')} (resume #{current_count + 1}; "
            f"answer_provided={answer_provided}; rewritten={rewrite_provided})"
        )
}
```

A triager reading the chat channel can see exactly which iteration the
resume happened in, which resume count it was, and whether the user
provided just an answer or a full rewrite. The audit message format is
deliberately grep-friendly (the leading `paperclip: HIL resume applied`
prefix is unique enough to filter on).

---

## Verification

```bash
# 1. HIL pause tests — must show 17/17 PASS (was 12 + 5 new M180)
python -m pytest src/ikigai/src/agents/paperclip/tests/test_hil_pause.py -v

# 2. Full paperclip suite + drift — must show 65 PASS (was 58 + 5 new HIL + 1 drift + 1 graph_smoke EXPECTED_NODES update)
python -m pytest src/ikigai/src/agents/paperclip/tests/ src/ikigai/tests/test_paperclip_drift.py -v

# 3. Drift net — must show 75 passed, 2 pre-existing skipped (was 72 + 3 = +1 M180 drift + 2 already in file)
python -m pytest src/ikigai/tests/test_drift_invariants.py \
                  src/ikigai/tests/test_drift_extended_invariants.py \
                  src/ikigai/tests/test_canonical_scope.py \
                  src/ikigai/tests/test_paperclip_drift.py

# 4. Lint + format (on M180-modified files only — pre-existing ruff
#    warnings in paperclip/cli.py are NOT in scope for M180)
python -m ruff check src/ikigai/src/agents/paperclip/nodes/hil_pause.py \
                      src/ikigai/src/agents/paperclip/state.py \
                      src/ikigai/src/agents/paperclip/graph.py \
                      src/ikigai/src/agents/paperclip/tests/test_hil_pause.py \
                      src/ikigai/src/agents/paperclip/tests/test_graph_smoke.py \
                      src/ikigai/tests/test_paperclip_drift.py
python -m ruff format --check <same files>

# 5. Sanity: importable, callable, returns expected shape
python -c "
from src.ikigai.src.agents.paperclip.nodes.hil_pause import hil_apply_user_resolution_node
from src.ikigai.src.agents.paperclip.state import PaperclipStateDict
state = PaperclipStateDict(task_id='t', spec_text='any',
    user_resolution={'answer':'use Flask', 'rewritten_spec':''},
    gap_iteration=1)
print(hil_apply_user_resolution_node(state))
"
# Expect: {'hil_resume_count': 1, 'hil_last_resume_at': '2026-...',
#          'last_step': 'hil_apply_user_resolution', 'messages': [...]}
```

---

## Acceptance

- [x] `state.py` declares `hil_resume_count: NotRequired[int]` and
      `hil_last_resume_at: NotRequired[str | None]`
- [x] `nodes/hil_pause.py` exports `hil_apply_user_resolution_node`
      (callable; takes `PaperclipStateDict`; returns dict with the
      four expected keys)
- [x] `graph.py` registers `hil_apply_user_resolution` in `NODES`,
      adds the `_safe_node` wrapper, the two new conditional edges, and
      the new `_route_after_hil_apply` routing function
- [x] `merge_user_resolution_node` is UNCHANGED — M180 is purely
      additive; the existing 12 HIL/merge tests still pass without
      modification
- [x] 5 new tests in `test_hil_pause.py` covering: count increment,
      audit-message content, spec-rewrite path, answer-only path, graph
      registration topology
- [x] 1 new drift invariant in `test_paperclip_drift.py`:
      `test_paperclip_hil_apply_user_resolution_node_exists`
- [x] 1 smoke test update in `test_graph_smoke.py`:
      `EXPECTED_NODES` set grew from 9 → 10
- [x] Drift net: **72 → 75** (+3)
- [x] `ruff check` + `ruff format --check` clean on all M180-modified files
- [x] `hil_apply_user_resolution_node` callable, accepts partial state
      (no `hil_resume_count` pre-set → bumps to 1)

---

## Lessons

1. **Narrow scope = easy tests.** The new node does NOT touch
   `spec_text` (that's `merge_user_resolution`'s job) and does NOT
   route anywhere other than `merge_user_resolution` (graph.py
   handles routing). Narrow responsibility → 5 focused tests cover
   the entire surface.

2. **Audit trail lives in the chat channel + counter fields, not in
   a side-channel log file.** Triagers can read `messages` directly
   in LangGraph Studio; no need to grep a separate audit log. The
   `hil_resume_count` + `hil_last_resume_at` fields give the
   "how-many + when" answer without parsing prose.

3. **Pre-existing ruff warnings are NOT in scope for M180.** The
   paperclip CLI (`cli.py`) has 8 pre-existing ruff errors
   (`Optional[bool]` → `X | None` + unsorted imports) that are
   unrelated to HIL resume. They were present in M169/M173/M175/M176
   and remain in M180 — fixing them is a separate cleanup, not part
   of M180 scope. M180's verification runs ruff on its modified
   files only and accepts the pre-existing CLI warnings as out-of-
   scope.

---

## Related

* [M169 Paperclip spec](file:///C:/Users/mathe/code_space/life-oss/life/specs/M169-paperclip/SPEC.md)
  — the 4th LangGraph graph that owns `hil_pause` + `merge_user_resolution`
* [M174 auto-spawner](file:///C:/Users/mathe/code_space/life-oss/life/specs/M174-paperclip-auto-spawner/SPEC.md)
  — the spawner script that may eventually trigger HIL pause
* [M173 cost gate](file:///C:/Users/mathe/code_space/life-oss/life/specs/M173-paperclip-cost-gate/SPEC.md)
  — the first auto-throttle (fail-OPEN)
* [M175 wall-clock gate](file:///C:/Users/mathe/code_space/life-oss/life/specs/M175-paperclip-wall-clock-gate/SPEC.md)
  — the second auto-throttle (fail-OPEN)
* [M176 risk gate](file:///C:/Users/mathe/code_space/life-oss/life/specs/M176-paperclip-risk-gate/SPEC.md)
  — the third auto-throttle (fail-CLOSED)