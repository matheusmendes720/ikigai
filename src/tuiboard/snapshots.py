"""JSON snapshot persistence for tuiboard (at data/tuiboard/snapshots/).

Per spec: idempotent on (name, filters). sha256 of canonical (sorted) task list.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


class SnapshotStore:
    """Persists tuiboard snapshots as JSON files."""

    def __init__(self, snapshots_dir: Path) -> None:
        self._dir = Path(snapshots_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _canonical_hash(self, tasks: list[dict]) -> str:
        canonical = json.dumps(tasks, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def save(
        self, *, name: str, tasks: list[dict],
        filters: dict | None = None, description: str | None = None,
    ) -> dict:
        # Idempotent on name: if a snapshot with this name exists, return its id
        existing = self._find_by_name(name)
        if existing is not None:
            return {
                "snapshot_id": existing["snapshot_id"],
                "name": existing["name"],
                "created_at": existing["created_at"],
                "task_count": existing["task_count"],
                "sha256": existing["sha256"],
            }
        sha = self._canonical_hash(tasks)
        sid = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        payload = {
            "snapshot_id": sid,
            "name": name,
            "created_at": now,
            "task_count": len(tasks),
            "sha256": sha,
            "tasks": tasks,
            "filters": filters or {},
            "description": description,
        }
        path = self._dir / f"{sid}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, path)
        return {
            "snapshot_id": sid, "name": name, "created_at": now,
            "task_count": len(tasks), "sha256": sha,
        }

    def load(self, snapshot_id: str) -> dict:
        path = self._dir / f"{snapshot_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"snapshot not found: {snapshot_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def list_all(self) -> list[dict]:
        results = []
        for path in self._dir.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            results.append({
                "snapshot_id": data["snapshot_id"], "name": data["name"],
                "created_at": data["created_at"], "task_count": data["task_count"],
                "sha256": data["sha256"],
            })
        return results

    def _find_by_name(self, name: str) -> dict | None:
        for path in self._dir.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("name") == name:
                return {
                    "snapshot_id": data["snapshot_id"], "name": data["name"],
                    "created_at": data["created_at"], "task_count": data["task_count"],
                    "sha256": data["sha256"],
                }
        return None
