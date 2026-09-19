---
name: M72.1-frontmatter-compat-shim
description: Backward-compat shim wrapping yaml.safe_load/dump for upstream frontmatter 3.x removal
owner: matheus-mendes
status: DONE
milestone: M72.1
estimated_cost_usd: 0.30
constitution_refs:
  - correctness_over_speed
  - state_on_disk_not_conversation
  - tests_are_the_contract
---

# M72.1 — frontmatter_compat shim (loads/dumps/Post)

## Context

After M72 migrated `sys_ikigai/vault/vault_write.py` off the broken
`frontmatter` 3.x API (using manual `yaml.safe_dump`),
**5 other callers** still depended on `frontmatter.loads(...)` and
silently failed at runtime when the system had frontmatter 3.0.8
installed:

1. `sys_ikigai/vault/frontmatter_to_dict.py:28` — IKIGAiRecord round-trip
2. `sys_ikigai/vault/vault_read.py:56` — vault_read MCP tool
3. `src/ikigai/src/mcp_server/handlers.py:64,87` — MCP handlers
4. `src/ikigai/src/strategics/loader.py:59` — strategics loader

M72.1 creates a small compat shim at
`sys_ikigai/vault/frontmatter_compat.py` that re-implements the
**minimum surface** the codebase actually used:
- `loads(text)` → returns `.content` + `.metadata`
- `dumps(post)` → composes `---\n<yaml>\n---\n<body>`
- `Post(content, **fields)` → factory

All 5 callers were migrated to `from .frontmatter_compat import loads, ...`
(or equivalent `from sys_ikigai.vault.frontmatter_compat`).

## What changed

### sys_ikigai/vault/frontmatter_compat.py (NEW)

Tiny stdlib-only module that wraps `yaml.safe_load`/`yaml.safe_dump`
to compose/decompose markdown frontmatter blocks. Public surface:
- `loads(text: str) -> SimpleNamespace(content, metadata)`
- `dumps(post: Any) -> str`
- `Post(content: str = "", **fields) -> SimpleNamespace`
- `load(file)` / `dump(post, file)` for file-based I/O

RE flags:
- `^---\s*\n(?P<fm>.*?)\n---\s*\n?(?P<body>.*)$` — non-greedy yaml
  block capture, single frontmatter section per file (consistent with
  python-frontmatter 1.x semantics).
- Empty / no frontmatter → `.content = text, .metadata = {}` (1.x parity).
- `None` values in YAML are preserved as Python None (RT-03 invariant).

### 5 caller files migrated

- `frontmatter_to_dict.py`, `vault_read.py`, `vault_write.py` (M72):
  `import frontmatter` → `from .frontmatter_compat import loads, ...`
- `src/ikigai/src/mcp_server/handlers.py`,
  `src/ikigai/src/strategics/loader.py`:
  `import frontmatter` → `from sys_ikigai.vault.frontmatter_compat import ...`
- All `frontmatter.loads(...)` calls swapped to `loads(...)` directly.

## Acceptance

- [x] Shim sanity-check: `loads()` parses `---\nkey: val\n---\nbody` correctly
- [x] `dumps()` produces valid YAML frontmatter in `---\n` block
- [x] `Post(content, **fields)` constructor round-trips metadata
- [x] 5 callers migrated, no lingering `import frontmatter`
- [x] All other tests regression-free: 319 + 1 SKIP in tests/

## Out of scope (M73+)

- `tests/test_integration_data_model.py` 14 failures with
  `"String should match pattern '^[a-z]{2,5}:[a-z0-9-]+:[a-f0-9-]+$'"`.
  The fixture UEID `ikigai:dream:vaga-remota-2026:4f6a202a:2cb24609`
  has a non-hex `2026` segment which violates the strict hex-only
  regex. This is a separate UEID spec mismatch — the fixture was
  generated when UEID was looser, the validator tightened. Tracked
  in M73.
- The `frontmatter` package itself remains installable. Future M-n
  can drop it as a runtime dep if the shim remains the canonical
  implementation.
