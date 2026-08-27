"""Bridge between operational CLI and vibe-ops vault_sync.

operational stays standalone — does NOT import vibe-ops directly.
This module runs as ``python -m scripts.vault_sync`` and emits JSON
on stdout for ``pav sync`` to consume.

Usage:
    python -m scripts.vault_sync vault --vault <path> [--db <path>] [--json]
    python -m scripts.vault_sync code --vault <path> [--db <path>] [--json]
    python -m scripts.vault_sync all --vault <path> [--db <path>] [--json]
    python -m scripts.vault_sync status [--db <path>] [--vault <path>] [--json]
    python -m scripts.vault_sync conflicts [--vault <path>] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat()


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)


def _emit(data: Dict[str, Any], json_out: bool) -> int:
    if json_out:
        sys.stdout.write(json.dumps(data, default=_json_default, indent=2))
        sys.stdout.write("\n")
    else:
        for k, v in data.items():
            sys.stdout.write(f"{k}: {v}\n")
    return 0


def cmd_vault(args: argparse.Namespace) -> int:
    from middleware.bidirectional_sync import BidirectionalSync
    vault = Path(args.vault)
    db = Path(args.db)
    if not vault.exists():
        return _emit({"ok": False, "error": f"vault not found: {vault}"}, args.json)
    if not db.exists():
        return _emit({"ok": False, "error": f"db not found: {db}"}, args.json)
    sync = BidirectionalSync(vault, db)
    stats = sync.sync_vault_to_code()
    return _emit(
        {"ok": True, "command": "vault", "stats": stats, "ts": _utcnow_iso()},
        args.json,
    )


def cmd_code(args: argparse.Namespace) -> int:
    from middleware.bidirectional_sync import BidirectionalSync
    from pipeline.hypothesis_evaluator import HypothesisEvaluator
    vault = Path(args.vault)
    db = Path(args.db)
    if not vault.exists():
        return _emit({"ok": False, "error": f"vault not found: {vault}"}, args.json)
    if not db.exists():
        return _emit({"ok": False, "error": f"db not found: {db}"}, args.json)
    sync = BidirectionalSync(vault, db)
    sync_stats = sync.sync_code_to_vault()

    import sqlite3
    conn = sqlite3.connect(str(db))
    try:
        evaluator = HypothesisEvaluator(conn, vault_path=vault)
        evals = evaluator.evaluate_all()
        evaluation_summary = [
            {
                "hypothesis_id": e.hypothesis_id,
                "verdict": e.verdict,
                "score": e.score,
            }
            for e in evals
        ]
    finally:
        conn.close()

    return _emit(
        {
            "ok": True,
            "command": "code",
            "sync_stats": sync_stats,
            "evaluations": evaluation_summary,
            "ts": _utcnow_iso(),
        },
        args.json,
    )


def cmd_all(args: argparse.Namespace) -> int:
    v_stats = cmd_vault(args)
    c_stats = cmd_code(args)
    return 0 if v_stats == 0 and c_stats == 0 else 1


def cmd_status(args: argparse.Namespace) -> int:
    from middleware.bidirectional_sync import BidirectionalSync
    vault = Path(args.vault) if args.vault else None
    db = Path(args.db)
    if not db.exists():
        return _emit({"ok": False, "error": f"db not found: {db}"}, args.json)
    sync = BidirectionalSync(vault, db) if vault else None
    out: Dict[str, Any] = {"ok": True, "command": "status"}
    if sync is not None:
        out.update(sync.status())
    else:
        # Without a vault, just count from DB.
        import sqlite3
        conn = sqlite3.connect(str(db))
        try:
            total = conn.execute(
                "SELECT COUNT(*) FROM planning_entities"
            ).fetchone()[0]
            out["total_entities"] = total
            rows = conn.execute(
                "SELECT entity_type, COUNT(*) FROM planning_entities "
                "GROUP BY entity_type"
            ).fetchall()
            out["by_type"] = {r[0]: r[1] for r in rows}
        finally:
            conn.close()
    out["ts"] = _utcnow_iso()
    return _emit(out, args.json)


def cmd_conflicts(args: argparse.Namespace) -> int:
    vault = Path(args.vault)
    conflicts_file = vault / ".sync-conflicts.md"
    if not conflicts_file.exists():
        return _emit(
            {"ok": True, "command": "conflicts", "found": False,
             "message": "No .sync-conflicts.md exists yet — no recorded conflicts."},
            args.json,
        )
    content = conflicts_file.read_text(encoding="utf-8")
    if args.json:
        return _emit(
            {
                "ok": True,
                "command": "conflicts",
                "found": True,
                "path": str(conflicts_file),
                "content": content,
                "ts": _utcnow_iso(),
            },
            args.json,
        )
    sys.stdout.write(content)
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vault_sync",
        description="Bidirectional sync bridge between Obsidian vault and vibe-ops engine.",
    )
    parser.add_argument("--vault", default="./vault", help="Path to Obsidian vault")
    parser.add_argument("--db", default="./vibe_ops.db", help="Path to vibe-ops SQLite DB")
    parser.add_argument("--json", action="store_true", help="Emit JSON on stdout")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("vault", help="Sync vault -> SQLite")
    sub.add_parser("code", help="Sync SQLite -> vault + evaluate hypotheses")
    sub.add_parser("all", help="Run both vault and code syncs")
    sub.add_parser("status", help="Show entity counts and last sync timestamps")
    sub.add_parser("conflicts", help="Print .sync-conflicts.md content")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    if args.command == "vault":
        return cmd_vault(args)
    if args.command == "code":
        return cmd_code(args)
    if args.command == "all":
        return cmd_all(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "conflicts":
        return cmd_conflicts(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())