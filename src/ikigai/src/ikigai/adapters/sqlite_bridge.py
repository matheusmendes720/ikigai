"""IKIGAiRecordBridge — backward-compatibility shim for SQLiteAdapter.upsert_ikigai_record.

Task 11 of data-model-unification: this class is kept as a re-export shim
for backward compatibility. The canonical implementation lives on
SQLiteAdapter.upsert_ikigai_record().
"""

from __future__ import annotations

from ikigai.entities.ikigai_record import IKIGAiRecord
from ikigai.propagation.sqlite_adapter import SQLiteAdapter


class IKIGAiRecordBridge:
    """Map IKIGAiRecord → SQLiteAdapter.upsert_ikigai_record().

    Stateless: one bridge per adapter; safe to share.

    .. deprecated::
        This class is a backward-compatibility shim. New code should call
        ``adapter.upsert_ikigai_record(record)`` directly on the
        SQLiteAdapter instance.
    """

    def __init__(self, adapter: SQLiteAdapter) -> None:
        self._adapter = adapter

    def upsert_ikigai_record(self, record: IKIGAiRecord) -> None:
        """Delegate directly to the adapter's new method."""
        self._adapter.upsert_ikigai_record(record)


__all__ = ["IKIGAiRecordBridge"]
