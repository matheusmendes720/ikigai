"""M132 tests — vault_log_rotation.py.

Verifies log rotation: count, archive listing, rotate (real + dry-run),
idempotence, parameter validation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.vault import log_rotation as lr  # noqa: E402
from tools.vault.log_rotation import (  # noqa: E402
    DEFAULT_KEEP_LINES,
    DEFAULT_MAX_LINES,
    count_lines,
    list_archives,
    main,
    next_archive_index,
    rotate,
    status,
)


@pytest.fixture
def log_path(tmp_path: Path) -> Path:
    """Create a vault-events log with 100 events."""
    p = tmp_path / ".vault_events.jsonl"
    p.write_text(
        "\n".join(f'{{"event": "vault.toggle_applied", "n": {i}}}' for i in range(100)) + "\n",
        encoding="utf-8",
    )
    return p


# === count_lines ===

def test_count_lines_basic(log_path: Path) -> None:
    """Counts lines in a 100-event log."""
    assert count_lines(log_path) == 100


def test_count_lines_nonexistent(tmp_path: Path) -> None:
    """Returns 0 for missing file."""
    assert count_lines(tmp_path / "missing.jsonl") == 0


def test_count_lines_empty(tmp_path: Path) -> None:
    """Returns 0 for empty file."""
    p = tmp_path / "empty.jsonl"
    p.write_text("", encoding="utf-8")
    assert count_lines(p) == 0


# === list_archives ===

def test_list_archives_empty(tmp_path: Path) -> None:
    """No archives → empty list."""
    p = tmp_path / ".vault_events.jsonl"
    p.write_text("event1\n", encoding="utf-8")
    assert list_archives(p) == []


def test_list_archives_multiple(tmp_path: Path) -> None:
    """Multiple archives → sorted by index."""
    p = tmp_path / ".vault_events.jsonl"
    p.write_text("", encoding="utf-8")
    (tmp_path / ".vault_events.jsonl.1.archived.jsonl").write_text("a\n", encoding="utf-8")
    (tmp_path / ".vault_events.jsonl.3.archived.jsonl").write_text("c\n", encoding="utf-8")
    (tmp_path / ".vault_events.jsonl.2.archived.jsonl").write_text("b\n", encoding="utf-8")
    archives = list_archives(p)
    assert len(archives) == 3
    assert archives[0].name.endswith(".1.archived.jsonl")
    assert archives[1].name.endswith(".2.archived.jsonl")
    assert archives[2].name.endswith(".3.archived.jsonl")


def test_list_archives_ignores_unrelated(tmp_path: Path) -> None:
    """Unrelated files are not archives."""
    p = tmp_path / ".vault_events.jsonl"
    p.write_text("", encoding="utf-8")
    (tmp_path / "other.log.1.archived.jsonl").write_text("a\n", encoding="utf-8")
    (tmp_path / ".vault_events.jsonl.999.bak").write_text("a\n", encoding="utf-8")
    assert list_archives(p) == []


# === next_archive_index ===

def test_next_archive_index_no_existing(log_path: Path) -> None:
    """No archives → next index is 1."""
    assert next_archive_index(log_path) == 1


def test_next_archive_index_increments(log_path: Path) -> None:
    """Existing archives → max+1."""
    log_path.parent.joinpath(".vault_events.jsonl.1.archived.jsonl").write_text("a\n", encoding="utf-8")
    log_path.parent.joinpath(".vault_events.jsonl.3.archived.jsonl").write_text("c\n", encoding="utf-8")
    assert next_archive_index(log_path) == 4


# === rotate ===

def test_rotate_no_op_below_threshold(log_path: Path) -> None:
    """Below max_lines → no rotation."""
    result = rotate(log_path, max_lines=200, keep_lines=100)
    assert result["rotated"] is False
    assert result["lines_before"] == 100
    assert result["lines_after"] == 100
    assert result["archive_path"] is None


def test_rotate_dry_run(log_path: Path) -> None:
    """dry_run=True → reports rotation but doesn't move files."""
    result = rotate(log_path, max_lines=80, keep_lines=50, dry_run=True)
    assert result["rotated"] is True
    assert result["lines_before"] == 100
    assert result["lines_after"] == 50
    assert "would-archive" in result["archive_path"]
    # File unchanged.
    assert count_lines(log_path) == 100


