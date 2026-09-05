"""B-D09 audit-log test for vault_write.

Per Plan A spec drift invariant (g) + ADR-014 R4:
    "Every vault_write call MUST append a record to .vault_audit.log at vault
    root containing actor + timestamp + path."

The audit log lives at `vault_root/.vault_audit.log` (NOT next to the written
file) per ADR-012 vault-only invariant. It is append-only and survives
across multiple vault_write calls.

Format (per vault_write.py:131):
    {ISO-8601 UTC timestamp} actor={actor} path={vault_path}\n

where actor ∈ {"user", "agent", "system"} per vault_write signature.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

# Ensure repo root on sys.path for imports
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sys_ikigai.vault.vault_write import vault_write  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vault_root(tmp_path: Path) -> Path:
    """Vault root dir for tests (fresh per test)."""
    root = tmp_path / "vault"
    root.mkdir()
    return root


def _audit_path(vault_root: Path) -> Path:
    """Canonical audit log path used by vault_write."""
    return vault_root / ".vault_audit.log"


def _read_audit_entries(vault_root: Path) -> list[str]:
    """Return all lines from the audit log (no stripping), one per write."""
    p = _audit_path(vault_root)
    if not p.exists():
        return []
    return p.read_text(encoding="utf-8").splitlines()


# Regex matching: "<ISO-timestamp> actor=<kind> path=<vault-relative-path>"
# ISO-8601 UTC examples: 2026-09-04T12:34:56.789012+00:00
_AUDIT_LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"
    r"\s+actor=(?P<actor>user|agent|system)"
    r"\s+path=(?P<path>.+)$"
)


# ---------------------------------------------------------------------------
# Core invariant tests
# ---------------------------------------------------------------------------


def test_audit_log_created_on_first_write(vault_root: Path) -> None:
    """After a single vault_write, .vault_audit.log exists with one entry."""
    assert not _audit_path(vault_root).exists(), "audit log should not pre-exist"

    vault_write(
        vault_root=vault_root,
        vault_path="plans/q3/task-x.md",
        frontmatter_fields={
            "ueid": "tsk:audit:00000000-0000-0000-0000-000000000000:0000000000000000",
            "title": "Audit Test",
        },
        body="# Audit Test\n",
    )

    assert _audit_path(vault_root).exists(), "audit log must exist after vault_write"
    entries = _read_audit_entries(vault_root)
    assert len(entries) == 1


def test_audit_log_entry_has_actor_timestamp_path(vault_root: Path) -> None:
    """Each audit entry MUST contain timestamp + actor + path per drift invariant (g)."""
    vault_write(
        vault_root=vault_root,
        vault_path="audit-fields.md",
        frontmatter_fields={
            "ueid": "tsk:fields:00000000-0000-0000-0000-000000000000:0000000000000001"
        },
        body="x",
        actor="agent",
    )

    entries = _read_audit_entries(vault_root)
    assert len(entries) == 1
    line = entries[0]
    m = _AUDIT_LINE_RE.match(line)
    assert m is not None, f"audit line does not match expected format: {line!r}"
    assert m.group("actor") == "agent"
    assert m.group("path") == "audit-fields.md"
    # Timestamp must be ISO-8601 UTC (presence + parseable)
    assert m.group("ts"), "timestamp must be present"


@pytest.mark.parametrize("actor", ["user", "agent", "system"])
def test_audit_log_records_each_actor(vault_root: Path, actor: str) -> None:
    """Each of the 3 valid actor values must be recorded faithfully."""
    vault_write(
        vault_root=vault_root,
        vault_path=f"by-{actor}.md",
        frontmatter_fields={
            "ueid": f"tsk:{actor}:00000000-0000-0000-0000-000000000000:000000000000000{len(actor)}"
        },
        body="x",
        actor=actor,  # type: ignore[arg-type]
    )

    entries = _read_audit_entries(vault_root)
    assert len(entries) == 1
    m = _AUDIT_LINE_RE.match(entries[0])
    assert m is not None
    assert m.group("actor") == actor
    assert m.group("path") == f"by-{actor}.md"


def test_audit_log_appends_across_multiple_writes(vault_root: Path) -> None:
    """Multiple vault_write calls MUST append, not overwrite."""
    paths = ["first.md", "second.md", "third.md"]
    for i, p in enumerate(paths):
        vault_write(
            vault_root=vault_root,
            vault_path=p,
            frontmatter_fields={
                "ueid": f"tsk:multi:00000000-0000-0000-0000-000000000000:000000000000000{i}"
            },
            body=f"content {i}",
            actor="user",
        )

    entries = _read_audit_entries(vault_root)
    assert len(entries) == 3, f"expected 3 entries (append-only), got {len(entries)}"
    recorded_paths = [_AUDIT_LINE_RE.match(e).group("path") for e in entries]  # type: ignore[union-attr]
    assert recorded_paths == paths, "audit log order must match write order"


def test_audit_log_preserves_previous_entries_on_overwrite(
    vault_root: Path,
) -> None:
    """Re-writing an existing vault path appends a new audit entry (does not erase)."""
    vault_write(
        vault_root=vault_root,
        vault_path="overwrite-me.md",
        frontmatter_fields={"v": 1},
        body="v1",
    )
    vault_write(
        vault_root=vault_root,
        vault_path="overwrite-me.md",
        frontmatter_fields={"v": 2},
        body="v2",
    )

    entries = _read_audit_entries(vault_root)
    assert len(entries) == 2
    assert all(
        _AUDIT_LINE_RE.match(e).group("path") == "overwrite-me.md"
        for e in entries  # type: ignore[union-attr]
    )


def test_audit_log_failure_does_not_fail_write(
    vault_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If audit log write fails, the vault_write itself MUST still succeed.

    Per vault_write.py:132-134, audit log failure is swallowed — the write
    is already on disk and the user shouldn't lose data due to log I/O.
    This test patches the audit write to raise and verifies the write
    returns success.
    """
    import sys_ikigai.vault.vault_write as vw

    real_open = vw.Path.open

    def failing_open(self, *args, **kwargs):
        # Fail only for the audit log path
        if self.name == ".vault_audit.log":
            raise OSError("simulated audit log failure")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(vw.Path, "open", failing_open)

    # This MUST NOT raise
    result = vault_write(
        vault_root=vault_root,
        vault_path="must-survive.md",
        frontmatter_fields={
            "ueid": "tsk:survive:00000000-0000-0000-0000-000000000000:0000000000000099"
        },
        body="important content",
    )

    assert result["written"] is True
    assert (vault_root / "must-survive.md").exists()
    assert "important content" in (vault_root / "must-survive.md").read_text()


