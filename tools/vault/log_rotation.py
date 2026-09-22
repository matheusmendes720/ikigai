"""M132 — vault_log_rotation.py

Rotation utility for `vault/.vault_events.jsonl`.

Append-only audit logs grow unbounded. This module provides:
  - `count_lines(path)` — fast line count
  - `rotate(path, max_lines)` — if line count > max_lines, archive oldest
                              lines to `<path>.<N>.archived.jsonl`, truncate
                              the live log to keep last `keep_lines` events.

Default: max_lines=10_000, keep_lines=5_000.

Append-only guarantee: we never DELETE events — only MOVE them to archive
files. The chain of archive files preserves the full history.

Commands:
  status   — show current line count + archive count
  rotate   — rotate if needed (idempotent)
  archives — list all .archived.jsonl files
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

VAULT_EVENTS = Path("vault") / ".vault_events.jsonl"
DEFAULT_MAX_LINES = 10_000
DEFAULT_KEEP_LINES = 5_000


def count_lines(path: Path) -> int:
    """Count lines in a text file. Fast for big files."""
    if not path.exists():
        return 0
    n = 0
    with path.open("rb") as f:
        for _ in f:
            n += 1
    return n


def list_archives(path: Path) -> list[Path]:
    """List existing archive files for this log, sorted by index."""
    parent = path.parent
    base = path.name
    archives: list[tuple[int, Path]] = []
    for p in parent.iterdir():
        if not p.name.startswith(f"{base}."):
            continue
        if not p.name.endswith(".archived.jsonl"):
            continue
        # Format: <base>.<N>.archived.jsonl
        try:
            idx_str = p.name[len(base) + 1:].split(".")[0]
            idx = int(idx_str)
        except (ValueError, IndexError):
            continue
        archives.append((idx, p))
    return [p for _, p in sorted(archives)]


def next_archive_index(path: Path) -> int:
    """Get the next archive index (max existing + 1)."""
    archives = list_archives(path)
    if not archives:
        return 1
    try:
        last = archives[-1].name
        idx_str = last[len(path.name) + 1:].split(".")[0]
        return int(idx_str) + 1
    except (ValueError, IndexError):
        return len(archives) + 1


def rotate(
    path: Path = VAULT_EVENTS,
    *,
    max_lines: int = DEFAULT_MAX_LINES,
    keep_lines: int = DEFAULT_KEEP_LINES,
    dry_run: bool = False,
) -> dict[str, object]:
    """Rotate the log if it exceeds max_lines.

    Returns dict with: {rotated, lines_before, lines_after, archive_path, dry_run}.
    Idempotent: returns rotated=False if no rotation needed.
    """
    if keep_lines >= max_lines:
        raise ValueError(f"keep_lines ({keep_lines}) must be < max_lines ({max_lines})")

    info: dict[str, object] = {
        "rotated": False,
        "lines_before": 0,
        "lines_after": 0,
        "archive_path": None,
        "dry_run": dry_run,
    }
    if not path.exists():
        return info
    lines_before = count_lines(path)
    info["lines_before"] = lines_before
    if lines_before <= max_lines:
        info["lines_after"] = lines_before
        return info

    if dry_run:
        info["rotated"] = True
        info["lines_after"] = keep_lines
        info["archive_path"] = f"<would-archive {(lines_before - keep_lines)} lines>"
        return info

    # Read all lines.
    with path.open("r", encoding="utf-8") as f:
        all_lines = f.readlines()

    # Split: archive the head (oldest), keep the tail (newest).
    archive_count = lines_before - keep_lines
    head = all_lines[:archive_count]
    tail = all_lines[archive_count:]

    # Move head to next archive file.
    archive_idx = next_archive_index(path)
    archive_path = path.with_name(f"{path.name}.{archive_idx}.archived.jsonl")
    archive_path.write_text("".join(head), encoding="utf-8")

    # Truncate the live log.
    path.write_text("".join(tail), encoding="utf-8")

    info["rotated"] = True
    info["lines_after"] = keep_lines
    info["archive_path"] = str(archive_path)
    return info


def status(path: Path = VAULT_EVENTS) -> dict[str, object]:
    """Report log + archive status."""
    line_count = count_lines(path)
    archives = list_archives(path)
    return {
        "log_exists": path.exists(),
        "log_path": str(path),
        "line_count": line_count,
        "archive_count": len(archives),
        "archive_paths": [str(p) for p in archives],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Rotate vault audit log")
    sub = p.add_subparsers(dest="cmd", required=True)

    # status + archives: just --log-path.
    for cmd in ("status", "archives"):
        sp = sub.add_parser(cmd)
        sp.add_argument("--log-path", type=Path, default=VAULT_EVENTS)

    # rotate: --log-path + rotation params.
    rot = sub.add_parser("rotate")
    rot.add_argument("--log-path", type=Path, default=VAULT_EVENTS)
    rot.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    rot.add_argument("--keep-lines", type=int, default=DEFAULT_KEEP_LINES)
    rot.add_argument("--dry-run", action="store_true")

    args = p.parse_args(argv)

    if args.cmd == "status":
        s = status(args.log_path)
        for k, v in s.items():
            print(f"{k}: {v}")
        return 0
    if args.cmd == "archives":
        for path in list_archives(args.log_path):
            print(path)
        return 0
    if args.cmd == "rotate":
        result = rotate(
            args.log_path,
            max_lines=args.max_lines,
            keep_lines=args.keep_lines,
            dry_run=args.dry_run,
        )
        for k, v in result.items():
            print(f"{k}: {v}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
