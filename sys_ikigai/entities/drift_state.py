"""DriftState — markdown-vs-mirror consistency (SPEC D14, §8.2)."""

from __future__ import annotations

from enum import Enum


class DriftState(str, Enum):
    IN_SYNC = "in_sync"
    MARKDOWN_NEWER = "markdown_newer"
    SQLITE_NEWER = "sqlite_newer"
    CONFLICT = "conflict"


__all__ = ["DriftState"]
