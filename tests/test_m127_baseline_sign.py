"""M127 tests — baseline_sign.py.

Verifies symmetric-gpg sign/verify cycle on the SHA256SUMS manifest.
Uses a per-test passphrase via env var (LIFE_BASELINE_PASSPHRASE) so
the real `reports/baselines/.passphrase` is never touched in tests.
"""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.backtest import baseline_sign as bs  # noqa: E402
from tools.backtest.baseline_sign import (  # noqa: E402
    ENCRYPTED_NAME,
    MANIFEST_NAME,
    PASSPHRASE_ENV_VAR,
    _gpg_available,
    get_passphrase,
    main,
    rotate_passphrase,
    sign_manifest,
    status,
    verify_signature,
)


@pytest.fixture
def baselines_dir(tmp_path: Path) -> Path:
    """Baselines dir with a SHA256SUMS file."""
    bdir = tmp_path / "baselines"
    bdir.mkdir()
    (bdir / MANIFEST_NAME).write_text(
        "abc123def456  2026-09-22.json\n"
        "789xyz012345  2026-09-22.llm.json\n",
        encoding="utf-8",
    )
    return bdir


@pytest.fixture
def test_passphrase(monkeypatch: pytest.MonkeyPatch) -> str:
    """Inject a unique random passphrase via env var."""
    pp = secrets.token_urlsafe(32)
    monkeypatch.setenv(PASSPHRASE_ENV_VAR, pp)
    return pp


@pytest.fixture
def skip_if_no_gpg() -> None:
    if not _gpg_available():
        pytest.skip("gpg not available on this system")


# === _gpg_available ===

def test_gpg_available_returns_bool() -> None:
    assert isinstance(_gpg_available(), bool)


# === get_passphrase ===

def test_get_passphrase_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Env var takes precedence over file."""
    pp = "test-from-env-" + secrets.token_urlsafe(16)
    monkeypatch.setenv(PASSPHRASE_ENV_VAR, pp)
    assert get_passphrase(tmp_path) == pp


def test_get_passphrase_auto_generates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No env, no file → auto-generates + persists to file."""
    monkeypatch.delenv(PASSPHRASE_ENV_VAR, raising=False)
    pp = get_passphrase(tmp_path)
    assert len(pp) > 20
    assert (tmp_path / ".passphrase").exists()


# === sign_manifest ===

def test_sign_creates_signature_file(baselines_dir: Path, test_passphrase: str, skip_if_no_gpg: None) -> None:
    enc = sign_manifest(baselines_dir)
    assert enc is not None
    assert enc.exists()
    assert enc == baselines_dir / ENCRYPTED_NAME
    assert enc.stat().st_size > 0  # encrypted output is non-empty


def test_sign_raises_on_missing_manifest(tmp_path: Path, test_passphrase: str, skip_if_no_gpg: None) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match="manifest not found"):
        sign_manifest(empty)


# === verify_signature ===

def test_verify_valid_signature(baselines_dir: Path, test_passphrase: str, skip_if_no_gpg: None) -> None:
    sign_manifest(baselines_dir)
    ok, msg = verify_signature(baselines_dir)
    assert ok is True
    assert msg == "valid"


def test_verify_detects_manifest_tampering(
    baselines_dir: Path, test_passphrase: str, skip_if_no_gpg: None
) -> None:
    sign_manifest(baselines_dir)
    # Tamper with the manifest — the signature was made on the original.
    (baselines_dir / MANIFEST_NAME).write_text(
        "tampered_content  2026-09-22.json\n",
        encoding="utf-8",
    )
    ok, msg = verify_signature(baselines_dir)
    assert ok is False
    assert "does not match" in msg


def test_verify_missing_signature(baselines_dir: Path, test_passphrase: str) -> None:
    ok, msg = verify_signature(baselines_dir)
    assert ok is False
    assert "signature missing" in msg


def test_verify_missing_manifest(tmp_path: Path, test_passphrase: str) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    ok, msg = verify_signature(empty)
    assert ok is False
    assert "manifest missing" in msg


