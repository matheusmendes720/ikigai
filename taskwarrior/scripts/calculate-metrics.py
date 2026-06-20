#!/usr/bin/env python3
"""Calculate basic metrics from Taskwarrior export JSON."""

import json
import sys
from datetime import datetime, timedelta


def parse_date(dstr: str | None):
    if not dstr:
        return None
    try:
        return datetime.fromisoformat(dstr.replace("Z", "+00:00"))
    except Exception:
        return None


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: calculate-metrics.py <export.json> [--days N]")
        return 1

    path = sys.argv[1]
    days = None
    if len(sys.argv) >= 4 and sys.argv[2] == "--days":
        try:
            days = int(sys.argv[3])
        except Exception:
            print("--days requires integer")
            return 1

    with open(path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    if days:
        cutoff = datetime.now(tz=datetime.now().astimezone().tzinfo) - timedelta(days=days)
        tasks = [t for t in tasks if parse_date(t.get("entry")) and parse_date(t.get("entry")) >= cutoff]

    total = len(tasks)
    completed = [t for t in tasks if t.get("status") == "completed"]
    pending = [t for t in tasks if t.get("status") == "pending"]
    waiting = [t for t in tasks if t.get("status") == "waiting"]

    rate = (len(completed) / total * 100) if total else 0
    print(f"Tasks: total={total} completed={len(completed)} pending={len(pending)} waiting={len(waiting)}")
    print(f"Taxa de Conclusao: {rate:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
