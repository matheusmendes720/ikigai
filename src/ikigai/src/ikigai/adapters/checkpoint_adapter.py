"""CheckpointAdapter — LangGraph checkpoints via JsonPlusSerializer (NO raw pickle).

Replaces raw pickle.loads at src/mcp_server/server.py:188-201, 419-421, 430-436.

SA-03: the serialized blob in `state_blob` MUST start with `{` / `[` (JSON),
never with `b"\x80"` (pickle protocol header).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from ikigai.entities.ikigai_record import IKIGAiRecord


class CheckpointAdapter:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.serde = JsonPlusSerializer()
        self._init_schema()

    def _init_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT PRIMARY KEY,
                    state_blob TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                )
            """)

    def save(self, record: IKIGAiRecord, thread_id: str) -> None:
        payload = record.model_dump(mode="python")
        # dumps_typed → (type_string, bytes). We store BOTH so the loader
        # can pass them back to loads_typed unchanged.
        type_string, blob = self.serde.dumps_typed(payload)
        # Store as JSON-safe: type header + base64-encoded blob. NOT raw
        # pickle — both ends of this adapter are pure JSON.
        import base64, json

        envelope = json.dumps(
            {
                "type": type_string,
                "data": base64.b64encode(blob).decode("ascii"),
            }
        )
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO checkpoints (thread_id, state_blob) VALUES (?, ?)",
                (thread_id, envelope),
            )

    def load(self, thread_id: str) -> IKIGAiRecord | None:
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT state_blob FROM checkpoints WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
        if row is None:
            return None
        import base64, json

        envelope = json.loads(row[0])
        type_string = envelope["type"]
        blob = base64.b64decode(envelope["data"])
        payload: dict[str, Any] = self.serde.loads_typed((type_string, blob))
        return IKIGAiRecord.model_validate(payload)


__all__ = ["CheckpointAdapter"]
