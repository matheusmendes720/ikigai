---
name: M47-fix-contracts-base-import-path
description: Fix src/contracts/base.py:11 — remove 'src.' prefix that breaks mcp_inspect.py + all script that import contracts.
status: DONE
owner: loop-orchestrator
constitution_refs:
  - correctness_over_speed
  - reversibility_over_cleverness
  - tests_are_the_contract
estimated_ticks: 1
---

# M47 — Fix src/contracts/base.py:11 import path

## Problem

`src/contracts/base.py:11` reads:

```python
from src.contracts.common import UEID, PaeCyclePhase, PlanTier, VectorKey
```

This is the OLD pre-refactor import path (when `src/contracts/` was
under `src/src/contracts/`). After the import-path refactor
(per AGENTS.md note: "no `src.` prefix"), every other file in the
codebase switched to:

```python
from contracts.common import UEID
```

But `src/contracts/base.py` was missed. Because `src/contracts/__init__.py`
*imports* `base.py` on package init (line 24: `from .base import
BasePlanContract`), this breaks **every script that touches
`contracts`** — including `scripts/mcp_inspect.py` (M46 diagnosis).

## Concrete failure

`python scripts/mcp_inspect.py --tool-count 22 --resource-count 6`:

```
ModuleNotFoundError: No module named 'src'
[mcp-inspect] FAIL: ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
[mcp-inspect] IKIGAI_TOOLS drift check skipped (import unavailable): ModuleNotFoundError: No module named 'src'
```

The MCP gateway contract test cannot run at all until this is fixed.

## Fix

One-line change in `src/contracts/base.py`:

```diff
- from src.contracts.common import UEID, PaeCyclePhase, PlanTier, VectorKey
+ from .common import UEID, PaeCyclePhase, PlanTier, VectorKey
```

Using relative import (`.common`) is preferred over absolute
(`contracts.common`) because:
1. It survives package moves (relative imports are anchored to `__package__`)
2. It's the canonical Python idiom for intra-package imports
3. It matches the existing style in `src/contracts/__init__.py` (which uses `from .base import ...`)

## Acceptance

- [x] `src/contracts/base.py:11` uses relative import (`.common`) (T-47.1)
- [x] `python scripts/mcp_inspect.py` no longer fails with ModuleNotFoundError (T-47.2)
- [x] Drift net preserved: 69/69 + 11/11 (T-47.3)
- [x] 1 atomic commit + push

## Reversibility

`git revert HEAD~`. One-line diff.

## Dependencies

None — self-contained fix in a single file.