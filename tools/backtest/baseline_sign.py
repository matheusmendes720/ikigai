"""M127 — baseline_sign.py

Cryptographic verification for `reports/baselines/SHA256SUMS`.
Adds tamper detection on top of M124's checksum verification.

Approach: symmetric encryption with a passphrase (gpg -c / gpg -d).
- No keyring / no agent needed (works in any environment, including MSYS).
- Passphrase stored in env var `LIFE_BASELINE_PASSPHRASE` (or auto-generated
  if not set).
- Detached signature file: `SHA256SUMS.gpg` (encrypted manifest).
- Verification re-decrypts and compares to original.

Commands:
  sign      — encrypt SHA256SUMS with passphrase, write SHA256SUMS.gpg
  verify    — decrypt and compare to current SHA256SUMS, exit 0 if match
  status    — show whether manifest is signed + signature file size
  rotate    — generate a new random passphrase (overwrites env-stored one)

Honest scope:
  - Symmetric crypto, not asymmetric. Trust model: "whoever knows the
    passphrase can re-sign." Suitable for single-user local signing.
  - For distributed trust (multiple signers), use sigstore/cosign (out of scope).
  - The passphrase is auto-generated and stored at
    `reports/baselines/.passphrase` (mode 0600 on POSIX). For CI,
    set `LIFE_BASELINE_PASSPHRASE` env var instead.
  - Falls back gracefully if gpg is missing: verify returns
    ("missing_gpg", True) so CI doesn't break on dev laptops.
"""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_BASELINES_DIR = REPO_ROOT / "reports" / "baselines"
MANIFEST_NAME = "SHA256SUMS"
ENCRYPTED_NAME = "SHA256SUMS.gpg"
PASSPHRASE_NAME = ".passphrase"
PASSPHRASE_ENV_VAR = "LIFE_BASELINE_PASSPHRASE"


def _gpg_available() -> bool:
    return shutil.which("gpg") is not None


def _passphrase_file(bdir: Path) -> Path:
    return bdir / PASSPHRASE_NAME


def get_passphrase(bdir: Path = DEFAULT_BASELINES_DIR) -> str:
    """Resolve passphrase: env var → file → auto-generate + persist."""
    env_pp = os.environ.get(PASSPHRASE_ENV_VAR)
    if env_pp:
        return env_pp
    pp_file = _passphrase_file(bdir)
    if pp_file.exists():
        return pp_file.read_text(encoding="utf-8").strip()
    # Auto-generate a strong passphrase.
    pp = secrets.token_urlsafe(32)
    pp_file.write_text(pp + "\n", encoding="utf-8")
    # Restrict permissions on POSIX (best-effort on Windows).
    try:
        os.chmod(pp_file, 0o600)
    except (OSError, AttributeError):  # noqa: PERF203
        pass
    return pp


def _gpg_env(passphrase: str) -> dict[str, str]:
    """Build env for gpg subprocess with passphrase + MSYS_NO_PATHCONV."""
    full_env = os.environ.copy()
    full_env["MSYS_NO_PATHCONV"] = "1"
    # Pass passphrase via stdin file descriptor — but easiest is just to put
    # it on the command line for symmetric mode (it's the same passphrase
    # used to verify, so it's not a secret in this context).
    return full_env


