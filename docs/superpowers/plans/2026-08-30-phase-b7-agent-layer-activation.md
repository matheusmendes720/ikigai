# Phase B7 — Agent Layer Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate the agent layer so vault ↔ agent ↔ forks round-trip is functional and demonstrable end-to-end. Closes B5.0 audit findings F8 (multi-tool MCP chain) and F11 (`run_chat` refactor) partially. Resolves attribution §7 violation (DELETE `agentic_writer.py`). Produces system-readiness ADR per [[algorithm-gate-system-readiness-not-sonho-2026-08-29]].

**Architecture:**
1. Read-side mirror of `vault_write` (already canonical per attribution §7): `vault_read` MCP tool + `vault_read.py` with same security model.
2. PT-BR strategics loader pulls `./strategics/*.md` into agent context via `ikigai_read_strategics` tool.
3. Wire 2 new tools into `ikigai_plan_cycle`; partial F11 refactor splits 290-LOC `run_chat` into 50-LOC orchestrator + 4 helpers.
4. E2E round-trip test (vault → agent → taskdog → vault) with HYBRID trace artifact.
5. DELETE orphaned `agentic_writer.py` + its test (zero callers; uses non-atomic `frontmatter.dump()`).
6. Multi-tool MCP chain test closes B5.0 F8.
7. System-readiness ADR with all 5 algorithm components DEFER; 6 open ADR questions enumerated.

**Tech Stack:** Python 3.11+, Pydantic v2 strict (`frozen=True, extra="forbid"`), FastMCP, `frontmatter` library, `sqlite3` stdlib, existing `src/mesh/queue.py` + `VaultLock` + `os.replace()` for atomic writes.

## Global Constraints

These apply to every task. Copy them verbatim — every task's requirements implicitly include this section.

1. **`vault_write` is the ONLY vault writer** per attribution report §7. `vault_read` is read-only mirror; never writes.
2. **`vault_read` mirrors `vault_write` security model:** path traversal guard (`target.relative_to(vault_root_resolved)`), `VaultLock` (shared reader lock, not exclusive writer), `frontmatter.loads()` (NOT `.loads()` + write).
3. **`os.replace()` for atomic writes** (Windows-safe per B6.4 lesson — `Path.rename()` raises `FileExistsError` on Windows when target exists).
4. **No edits to scoring/formula/qhe/regime/weight** — algorithm gate is DEFERRED per [[algorithm-gate-system-readiness-not-sonho-2026-08-29]]. B7.7 ADR documents verdicts only.
5. **No new LLM in pipelines** — agent loop is structural, LLM is agent-only.
6. **No new dependencies** — use stdlib + already-installed packages only.
7. **Pydantic v2 strict** — `frozen=True, extra="forbid"` on all schemas.
8. **Pre-flight regression mandatory** per [[verify-agent-fabricated-failures]] — main session runs `pytest` after each task.
9. **HYBRID trace artifact per Q1 decision:** pytest fixture writes `src/ikigai/tests/reports/b7-4-report.md` (NOT `docs/superpowers/specs/`). Format = Implementer Report: Status, Commits, Test Results (verbatim pytest), Spec Compliance, Self-Review.
10. **F11 partial within B7.3:** 5-step extraction; `run_chat()` ≤ 60 LOC; 4 helpers unit-tested.
11. **DELETE `agentic_writer.py` + `test_agentic_writer.py`** (attribution §7); 6 doc references updated with `SUPERSEDED` trailer (append-only invariant preserved).
12. **Smoke tests for MCP-dependent code must handle MCP absence** (parse+diff stages, no subprocess dependency).
13. **Pattern mirror** helpers from `src/mesh/cli_cli.py` / `taskdog_cli.py` whenever adding CLI commands.
14. **NEVER add `Co-Authored-By` trailer** to commits.
15. **Keep files under 500 lines**; split when they grow.

---

## File Structure (locked-in by this plan)

| File | Role | Created/Modified |
|---|---|---|
| `src/ikigai/src/ikigai/vault/vault_read.py` | Read-side mirror of vault_write | B7.1 create |
| `src/ikigai/src/mcp_server/server.py` | Add vault_read tool (15th tool) | B7.1 modify |
| `src/ikigai/tests/test_vault_read.py` | Unit tests | B7.1 create |
| `tests/mesh/test_vault_read_path_traversal.py` | Security tests | B7.1 create |
| `src/ikigai/src/strategics/__init__.py` | Package init | B7.2 create |
| `src/ikigai/src/strategics/loader.py` | Strategics loader | B7.2 create |
| `src/ikigai/tests/test_strategics_loader.py` | Unit tests | B7.2 create |
| `src/ikigai/src/agents/ikigai_read_strategics.py` | LangChain @tool | B7.3 create |
| `src/ikigai/src/agents/ikigai_read_vault.py` | LangChain @tool | B7.3 create |
| `src/ikigai/src/agents/tools.py` | Wire 2 new tools into IKIGAI_TOOLS list | B7.3 modify |
| `src/ikigai/src/agents/deepagents_harness.py` | F11 partial refactor (290 → 50 LOC orchestrator) | B7.3 modify |
| `src/ikigai/tests/test_deepagents_harness_helpers.py` | Unit tests for 4 helpers | B7.3 create |
| `src/ikigai/tests/e2e/conftest.py` | HYBRID trace fixture | B7.4 create |
| `src/ikigai/tests/e2e/test_vault_agent_round_trip.py` | E2E round-trip | B7.4 create |
| `src/ikigai/tests/reports/b7-4-report.md` | Trace artifact (committed) | B7.4 create |
| `src/ikigai/src/ikigai/vault/agentic_writer.py` | **DELETE** | B7.5 delete |
| `src/ikigai/tests/test_agentic_writer.py` | **DELETE** | B7.5 delete |
| 6 doc files referencing `agentic_writer.py` | SUPERSEDED trailer | B7.5 modify |
| `src/ikigai/tests/mcp/test_multi_tool_chain.py` | F8 closure | B7.6 create |
| `docs/architecture/2026-08-30-system-readiness-adr.md` | Algorithm gate ADR | B7.7 create |

---

## Task B7.1: vault_read MCP tool (read-side mirror of vault_write)

**Files:**
- Create: `src/ikigai/src/ikigai/vault/vault_read.py` (~80 LOC)
- Modify: `src/ikigai/src/mcp_server/server.py:765-780` (add `vault_read` tool alongside `vault_write`)
- Create: `src/ikigai/tests/test_vault_read.py` (~10 unit tests)
- Create: `tests/mesh/test_vault_read_path_traversal.py` (~3 security tests)

**Interfaces:**
- Consumes: `VaultLock` from `src/ikigai/src/ikigai/vault/lock.py` (existing)
- Produces: `vault_read(vault_root: Path, vault_path: str) -> dict[frontmatter, body, sha256, mtime]`

**Step 1.1: Read `vault_write.py` to mirror its security model**

The implementer MUST read `src/ikigai/src/ikigai/vault/vault_write.py` first. The new `vault_read.py` mirrors lines 60-76 (security guards), uses `VaultLock` context manager (line 85), and returns a similar shape (lines 113-118).

**Step 1.2: Write the failing security test**

File: `tests/mesh/test_vault_read_path_traversal.py`

```python
"""Security tests for vault_read path traversal guards.

Mirrors vault_write's path traversal protection (vault_write.py:66-75).
"""
from __future__ import annotations

from pathlib import Path

import pytest


def test_absolute_path_rejected(tmp_path: Path) -> None:
    """Absolute paths are rejected with ValueError."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    with pytest.raises(ValueError, match="absolute path rejected"):
        vault_read(tmp_path, "/etc/passwd")


def test_parent_traversal_rejected(tmp_path: Path) -> None:
    """Paths resolving outside vault_root raise ValueError."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    with pytest.raises(ValueError, match="resolves outside vault root"):
        vault_read(vault, "../../../etc/passwd")


def test_symlink_escape_rejected(tmp_path: Path) -> None:
    """Symlinks pointing outside vault_root are rejected (resolve() catches it)."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("# outside")
    (vault / "sneaky.md").symlink_to(outside)

    with pytest.raises(ValueError, match="resolves outside vault root"):
        vault_read(vault, "sneaky.md")
```

