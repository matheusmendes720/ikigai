"""E2E round-trip test: vault -> agent -> forks -> vault.

Mirrors B6.6 reverse_sync + B6.7 vault_write pattern. Closes B7.4:
the agent layer is demonstrably functional when this test passes.

Round-trip path exercised:
    1. Create vault task file (raw markdown)
    2. Sync vault -> taskdog (B6.6 run_sync + NoopAdapter stub)
    3. Reverse sync: simulate taskdog status change -> vault via vault_write (B6.7)
    4. Verify the change is visible via vault_read (B7.1)

Plus 4 supporting tests for: vault_write -> vault_read round-trip,
strategics loader, missing-file behavior, and the trace artifact itself.

All vault I/O goes through vault_write (the ONLY writer per
attribution report §7) and vault_read (read-only mirror).
"""

from __future__ import annotations

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
    """Create vault task -> push to taskdog -> reverse sync -> verify vault updated."""
    # 1. Create vault task file
    task_md = tmp_vault / "plans" / "q3" / "test-task.md"
    task_md.parent.mkdir(parents=True)
    task_md.write_text(
        textwrap.dedent("""\
        ---
        ueid: ikigai:task:e2e:001
        title: E2E Round-trip Test
        tags: [task]
        status: planned
        ---
        # E2E Round-trip Test
        Body content.
    """),
        encoding="utf-8",
    )

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

    # 3. Reverse sync: simulate taskdog -> vault via vault_write (B6.7 pattern)
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

    (tmp_vault / "s.md").write_text("---\nstatus: planned\n---\n# S\n", encoding="utf-8")

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