def test_rotate_creates_archive(log_path: Path) -> None:
    """rotate → archive file created with oldest events, live log truncated."""
    result = rotate(log_path, max_lines=80, keep_lines=50)
    assert result["rotated"] is True
    assert result["lines_before"] == 100
    assert result["lines_after"] == 50
    archive_path = Path(result["archive_path"])
    assert archive_path.exists()
    # Archive has 50 events (100 - 50).
    assert count_lines(archive_path) == 50
    # Live log has 50 events.
    assert count_lines(log_path) == 50


def test_rotate_preserves_event_order(log_path: Path) -> None:
    """Archive has oldest events; live log has newest."""
    rotate(log_path, max_lines=80, keep_lines=50)
    # Live log starts with event n=50.
    first_live = log_path.read_text(encoding="utf-8").splitlines()[0]
    assert '"n": 50' in first_live
    # Archive starts with event n=0.
    archives = list_archives(log_path)
    assert len(archives) == 1
    first_archive = archives[0].read_text(encoding="utf-8").splitlines()[0]
    assert '"n": 0' in first_archive


def test_rotate_multiple_iterations(log_path: Path) -> None:
    """Multiple rotations → multiple archive files with incrementing index."""
    rotate(log_path, max_lines=80, keep_lines=50)
    rotate(log_path, max_lines=80, keep_lines=50)
    archives = list_archives(log_path)
    # Each rotation archives 30 lines (80 - 50). After first rotation log has 50
    # lines (under 80), so second rotation does nothing.
    # Need to add more events to force second rotation.
    with log_path.open("a", encoding="utf-8") as f:
        for i in range(50):
            f.write(f'{{"event": "added", "n": {i}}}\n')
    rotate(log_path, max_lines=80, keep_lines=50)
    archives = list_archives(log_path)
    assert len(archives) >= 2


def test_rotate_missing_file(tmp_path: Path) -> None:
    """Missing log file → no rotation, no error."""
    result = rotate(tmp_path / "missing.jsonl", max_lines=10, keep_lines=5)
    assert result["rotated"] is False
    assert result["lines_before"] == 0


def test_rotate_invalid_params(log_path: Path) -> None:
    """keep_lines >= max_lines → ValueError."""
    with pytest.raises(ValueError, match="keep_lines .* must be < max_lines"):
        rotate(log_path, max_lines=10, keep_lines=10)
    with pytest.raises(ValueError, match="keep_lines .* must be < max_lines"):
        rotate(log_path, max_lines=10, keep_lines=20)


# === status ===

def test_status_existing_log(log_path: Path) -> None:
    """Status of existing log reports line count + 0 archives."""
    s = status(log_path)
    assert s["log_exists"] is True
    assert s["line_count"] == 100
    assert s["archive_count"] == 0


def test_status_with_archives(log_path: Path) -> None:
    """Status reports archive count + paths."""
    log_path.parent.joinpath(".vault_events.jsonl.1.archived.jsonl").write_text("a\n", encoding="utf-8")
    s = status(log_path)
    assert s["archive_count"] == 1


def test_status_missing_log(tmp_path: Path) -> None:
    """Missing log → log_exists=False, line_count=0."""
    s = status(tmp_path / "missing.jsonl")
    assert s["log_exists"] is False
    assert s["line_count"] == 0


# === CLI ===

def test_main_status(log_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["status", "--log-path", str(log_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "line_count: 100" in captured.out


def test_main_archives_empty(log_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["archives", "--log-path", str(log_path)])
    assert rc == 0


def test_main_rotate_dry_run(log_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main([
        "rotate", "--log-path", str(log_path),
        "--max-lines", "80", "--keep-lines", "50", "--dry-run",
    ])
    assert rc == 0
    assert count_lines(log_path) == 100  # unchanged


def test_main_rotate_real(log_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main([
        "rotate", "--log-path", str(log_path),
        "--max-lines", "80", "--keep-lines", "50",
    ])
    assert rc == 0
    assert count_lines(log_path) == 50


def test_main_invalid_cmd(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["bogus", "--log-path", str(tmp_path / "x")])


# === Default constants ===

def test_default_constants() -> None:
    """Defaults are sensible: 10k max, 5k keep."""
    assert DEFAULT_MAX_LINES == 10_000
    assert DEFAULT_KEEP_LINES == 5_000