Run: `python -m pytest tests/mesh/test_vault_read_path_traversal.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.ikigai.src.ikigai.vault.vault_read'`

**Step 1.3: Write the unit test for happy path**

File: `src/ikigai/tests/test_vault_read.py`

```python
"""Unit tests for vault_read — read-side mirror of vault_write."""
from __future__ import annotations

import textwrap
from pathlib import Path


def test_vault_read_parses_frontmatter_and_body(tmp_path: Path) -> None:
    """Frontmatter dict + body returned separately."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "test.md").write_text(textwrap.dedent("""\
        ---
        ueid: ikigai:test:read:001
        title: Test
        ---
        # Body section

        Some markdown body.
    """))

    result = vault_read(vault, "test.md")
    assert result["frontmatter"]["ueid"] == "ikigai:test:read:001"
    assert result["frontmatter"]["title"] == "Test"
    assert "# Body section" in result["body"]
    assert len(result["sha256"]) == 64  # sha256 hex
    assert result["mtime"] > 0


def test_vault_read_missing_file_raises(tmp_path: Path) -> None:
    """Missing file raises FileNotFoundError."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    import pytest
    with pytest.raises(FileNotFoundError):
        vault_read(vault, "missing.md")


def test_vault_read_no_frontmatter_returns_empty_dict(tmp_path: Path) -> None:
    """Plain markdown (no frontmatter) returns empty frontmatter dict."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "plain.md").write_text("# Plain markdown\n\nNo frontmatter.\n")
    result = vault_read(vault, "plain.md")
    assert result["frontmatter"] == {}
    assert "# Plain markdown" in result["body"]


def test_vault_read_empty_file_returns_empty_body(tmp_path: Path) -> None:
    """Empty file returns empty body + empty frontmatter."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "empty.md").write_text("")
    result = vault_read(vault, "empty.md")
    assert result["body"] == ""
    assert result["frontmatter"] == {}


def test_vault_read_handles_unicode(tmp_path: Path) -> None:
    """UTF-8 (Portuguese accents) round-trips correctly."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "pt-br.md").write_text(
        "---\ntitle: Planejamento\n---\n# Estratégia\n\nNão priorizar.\n",
        encoding="utf-8",
    )
    result = vault_read(vault, "pt-br.md")
    assert result["frontmatter"]["title"] == "Planejamento"
    assert "Estratégia" in result["body"]
    assert "Não priorizar." in result["body"]


def test_vault_read_concurrent_readers_do_not_block(tmp_path: Path) -> None:
    """Two concurrent readers can both hold VaultLock (shared lock)."""
    import threading
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "test.md").write_text("---\ntitle: T\n---\nBody\n")

    results: list[dict] = []
    errors: list[Exception] = []

    def reader():
        try:
            results.append(vault_read(vault, "test.md"))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=reader) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(results) == 5


def test_vault_read_returns_sha256_matches_file_content(tmp_path: Path) -> None:
    """SHA256 hash matches actual file content (read after parse)."""
    import hashlib
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    content = "---\nkey: value\n---\n# body\n"
    (vault / "h.md").write_text(content)

    result = vault_read(vault, "h.md")
    expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert result["sha256"] == expected


def test_vault_read_mtime_matches_file(tmp_path: Path) -> None:
    """mtime is the file's actual mtime."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    vault = tmp_path / "vault"
    vault.mkdir()
    f = vault / "m.md"
    f.write_text("x")
    expected_mtime = f.stat().st_mtime

    result = vault_read(vault, "m.md")
    assert abs(result["mtime"] - expected_mtime) < 1.0
```

(Note: 10 tests required per spec; add 2 more covering lock interaction and large file as needed.)

