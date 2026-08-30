"""Pydantic v2 frozen models for tuiboard tools."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TuiboardLayoutName = Literal["kanban", "list", "calendar", "tree"]


class _Base(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class _Filters(_Base):
    status: Literal["planned", "scheduled", "in_progress", "done", "skipped"] | None = (
        None
    )
    vector: Literal["passion", "skill", "market", "revenue", "course"] | None = None
    tags: list[str] | None = None
    due_before: str | None = None  # ISO 8601


class _RenderOptions(_Base):
    max_width: int = 120
    show_ueid: bool = False
    compact: bool = False


class TuiboardRenderInput(_Base):
    ueids: list[str] = []  # 1..N if non-empty
    layout: TuiboardLayoutName
    filters: _Filters | None = None
    render_options: _RenderOptions | None = None


class TuiboardPosition(_Base):
    section: str
    row: int
    col: int


class TuiboardFrame(_Base):
    ueid: str
    title: str
    status: str | None = None
    due: str | None = None
    vector: str | None = None
    tags: list[str] = []
    position: TuiboardPosition
    child_ueids: list[str] = []


class TuiboardMetadata(_Base):
    total_tasks: int
    shown_tasks: int
    truncated: bool


class TuiboardRenderOutput(_Base):
    layout: TuiboardLayoutName
    frames: list[TuiboardFrame]
    metadata: TuiboardMetadata


class TuiboardSnapshotInput(_Base):
    name: str = Field(..., min_length=1, max_length=64)
    layout: TuiboardLayoutName
    filters: _Filters | None = None
    description: str | None = Field(None, max_length=500)


class TuiboardSnapshotOutput(_Base):
    snapshot_id: str  # uuid v4 hex
    name: str
    created_at: str  # ISO 8601
    task_count: int
    sha256: str


class TuiboardDiffInput(_Base):
    from_snapshot_id: str = Field(..., min_length=1)
    to_snapshot_id: str = Field(..., min_length=1)
    include_unchanged: bool = False


class TuiboardTaskEntry(_Base):
    ueid: str
    title: str
    status: str | None = None


class TuiboardChange(_Base):
    ueid: str
    field: str
    before: Any
    after: Any


class TuiboardDiffOutput(_Base):
    from_snapshot_id: str
    to_snapshot_id: str
    added: list[TuiboardTaskEntry]
    removed: list[TuiboardTaskEntry]
    changed: list[TuiboardChange]
    unchanged_count: int = 0


class TuiboardAggregateInput(_Base):
    """Input for tuiboard_aggregate tool — no parameters required."""
    pass


class TuiboardAggregateTask(_Base):
    """One task in the aggregated view across all forks."""
    ueid: str
    title: str
    status: str | None = None
    source: Literal["cli", "taskdog", "solverforge-calendar"]
    due: str | None = None
    vector: str | None = None
    tags: list[str] = []


class TuiboardAggregateOutput(_Base):
    """Aggregated view across all 3 forks with source breakdown."""
    tasks: list[TuiboardAggregateTask]
    count: int
    sources: dict[str, int]