def test_verify_wrong_passphrase(baselines_dir: Path, skip_if_no_gpg: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sign with one passphrase, verify with another → fails."""
    monkeypatch.setenv(PASSPHRASE_ENV_VAR, "pass-a-" + secrets.token_urlsafe(16))
    sign_manifest(baselines_dir)
    monkeypatch.setenv(PASSPHRASE_ENV_VAR, "pass-b-" + secrets.token_urlsafe(16))
    ok, msg = verify_signature(baselines_dir)
    assert ok is False


# === status ===

def test_status_returns_expected_fields(baselines_dir: Path, test_passphrase: str, skip_if_no_gpg: None) -> None:
    sign_manifest(baselines_dir)
    s = status(baselines_dir)
    assert s["manifest_exists"] == "yes"
    assert s["signature_exists"] == "yes"
    assert s["gpg_available"] == "yes"
    assert s["passphrase_source"] == "env"
    assert s["signature_valid"] == "yes"


def test_status_shows_unsigned_when_no_sig(baselines_dir: Path, test_passphrase: str, skip_if_no_gpg: None) -> None:
    s = status(baselines_dir)
    assert s["signature_exists"] == "no"
    assert s["signature_valid"] == "no"


def test_status_records_signature_size(baselines_dir: Path, test_passphrase: str, skip_if_no_gpg: None) -> None:
    sign_manifest(baselines_dir)
    s = status(baselines_dir)
    assert "signature_size_bytes" in s
    assert int(s["signature_size_bytes"]) > 0


# === rotate_passphrase ===

def test_rotate_changes_passphrase_and_resigns(
    baselines_dir: Path, test_passphrase: str, skip_if_no_gpg: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sign_manifest(baselines_dir)
    # Rotate (drops env var so it auto-generates).
    monkeypatch.delenv(PASSPHRASE_ENV_VAR, raising=False)
    new_pp = rotate_passphrase(baselines_dir)
    assert len(new_pp) > 20
    # Old env-var passphrase should no longer verify.
    monkeypatch.setenv(PASSPHRASE_ENV_VAR, test_passphrase)
    ok, _ = verify_signature(baselines_dir)
    assert ok is False
    # New passphrase does verify.
    monkeypatch.setenv(PASSPHRASE_ENV_VAR, new_pp)
    ok, _ = verify_signature(baselines_dir)
    assert ok is True


# === CLI ===

def test_main_sign(baselines_dir: Path, test_passphrase: str, capsys, skip_if_no_gpg: None) -> None:
    rc = main(["sign", "--baselines-dir", str(baselines_dir)])
    assert rc == 0
    assert (baselines_dir / ENCRYPTED_NAME).exists()


def test_main_verify_ok(baselines_dir: Path, test_passphrase: str, skip_if_no_gpg: None) -> None:
    sign_manifest(baselines_dir)
    rc = main(["verify", "--baselines-dir", str(baselines_dir)])
    assert rc == 0


def test_main_verify_fails_on_tamper(baselines_dir: Path, test_passphrase: str, skip_if_no_gpg: None) -> None:
    sign_manifest(baselines_dir)
    (baselines_dir / MANIFEST_NAME).write_text("tampered", encoding="utf-8")
    rc = main(["verify", "--baselines-dir", str(baselines_dir)])
    assert rc == 1


def test_main_status(baselines_dir: Path, test_passphrase: str, capsys, skip_if_no_gpg: None) -> None:
    sign_manifest(baselines_dir)
    rc = main(["status", "--baselines-dir", str(baselines_dir)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "signature_valid: yes" in captured.out


def test_main_rotate(baselines_dir: Path, test_passphrase: str, capsys, skip_if_no_gpg: None, monkeypatch: pytest.MonkeyPatch) -> None:
    sign_manifest(baselines_dir)
    monkeypatch.delenv(PASSPHRASE_ENV_VAR, raising=False)
    rc = main(["rotate", "--baselines-dir", str(baselines_dir)])
    assert rc == 0


def test_main_invalid_cmd(baselines_dir: Path) -> None:
    with pytest.raises(SystemExit):
        main(["bogus", "--baselines-dir", str(baselines_dir)])


# === Pipeline integration ===

def test_full_sign_verify_roundtrip(
    tmp_path: Path, test_passphrase: str, skip_if_no_gpg: None
) -> None:
    """Full cycle: write manifest → sign → tamper → restore → re-sign → verify OK."""
    bdir = tmp_path / "baselines"
    bdir.mkdir()
    manifest = bdir / MANIFEST_NAME
    manifest.write_text("hash1  file1.json\nhash2  file2.json\n", encoding="utf-8")

    # Sign
    sign_manifest(bdir)
    assert (bdir / ENCRYPTED_NAME).exists()

    # Verify (clean)
    ok, _ = verify_signature(bdir)
    assert ok

    # Tamper with manifest
    manifest.write_text("tampered  file1.json\n", encoding="utf-8")
    ok, msg = verify_signature(bdir)
    assert ok is False
    assert "does not match" in msg

    # Restore manifest
    manifest.write_text("hash1  file1.json\nhash2  file2.json\n", encoding="utf-8")
    # Verify (no re-sign needed — original sig still valid)
    ok, _ = verify_signature(bdir)
    assert ok