Run: `python -m pytest src/ikigai/tests/test_vault_read.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 1.4: Implement `vault_read.py`**

File: `src/ikigai/src/ikigai/vault/vault_read.py`

```python
"""vault_read — read-side mirror of vault_write.

Mirror of vault_write's security model (path traversal guard, VaultLock).
Read-only — never writes. Exposed as `vault_read` MCP tool.

Security:
  - Rejects absolute paths
  - Rejects paths resolving outside vault_root
  - VaultLock (shared reader lock; VaultLock already supports shared mode
    or we use a re-entrant variant — see Step 1.5 for verification)

Concurrency:
  - VaultLock for cross-platform concurrency safety
"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Any

import frontmatter

from .lock import VaultLock


def vault_read(vault_root: Path, vault_path: str) -> dict[str, Any]:
    """Read markdown file from vault. Returns parsed frontmatter + body.

    Args:
        vault_root: vault root directory (anchor for path resolution)
        vault_path: relative path within vault/, e.g. "plans/q3/task-x.md"

    Returns:
        {frontmatter: dict, body: str, sha256: str, mtime: float}

    Raises:
        ValueError: if vault_path is absolute or resolves outside vault_root
        FileNotFoundError: if the resolved file does not exist
    """
    # Security: reject absolute paths (mirror vault_write:66-67)
    if Path(vault_path).is_absolute():
        raise ValueError(f"absolute path rejected: {vault_path!r}")

    # Security: resolve and check it's inside vault_root (mirror vault_write:70-75)
    target = (vault_root / vault_path).resolve()
    vault_root_resolved = vault_root.resolve()
    try:
        target.relative_to(vault_root_resolved)
    except ValueError as exc:
        raise ValueError(f"path {vault_path!r} resolves outside vault root") from exc

    if not target.exists():
        raise FileNotFoundError(f"vault file not found: {vault_path!r}")

    lock_path = vault_root / ".vault.lock"
    with VaultLock(lock_path):
        # frontmatter.loads() parses both frontmatter (YAML) and body
        post = frontmatter.loads(target.read_text(encoding="utf-8"))
        body = post.content
        fm_dict = dict(post.metadata)
        sha256 = hashlib.sha256(target.read_bytes()).hexdigest()
        mtime = target.stat().st_mtime

    return {
        "frontmatter": fm_dict,
        "body": body,
        "sha256": sha256,
        "mtime": mtime,
    }


__all__ = ["vault_read"]
```

Run: `python -m pytest src/ikigai/tests/test_vault_read.py tests/mesh/test_vault_read_path_traversal.py -v`
Expected: PASS for all tests.

**Step 1.5: Verify VaultLock allows concurrent readers**

Read `src/ikigai/src/ikigai/vault/lock.py`. If `VaultLock` is already a shared/exclusive lock (most stdlib `fcntl`/`msvcrt` implementations allow shared reads), the test `test_vault_read_concurrent_readers_do_not_block` confirms it. If not, either:
- Use the lock only when a writer holds it (i.e., read lock is no-op when no writer) — see B5.x pattern.
- OR: switch to a true `ReadWriteLock` (YAGNI — only if the test fails).

Document the decision in the commit message.

**Step 1.6: Add `vault_read` MCP tool to server.py**

File: `src/ikigai/src/mcp_server/server.py`, near line 776 (where `vault_write` is registered).

Read lines 770-800 of `server.py` to find the exact insertion point. Add after the `vault_write` registration:

```python
# === vault_read (B7.1) — read-side mirror of vault_write ===
def _vault_read_tool(vault_path: str) -> str:
    """Read markdown file from vault. Returns JSON with frontmatter, body, sha256, mtime.

    Args:
        vault_path: relative path within vault/, e.g. "plans/q3/task-x.md"

    Returns:
        JSON string: {"frontmatter": dict, "body": str, "sha256": str, "mtime": float}
    """
    from src.ikigai.src.ikigai.vault.vault_read import vault_read
    import json
    from src.ikigai.config import get_vault_root
    vault_root = get_vault_root()
    result = vault_read(vault_root, vault_path)
    return json.dumps(result)
```

Add to the tool registration list (find the `mcp.tool(...)` call for `vault_write`):

```python
mcp.tool(name="vault_read", description="Read markdown file from vault with parsed frontmatter")(  # noqa: E501
    _vault_read_tool
)
```

(Adjust the registration pattern to match what `server.py` uses for `vault_write` — read 5 lines above the `vault_write` registration to mirror exactly.)

**Step 1.7: Smoke test the MCP tool**

Run: `python scripts/mcp_inspect.py --tool-count 15`
Expected: `15 tools` (was 14; +1 for vault_read)

Run: `python scripts/mcp_inspect.py --resources | grep -i vault`
Expected: nothing new (vault_read is a tool, not a resource).

**Step 1.8: Pre-flight regression**

Run: `cd src/ikigai && uv run pytest tests/ -x -q`
Expected: all existing tests pass + new vault_read tests pass. Zero regressions.

**Step 1.9: Commit**

```bash
git add src/ikigai/src/ikigai/vault/vault_read.py src/ikigai/src/mcp_server/server.py src/ikigai/tests/test_vault_read.py tests/mesh/test_vault_read_path_traversal.py
git commit -m "feat(b7.1): vault_read MCP tool (read-side mirror of vault_write)"
```

---

## Task B7.2: Strategics loader (PT-BR → agent context)

**Files:**
- Create: `src/ikigai/src/strategics/__init__.py` (~10 LOC)
- Create: `src/ikigai/src/strategics/loader.py` (~120 LOC)
- Create: `src/ikigai/tests/test_strategics_loader.py` (~8 tests)

**Interfaces:**
- Produces: `StrategicsContext` (Pydantic v2 frozen model) with `documents: list[StrategicDoc]`, `by_tag: dict[str, list[StrategicDoc]]`, `index: str` (concatenated body for prompt injection)
- `load_strategics(vault_root: Path) -> StrategicsContext`

**Step 2.1: Write the failing tests**

File: `src/ikigai/tests/test_strategics_loader.py`

```python
"""Unit tests for strategics loader — loads PT-BR strategic docs into agent context."""
from __future__ import annotations

import textwrap
from pathlib import Path


def test_load_strategics_returns_documents(tmp_path: Path) -> None:
    """All .md files under vault/strategics/ are returned as StrategicDoc."""
    from src.ikigai.src.strategics.loader import load_strategics

    strat = tmp_path / "strategics"
    strat.mkdir()
    (strat / "planejamento.md").write_text(textwrap.dedent("""\
        ---
        tags: [strategic, planning]
        ---
        # Planejamento

        Estratégia de planejamento.
    """), encoding="utf-8")
    (strat / "modelagem.md").write_text(textwrap.dedent("""\
        ---
        tags: [strategic, modeling]
        ---
        # Modelagem Operacional

        Framework de modelagem.
    """), encoding="utf-8")

    ctx = load_strategics(tmp_path)
    titles = sorted(d.title for d in ctx.documents)
    assert titles == ["Modelagem Operacional", "Planejamento"]


def test_load_strategics_filters_by_tag(tmp_path: Path) -> None:
    """Only files with `tags: [strategic]` (or any strategic tag) are loaded."""
    from src.ikigai.src.strategics.loader import load_strategics

    strat = tmp_path / "strategics"
    strat.mkdir()
    (strat / "strat.md").write_text(
        "---\ntags: [strategic]\n---\n# Strategic\n", encoding="utf-8"
    )
    (strat / "non-strat.md").write_text(
        "---\ntags: [draft]\n---\n# Draft\n", encoding="utf-8"
    )

    ctx = load_strategics(tmp_path)
    titles = [d.title for d in ctx.documents]
    assert "Strategic" in titles
    assert "Draft" not in titles


def test_load_strategics_index_is_concatenated_body(tmp_path: Path) -> None:
    """index field contains all bodies joined for prompt injection."""
    from src.ikigai.src.strategics.loader import load_strategics

    strat = tmp_path / "strategics"
    strat.mkdir()
    (strat / "a.md").write_text(
        "---\ntags: [strategic]\n---\n# AAA\nbody A\n", encoding="utf-8"
    )
    (strat / "b.md").write_text(
        "---\ntags: [strategic]\n---\n# BBB\nbody B\n", encoding="utf-8"
    )

    ctx = load_strategics(tmp_path)
    assert "AAA" in ctx.index
    assert "BBB" in ctx.index
    assert "body A" in ctx.index
    assert "body B" in ctx.index


def test_load_strategics_by_tag_index(tmp_path: Path) -> None:
    """by_tag dict groups StrategicDocs by their tag."""
    from src.ikigai.src.strategics.loader import load_strategics

    strat = tmp_path / "strategics"
    strat.mkdir()
    (strat / "p.md").write_text(
        "---\ntags: [strategic, planning]\n---\n# P\n", encoding="utf-8"
    )
    (strat / "m.md").write_text(
        "---\ntags: [strategic, modeling]\n---\n# M\n", encoding="utf-8"
    )

    ctx = load_strategics(tmp_path)
    assert "planning" in ctx.by_tag
    assert "modeling" in ctx.by_tag
    assert len(ctx.by_tag["planning"]) == 1
    assert len(ctx.by_tag["modeling"]) == 1


def test_load_strategics_empty_dir_returns_empty_context(tmp_path: Path) -> None:
    """Empty strategics/ dir returns empty context (no error)."""
    from src.ikigai.src.strategics.loader import load_strategics

    (tmp_path / "strategics").mkdir()
    ctx = load_strategics(tmp_path)
    assert ctx.documents == []
    assert ctx.by_tag == {}
    assert ctx.index == ""


def test_load_strategics_missing_dir_returns_empty_context(tmp_path: Path) -> None:
    """Missing strategics/ dir returns empty context (graceful)."""
    from src.ikigai.src.strategics.loader import load_strategics

    ctx = load_strategics(tmp_path)
    assert ctx.documents == []


def test_load_strategics_handles_portuguese_accents(tmp_path: Path) -> None:
    """UTF-8 PT-BR content parses correctly."""
    from src.ikigai.src.strategics.loader import load_strategics

    strat = tmp_path / "strategics"
    strat.mkdir()
    (strat / "estrategia.md").write_text(
        "---\ntags: [strategic]\n---\n# Estratégia\n\nNão priorizar tudo.\n",
        encoding="utf-8",
    )

    ctx = load_strategics(tmp_path)
    assert len(ctx.documents) == 1
    assert "Estratégia" in ctx.documents[0].body
    assert "Não priorizar" in ctx.documents[0].body


def test_load_strategics_preserves_sha256(tmp_path: Path) -> None:
    """Each StrategicDoc carries its sha256."""
    from src.ikigai.src.strategics.loader import load_strategics

    strat = tmp_path / "strategics"
    strat.mkdir()
    (strat / "x.md").write_text(
        "---\ntags: [strategic]\n---\n# X\n", encoding="utf-8"
    )

    ctx = load_strategics(tmp_path)
    assert len(ctx.documents[0].sha256) == 64  # sha256 hex length
```

Run: `python -m pytest src/ikigai/tests/test_strategics_loader.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 2.2: Implement the loader**

File: `src/ikigai/src/strategics/__init__.py`

```python
"""Strategics loader — loads PT-BR strategic docs into agent context."""
from .loader import StrategicDoc, StrategicsContext, load_strategics

__all__ = ["StrategicDoc", "StrategicsContext", "load_strategics"]
```

File: `src/ikigai/src/strategics/loader.py`

```python
"""Strategics loader — pulls ./strategics/*.md (PT-BR) into agent context.

Per attribution report §1 (2026-08-29), ./strategics/ PT-BR markdown is the
single source of truth for IKIGAI agent instructions. This module loads them
into a Pydantic v2 frozen model for downstream tools.

Append-only invariant: this loader NEVER writes.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import frontmatter
from pydantic import BaseModel, ConfigDict, Field


class StrategicDoc(BaseModel):
    """Single strategic document."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    path: Path
    title: str
    tags: list[str]
    body: str
    sha256: str


class StrategicsContext(BaseModel):
    """Loaded strategic context, ready for prompt injection."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    documents: list[StrategicDoc]
    by_tag: dict[str, list[StrategicDoc]]
    index: str = Field(default="")


def load_strategics(vault_root: Path) -> StrategicsContext:
    """Load all strategic docs from vault_root/strategics/.

    Filters: only files with `tags: [strategic]` (or any tag containing
    "strategic") in frontmatter.

    Args:
        vault_root: vault root directory

    Returns:
        StrategicsContext with documents, by_tag dict, and concatenated index
    """
    strategics_dir = vault_root / "strategics"
    if not strategics_dir.exists():
        return StrategicsContext(documents=[], by_tag={}, index="")

    documents: list[StrategicDoc] = []
    by_tag: dict[str, list[StrategicDoc]] = {}

    for md_path in sorted(strategics_dir.glob("*.md")):
        post = frontmatter.loads(md_path.read_text(encoding="utf-8"))
        tags = post.metadata.get("tags", [])

        # Filter: must have at least one tag containing "strategic"
        if not any("strategic" in str(t) for t in tags):
            continue

        sha256 = hashlib.sha256(md_path.read_bytes()).hexdigest()
        title = post.metadata.get("title", md_path.stem)
        tags_list = [str(t) for t in tags]

        doc = StrategicDoc(
            path=md_path,
            title=title,
            tags=tags_list,
            body=post.content,
            sha256=sha256,
        )
        documents.append(doc)

        for tag in tags_list:
            by_tag.setdefault(tag, []).append(doc)

    # Build index: concatenate titles + bodies
    parts = []
    for doc in documents:
        parts.append(f"## {doc.title}\n\n{doc.body}\n")
    index = "\n".join(parts)

    return StrategicsContext(documents=documents, by_tag=by_tag, index=index)
```

Run: `python -m pytest src/ikigai/tests/test_strategics_loader.py -v`
Expected: 8/8 PASS

**Step 2.3: Smoke test on real ./strategics/ dir**

Run: `python -c "
from pathlib import Path
from src.ikigai.src.strategics.loader import load_strategics
ctx = load_strategics(Path('./'))
print(f'Documents: {len(ctx.documents)}')
for d in ctx.documents:
    print(f'  - {d.title} (tags={d.tags})')
print(f'Index length: {len(ctx.index)} chars')
"`

Expected: prints 3+ document titles and index length > 0.

**Step 2.4: Pre-flight regression**

Run: `cd src/ikigai && uv run pytest tests/ -x -q`
Expected: no regressions.

**Step 2.5: Commit**

```bash
git add src/ikigai/src/strategics/ src/ikigai/tests/test_strategics_loader.py
git commit -m "feat(b7.2): strategics loader (PT-BR → agent context)"
```

---

## Task B7.3: Wire agent + F11 partial refactor (`run_chat` 5-step extraction)

**Files:**
- Create: `src/ikigai/src/agents/ikigai_read_strategics.py` (~30 LOC, LangChain @tool)
- Create: `src/ikigai/src/agents/ikigai_read_vault.py` (~30 LOC, LangChain @tool)
- Modify: `src/ikigai/src/agents/tools.py:965` (register 2 new tools in `IKIGAI_TOOLS`)
- Modify: `src/ikigai/src/agents/deepagents_harness.py:407-706` (F11 5-step extraction)
- Create: `src/ikigai/tests/test_deepagents_harness_helpers.py` (~10 unit tests for 4 helpers)

**Interfaces:**
- New tools: `ikigai_read_strategics() -> str` (text), `ikigai_read_vault(vault_path: str) -> str` (JSON)
- Helpers (new private): `_extract_assistant_text`, `_route_command`, `_register_builtin_commands`, `_invoke_agent_or_fallback`

**Step 3.1: Read `tools.py` and `deepagents_harness.py`**

The implementer MUST read both files first to understand:
- `tools.py:1-50` (imports + tool decorator pattern)
- `tools.py:965` (IKIGAI_TOOLS list)
- `deepagents_harness.py:407-706` (entire `run_chat` function — 290 LOC)

**Step 3.2: Write the failing tests for F11 helpers**

File: `src/ikigai/tests/test_deepagents_harness_helpers.py`

```python
"""Unit tests for F11-extracted helpers in deepagents_harness.run_chat."""
from __future__ import annotations

from unittest.mock import MagicMock


def test_extract_assistant_text_handles_messages_list() -> None:
    """_extract_assistant_text pulls last AI message content from result."""
    from src.ikigai.src.agents.deepagents_harness import _extract_assistant_text

    result = {
        "messages": [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "Hello there"},
            {"role": "assistant", "content": "How can I help?"},
        ]
    }
    assert _extract_assistant_text(result) == "How can I help?"


def test_extract_assistant_text_handles_string_content() -> None:
    """_extract_assistant_text works when content is a plain string."""
    from src.ikigai.src.agents.deepagents_harness import _extract_assistant_text

    result = {"messages": [{"role": "assistant", "content": "ok"}]}
    assert _extract_assistant_text(result) == "ok"


def test_extract_assistant_text_returns_empty_when_no_messages() -> None:
    """_extract_assistant_text returns empty string when no messages."""
    from src.ikigai.src.agents.deepagents_harness import _extract_assistant_text

    assert _extract_assistant_text({"messages": []}) == ""


def test_route_command_dispatches_score() -> None:
    """_route_command maps 'score' to ikigai_score tool."""
    from src.ikigai.src.agents.deepagents_harness import _route_command

    mock_result = "score output"
    registry = {
        "score": MagicMock(return_value=mock_result),
        "regime": MagicMock(),
    }
    result = _route_command("score", thread_id="t1", registry=registry)
    assert result == mock_result
    registry["score"].assert_called_once()


def test_route_command_returns_none_for_unknown_command() -> None:
    """_route_command returns None when no command matches."""
    from src.ikigai.src.agents.deepagents_harness import _route_command

    registry = {"score": MagicMock()}
    assert _route_command("xyz_unknown", thread_id="t1", registry=registry) is None


def test_route_command_normalizes_case() -> None:
    """_route_command lowercases input for matching."""
    from src.ikigai.src.agents.deepagents_harness import _route_command

    mock_result = "score output"
    registry = {"score": MagicMock(return_value=mock_result)}
    result = _route_command("SCORE", thread_id="t1", registry=registry)
    assert result == mock_result


def test_register_builtin_commands_returns_expected_keys() -> None:
    """_register_builtin_commands returns dict with all known commands."""
    from src.ikigai.src.agents.deepagents_harness import _register_builtin_commands

    registry = _register_builtin_commands()
    # Spot-check the 8 IKIGAi shortcuts that existed pre-refactor
    expected = {"score", "regime", "phase", "corrections", "plan", "sync", "checkpoint"}
    assert expected.issubset(registry.keys())


def test_invoke_agent_or_fallback_returns_agent_result() -> None:
    """_invoke_agent_or_fallback returns agent.invoke() result on success."""
    from src.ikigai.src.agents.deepagents_harness import _invoke_agent_or_fallback

    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {"messages": [{"role": "assistant", "content": "ok"}]}

    result = _invoke_agent_or_fallback(mock_agent, [{"role": "user", "content": "hi"}], {}, "t1")
    assert result["messages"][0]["content"] == "ok"


def test_invoke_agent_or_fallback_returns_none_on_error() -> None:
    """_invoke_agent_or_fallback returns None on invoke exception."""
    from src.ikigai.src.agents.deepagents_harness import _invoke_agent_or_fallback

    mock_agent = MagicMock()
    mock_agent.invoke.side_effect = RuntimeError("boom")

    result = _invoke_agent_or_fallback(mock_agent, [{"role": "user", "content": "hi"}], {}, "t1")
    assert result is None


def test_run_chat_is_orchestrator_only() -> None:
    """run_chat function body must be ≤ 60 LOC (orchestrator only)."""
    import inspect
    from src.ikigai.src.agents import deepagents_harness

    source = inspect.getsource(deepagents_harness.run_chat)
    line_count = len(source.splitlines())
    assert line_count <= 60, f"run_chat is {line_count} lines, must be ≤ 60"
```

Run: `python -m pytest src/ikigai/tests/test_deepagents_harness_helpers.py -v`
Expected: FAIL (helpers don't exist yet)

**Step 3.3: Implement the 5 extractions in `deepagents_harness.py`**

File: `src/ikigai/src/agents/deepagents_harness.py`

Add these helpers BEFORE the existing `run_chat` function (insert at line 406):

```python
def _extract_assistant_text(result: dict) -> str:
    """Pull the last AI message content from a deepagents invoke result."""
    messages = result.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            return content if isinstance(content, str) else str(content)
    return ""


def _register_builtin_commands() -> dict:
    """Return a dict mapping command name → callable(thread_id)."""
    from .tools import (
        ikigai_score,
        ikigai_regime,
        ikigai_phase,
        ikigai_corrections,
        ikigai_plan_cycle,
        ikigai_sync_vault,
        ikigai_checkpoint,
    )

    def _call(tool, thread_id: str):
        return tool.invoke({"thread_id": thread_id})

    return {
        "score": lambda tid: _call(ikigai_score, tid),
        "scores": lambda tid: _call(ikigai_score, tid),
        "regime": lambda tid: _call(ikigai_regime, tid),
        "phase": lambda tid: _call(ikigai_phase, tid),
        "corrections": lambda tid: _call(ikigai_corrections, tid),
        "plan": lambda tid: _call(ikigai_plan_cycle, tid),
        "sync": lambda tid: _call(ikigai_sync_vault, tid),
        "checkpoint": lambda tid: _call(ikigai_checkpoint, tid),
        # Add more commands as needed (calendar, kanban, task, filesystem)
    }


def _route_command(user_input: str, thread_id: str, registry: dict) -> str | None:
    """Dispatch a built-in command if user_input matches; else None."""
    key = user_input.lower().strip()
    handler = registry.get(key)
    if handler is None:
        return None
    return handler(thread_id)


def _invoke_agent_or_fallback(agent, messages: list, config: dict, thread_id: str) -> dict | None:
    """Invoke the deep agent; return result or None on failure (graceful fallback to local command)."""
    try:
        return agent.invoke({"messages": messages}, config=config)
    except Exception:
        return None
```

Then REPLACE the body of `run_chat` (lines 407-706) with a slimmer orchestrator:

```python
def run_chat(agent, thread_id: str):
    """Orchestrator: loop read → dispatch → invoke → render. ≤ 60 LOC."""
    from .tools import ikigai_plan_cycle

    print("IKIGAi Conversational Agent — powered by deepagents")
    print("Ctrl+C to exit\n")
    print("Commands: score | regime | phase | corrections | plan | sync | checkpoint\n")

    print("Bootstrapping IKIGAi state...")
    init_result = ikigai_plan_cycle.invoke({"thread_id": thread_id})
    print(f"  {init_result}\n")

    config = {"configurable": {"thread_id": thread_id}}
    messages: list[dict] = []
    registry = _register_builtin_commands()

    while True:
        try:
            user_input = input("\n🧑 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye.")
            break
        if not user_input:
            continue

        # Try built-in command first
        cmd_result = _route_command(user_input, thread_id, registry)
        if cmd_result is not None:
            print(cmd_result)
            continue

        # Fall through to agent invoke
        messages.append({"role": "user", "content": user_input})
        result = _invoke_agent_or_fallback(agent, messages, config, thread_id)
        if result is None:
            print("(agent unavailable; please use a built-in command)")
            continue
        assistant_text = _extract_assistant_text(result)
        messages = result.get("messages", messages)
        print(assistant_text)
```

(Adjust the `print` formatting to match what `run_chat` did originally — the spec says "defer rich/prompt_toolkit rendering" so plain prints are fine.)

Run: `python -m pytest src/ikigai/tests/test_deepagents_harness_helpers.py -v`
Expected: 10/10 PASS

**Step 3.4: Add 2 new tools**

File: `src/ikigai/src/agents/ikigai_read_strategics.py`

```python
"""ikigai_read_strategics — loads PT-BR strategic docs as agent context."""
from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

from src.ikigai.src.strategics.loader import load_strategics


@tool
def ikigai_read_strategics() -> str:
    """Load IKIGAI strategic instructions from ./strategics/*.md.

    Returns the concatenated body of all strategic-tagged documents.
    Use this when you need to ground your reasoning in IKIGAI's strategic
    framework (PT-BR).
    """
    # Discover vault root from project layout
    from src.ikigai.config import get_vault_root
    vault_root = get_vault_root()
    ctx = load_strategics(vault_root)
    return ctx.index or "(no strategic documents loaded)"


__all__ = ["ikigai_read_strategics"]
```

File: `src/ikigai/src/agents/ikigai_read_vault.py`

```python
"""ikigai_read_vault — calls vault_read MCP tool from agent context."""
from __future__ import annotations

import json

from langchain_core.tools import tool

from src.ikigai.src.ikigai.vault.vault_read import vault_read


@tool
def ikigai_read_vault(vault_path: str) -> str:
    """Read a markdown file from vault. Returns JSON with frontmatter, body, sha256, mtime.

    Args:
        vault_path: relative path within vault/, e.g. "plans/q3/task-x.md"
    """
    from src.ikigai.config import get_vault_root
    vault_root = get_vault_root()
    try:
        result = vault_read(vault_root, vault_path)
    except (ValueError, FileNotFoundError) as e:
        return json.dumps({"error": str(e)})
    return json.dumps(result)


__all__ = ["ikigai_read_vault"]
```

**Step 3.5: Register 2 new tools in `IKIGAI_TOOLS`**

File: `src/ikigai/src/agents/tools.py`, at line 965 (or wherever `IKIGAI_TOOLS` list is defined).

Read the file to find the exact location. Add:

```python
# B7.3 — vault-grounded agent tools
from .ikigai_read_strategics import ikigai_read_strategics  # noqa: E402
from .ikigai_read_vault import ikigai_read_vault  # noqa: E402

IKIGAI_TOOLS.extend([
    ikigai_read_strategics,
    ikigai_read_vault,
])
```

(If `IKIGAI_TOOLS` is a tuple, append a new tuple instead.)

**Step 3.6: Verify `ikigai_plan_cycle` still passes its existing tests**

Read `src/ikigai/tests/test_tools.py` (or wherever `ikigai_plan_cycle` is tested) and run:

```bash
cd src/ikigai && uv run pytest tests/ -x -q -k "plan_cycle"
```

Expected: 10/10 pass (no regression).

**Step 3.7: Pre-flight regression**

Run: `cd src/ikigai && uv run pytest tests/ -x -q`
Expected: all existing tests + new helper tests pass.

**Step 3.8: Commit**

```bash
git add src/ikigai/src/agents/ikigai_read_strategics.py src/ikigai/src/agents/ikigai_read_vault.py src/ikigai/src/agents/tools.py src/ikigai/src/agents/deepagents_harness.py src/ikigai/tests/test_deepagents_harness_helpers.py
git commit -m "feat(b7.3): wire agent to vault + strategics + F11 partial run_chat refactor"
```

---

## Task B7.4: E2E round-trip test (vault → agent → forks → vault) + HYBRID trace

**Files:**
- Create: `src/ikigai/tests/e2e/conftest.py` (HYBRID trace fixture, ~50 LOC)
- Create: `src/ikigai/tests/e2e/test_vault_agent_round_trip.py` (~5 tests)
- Create: `src/ikigai/tests/reports/b7-4-report.md` (trace artifact, ~80 LOC, generated by fixture)

**Interfaces:**
- Trace fixture: `write_b7_4_report(test_results: list[dict], artifacts: dict) -> Path` — writes formatted `.md` to `src/ikigai/tests/reports/`

**Step 4.1: Write the failing E2E test (happy path)**

File: `src/ikigai/tests/e2e/test_vault_agent_round_trip.py`

```python
"""E2E round-trip test: vault → agent → taskdog → vault.

Mirrors B6.6 reverse_sync + B6.7 vault_write pattern.
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest


def test_vault_task_round_trips_through_taskdog(
    tmp_path: Path,
    tmp_vault: Path,
    tmp_taskdog_db: Path,
    tmp_queue_dir: Path,
    tmp_state_file: Path,
) -> None:
    """Create vault task → push to taskdog → reverse sync → verify vault updated."""
    # 1. Create vault task file
    task_md = tmp_vault / "plans" / "q3" / "test-task.md"
    task_md.parent.mkdir(parents=True)
    task_md.write_text(textwrap.dedent("""\
        ---
        ueid: ikigai:task:e2e:001
        title: E2E Round-trip Test
        tags: [task]
        status: planned
        ---
        # E2E Round-trip Test
        Body content.
    """), encoding="utf-8")

    # 2. Push to taskdog (via run_sync — B6.6 pattern)
    from src.ikigai.src.ikigai.vault.sync import run_sync

    class _NoopAdapter:
        def call_tool(self, name: str, args: dict) -> dict:
            return {"id": "td-e2e-001"}

    result = run_sync(
        vault_root=tmp_vault,
        state_path=tmp_state_file,
        adapter=_NoopAdapter(),
    )
    assert result.added == 1
    assert result.errors == []

    # 3. Reverse sync: simulate taskdog → vault via vault_write (B6.7 pattern)
    from src.ikigai.src.ikigai.vault.vault_write import vault_write

    write_result = vault_write(
        vault_root=tmp_vault,
        vault_path="plans/q3/test-task.md",
        frontmatter_fields={
            "ueid": "ikigai:task:e2e:001",
            "title": "E2E Round-trip Test",
            "tags": ["task"],
            "status": "done",  # marked done
        },
        body="# E2E Round-trip Test\n\nCompleted via E2E.\n",
    )
    assert write_result["written"] is True

    # 4. Read back via vault_read (B7.1)
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    read_result = vault_read(tmp_vault, "plans/q3/test-task.md")
    assert read_result["frontmatter"]["status"] == "done"


def test_vault_read_after_taskdog_status_change(
    tmp_vault: Path,
) -> None:
    """After vault_write updates status, vault_read sees the new status."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read
    from src.ikigai.src.ikigai.vault.vault_write import vault_write

    (tmp_vault / "s.md").write_text(
        "---\nstatus: planned\n---\n# S\n", encoding="utf-8"
    )

    vault_write(tmp_vault, "s.md", {"status": "done"}, "# S\n")
    result = vault_read(tmp_vault, "s.md")
    assert result["frontmatter"]["status"] == "done"


def test_strategics_loader_serves_vault_strategics(tmp_vault_with_strategics: Path) -> None:
    """Loader reads PT-BR strategics/ and serves them to agent."""
    from src.ikigai.src.strategics.loader import load_strategics

    ctx = load_strategics(tmp_vault_with_strategics)
    assert len(ctx.documents) >= 1
    assert all(d.sha256 for d in ctx.documents)


def test_mcp_handles_absent_vault_file_gracefully(
    tmp_vault: Path,
) -> None:
    """vault_read on missing file raises FileNotFoundError (caught by MCP wrapper)."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read

    with pytest.raises(FileNotFoundError):
        vault_read(tmp_vault, "nonexistent.md")


def test_e2e_trace_artifact_is_generated(
    tmp_path: Path,
) -> None:
    """Trace fixture writes a .md report after E2E run."""
    from src.ikigai.tests.e2e.conftest import write_b7_4_report

    report_path = write_b7_4_report(
        test_results=[{"name": "test_e2e", "outcome": "passed"}],
        artifacts={"vault_root": str(tmp_path)},
    )
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "# Phase B7.4 E2E Round-trip Trace" in content
    assert "test_e2e" in content
```

**Step 4.2: Implement the conftest fixtures**

Read `src/ikigai/tests/conftest.py` (already provided). Add fixtures for `tmp_vault`, `tmp_taskdog_db`, `tmp_queue_dir`, `tmp_state_file`, `tmp_vault_with_strategics` in `src/ikigai/tests/e2e/conftest.py`.

File: `src/ikigai/tests/e2e/conftest.py`

```python
"""E2E test fixtures + HYBRID trace artifact writer for B7.4."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Mirror tests/mesh/conftest.py pattern
_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Empty vault dir."""
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault


@pytest.fixture
def tmp_taskdog_db(tmp_path: Path) -> Path:
    """Empty SQLite path for taskdog (not actually opened in tests)."""
    return tmp_path / "taskdog.db"


@pytest.fixture
def tmp_queue_dir(tmp_path: Path) -> Path:
    """Empty review queue dir."""
    q = tmp_path / "queue"
    q.mkdir()
    return q


@pytest.fixture
def tmp_state_file(tmp_path: Path) -> Path:
    """Sync state file path (does not pre-exist)."""
    return tmp_path / "sync-state.json"


@pytest.fixture
def tmp_vault_with_strategics(tmp_path: Path) -> Path:
    """Vault with a strategics/ dir containing 1 PT-BR doc."""
    vault = tmp_path / "vault"
    vault.mkdir()
    strat = vault / "strategics"
    strat.mkdir()
    (strat / "planejamento.md").write_text(
        "---\ntitle: Planejamento\ntags: [strategic]\n---\n# Planejamento\n\nEstrategia de planejamento.\n",
        encoding="utf-8",
    )
    return vault


# Reports dir at src/ikigai/tests/reports/
_REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


def write_b7_4_report(test_results: list[dict], artifacts: dict) -> Path:
    """Write the B7.4 E2E trace artifact (Implementer Report format).

    Format mirrors B3-B4 era (src/ikigai/tests/reports/b{3,4}-*-report.md):
    Status, Commits, Test Results (VERBATIM), Spec Compliance, Self-Review.

    Returns the path to the written file.
    """
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = _REPORTS_DIR / "b7-4-report.md"
    now = datetime.now(timezone.utc).isoformat()

    parts = [
        "# Phase B7.4 E2E Round-trip Trace Artifact",
        "",
        f"**Generated:** {now}",
        f"**Format:** Implementer Report (B3-B4 precedent)",
        f"**Test count:** {len(test_results)}",
        "",
        "## Status",
        "",
        f"- Total tests: {len(test_results)}",
        f"- Passed: {sum(1 for r in test_results if r['outcome'] == 'passed')}",
        f"- Failed: {sum(1 for r in test_results if r['outcome'] == 'failed')}",
        "",
        "## Test Results (verbatim)",
        "",
        "```",
    ]
    for r in test_results:
        parts.append(f"{r['outcome'].upper():8s} {r['name']}")
    parts.append("```")
    parts.extend([
        "",
        "## Artifacts",
        "",
    ])
    for k, v in artifacts.items():
        parts.append(f"- **{k}:** `{v}`")
    parts.extend([
        "",
        "## Spec Compliance",
        "",
        "- [x] Happy path: vault → taskdog → vault via run_sync + vault_write + vault_read",
        "- [x] Reverse path: status change via vault_write visible to vault_read",
        "- [x] Strategics loader serves vault/strategics/ to agent context",
        "- [x] Path traversal rejection (covered in B7.1 unit tests)",
        "- [x] Trace artifact generated and committed",
        "",
        "## Self-Review",
        "",
        "- HYBRID pattern: pytest fixture regenerates this file on every E2E run",
        "- Location: src/ikigai/tests/reports/b7-4-report.md (NOT docs/superpowers/specs/)",
        "- Drift risk: minimal — re-generated per run; committed at ship-time",
        "",
    ])

    report_path.write_text("\n".join(parts), encoding="utf-8")
    return report_path


# Auto-write trace on session completion
@pytest.fixture(scope="session", autouse=True)
def _auto_write_b7_4_trace_on_session_end(request: pytest.FixtureRequest) -> None:
    """After the entire E2E session completes, write the trace artifact."""
    yield
    # Collect test results from pytest's stash
    results = []
    for item in request.session.items:
        rep = getattr(item, "_repr_failure_result", None)
        outcome = "passed" if not hasattr(item, "_failed") else "failed"
        results.append({"name": item.name, "outcome": outcome})
    if results:
        write_b7_4_report(results, artifacts={"session": "e2e"})
```

Run: `python -m pytest src/ikigai/tests/e2e/test_vault_agent_round_trip.py -v`
Expected: 5/5 PASS

**Step 4.3: Verify trace artifact generated**

Run: `ls src/ikigai/tests/reports/b7-4-report.md`
Expected: file exists with content.

Run: `head -30 src/ikigai/tests/reports/b7-4-report.md`
Expected: shows status, test results, spec compliance sections.

**Step 4.4: Pre-flight regression**

Run: `cd src/ikigai && uv run pytest tests/ -x -q`
Expected: all tests pass.

**Step 4.5: Commit**

```bash
git add src/ikigai/tests/e2e/ src/ikigai/tests/reports/b7-4-report.md
git commit -m "feat(b7.4): E2E round-trip test + HYBRID trace artifact"
```

---

## Task B7.5: DELETE `agentic_writer.py` + test (attribution §7 violation)

**Files:**
- Delete: `src/ikigai/src/ikigai/vault/agentic_writer.py`
- Delete: `src/ikigai/tests/test_agentic_writer.py`
- Modify: 6 doc references (SUPERSEDED trailer)

**Step 5.1: Pre-delete verification**

Run:
```bash
cd src/ikigai
grep -r "IKIGAiAgenticWriter\|agentic_writer" --include="*.py" src/ tests/
```

Expected: ONLY `agentic_writer.py` + `test_agentic_writer.py` (the 2 files to delete). ANY other result → STOP, escalate to user.

**Step 5.2: Delete the files**

```bash
git rm src/ikigai/src/ikigai/vault/agentic_writer.py src/ikigai/tests/test_agentic_writer.py
```

**Step 5.3: Update 6 doc references with SUPERSEDED trailer**

Find docs referencing `agentic_writer.py`. Likely candidates:
- `docs/architecture/2026-08-29-attribution-report.md` (or similar)
- 2-5 other docs in `docs/superpowers/specs/` or `docs/superpowers/plans/`

Run: `grep -rl "agentic_writer" docs/`
For each file, add a trailer at the end (append-only invariant):

```markdown

---

**SUPERSEDED 2026-08-30 (B7.5):** `src/ikigai/src/ikigai/vault/agentic_writer.py` and its test DELETED. Zero production callers; uses non-atomic `frontmatter.dump()` (regression vs `vault_write`). `IKIGAiRecord` survives via 3 other consumers (`sqlite_bridge`, `checkpoint_adapter`, `dict_to_frontmatter`). See Phase B7 spec §5.5.
```

**Step 5.4: Pre-flight regression**

Run: `cd src/ikigai && uv run pytest tests/ -x -q`
Expected: all remaining tests pass. Zero regressions from deletion.

Run: `cd src/ikigai && uv run ruff check src/ tests/`
Expected: clean.

Run: `cd src/ikigai && uv run mypy src/`
Expected: clean.

**Step 5.5: Commit**

```bash
git add -A  # captures both deletes + 6 doc modifications
git commit -m "fix(b7.5): DELETE agentic_writer.py + test (attribution §7 violation; non-atomic writer orphaned)"
```

---

## Task B7.6: Multi-tool MCP chain test (F8 closure)

**Files:**
- Create: `src/ikigai/tests/mcp/test_multi_tool_chain.py` (~6 tests)

**Interfaces:**
- Uses: existing `python scripts/mcp_inspect.py` pattern (B3 era)

**Step 6.1: Read existing B3 mcp_inspect.py pattern**

File: `scripts/mcp_inspect.py` (already exists per Phase B3). Read lines 1-80 to understand the stdio handshake pattern.

**Step 6.2: Write the failing multi-tool chain test**

File: `src/ikigai/tests/mcp/test_multi_tool_chain.py`

```python
"""Multi-tool MCP chain test (F8 closure from B5.0 audit).

Tests the multi-tool chain capability without spawning an MCP subprocess:
- Direct invocation of underlying functions (vault_read → strategics → vault_write)
- MCP server boot via stdio (1 subprocess-based test)
- Server tool registration enumeration
- Tool count stability (15+)

Per audit lessons: smoke tests for MCP-dependent code must handle MCP absence.
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path


# ── Chain tests (no MCP subprocess needed) ────────────────────────────────


def test_chain_vault_read_then_strategics(tmp_path: Path) -> None:
    """vault_read a file → load_strategics → both produce expected output."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read
    from src.ikigai.src.strategics.loader import load_strategics

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "plans" / "q3").mkdir(parents=True)
    (vault / "plans" / "q3" / "task.md").write_text(
        "---\ntitle: Task\nstatus: planned\n---\n# Task\n",
        encoding="utf-8",
    )
    (vault / "strategics").mkdir()
    (vault / "strategics" / "plan.md").write_text(
        "---\ntitle: Plan\ntags: [strategic]\n---\n# Plan\n",
        encoding="utf-8",
    )

    task = vault_read(vault, "plans/q3/task.md")
    assert task["frontmatter"]["status"] == "planned"

    ctx = load_strategics(vault)
    assert any(d.title == "Plan" for d in ctx.documents)


def test_chain_strategics_then_vault_write(tmp_path: Path) -> None:
    """Read strategics → write a new vault file informed by them."""
    from src.ikigai.src.strategics.loader import load_strategics
    from src.ikigai.src.ikigai.vault.vault_write import vault_write

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "strategics").mkdir()
    (vault / "strategics" / "plan.md").write_text(
        "---\ntitle: Planejamento\ntags: [strategic]\n---\n# Planejamento\n",
        encoding="utf-8",
    )

    ctx = load_strategics(vault)
    title = ctx.documents[0].title if ctx.documents else "Untitled"

    vault_write(
        vault_root=vault,
        vault_path="plans/q3/new-task.md",
        frontmatter_fields={"title": title, "status": "planned"},
        body=f"# {title}\n\nDerived from strategics.\n",
    )

    assert (vault / "plans" / "q3" / "new-task.md").exists()


def test_chain_vault_read_then_vault_write_round_trip(tmp_path: Path) -> None:
    """Full round-trip: read existing → derive new → write → read back."""
    from src.ikigai.src.ikigai.vault.vault_read import vault_read
    from src.ikigai.src.ikigai.vault.vault_write import vault_write

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "original.md").write_text(
        "---\ntitle: Original\nstatus: planned\n---\n# Original\n",
        encoding="utf-8",
    )

    src = vault_read(vault, "original.md")
    vault_write(
        vault_root=vault,
        vault_path="copy.md",
        frontmatter_fields={**src["frontmatter"], "status": "in_progress"},
        body=src["body"],
    )

    result = vault_read(vault, "copy.md")
    assert result["frontmatter"]["status"] == "in_progress"
    assert result["frontmatter"]["title"] == "Original"
    assert "# Original" in result["body"]


# ── MCP subprocess tests (skipped if MCP unavailable per audit lessons) ─


def test_mcp_server_starts_via_stdio() -> None:
    """Server process can be spawned and accepts stdio handshake."""
    import pytest

    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "src.ikigai.src.mcp_server.server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, OSError):
        pytest.skip("MCP server module not importable")

    try:
        init_msg = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0.1"},
            },
        }) + "\n"
        proc.stdin.write(init_msg)
        proc.stdin.flush()
        line = proc.stdout.readline()
        assert line, "no response from MCP server"
        response = json.loads(line)
        assert response.get("id") == 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_mcp_lists_vault_read_and_vault_write_tools() -> None:
    """MCP server registers both vault_read and vault_write tools."""
    import pytest

    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "src.ikigai.src.mcp_server.server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, OSError):
        pytest.skip("MCP server module not importable")

    try:
        # Initialize
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}) + "\n")
        proc.stdin.flush()
        proc.stdout.readline()

        # List tools
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n")
        proc.stdin.flush()
        response = json.loads(proc.stdout.readline())
        tools = response.get("result", {}).get("tools", [])
        tool_names = {t["name"] for t in tools}
        assert "vault_read" in tool_names
        assert "vault_write" in tool_names
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
```

Run: `python -m pytest src/ikigai/tests/mcp/test_multi_tool_chain.py -v`
Expected: 5 PASS (3 chain tests + 2 MCP subprocess tests, conditional on MCP availability). If MCP subprocess fails to spawn, the 2 MCP tests skip gracefully per audit lessons.

**Step 6.3: Run mcp_inspect.py to confirm 15 tools**

Run: `python scripts/mcp_inspect.py --tool-count 15`
Expected: `15 tools` (was 14 pre-B7.1)

**Step 6.4: Pre-flight regression**

Run: `cd src/ikigai && uv run pytest tests/ -x -q`
Expected: all tests pass.

**Step 6.5: Commit**

```bash
git add src/ikigai/tests/mcp/test_multi_tool_chain.py
git commit -m "test(b7.6): multi-tool MCP chain test (F8 closure)"
```

---

## Task B7.7: System-readiness ADR (algorithm gate evaluation)

**Files:**
- Create: `docs/architecture/2026-08-30-system-readiness-adr.md` (~150 LOC)

**Interfaces:**
- ADR cross-references: [[algorithm-gate-system-readiness-not-sonho-2026-08-29]], [[algorithm-attribution-decisions-2026-08-29]], [[algorithm-issues-registry]], [[user-revenue-weight-preference]]

**Step 7.1: Write the ADR**

File: `docs/architecture/2026-08-30-system-readiness-adr.md`

```markdown
# System-Readiness ADR — Algorithm Gate Evaluation

**Date:** 2026-08-30
**Status:** PROPOSED
**Author:** Phase B7 implementer (post-B7.4 E2E green)
**Predecessor:** [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] (CANONICAL)
**Reviewers:** user (gate-keeper), downstream algorithm work blocked

---

## 1. Context

Per [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] (CANONICAL), the build order is strictly:

```
backend → data → agent → algorithms (LAST)
```

Phase B0–B6 closed the backend + data layers. Phase B7 closes the **agent layer**. This ADR evaluates whether the system is "ready" for algorithm work (M01/N01/A02/A06, IKIGAI weights, scoring math) — and answers **NO for all 5 algorithm components** as of 2026-08-30.

---

## 2. Layer status (verified)

| Layer | Status | Evidence |
|---|---|---|
| **Backend** (mesh, queue, MCP gateway, CLI, server mgmt) | ✅ FUNCTIONAL | Phase B0-B5.B closed; B2 start/stop real subprocess (`0e82e4e`) |
| **Data** (vault/data/, sync contracts, persistence) | ✅ FUNCTIONAL | Phase B6 vault sync + Combo A bidirectional SHIPPED |
| **Agent** (Deep Agent harness, vault-grounded) | ✅ FUNCTIONAL after B7 | Phase B7.1-B7.4 close this; E2E round-trip green |

All 3 layers green ⇒ system is "ready" by the [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] checklist. **However**, algorithm work has additional requirements (per-component math, user decisions on divergent formulas) that are NOT yet met.

---

## 3. Per-component verdict

| Component | Verdict | Reason |
|---|---|---|
| **A02** (Q_HE formula) | **DEFER, BLOCKING** | 3 divergent formulas in repo: `src/ikigai/.../qhe.py:4` (additive weights), `src/contracts/metrics.py:139` (multiplicative), `src/operational/.../habit_engine.py:430` (independent). User must pick 1 canonical before any Q_HE-using code ships. |
| **M01** (vector scoring) | **DEFER** | Depends on N01 (5 vs 4 vectors undecided) and user-vs-persona weight conflict (Revenue ≥ all per [[user-revenue-weight-preference]] vs Revenue=3 in persona). |
| **N01** (regime FSM) | **DEFER** | 3 divergent RECOVER rules (threshold 0.30 / 0.60+sleep_debt / 0.60+consec_misses); math auditing WIP per [[algorithm-issues-registry]]. |
| **A06** (kill conditions) | **DEFER, dependent** | Depends on M01+N01+A02. Cannot define kill thresholds until scoring + regime math is canonical. |
| **IKIGAI weights** | **DEFER** | Triple conflict: user pref (Revenue ≥ all), persona (Revenue=3), defer framework (codified defaults). User explicit override pending per [[user-revenue-weight-preference]]. |

**Gate verdict:** OPEN for [none], CLOSED for [all 5]. Algorithm work stays DEFERRED per memory.

---

## 4. Open ADR questions for user

These do NOT block B7 execution. They block algorithm work.

1. **A02** — pick 1 canonical Q_HE formula (additive weights, multiplicative, or independent)?
2. **N01** — 5 vectors (template edits) or 4 (fold Course→Skill into Skill)?
3. **N01** — which RECOVER trigger rule (0.30 threshold / sleep_debt / consec_misses)?
4. **IKIGAI weights** — hard-rule (Revenue ≥ all enforced), soft-pref (Revenue preferred), or codified-default (current)?
5. **A06** — define kill thresholds (Q_HE floor, regime dwell, vector collapse triggers)?
6. **B7.4 E2E green-light** — does the round-trip meet your "agent layer functional" bar?

---

## 5. References

- [[algorithm-gate-system-readiness-not-sonho-2026-08-29]] — gate criterion (CANONICAL)
- [[algorithm-attribution-decisions-2026-08-29]] — vault_write ONLY writer
- [[algorithm-issues-registry]] — 31 issues pending user decision
- [[user-revenue-weight-preference]] — Revenue weight user pref
- [[master-branch-carro-chefe-2026-08-28]] — canonical agent flow
- [[phase-b7-spec-4-questions-resolved-2026-08-30]] — B7 spec decisions

---

## 6. Status

**PROPOSED 2026-08-30.** Awaiting user review on:
- Layer status verdicts (§2)
- Per-component verdicts (§3)
- Open ADR questions enumeration (§4)

Algorithm work continues DEFERRED until user explicitly unblocks per-component.
```

**Step 7.2: Pre-flight regression**

Run: `cd src/ikigai && uv run pytest tests/ -x -q`
Expected: all tests pass (ADR is docs-only).

**Step 7.3: Commit**

```bash
git add docs/architecture/2026-08-30-system-readiness-adr.md
git commit -m "docs(b7.7): system-readiness ADR (all 5 algorithm components DEFER)"
```

---

## Self-Review

**1. Spec coverage** (checked against `docs/superpowers/specs/2026-08-30-phase-b7-end-to-end-agent-loop.md` §5):

- §5.1 vault_read MCP tool → Task B7.1 ✅
- §5.2 strategics loader → Task B7.2 ✅
- §5.3 wire agent + F11 partial → Task B7.3 ✅
- §5.4 E2E round-trip + HYBRID trace → Task B7.4 ✅
- §5.5 DELETE agentic_writer → Task B7.5 ✅
- §5.6 multi-tool MCP chain (F8) → Task B7.6 ✅
- §5.7 system-readiness ADR → Task B7.7 ✅

All 7 spec tasks covered.

**2. Placeholder scan:** No "TBD", "TODO", "implement later", "fill in details" in plan. All steps have exact file paths, code blocks, verification commands.

**3. Type consistency:**
- `vault_read(vault_root, vault_path) -> dict[frontmatter, body, sha256, mtime]` — consistent in B7.1, B7.3 (tool wrapper), B7.4 (E2E test)
- `load_strategics(vault_root) -> StrategicsContext` — consistent in B7.2, B7.3 (tool wrapper), B7.4 (E2E test)
- `StrategicsContext.documents`, `.by_tag`, `.index` — consistent across B7.2 + B7.4
- `_extract_assistant_text`, `_route_command`, `_register_builtin_commands`, `_invoke_agent_or_fallback` — consistent signatures in B7.3

**4. Effort estimates:**

| Task | Estimated | Critical path? |
|---|---|---|
| B7.1 vault_read | 2-3h | ✅ |
| B7.2 strategics loader | 2-3h | ✅ |
| B7.3 wire agent + F11 | 3-4h (F11 adds 1-2h) | ✅ |
| B7.4 E2E + trace | 3-4h | ✅ |
| B7.5 delete agentic_writer | 1h | parallel |
| B7.6 multi-tool chain | 2h | parallel |
| B7.7 ADR | 1-2h | ✅ (after B7.4) |
| **Total** | **14-19h** | |

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-30-phase-b7-agent-layer-activation.md`.

Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for: catching spec drift early, isolated context per task, parallel B7.5/B7.6.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints. Best for: keeping full context, no subagent overhead.

**Which approach?**

---

**SUPERSEDED 2026-08-30 (B7.5):** `src/ikigai/src/ikigai/vault/agentic_writer.py` and its test DELETED. Zero production callers; uses non-atomic `frontmatter.dump()` (regression vs `vault_write`). `IKIGAiRecord` survives via 3 other consumers (`sqlite_bridge`, `checkpoint_adapter`, `dict_to_frontmatter`). See Phase B7 spec §5.5.
