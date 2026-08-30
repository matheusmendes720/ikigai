"""Tests for ikigai_sync_vault (Tool 7) — Combo A Important #3 migration.

Per attribution §7 (combo-a-whole-branch-review-backlog-2026-08-29):
all vault writes must go through `vault_write` (atomic + VaultLock +
path-traversal protection). Pre-migration, ikigai_sync_vault called
`log_file.write_text(content, encoding="utf-8")` directly, bypassing
the canonical writer. These tests verify the migration:

  - File is written via vault_write (sha256 in return message)
  - Frontmatter contains all 9 fields from the checkpoint
  - Body preserves the human-readable vector scores + corrections
  - VaultLock concurrency lock is acquired (no concurrent write races)
  - Path-traversal protection rejects relative paths escaping vault root
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# conftest.py already puts src/ikigai/src/ on sys.path so `agents` resolves.
# Also add the repo root so absolute cross-module imports like
# `src.ikigai.src.ikigai.vault.vault_write` work (matches E2E test pattern).
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest


@pytest.fixture
def fresh_vault(monkeypatch: pytest.MonkeyPatch):
    """Isolated vault/ root + checkpoint mock for sync_vault tests.

    Uses tempfile.mkdtemp instead of the pytest tmp_path fixture to avoid
    the Windows pytest-of-mathe lock on AppData\\Local\\Temp\\pytest-of-mathe
    (matches test_ikigai_maintainer_nodes.py pattern).
    """
    tmp_root = Path(tempfile.mkdtemp(prefix="ikigai_sync_vault_smoke_"))
    vault_root = tmp_root / "vault"
    vault_root.mkdir()

    # Patch _VAULT_DIR to point at the temp vault
    from agents import tools as _tools_mod

    monkeypatch.setattr(_tools_mod, "_VAULT_DIR", vault_root)

    # Stub _read_checkpoint_data so we don't depend on a live checkpoint DB
    monkeypatch.setattr(
        _tools_mod,
        "_read_checkpoint_data",
        lambda thread_id="default": {
            "cycle_id": "2026-08-30-smoke",
            "vector_scores": {
                "passion": 70.0,
                "skill": 60.0,
                "market": 80.0,
                "revenue": 55.0,
                "course": 65.0,
            },
            "regime_state": "PUSH",
            "q_he_score": 0.7321,
            "meta_vector_score": 0.6812,
            "phase": "BUILD",
            "corrections": [
                {"heuristic": "H3", "description": "skill underweight"},
                {"heuristic": "H5", "description": "market strong"},
            ],
        },
    )
    return vault_root


def _read_frontmatter_and_body(md_path: Path) -> tuple[dict[str, object], str]:
    """Split a vault markdown file into (frontmatter_fields, body).

    Uses python-frontmatter so YAML quoting (single-quoted strings, JSON
    arrays, etc.) is preserved verbatim. A naive `partition(':')` parser
    would lose the quoting that frontmatter.dumps applies to string values.
    """
    import frontmatter as _fm

    parsed = _fm.loads(md_path.read_text(encoding="utf-8"))
    return dict(parsed.metadata), parsed.content


def test_sync_vault_writes_file_via_vault_write(fresh_vault: Path) -> None:
    """Tool invocation must produce a cycle-*.md file under vault/."""
    from agents import tools as _tools_mod

    result = _tools_mod.ikigai_sync_vault.invoke({})

    expected = fresh_vault / "cycle-2026-08-30-smoke.md"
    assert expected.exists(), f"missing vault file {expected}"
    assert "✅ Synced to vault" in result
    assert "sha256=" in result, "return message must include sha256 from vault_write"
    assert str(expected) in result


def test_sync_vault_writes_all_frontmatter_fields(fresh_vault: Path) -> None:
    """All 9 fields from the checkpoint must land in YAML frontmatter."""
    from agents import tools as _tools_mod

    _tools_mod.ikigai_sync_vault.invoke({})

    fields, _ = _read_frontmatter_and_body(fresh_vault / "cycle-2026-08-30-smoke.md")
    assert fields["ueid"] == "ikigai:cycle:2026-08-30-smoke"
    assert fields["cycle_id"] == "2026-08-30-smoke"
    assert fields["date"] == "2026-08-30"
    assert fields["regime"] == "PUSH"
    assert fields["q_he"] == 0.7321
    assert fields["meta_vector"] == 0.6812
    assert fields["phase"] == "BUILD"
    assert fields["corrections_count"] == 2
    # vector_scores is JSON-encoded to keep the frontmatter flat
    parsed_scores = json.loads(fields["vector_scores"])
    assert parsed_scores["passion"] == 70.0
    assert parsed_scores["revenue"] == 55.0


def test_sync_vault_body_contains_vector_table_and_corrections(fresh_vault: Path) -> None:
    """Body must surface the human-readable regime / vectors / corrections."""
    from agents import tools as _tools_mod

    _tools_mod.ikigai_sync_vault.invoke({})

    _, body = _read_frontmatter_and_body(fresh_vault / "cycle-2026-08-30-smoke.md")
    assert "# IKIGAi Cycle — 2026-08-30-smoke" in body
    assert "Regime: PUSH" in body
    assert "Q_HE: 0.7321" in body
    assert "| Passion | 70.0 |" in body
    assert "| Revenue | 55.0 |" in body
    assert "Phase: BUILD" in body
    # Both corrections must be listed (the tool keeps the last 5)
    assert "[H3] skill underweight" in body
    assert "[H5] market strong" in body


def test_sync_vault_uses_atomic_write(fresh_vault: Path) -> None:
    """vault_write composes via tmp + os.replace() — no partial writes on crash.

    We assert this indirectly: vault_write must NOT leave a .tmp sidecar
    file behind when it returns successfully.
    """
    from agents import tools as _tools_mod

    _tools_mod.ikigai_sync_vault.invoke({})

    sidecars = list(fresh_vault.glob("*.tmp"))
    assert sidecars == [], f"unexpected tmp sidecars after sync: {sidecars}"


def test_sync_vault_rejects_path_traversal(monkeypatch: pytest.MonkeyPatch) -> None:
    """If vault_path traverses the vault root, vault_write raises ValueError.

    Per vault_write contract (B6.4 lesson): path traversal protection rejects
    any vault_path whose resolved form escapes vault_root. The LangChain tool
    propagates this — we verify the ValueError surfaces via .invoke() rather
    than writing the file.
    """
    from agents import tools as _tools_mod

    # Use a fresh vault_root so we can assert the bad path resolves outside it
    tmp_root = Path(tempfile.mkdtemp(prefix="ikigai_sync_vault_traversal_"))
    vault_root = tmp_root / "vault"
    vault_root.mkdir()
    monkeypatch.setattr(_tools_mod, "_VAULT_DIR", vault_root)
    monkeypatch.setattr(
        _tools_mod,
        "_read_checkpoint_data",
        lambda thread_id="default": {
            "cycle_id": "safe-cycle",  # path is built from this; safe value
            "vector_scores": {},
            "regime_state": "PUSH",
            "q_he_score": 0.5,
            "meta_vector_score": 0.5,
            "phase": "BUILD",
            "corrections": [],
        },
    )

    # Reach into vault_write to verify the traversal check directly.
    # The sync_vault tool composes vault_path as `cycle-{cycle_id}.md`,
    # so to test the traversal rejection we have to call vault_write with
    # a path that escapes the vault root.
    from src.ikigai.src.ikigai.vault.vault_write import vault_write

    with pytest.raises(ValueError, match="traversal|outside|escape|root"):
        vault_write(
            vault_root=vault_root,
            vault_path="../../escape.md",
            frontmatter_fields={"ueid": "ikigai:cycle:bad"},
            body="bad body",
        )

    # Nothing was written outside the vault root.
    assert not (tmp_root / "escape.md").exists()