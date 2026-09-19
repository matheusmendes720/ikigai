---
name: M73.5-sync-vault-shim
description: Extract ikigai_sync_vault from v2/tools_legacy_reference.py into tools.py + dual-identity sweep completion
owner: matheus-mendes
status: DONE
milestone: M73.5
estimated_cost_usd: 0.15
constitution_refs:
  - correctness_over_speed
  - tests_are_the_contract
---

# M73.5 — sync_vault shim + dual-identity completion

## Context

M73.3 fixed 11 dual-identity bugs but missed 2 cases:
- `from mesh import queue as _queue` in `mcp_server/resources.py` and `tools_mesh.py`
  (M73.3 regex `from mesh\.` didn't catch `from mesh import` style).

Additionally, `tests/test_ikigai_sync_vault.py` tests reference
`agents.tools.ikigai_sync_vault` + `agents.tools._VAULT_DIR` +
`agents.tools._read_checkpoint_data`, but the actual sync_vault tool
lives in `agents/v2/tools_legacy_reference.py` (stripped from production
in M12).

## What changed

### Dual-identity sweep completion
- `src/ikigai/src/mcp_server/resources.py`:
  `from mesh import queue as _queue` → `from src.mesh import queue as _queue`
- `src/ikigai/src/mcp_server/tools_mesh.py`: same fix.

### agents/tools.py — sync_vault shim

Added module-level placeholders that let tests monkeypatch without
requiring the actual sync_vault tool to be in IKIGAI_TOOLS:
```python
def _VAULT_DIR() -> Path:
    return Path(...).parent.parent.parent.parent.parent / "vault"

def _read_checkpoint_data(thread_id="default") -> dict:
    return {"cycle_id": ..., ...}
```

Also extracted `ikigai_sync_vault` from
`agents/v2/tools_legacy_reference.py` and registered it as a
LangChain `@tool` on the same module. Body now includes corrections
in the same `- [H3] desc` format the test expects. Returns the
"✅ Synced to vault: ..." message format the test asserts on.

### tests/test_ikigai_sync_vault.py

Migrated from `import frontmatter; frontmatter.loads(...)` to
`from sys_ikigai.vault.frontmatter_compat import loads` (M72.1 shim).

## Acceptance (verified 2026-09-19)

- [x] tests/test_ikigai_sync_vault.py : 5/5 PASS (was 1/5)
- [x] tests/test_resources.py : 7/7 PASS (was 6/7) — dual-identity fix
- [x] tests/test_tools_mesh.py : 7/7 PASS (was 6/7) — dual-identity fix
- [x] ikigai total : 778 PASS + 22 SKIP, 45 failed + 4 errors
       (was 772 + 22, 47 + 4)
- [x] tests/ root : 329 PASS + 1 SKIP (no regression)
- [x] Drift net canônico : 18/18 PASS
