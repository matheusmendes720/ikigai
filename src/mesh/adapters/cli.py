"""Adapter for interfaces/cli tasks.jsonl file."""
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from src.contracts.common import UEID
from src.contracts.task_change import PropagationEvent

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TASKS_JSONL = PROJECT_ROOT / "data" / "tasks.jsonl"

SUPPORTED_FIELDS = {"title", "due", "priority", "ueid", "written_at", "source_fork"}


class CliAdapter:
    """Read/write the interfaces/cli tasks.jsonl slice."""
    name = "cli"

    def read(self, ueid: UEID) -> dict[str, Any] | None:
        if not TASKS_JSONL.exists():
            return None
        for line in TASKS_JSONL.read_text().splitlines():
            if not line.strip():
                continue
            task = json.loads(line)
            if task.get("ueid") == ueid:
                return task
        return None

    def apply_change(self, event: PropagationEvent) -> None:
        if event.action.value != "create":
            return  # v1 only supports create

        TASKS_JSONL.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ueid": event.ueid,
            "title": event.fields.get("title"),
            "due": event.fields.get("due"),
            "priority": event.fields.get("priority", "medium"),
            "written_at": event.approved_at.isoformat(),
            "source_fork": event.source_fork,
        }
        line = json.dumps(record) + "\n"

        # Atomic append via temp + rename (works on Windows + Unix)
        tmp = TASKS_JSONL.with_suffix(".tmp")
        existing = TASKS_JSONL.read_text() if TASKS_JSONL.exists() else ""
        tmp.write_text(existing + line)
        os.replace(tmp, TASKS_JSONL)

    def supports_field(self, field_name: str) -> bool:
        return field_name in SUPPORTED_FIELDS
