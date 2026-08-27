"""File-backed shared message bus for inter-agent communication.

Pub/sub via JSON log files — matches LangGraph's shared state concept.
Every agent reads/writes structured JSON messages to a bus file.

Bus file format (one JSON object per line — JSONL):
    {"ts": "...", "from": "node_id", "to": "node_id|*", "type": "msg|event|result|error", "payload": {...}}

Usage:
    bus = SharedMessageBus(workflow_id="qa_swarm")
    bus.publish("ux_io_analyst", "tdd_agent", "result", {"qhe_range": [0.079, 1.0]})
    for msg in bus.consume("tdd_agent", since_offset=0):
        print(msg)
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Iterator

# ── Path helpers ──────────────────────────────────────────────────────────────

def _bus_path(workflow_id: str) -> Path:
    base = Path.home() / ".time-tasker" / "agent_harness"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{workflow_id}_bus.jsonl"


def _offset_path(workflow_id: str, agent_id: str) -> Path:
    base = Path.home() / ".time-tasker" / "agent_harness"
    return base / f"{workflow_id}_{agent_id}_offset.txt"


# ── Message types ─────────────────────────────────────────────────────────────

class MessageType:
    RESULT = "result"      # Agent computed output
    ERROR = "error"        # Agent failed
    EVENT = "event"        # Lifecycle event (started, waiting, etc.)
    SIGNAL = "signal"      # Control signal (stop, pause, resume)
    CHECKPOINT = "checkpoint"  # State snapshot


# ── SharedMessageBus ──────────────────────────────────────────────────────────

class SharedMessageBus:
    """Thread-safe file-backed pub/sub bus.

    Agents publish messages to a JSONL file.
    Each agent maintains its own read-offset so it only sees new messages.
    """

    def __init__(self, workflow_id: str, ttl_s: int = 86400):
        self.workflow_id = workflow_id
        self.bus_path = _bus_path(workflow_id)
        self.ttl_s = ttl_s
        self._lock = threading.RLock()

    # ── Publish ────────────────────────────────────────────────────────────

    def publish(
        self,
        from_node: str,
        to_node: str,        # "*" for broadcast
        msg_type: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        entry = {
            "id": f"{from_node}_{int(time.time() * 1000)}",
            "ts": datetime.now(UTC).isoformat(),
            "from": from_node,
            "to": to_node,
            "type": msg_type,
            "payload": payload,
            "correlation_id": correlation_id,
        }
        with self._lock:
            with open(self.bus_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def broadcast(self, from_node: str, msg_type: str, payload: dict[str, Any]) -> None:
        self.publish(from_node, "*", msg_type, payload)

    # ── Consume ────────────────────────────────────────────────────────────

    def consume(
        self,
        agent_id: str,
        since_offset: int = 0,
        msg_type: str | None = None,
        timeout_s: float = 0,
    ) -> Iterator[dict[str, Any]]:
        """Yield messages for `agent_id` (or broadcast "*") since line `since_offset`."""
        offset_file = _offset_path(self.workflow_id, agent_id)
        if offset_file.exists():
            current_offset = int(offset_file.read_text(encoding="utf-8").strip() or "0")
        else:
            current_offset = since_offset

        deadline = time.time() + timeout_s if timeout_s > 0 else None
        while True:
            with self._lock:
                if not self.bus_path.exists():
                    if deadline and time.time() >= deadline:
                        break
                    time.sleep(0.1)
                    continue

                lines = self.bus_path.read_text(encoding="utf-8").splitlines()
                new_offset = len(lines)

            new_messages = []
            for i, line in enumerate(lines[current_offset:], start=current_offset):
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Filter by recipient
                if msg["to"] not in (agent_id, "*"):
                    continue
                if msg_type and msg["type"] != msg_type:
                    continue

                new_messages.append(msg)

            if new_messages:
                # Advance offset
                with self._lock:
                    offset_file.write_text(str(new_offset), encoding="utf-8")
                current_offset = new_offset
                for msg in new_messages:
                    yield msg
            else:
                if deadline and time.time() >= deadline:
                    break
                time.sleep(0.1)

    # ── Checkpoint ────────────────────────────────────────────────────────

    def read_state(self, key: str) -> Any:
        """Read a value published to the bus with type=checkpoint, key=..."""
        if not self.bus_path.exists():
            return None
        for line in reversed(self.bus_path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
                if msg["type"] == "checkpoint" and msg["payload"].get("key") == key:
                    return msg["payload"].get("value")
            except json.JSONDecodeError:
                continue
        return None

    def write_state(self, key: str, value: Any) -> None:
        """Write a key=value snapshot to the bus (overwrites previous)."""
        self.publish(
            from_node="harness",
            to_node="*",
            msg_type=MessageType.CHECKPOINT,
            payload={"key": key, "value": value},
        )

    # ── Housekeeping ──────────────────────────────────────────────────────

    def purge(self) -> None:
        """Remove bus file and all offsets for this workflow."""
        with self._lock:
            if self.bus_path.exists():
                self.bus_path.unlink()
            base = Path.home() / ".time-tasker" / "agent_harness"
            for f in base.glob(f"{self.workflow_id}_*_offset.txt"):
                f.unlink()
