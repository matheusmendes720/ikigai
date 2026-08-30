"""vault_write lower-level function — the only vault writer per attribution §7."""
import hashlib
import sys
from pathlib import Path

import pytest

# Ensure repo root on sys.path for imports
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.ikigai.src.ikigai.vault.vault_write import vault_write


@pytest.fixture
def vault_root(tmp_path: Path) -> Path:
    """Vault root dir for tests."""
    root = tmp_path / "vault"
    root.mkdir()
    return root


def test_vault_write_creates_markdown_file(vault_root: Path) -> None:
    """vault_write creates a .md file with frontmatter + body."""
    result = vault_write(
        vault_root=vault_root,
        vault_path="plans/q3/task-x.md",
        frontmatter_fields={"ueid": "ikigai:task:x:1", "title": "Task X", "status": "planned"},
        body="# Task X\n\nDetails here.\n",
    )
    assert result["written"] is True
    target = vault_root / "plans" / "q3" / "task-x.md"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "ueid: ikigai:task:x:1" in content
    assert "title: Task X" in content
    assert "# Task X" in content


def test_vault_write_rejects_path_traversal(vault_root: Path) -> None:
    """vault_path with .. that resolves outside vault/ → rejection."""
    with pytest.raises(ValueError, match="path.*outside vault"):
        vault_write(
            vault_root=vault_root,
            vault_path="../../../etc/passwd.md",
            frontmatter_fields={"x": 1},
            body="bad",
        )


def test_vault_write_rejects_absolute_path(vault_root: Path) -> None:
    """Absolute paths rejected (must be relative to vault root)."""
    with pytest.raises(ValueError, match="absolute"):
        vault_write(
            vault_root=vault_root,
            vault_path="C:\\Windows\\System32\\test.md",
            frontmatter_fields={"x": 1},
            body="bad",
        )


def test_vault_write_returns_sha256(vault_root: Path) -> None:
    """sha256 in result is sha256 of final file content."""
    body = "x" * 100
    fm = {"ueid": "ikigai:task:y:2"}
    result = vault_write(
        vault_root=vault_root,
        vault_path="y.md",
        frontmatter_fields=fm,
        body=body,
    )
    target = vault_root / "y.md"
    expected = hashlib.sha256(target.read_bytes()).hexdigest()
    assert result["sha256"] == expected


def test_vault_write_atomic_no_partial_file(vault_root: Path) -> None:
    """Atomic write: no .tmp leftover on success."""
    vault_write(
        vault_root=vault_root,
        vault_path="z.md",
        frontmatter_fields={"x": 1},
        body="z",
    )
    target = vault_root / "z.md"
    assert target.exists()
    assert not (vault_root / "z.tmp").exists()


def test_vault_write_rejects_empty_body_and_frontmatter(vault_root: Path) -> None:
    """Empty body + empty frontmatter → rejection (no-op protection)."""
    with pytest.raises(ValueError, match="empty"):
        vault_write(
            vault_root=vault_root,
            vault_path="empty.md",
            frontmatter_fields={},
            body="",
        )


def test_vault_write_overwrites_existing_atomically(vault_root: Path) -> None:
    """Second write to same path replaces first (Windows-safe)."""
    vault_write(
        vault_root=vault_root,
        vault_path="w.md",
        frontmatter_fields={"v": 1},
        body="first",
    )
    vault_write(
        vault_root=vault_root,
        vault_path="w.md",
        frontmatter_fields={"v": 2},
        body="second",
    )
    content = (vault_root / "w.md").read_text()
    assert "v: 2" in content
    assert "second" in content
    assert "first" not in content


