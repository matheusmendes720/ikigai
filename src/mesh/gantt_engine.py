"""M167: Gantt rendering engine for taskdog tasks.

Renders task slices as Gantt charts in three output modes:
  - ascii: box-drawing characters (light/medium/heavy) with status glyphs
  - html : valid HTML5 <table> rendering with CSS classes
  - json : structured data (days × tasks matrix + per-task metadata)

The engine is **pure** — it consumes a list of task dicts (with the
canonical fields ``ueid``, ``name``, ``status``, ``priority``,
``planned_start``, ``planned_end``, ``deadline``, ``created_at``,
``started_at``, ``completed_at``, ``deps``) plus a list of dep edges,
and produces a string/HTML/JSON output. No I/O, no DB access, no
adapter calls — caller wires it up.

This keeps the rendering logic trivially testable (snapshot tests on
the ASCII output; HTML parse tests; JSON shape tests).

Conventions
-----------
- One row per task. Tasks are ordered by ``planned_start`` (ISO date
  string; lexicographic = chronological). Tasks with no planned_start
  fall to the end, in insertion order.
- Columns = days. The day axis spans the earliest planned_start to the
  latest planned_end (or deadline if no planned_end), inclusive, on
  both sides. Empty days outside any task range are trimmed.
- Day labels: ``D1``, ``D2`` ... ``D{N}`` by default. If a task has
  a real planned_start, the axis prints ISO dates (``2026-09-15``)
  along the bottom row in addition to the D{N} labels.
- Status glyphs (one ASCII char per cell):
    planned       ``░``  light shade
    in_progress   ``█``  full block
    done          ``✓``  check mark
    cancelled     ``✗``  cross mark
    overdue       ``!``  exclamation (priority signal)
- Dep arrows (in the right-side annotation column):
    depends-on (this task is blocked by another)  ``↓``
    blocks (this task blocks another)             ``→``

Usage
-----
    from src.mesh.gantt_engine import GanttEngine, GanttConfig

    cfg = GanttConfig(mode="ascii", day_width=3)
    out = GanttEngine(tasks, deps).render(cfg)
    print(out)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Iterable


# ----------------------------------------------------------------------
# Public dataclasses
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class GanttConfig:
    """Configuration for the Gantt renderer.

    Attributes:
        mode:           output mode (``"ascii"`` | ``"html"`` | ``"json"``)
        day_width:      width (chars) of one day column in ASCII mode
        ueid_width:     truncation width for the UEID column header
        name_width:     truncation width for the name column
        title:          chart title (printed in HTML/JSON; ignored by ASCII)
        show_dep_arrows: whether to render the right-side dep arrow column
    """

    mode: str = "ascii"
    day_width: int = 3
    ueid_width: int = 16
    name_width: int = 28
    title: str = "Taskdog Gantt"
    show_dep_arrows: bool = True


# Status glyph set (1 char each). Kept in module scope so renderers stay
# pure functions of (task_slice, cfg).
_STATUS_GLYPHS: dict[str, str] = {
    "planned": "░",
    "in_progress": "█",
    "done": "✓",
    "cancelled": "✗",
}


@dataclass(frozen=True)
class GanttRow:
    """One task rendered as a row of glyphs (one per day)."""

    ueid: str
    name: str
    status: str
    priority: int | None
    glyphs: tuple[str, ...]
    span_start: int  # index into the day axis where the task begins
    span_end: int  # exclusive
    deps_down: tuple[str, ...] = ()  # UEIDs this task is blocked by (↓)
    deps_out: tuple[str, ...] = ()  # UEIDs this task blocks (→)
    overdue: bool = False


@dataclass(frozen=True)
class GanttPlan:
    """Computed rendering plan (rows + day axis).

    Used by both the ASCII and HTML renderers; JSON mode serializes
    this directly.
    """

    rows: tuple[GanttRow, ...]
    days: tuple[str, ...]  # ISO date strings for each column
    title: str
    config: GanttConfig

    def to_json(self) -> str:
        """Serialize as JSON."""
        payload: dict[str, Any] = {
            "title": self.title,
            "config": {
                "mode": self.config.mode,
                "day_width": self.config.day_width,
            },
            "days": list(self.days),
            "tasks": [
                {
                    "ueid": r.ueid,
                    "name": r.name,
                    "status": r.status,
                    "priority": r.priority,
                    "span_start": r.span_start,
                    "span_end": r.span_end,
                    "deps_down": list(r.deps_down),
                    "deps_out": list(r.deps_out),
                    "overdue": r.overdue,
                    "glyphs": list(r.glyphs),
                }
                for r in self.rows
            ],
        }
        return json.dumps(payload, indent=2, sort_keys=True)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _parse_iso_date(s: str | None) -> date | None:
    """Parse an ISO 8601 date or datetime string → ``date``.

    Returns ``None`` for empty / unparseable input. The mesh stores
    dates as either ``YYYY-MM-DD`` (from the canonical schema) or full
    ISO 8601 timestamps (``2026-09-15T14:30:00+00:00``); this helper
    accepts both.
    """
    if not s:
        return None
    s = str(s).strip()
    # Try date-only first (canonical schema format).
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        pass
    # Try ISO datetime — accept the first 10 chars either way.
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None


# Renderers (ASCII + HTML) live in gantt_renderers.py to keep this
# module under the project's 500-line cap. The render() method above
# imports them lazily to avoid a hard circular dependency.


def _build_day_axis(tasks: Iterable[dict[str, Any]]) -> tuple[list[date], list[str]]:
    """Compute the day axis spanning all tasks.

    Returns ``(dates, iso_strings)``. The axis starts at the earliest
    planned_start (fallback: earliest started_at) and ends at the latest
    planned_end (fallback: completed_at). Empty span (no dated tasks)
    yields a single-day axis anchored at ``date.today()``.

    Note: deadlines and created_at are intentionally excluded so the
    chart shows the *planned* schedule, not loose date hints.
    """
    starts: list[date] = []
    ends: list[date] = []
    for t in tasks:
        s = _parse_iso_date(t.get("planned_start")) or _parse_iso_date(
            t.get("started_at")
        )
        e = _parse_iso_date(t.get("planned_end")) or _parse_iso_date(
            t.get("completed_at")
        )
        if s is not None:
            starts.append(s)
        if e is not None:
            ends.append(e)

    if not starts and not ends:
        today = date.today()
        return [today], [today.isoformat()]

    axis_start = min(starts) if starts else (min(ends) if ends else date.today())
    axis_end = max(ends) if ends else (max(starts) if starts else date.today())
    if axis_end < axis_start:
        axis_end = axis_start

    days: list[date] = []
    cur = axis_start
    while cur <= axis_end:
        days.append(cur)
        cur += timedelta(days=1)
    return days, [d.isoformat() for d in days]


def _index_deps(
    tasks: list[dict[str, Any]],
    explicit_deps: Iterable[tuple[str, str]] | None = None,
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Build two maps: deps_down[ueid] = [ueids it depends on],
    deps_out[ueid] = [ueids it blocks].

    Reads from each task's ``deps`` field (canonical M163 column).
    Optional explicit edges (UEID pairs) are merged on top. Tasks
    missing from the slice are simply skipped — we render only what
    was loaded.
    """
    ueids = {str(t.get("ueid") or "") for t in tasks}
    down: dict[str, list[str]] = {u: [] for u in ueids if u}
    out_map: dict[str, list[str]] = {u: [] for u in ueids if u}
    for t in tasks:
        ueid = str(t.get("ueid") or "")
        if not ueid:
            continue
        for d in t.get("deps") or []:
            sd = str(d or "")
            if not sd or sd not in ueids:
                continue
            if sd not in down[ueid]:
                down[ueid].append(sd)
            if ueid not in out_map[sd]:
                out_map[sd].append(ueid)
    for src, dst in explicit_deps or ():
        if src in down and dst in ueids and dst not in down[src]:
            down[src].append(dst)
        if dst in out_map and src in ueids and src not in out_map[dst]:
            out_map[dst].append(src)
    return down, out_map


