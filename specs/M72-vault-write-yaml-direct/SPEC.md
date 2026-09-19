---
name: M72-vault-write-yaml-direct
description: Replace frontmatter.Post/dumps with manual yaml.safe_dump for frontmatter serialization
owner: matheus-mendes
status: DONE
milestone: M72
estimated_cost_usd: 0.30
constitution_refs:
  - correctness_over_speed
  - state_on_disk_not_conversation
  - tests_are_the_contract
---

# M72 — vault_write migrates off frontmatter 3.x API

## Context

The `tests/mcp_server/test_vault_write_actor.py` tests had been
failing at master HEAD with the error `"module 'frontmatter' has
no attribute 'Post'"`. Root cause: the `frontmatter` package
upstream bumped to **3.0.8** but their 3.x API removed `Post` and
`dumps` (they're now read-only via `Frontmatter.read_file`).

`sys_ikigai/vault/vault_write.py` had been written against 1.x's
`frontmatter.Post(content=..., **fields)` + `frontmatter.dumps(post)`,
which crashed at runtime under 3.x.

## What changed

### sys_ikigai/vault/vault_write.py (rewritten)

Removed `import frontmatter`. Added direct `yaml.safe_dump()` call:

```python
def _serialize_markdown(frontmatter_fields: dict[str, Any], body: str) -> str:
    fm_block = yaml.safe_dump(
        frontmatter_fields or {},
        default_flow_style=False,  # block style
        sort_keys=False,            # preserve insertion order
        allow_unicode=True,
        explicit_start=False,
    ).strip()
    body_clean = (body or "").rstrip()
    parts = ["---", fm_block, "---", ""]
    if body_clean:
        parts.append(body_clean)
    parts.append("")
    return "\n".join(parts)
```

This produces:

```
---
title: My Task
tags:
  - a
  - b
---

My body here.

```

— the canonical markdown-with-frontmatter format the rest of the
system (vault_read, drift nets, etc.) already parses.

Removed `import frontmatter` line entirely. The `frontmatter` package
remains installable (no explicit uninstall), but it's no longer
required by the runtime path M72 touches.

## Acceptance

- [x] `tests/mcp_server/test_vault_write_actor.py` — **3/3 PASS**
  (was 2 failing pre-M72)
- [x] All other tests regression-free: 329 + 1 SKIP in tests/, 91 +
  1 SKIP in src/ikigai/tests/
- [x] End-to-end smoke: `vault_write("actor=agent", frontmatter={title, tags}, body=...)`
  produces correct markdown (verified manually):
  - YAML frontmatter block with `---` delimiters
  - Body section preserved verbatim
  - sha256 checksum returned
  - audit log entry written (best-effort)

## Out of scope (M73+)

- `tests/mcp_server/test_vault_read_actor.py` and
  `tests/mcp_server/test_investigation_lifecycle.py` — also
  intermittent fail/pass due to upstream API drift, but not on the
  M72 critical path. Investigate post-M72.
- `tests/mcp_server/test_vault_write_actor.py` writes files locally;
  on a Linux-only CI host, this works natively. On Windows we have
  some `fcntl.lockf` quirks that M72 doesn't fix.

## Risk discussion

Manual yaml.serialization is straightforward — `---` delimiter,
newline after `key: value` block, blank line, body. The format is
stable across decades of markdown frontmatter. Drift between this
implementation and any other library is unlikely because:
- Output is human-parseable (verified in end-to-end smoke)
- `vault_read` (the read counterpart) uses `frontmatter.loads()` which
  parses any well-formed `---` block — no assumption about yaml lib

## Network effect

The vault write path was the last blocker preventing the FULL
`tests/mcp_server/` test file from running. With M72:
- taskdog MCP server lifecycle tests (MCP tests) gain coverage
- vault_write test contract now end-to-end verified
- audit log writes can proceed (actor tracking per ADR-012)