def test_vault_write_uses_os_replace_for_atomicity(
    vault_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """vault_write uses os.replace() (atomic rename), NOT frontmatter.dump().

    The docstring claim was: "frontmatter.dump() writes temp + renames".
    This is FALSE — frontmatter.dump() only does f.write(). The fix
    replaced frontmatter.dump() with explicit tmp-write + os.replace().
    This test verifies the fix by spying on os.replace.
    """
    import src.ikigai.src.ikigai.vault.vault_write as vw

    calls: list[tuple[str, str]] = []
    real_replace = vw.os.replace

    def spy_replace(src, dst):
        calls.append((str(src), str(dst)))
        return real_replace(src, dst)

    monkeypatch.setattr(vw.os, "replace", spy_replace)

    vault_write(
        vault_root=vault_root,
        vault_path="atomic-spy.md",
        frontmatter_fields={"ueid": "task:a:001:002"},
        body="hello",
    )

    assert len(calls) == 1
    src, dst = calls[0]
    # src must be a tmp file in vault_root
    assert ".tmp_vault_write_" in src
    assert src.startswith(str(vault_root))
    # dst must be the target path
    assert dst.endswith("atomic-spy.md")
    # Tmp file must be gone after os.replace
    assert not Path(src).exists()
    # Target file must exist with expected content
    assert Path(dst).exists()
    content = Path(dst).read_text(encoding="utf-8")
    assert "ueid: task:a:001:002" in content
    assert "hello" in content


def test_vault_write_atomic_no_partial_on_rename_failure(
    vault_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If os.replace() fails, target file is NOT partially created.

    The os.replace() pattern guarantees atomicity: either the rename
    succeeds (file fully written) or fails (no partial target exists).
    This test forces os.replace to raise and verifies the target file
    is never partially visible.
    """
    import src.ikigai.src.ikigai.vault.vault_write as vw

    def failing_replace(src, dst):
        raise OSError("simulated rename failure")

    monkeypatch.setattr(vw.os, "replace", failing_replace)

    target_path = "fail-on-rename.md"
    target_abs = vault_root / target_path

    with pytest.raises(OSError, match="simulated rename failure"):
        vault_write(
            vault_root=vault_root,
            vault_path=target_path,
            frontmatter_fields={"x": 1},
            body="never written",
        )

    # Target must NOT exist — atomicity guarantees no partial file
    assert not target_abs.exists()
    # Tmp files must be cleaned up on failure
    leftover_tmp = list(vault_root.glob(".tmp_vault_write_*"))
    assert leftover_tmp == [], f"leftover tmp files: {leftover_tmp}"


def test_vault_write_atomic_writer_observation_during_write(
    vault_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """During write, target file is either absent OR fully present.

    With os.replace() the rename is atomic — readers observe either the
    old (absent) state or the new (fully-written) state, never partial
    bytes. This test patches os.replace() to delay so the polling thread
    can sample the target file mid-write.
    """
    import threading
    import time

    import src.ikigai.src.ikigai.vault.vault_write as vw

    body = "x" * 200_000  # 200KB — slow enough to observe
    target_abs = vault_root / "atomic-during.md"

    real_replace = vw.os.replace
    replace_started = threading.Event()

    def slow_replace(src, dst):
        replace_started.set()
        time.sleep(0.15)  # window for polling thread to sample
        return real_replace(src, dst)

    monkeypatch.setattr(vw.os, "replace", slow_replace)

    observations: list[int] = []
    stop = threading.Event()

    def poller() -> None:
        while not stop.is_set():
            if target_abs.exists():
                observations.append(target_abs.stat().st_size)
            else:
                observations.append(0)
            time.sleep(0.005)

    poll_thread = threading.Thread(target=poller)
    poll_thread.start()

    try:
        vault_write(
            vault_root=vault_root,
            vault_path="atomic-during.md",
            frontmatter_fields={"ueid": "task:observe:001:002"},
            body=body,
        )
    finally:
        stop.set()
        poll_thread.join(timeout=2.0)

    # After write completes, file must exist with full content
    assert target_abs.exists()
    final_size = target_abs.stat().st_size

    # Every observation must be 0 (absent) or final_size (complete).
    # Any intermediate size = partial write visible = atomicity violated.
    partial = [o for o in observations if o != 0 and o != final_size]
    assert partial == [], (
        f"observed partial file sizes during write: {partial} "
        f"(final={final_size}, all_obs={observations[:20]}...)"
    )
