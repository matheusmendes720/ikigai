"""M124 — baseline_integrity.py

SHA256 manifest for `reports/baselines/*.json` files. Detects tampering
or accidental corruption.

Commands:
  snapshot  — recompute SHA256 of every baseline file, write reports/baselines/SHA256SUMS
  verify    — recompute SHA256, compare against stored SHA256SUMS, exit non-zero on mismatch
  show      — print current SHA256 of every baseline file (no manifest update)

Output:
  - reports/baselines/SHA256SUMS — manifest file, format `<hex>  <rel_path>`
    (standard sha256sum format — can be verified with `sha256sum -c`)

Honest scope:
  - No signature (just checksum). A determined attacker can rewrite both
    file AND manifest. For trusted environments, that's enough. For stronger
    guarantees, sign the manifest with GPG (out of scope for M124).
  - The manifest itself lives in `reports/baselines/` — committing it to
    git makes tampering detectable across distributed clones.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_BASELINES_DIR = REPO_ROOT / "reports" / "baselines"
MANIFEST_NAME = "SHA256SUMS"


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _iter_baselines(bdir: Path) -> list[Path]:
    """Sorted list of baseline JSONs (excludes manifest itself)."""
    return sorted(p for p in bdir.glob("*.json"))


def snapshot(bdir: Path = DEFAULT_BASELINES_DIR) -> Path:
    """Recompute SHA256 of every baseline, write the manifest. Returns manifest path."""
    bdir.mkdir(parents=True, exist_ok=True)
    manifest = bdir / MANIFEST_NAME
    lines = []
    for p in _iter_baselines(bdir):
        h = _hash_file(p)
        # Manifest format: <hex><two spaces><rel-path-to-bdir>
        rel = p.relative_to(bdir).as_posix()
        lines.append(f"{h}  {rel}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def verify(bdir: Path = DEFAULT_BASELINES_DIR) -> tuple[bool, list[str]]:
    """Verify SHA256 of every baseline against the manifest.

    Returns (ok, [messages]). ok=True means all files match.
    """
    manifest = bdir / MANIFEST_NAME
    if not manifest.exists():
        return False, [f"manifest not found: {manifest}"]
    expected: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        # Format: "<hex>  <path>" or "<hex> *<path>" (binary mode marker)
        parts = line.split("  ", 1) if "  " in line else line.split(" *", 1)
        if len(parts) != 2:
            continue
        expected[parts[1].lstrip("*")] = parts[0]

    messages: list[str] = []
    ok = True
    seen: set[str] = set()
    for p in _iter_baselines(bdir):
        rel = p.relative_to(bdir).as_posix()
        seen.add(rel)
        h = _hash_file(p)
        exp = expected.get(rel)
        if exp is None:
            messages.append(f"NEW: {rel} (not in manifest)")
            ok = False
        elif exp != h:
            messages.append(f"MISMATCH: {rel} (expected {exp[:8]}, got {h[:8]})")
            ok = False

    # Detect files in manifest that no longer exist
    for rel in expected:
        if rel not in seen:
            messages.append(f"MISSING: {rel} (in manifest but file deleted)")
            ok = False

    return ok, messages


def show(bdir: Path = DEFAULT_BASELINES_DIR) -> int:
    """Print SHA256 of every baseline file."""
    for p in _iter_baselines(bdir):
        h = _hash_file(p)
        rel = p.relative_to(bdir).as_posix()
        print(f"{h}  {rel}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Baseline integrity (SHA256)")
    sub = p.add_subparsers(dest="cmd", required=True)

    for cmd in ("snapshot", "verify", "show"):
        sp = sub.add_parser(cmd, help=f"{cmd} baseline files")
        sp.add_argument("--baselines-dir", type=Path, default=DEFAULT_BASELINES_DIR)

    args = p.parse_args(argv)

    if args.cmd == "snapshot":
        m = snapshot(args.baselines_dir)
        print(f"# Wrote {m}")
        return 0
    if args.cmd == "verify":
        ok, msgs = verify(args.baselines_dir)
        for m in msgs:
            print(f"# {m}")
        if ok:
            print("# All baseline files match manifest.")
            return 0
        print("# INTEGRITY CHECK FAILED")
        return 1
    if args.cmd == "show":
        return show(args.baselines_dir)
    return 1


if __name__ == "__main__":
    sys.exit(main())
