"""Common adapter contract for fork adapters."""
from typing import Any, Protocol, runtime_checkable

from src.contracts.common import UEID
from src.contracts.task_change import PropagationEvent


@runtime_checkable
class ForkAdapter(Protocol):
    """Every fork adapter implements read() + apply_change() + supports_field()."""
    name: str

    def read(self, ueid: UEID) -> dict[str, Any] | None:
        """Return slice for this UEID, or None if not found."""
        ...

    def apply_change(self, event: PropagationEvent) -> None:
        """Apply change to fork store. Idempotent (safe to retry)."""
        ...

    def supports_field(self, field_name: str) -> bool:
        """Return True if this adapter persists this field."""
        ...