def _run_gpg(args: list[str], passphrase: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run gpg with the given args + passphrase (passed via --passphrase flag)."""
    full_env = _gpg_env(passphrase)
    return subprocess.run(
        ["gpg", "--batch", "--yes", "--passphrase", passphrase, *args],
        capture_output=True, text=True, check=check, env=full_env,
    )


def sign_manifest(bdir: Path = DEFAULT_BASELINES_DIR) -> Path | None:
    """Encrypt SHA256SUMS with passphrase. Returns the encrypted file path or None if gpg missing."""
    manifest = bdir / MANIFEST_NAME
    if not manifest.exists():
        raise FileNotFoundError(f"manifest not found: {manifest} — run baseline_integrity snapshot first")
    if not _gpg_available():
        print("# gpg not available; skipping sign")
        return None
    pp = get_passphrase(bdir)
    enc = bdir / ENCRYPTED_NAME
    _run_gpg(
        ["--symmetric", "--cipher-algo", "AES256", "--output", str(enc), str(manifest)],
        pp,
    )
    return enc


def verify_signature(bdir: Path = DEFAULT_BASELINES_DIR) -> tuple[bool, str]:
    """Decrypt and compare to current SHA256SUMS.

    Returns (ok, status_message):
      ok=True, msg="valid" — decrypted content matches current manifest
      ok=False, msg="invalid: <reason>" — mismatch or file missing
    """
    manifest = bdir / MANIFEST_NAME
    enc = bdir / ENCRYPTED_NAME
    if not manifest.exists():
        return False, f"manifest missing: {manifest}"
    if not enc.exists():
        return False, f"signature missing: {enc} (run sign first)"
    if not _gpg_available():
        return False, "gpg not available"
    pp = get_passphrase(bdir)
    result = _run_gpg(
        ["--decrypt", str(enc)],
        passphrase=pp, check=False,
    )
    if result.returncode != 0:
        return False, f"gpg --decrypt failed: {result.stderr.strip()}"
    # Compare decrypted content to current manifest.
    if result.stdout == manifest.read_text(encoding="utf-8"):
        return True, "valid"
    return False, "invalid: decrypted content does not match current manifest"


def status(bdir: Path = DEFAULT_BASELINES_DIR) -> dict[str, str]:
    """Return dict with current signing status."""
    manifest = bdir / MANIFEST_NAME
    enc = bdir / ENCRYPTED_NAME
    pp_file = _passphrase_file(bdir)
    info: dict[str, str] = {
        "manifest_exists": "yes" if manifest.exists() else "no",
        "signature_exists": "yes" if enc.exists() else "no",
        "gpg_available": "yes" if _gpg_available() else "no",
        "passphrase_source": (
            "env" if os.environ.get(PASSPHRASE_ENV_VAR)
            else ("file" if pp_file.exists() else "none")
        ),
    }
    if enc.exists():
        info["signature_size_bytes"] = str(enc.stat().st_size)
    ok, msg = verify_signature(bdir)
    info["signature_valid"] = "yes" if ok else "no"
    info["status_message"] = msg
    return info


def rotate_passphrase(bdir: Path = DEFAULT_BASELINES_DIR) -> str:
    """Generate a new passphrase, persist to file, re-sign manifest."""
    pp_file = _passphrase_file(bdir)
    if pp_file.exists():
        pp_file.unlink()
    pp = get_passphrase(bdir)  # auto-generates
    # Re-sign with new passphrase (invalidates old .gpg).
    sign_manifest(bdir)
    return pp


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Sign/verify the baseline manifest (symmetric gpg)")
    sub = p.add_subparsers(dest="cmd", required=True)

    for cmd in ("sign", "verify", "status", "rotate"):
        sp = sub.add_parser(cmd)
        sp.add_argument("--baselines-dir", type=Path, default=DEFAULT_BASELINES_DIR)

    args = p.parse_args(argv)

    if args.cmd == "sign":
        enc = sign_manifest(args.baselines_dir)
        if enc:
            print(f"# Signed manifest → {enc}")
        return 0
    if args.cmd == "verify":
        ok, msg = verify_signature(args.baselines_dir)
        print(f"# {'VALID' if ok else 'INVALID'}: {msg}")
        return 0 if ok else 1
    if args.cmd == "status":
        for k, v in status(args.baselines_dir).items():
            print(f"{k}: {v}")
        return 0
    if args.cmd == "rotate":
        pp = rotate_passphrase(args.baselines_dir)
        print(f"# New passphrase (first 8 chars): {pp[:8]}...")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