# ---------------------------------------------------------------------------
# Negative tests
# ---------------------------------------------------------------------------


def test_vault_write_rejects_invalid_actor(vault_root: Path) -> None:
    """Invalid actor value MUST raise ValueError (per ADR-014 R4)."""
    with pytest.raises(ValueError, match="actor must be one of"):
        vault_write(
            vault_root=vault_root,
            vault_path="bad-actor.md",
            frontmatter_fields={"x": 1},
            body="x",
            actor="hacker",  # type: ignore[arg-type]
        )

    # Audit log must NOT contain the failed write
    entries = _read_audit_entries(vault_root)
    assert entries == [], "failed writes must not be audited"


def test_failed_write_does_not_create_audit_entry(
    vault_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When vault_write raises (e.g., path traversal), NO audit entry is created."""
    with pytest.raises(ValueError, match="resolves outside"):
        vault_write(
            vault_root=vault_root,
            vault_path="../../../etc/passwd.md",
            frontmatter_fields={"x": 1},
            body="bad",
        )

    assert not _audit_path(vault_root).exists(), "audit log must not be created on failed writes"


# ---------------------------------------------------------------------------
# Drift invariant (g) — bulk scan
# ---------------------------------------------------------------------------


def test_all_vault_write_calls_produce_audit_entries(vault_root: Path) -> None:
    """N writes MUST produce exactly N audit entries (drift invariant (g))."""
    n_writes = 5
    for i in range(n_writes):
        vault_write(
            vault_root=vault_root,
            vault_path=f"bulk-{i}.md",
            frontmatter_fields={
                "ueid": f"tsk:bulk:00000000-0000-0000-0000-000000000000:000000000000000{i}"
            },
            body=f"bulk {i}",
        )

    entries = _read_audit_entries(vault_root)
    assert len(entries) == n_writes, (
        f"audit invariant (g) violated: {n_writes} writes produced {len(entries)} entries"
    )

    # Every entry must have a parseable timestamp + actor + path
    for entry in entries:
        m = _AUDIT_LINE_RE.match(entry)
        assert m is not None, f"unparseable audit entry: {entry!r}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