def _row_for_task(
    task: dict[str, Any],
    day_index: dict[str, int],
    down: list[str],
    out: list[str],
    overdue: bool,
) -> GanttRow:
    """Compute the glyph row for one task.

    The glyph sequence covers the full day axis. Outside the task's
    span, cells are blank (" "). Inside the span, cells use the
    status glyph (or ``!`` if overdue).
    """
    ueid = str(task.get("ueid") or "")
    name = str(task.get("name") or "")
    status = str(task.get("status") or "planned")
    priority = task.get("priority")
    if priority is not None:
        try:
            priority = int(priority)
        except (TypeError, ValueError):
            priority = None

    glyph_char = _STATUS_GLYPHS.get(status, "·")
    if overdue:
        glyph_char = "!"

    span_start_idx = 0
    span_end_idx = 0
    p_start = _parse_iso_date(task.get("planned_start")) or _parse_iso_date(
        task.get("started_at")
    )
    p_end = _parse_iso_date(task.get("planned_end")) or _parse_iso_date(
        task.get("completed_at")
    )

    if p_start is not None and day_index:
        span_start_idx = day_index.get(p_start.isoformat(), 0)
    if p_end is not None and day_index:
        iso_end = p_end.isoformat()
        if iso_end in day_index:
            span_end_idx = day_index[iso_end] + 1
        else:
            span_end_idx = len(day_index)
    if span_end_idx < span_start_idx:
        span_end_idx = span_start_idx + 1

    width = len(day_index) if day_index else 1
    glyphs: list[str] = []
    for i in range(width):
        if span_start_idx <= i < span_end_idx:
            glyphs.append(glyph_char)
        else:
            glyphs.append(" ")

    return GanttRow(
        ueid=ueid,
        name=name,
        status=status,
        priority=priority,
        glyphs=tuple(glyphs),
        span_start=span_start_idx,
        span_end=span_end_idx,
        deps_down=tuple(down),
        deps_out=tuple(out),
        overdue=overdue,
    )


