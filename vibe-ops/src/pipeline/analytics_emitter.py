import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class EventType(str, Enum):  # noqa: UP042 - keep (str, Enum) member repr for DB payloads
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    MODE_CHANGED = "mode_changed"
    IKIGAI_DRIFT = "ikigai_drift"


class AnalyticsEmitter:
    """
    Multi-sink JSONL emitter para telemetria da mesh.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def emit(self, event_type: EventType, payload: dict[str, Any]):
        log_file = self.data_dir / f"{event_type.value}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event": event_type.value,
                "payload": payload,
            }
            f.write(json.dumps(entry) + "\n")

    def task_created(self, task_id: str, title: str):
        self.emit(EventType.TASK_CREATED, {"id": task_id, "title": title})
