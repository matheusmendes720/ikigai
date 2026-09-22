"""M124 tests — baseline_integrity.py.

Verifies SHA256 manifest creation, verification, and tamper detection.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest import baseline_integrity as bi  # noqa: E402
from tools.backtest.baseline_integrity import (  # noqa: E402
    _hash_file,
    _iter_baselines,
    main,
    show,
    snapshot,
    verify,
)


@pytest.fixture
def bdir(tmp_path: Path) -> Path:
    b = tmp_path / "baselines"
    b.mkdir()
    (b / "2026-09-22.json").write_text(json.dumps({"scores": {"total_score": 90.0}}), encoding="utf-8")
    (b / "2026-09-22.llm.json").write_text(json.dumps({"aggregate": {"overall": 0.7}}), encoding="utf-8")
    return b


# === _hash_file ===

def test_hash_file_deterministic(bdir: Path) -> None:
    h1 = _hash_file(bdir / "2026-09-22.json")
    h2 = _hash_file(bdir / "2026-09-22.json")
    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex


def test_hash_file_changes_on_modification(bdir: Path) -> None:
    h1 = _hash_file(bdir / "2026-09-22.json")
    (bdir / "2026-09-22.json").write_text('{"tampered": true}', encoding="utf-8")
    h2 = _hash_file(bdir / "2026-09-22.json")
    assert h1 != h2


# === _iter_baselines ===

def test_iter_baselines_includes_llm(bdir: Path) -> None:
    paths = _iter_baselines(bdir)
    names = [p.name for p in paths]
    assert "2026-09-22.json" in names
    assert "2026-09-22.llm.json" in names


def test_iter_baselines_excludes_manifest(bdir: Path) -> None:
    snapshot(bdir)  # creates SHA256SUMS
    paths = _iter_baselines(bdir)
    names = [p.name for p in paths]
    assert "SHA256SUMS" not in names


def test_iter_baselines_missing_dir(tmp_path: Path) -> None:
    assert _iter_baselines(tmp_path / "missing") == []


# === snapshot ===

def test_snapshot_creates_manifest(bdir: Path) -> None:
    m = snapshot(bdir)
    assert m.exists()
    content = m.read_text(encoding="utf-8")
    assert "2026-09-22.json" in content
    assert "2026-09-22.llm.json" in content


def test_snapshot_format_compatible_with_sha256sum(bdir: Path) -> None:
    """Format is `<hex>  <path>` — compatible with sha256sum -c verification."""
    m = snapshot(bdir)
    content = m.read_text(encoding="utf-8")
    for line in content.splitlines():
        assert "  " in line, f"missing two spaces: {line!r}"
        hex_part, _, path_part = line.partition("  ")
        assert len(hex_part) == 64
        assert "/" not in hex_part  # only the path has slashes


def test_snapshot_creates_dir_if_missing(tmp_path: Path) -> None:
    bdir = tmp_path / "new" / "baselines"
    snapshot(bdir)
    assert (bdir / "SHA256SUMS").exists()


# === verify ===

def test_verify_ok_when_clean(bdir: Path) -> None:
    snapshot(bdir)
    ok, msgs = verify(bdir)
    assert ok is True
    assert msgs == []


def test_verify_detects_tampering(bdir: Path) -> None:
    snapshot(bdir)
    # Tamper with one file
    (bdir / "2026-09-22.json").write_text('{"tampered": true}', encoding="utf-8")
    ok, msgs = verify(bdir)
    assert ok is False
    assert any("MISMATCH" in m for m in msgs)


def test_verify_detects_new_file(bdir: Path) -> None:
    snapshot(bdir)
    # Add a new file (not in manifest)
    (bdir / "2026-09-23.json").write_text('{"new": true}', encoding="utf-8")
    ok, msgs = verify(bdir)
    assert ok is False
    assert any("NEW" in m for m in msgs)


def test_verify_detects_missing_file(bdir: Path) -> None:
    snapshot(bdir)
    (bdir / "2026-09-22.json").unlink()
    ok, msgs = verify(bdir)
    assert ok is False
    assert any("MISSING" in m for m in msgs)


def test_verify_missing_manifest(tmp_path: Path) -> None:
    bdir = tmp_path / "no_manifest"
    bdir.mkdir()
    ok, msgs = verify(bdir)
    assert ok is False
    assert any("manifest not found" in m for m in msgs)


# === show ===

def test_show_prints_all(bdir: Path, capsys) -> None:
    rc = show(bdir)
    assert rc == 0
    out = capsys.readouterr().out
    assert "2026-09-22.json" in out
    assert "2026-09-22.llm.json" in out


# === CLI ===

def test_main_snapshot(bdir: Path, capsys) -> None:
    rc = main(["snapshot", "--baselines-dir", str(bdir)])
    assert rc == 0
    assert (bdir / "SHA256SUMS").exists()


def test_main_verify_ok(bdir: Path, capsys) -> None:
    snapshot(bdir)
    rc = main(["verify", "--baselines-dir", str(bdir)])
    assert rc == 0


def test_main_verify_fails_on_tamper(bdir: Path, capsys) -> None:
    snapshot(bdir)
    (bdir / "2026-09-22.json").write_text('{}', encoding="utf-8")
    rc = main(["verify", "--baselines-dir", str(bdir)])
    assert rc == 1


def test_main_show(bdir: Path, capsys) -> None:
    rc = main(["show", "--baselines-dir", str(bdir)])
    assert rc == 0


def test_main_invalid_cmd(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["bogus", "--baselines-dir", str(tmp_path)])
