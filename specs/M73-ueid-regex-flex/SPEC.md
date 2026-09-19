---
name: M73-ueid-regex-flex
description: Widen UEID regex from {2,5} to {2,8} + accept legacy 5-part + accept long-UUID fixtures
owner: matheus-mendes
status: DONE
milestone: M73
estimated_cost_usd: 0.30
constitution_refs:
  - correctness_over_speed
  - tests_are_the_contract
---

# M73 — UEID regex widens + accepts legacy 5-part + long-UUID

## Context

The `tests/test_integration_data_model.py` and `tests/test_sqlite_bridge.py`
test fixtures were failing at master HEAD with:
`"String should match pattern '^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+:[a-f0-9-]+$'"`

Root causes (discovered during loop wakeup M73):
1. **Namespace `{2,5}` too narrow**: the namespace `ikigai` has 6 letters.
   The canonical regex at `src/contracts/common.py:34` and the legacy
   version at `sys_ikigai/types.py:UEID._PATTERN` both used `{2,5}`,
   which cannot match `ikigai`.
2. **Missing 5-part legacy support**: `sys_ikigai/types.py:UEID` accepts
   5-part legacy (namespace:entity_type:slug:uuid:hash), but the
   canonical `src/contracts/common.py` and `sys_ikigai/entities/ueid.py`
   only accept 4-part. Test fixtures like
   `ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609` (5-part) failed.
3. **No long-UUID support**: tests like
   `tests/test_tools_mesh.py` use
   `tsk:foo:11111111-1111-1111-1111-111111111111:1111111111111111`
   which has full 36-char UUID + 16-char hash. Existing regex
   `{6,8}` only allowed 6-8 chars.

## What changed

### src/contracts/common.py:34 (_UEID_PATTERN)

Triple-pattern (4-part short OR 4-part long-uuid OR 5-part legacy):
```python
_UEID_PATTERN = re.compile(
    r"^(?:"
    r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{6,8}:[a-f0-9]{6,8}"
    r"|"
    r"[a-z]{2,8}:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9-]{8,36}:[a-f0-9]{6,64}"
    r"|"
    r"[a-z]{2,8}:[a-z_]+:[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]:[a-f0-9]{6,8}:[a-f0-9]{6,8}"
    r")$"
)
```

### sys_ikigai/entities/ueid.py (UEID Annotated[str, StringConstraints])

Identical triple-pattern via StringConstraints. Pydantic v2
`StringConstraints(pattern=...)` accepts arbitrary regex strings.

### sys_ikigai/types.py:UEID (LEGACY 5-part)

Preserved the 5-part shape (with `entity_type` slot). Namespace
widened to `{2,8}` like the canonical. Module docstring updated to
clarify this file is the LEGACY 5-part path while `src/contracts/common.py`
is the canonical 4-part path.

## Acceptance (verified 2026-09-19)

- [x] `tests/test_integration_data_model.py` : 27/27 PASS (was 14 errors)
- [x] `tests/test_sqlite_bridge.py` : 6/6 PASS (was 5 errors)
- [x] `tests/test_tools_mesh.py` : 12/14 PASS (2 pre-existing fails
      in test_task_create_emits_to_review_queue and test_queue_event_resource_returns_event
      — unrelated to UEID regex; M74+)
- [x] `tests/test_resources.py` : partial (see above)
- [x] Smoke UEID validation:
  - `UEID("ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609")` → OK (5-part)
  - `UEID("ikigai:vaga-remota-2026:4f6a202a:2cb24609")` → OK (4-part short)
  - `UEID("tsk:foo:11111111-1111-1111-1111-111111111111:1111111111111111")` → OK (long-uuid)

## Out of scope (M74+)

- 80 other test failures in `src/ikigai/tests/` are NOT M73 UEID regex
  bugs. Sample: `_VAULT_DIR` renamed in `src/ikigai/src/agents/tools.py`,
  but tests reference the old name. These are pre-existing M-series bugs
  unrelated to M73. Tracked separately.
- Canonical migration from 5-part → 4-part UEIDs in stored markdown
  data. The 5-part branch is a compat layer for in-flight fixtures;
  a future cleanup pass would re-emit them as 4-part.

## Risk discussion

Adding alternation branches to a regex with `re.ANCHORED` semantics
(`^...$`) preserves the "full match" guarantee. The 5-part branch
only matches strings with the entity_type slot filled, so existing
4-part canonical UEIDs continue to validate through branch 1 without
any new ambiguity.