def _is_overdue(task: dict[str, Any], today: date) -> bool:
    """Return True if a task is past its deadline but not yet done."""
    status = str(task.get("status") or "")
    if status in ("done", "cancelled"):
        return False
    dl = _parse_iso_date(task.get("deadline"))
    return dl is not None and dl < today


# ----------------------------------------------------------------------
# Engine
# ----------------------------------------------------------------------


class GanttEngine:
    """Pure renderer for taskdog task slices.

    Inputs:
        tasks: list of dicts (slice shape from ``TaskdogAdapter.list_all``)
        deps:  optional list of explicit dep edges (UEID pairs). When
               empty (default), the engine reads ``task["deps"]`` for
               each row.

    Outputs:
        render(cfg) → string (ASCII) | HTML string | JSON string based
        on ``cfg.mode``.
    """

    def __init__(
        self,
        tasks: list[dict[str, Any]],
        deps: Iterable[tuple[str, str]] | None = None,
        today: date | None = None,
    ) -> None:
        self._tasks = list(tasks)
        self._explicit_deps: list[tuple[str, str]] = list(deps or [])
        self._today = today or date.today()

    # ──── Public API ────

    def plan(self, cfg: GanttConfig) -> GanttPlan:
        """Compute the render plan. Use this for HTML / JSON / inspection."""
        days, iso_days = _build_day_axis(self._tasks)
        day_index = {iso: i for i, iso in enumerate(iso_days)}
        down_map, out_map = _index_deps(self._tasks, self._explicit_deps)

        rows: list[GanttRow] = []
        # Sort tasks: by planned_start (lex on iso), then by ueid for stability.
        sorted_tasks = sorted(
            self._tasks,
            key=lambda t: (
                str(t.get("planned_start") or "9999"),
                str(t.get("ueid") or ""),
            ),
        )
        for t in sorted_tasks:
            ueid = str(t.get("ueid") or "")
            if not ueid:
                continue
            rows.append(
                _row_for_task(
                    t,
                    day_index,
                    down_map.get(ueid, []),
                    out_map.get(ueid, []),
                    overdue=_is_overdue(t, self._today),
                )
            )
        return GanttPlan(
            rows=tuple(rows),
            days=tuple(iso_days),
            title=cfg.title,
            config=cfg,
        )

    def render(self, cfg: GanttConfig) -> str:
        """Render the plan as a string in the requested mode."""
        plan = self.plan(cfg)
        if cfg.mode == "ascii":
            # Local import keeps gantt_renderers lazy (and avoids a
            # circular import — renderers import nothing from here).
            from src.mesh.gantt_renderers import render_ascii

            return render_ascii(plan)
        if cfg.mode == "html":
            from src.mesh.gantt_renderers import render_html

            return render_html(plan)
        if cfg.mode == "json":
            return plan.to_json()
        raise ValueError(f"unknown gantt mode: {cfg.mode!r}")


__all__ = ["GanttConfig", "GanttEngine", "GanttPlan", "GanttRow"]


# ──── Heavy-set variant retained for callers that prefer double-line ────


@dataclass(frozen=True)
class GanttConfigHeavy(GanttConfig):
    """Same as ``GanttConfig`` but signals a preference for heavy
    box-drawing characters. The ASCII renderer ignores this for now
    (kept as a stable forward-compat hook for M168+ HTML templates).
    """

    style: str = field(default="heavy", init=False)
