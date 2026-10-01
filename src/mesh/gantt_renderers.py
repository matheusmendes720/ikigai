"""M167: Gantt output renderers — ASCII (box-drawing) + HTML5 <table>.

These are pure functions of a ``GanttPlan`` (computed by
``GanttEngine.plan()``). Splitting the renderers out of
``gantt_engine.py`` keeps each module under the 500-line cap the
project's CLAUDE.md sets.

ASCII renderer:
    Light box-drawing chart with status glyphs (░ █ ✓ ✗ !) and
    a dep arrow column (↓ depends-on, → blocks). Title on row 0,
    legend on the final row.

HTML renderer:
    Self-contained HTML5 document with embedded CSS. Each day-cell
    carries a CSS class so styles can be re-skinned without
    touching the renderer.

The JSON mode is provided directly by ``GanttPlan.to_json()`` — no
renderer function needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.mesh.gantt_engine import GanttPlan


# ─────────────────────────────────────────────────────────────────────
# Helpers (also re-exported by gantt_engine for ASCII rendering tests)
# ─────────────────────────────────────────────────────────────────────


def _truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _html_escape(s: str) -> str:
    """Escape characters that have meaning inside HTML text/attributes."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


# ─────────────────────────────────────────────────────────────────────
# ASCII renderer
# ─────────────────────────────────────────────────────────────────────


def render_ascii(plan: "GanttPlan") -> str:
    """Render ``plan`` as a box-drawing chart.

    Layout::

        TITLE
        ┌─────────┬───┬───┬───┬───┬───┐
        │ UEID    │ D1 D2 D3 D4 D5│ →/↓
        ├─────────┼───┼───┼───┼───┼───┤
        │ name    │ ░ ░ █ █ ✓   │ →tsk:foo
        └─────────┴───┴───┴───┴───┴───┘
        days: 2026-09-01 ... 2026-09-05
    """
    cfg = plan.config
    n_days = len(plan.days)
    day_width = max(1, cfg.day_width)
    ueid_col = max(8, cfg.ueid_width)
    name_col = max(8, cfg.name_width)
    arrow_col = 24 if cfg.show_dep_arrows else 0

    # Box-drawing characters (light set).
    H, V = "─", "│"

    def _join(cells: list[str], t_char: str, l_char: str, r_char: str) -> str:
        return l_char + t_char.join(cells) + r_char

    def top() -> str:
        cells = [H * ueid_col, H * name_col]
        for _ in range(n_days):
            cells.append(H * day_width)
        if arrow_col:
            cells.append(H * arrow_col)
        return _join(cells, "┬", "┌", "┐")

    def mid() -> str:
        cells = [H * ueid_col, H * name_col]
        for _ in range(n_days):
            cells.append(H * day_width)
        if arrow_col:
            cells.append(H * arrow_col)
        return _join(cells, "┼", "├", "┤")

    def bot() -> str:
        cells = [H * ueid_col, H * name_col]
        for _ in range(n_days):
            cells.append(H * day_width)
        if arrow_col:
            cells.append(H * arrow_col)
        return _join(cells, "┴", "└", "┘")

    lines: list[str] = []
    lines.append(plan.title)
    lines.append(top())

    # Header row: "UEID", "TASK", "D1", "D2", ..., arrows
    header_cells = [
        "UEID".ljust(ueid_col),
        "TASK".ljust(name_col),
    ]
    for i in range(n_days):
        header_cells.append(f"D{i + 1}".center(day_width))
    if arrow_col:
        header_cells.append("deps".ljust(arrow_col))
    lines.append(V + V.join(header_cells) + V)
    lines.append(mid())

    # Data rows.
    for r in plan.rows:
        ueid_cell = _truncate(r.ueid, ueid_col).ljust(ueid_col)
        name_cell = _truncate(r.name, name_col).ljust(name_col)
        glyph_cells = [g.center(day_width) for g in r.glyphs]
        row_cells = [ueid_cell, name_cell] + glyph_cells
        if arrow_col:
            arrow_bits: list[str] = []
            if r.deps_down:
                arrow_bits.append(
                    "↓" + ",".join(_truncate(d, 6) for d in r.deps_down)
                )
            if r.deps_out:
                arrow_bits.append(
                    "→" + ",".join(_truncate(d, 6) for d in r.deps_out)
                )
            if r.overdue:
                arrow_bits.append("OVERDUE")
            arrow_text = " ".join(arrow_bits) or "-"
            row_cells.append(arrow_text.ljust(arrow_col)[:arrow_col])
        lines.append(V + V.join(row_cells) + V)

    lines.append(bot())

    # Day labels under the chart (ISO dates).
    if plan.days:
        date_row = " " * (ueid_col + 1) + " " * (name_col + 1)
        for iso in plan.days:
            date_row += iso.center(day_width) + V
        lines.append(date_row.rstrip(V))
        # Legend.
        lines.append(
            "legend: ░ planned   █ in_progress   ✓ done   ✗ cancelled   ! overdue   "
            "↓ depends-on   → blocks"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# HTML renderer
# ─────────────────────────────────────────────────────────────────────


def render_html(plan: "GanttPlan") -> str:
    """Render ``plan`` as a self-contained HTML5 <table> with embedded CSS.

    No external resources are required. Each task is one row; the day
    cells carry CSS classes (gantt-planned, gantt-progress, gantt-done,
    gantt-overdue, gantt-empty) so downstream styles can re-skin
    without touching the renderer.
    """
    cfg = plan.config
    css = (
        "<style>"
        "table.gantt{border-collapse:collapse;font-family:monospace;}"
        "table.gantt th,table.gantt td{border:1px solid #888;padding:2px 4px;text-align:center;}"
        "table.gantt th{background:#eee;}"
        "td.gantt-planned{background:#e6f0ff;}"
        "td.gantt-progress{background:#7ec47e;color:#fff;font-weight:bold;}"
        "td.gantt-done{background:#b8e6b8;color:#222;}"
        "td.gantt-cancelled{background:#e0e0e0;color:#777;text-decoration:line-through;}"
        "td.gantt-overdue{background:#ffd2d2;color:#a00;font-weight:bold;}"
        "td.gantt-empty{background:#fafafa;}"
        "td.gantt-ueid{text-align:left;font-family:monospace;}"
        "td.gantt-deps{text-align:left;font-size:0.9em;color:#444;}"
        "</style>"
    )

    status_class = {
        "planned": "gantt-planned",
        "in_progress": "gantt-progress",
        "done": "gantt-done",
        "cancelled": "gantt-cancelled",
    }

    parts: list[str] = []
    parts.append(
        f'<!DOCTYPE html><html lang="en"><head>'
        f'<meta charset="utf-8"><title>{_html_escape(plan.title)}</title>'
        f"{css}</head><body>"
    )
    parts.append(f"<h2>{_html_escape(plan.title)}</h2>")
    parts.append('<table class="gantt">')

    # Header row.
    parts.append("<thead><tr>")
    parts.append("<th>UEID</th>")
    parts.append("<th>Task</th>")
    for i, iso in enumerate(plan.days):
        parts.append(f'<th title="{iso}">D{i + 1}</th>')
    if cfg.show_dep_arrows:
        parts.append("<th>Deps</th>")
    parts.append("</tr></thead>")

    # Data rows.
    parts.append("<tbody>")
    for r in plan.rows:
        parts.append("<tr>")
        parts.append(
            f'<td class="gantt-ueid">{_html_escape(_truncate(r.ueid, cfg.ueid_width))}</td>'
        )
        parts.append(f"<td>{_html_escape(_truncate(r.name, cfg.name_width))}</td>")
        cls = "gantt-overdue" if r.overdue else status_class.get(
            r.status, "gantt-empty"
        )
        for glyph in r.glyphs:
            parts.append(f'<td class="{cls}">{_html_escape(glyph)}</td>')
        if cfg.show_dep_arrows:
            bits: list[str] = []
            if r.deps_down:
                bits.append(
                    "↓ " + ", ".join(_html_escape(d) for d in r.deps_down)
                )
            if r.deps_out:
                bits.append(
                    "→ " + ", ".join(_html_escape(d) for d in r.deps_out)
                )
            if r.overdue:
                bits.append("OVERDUE")
            dep_text = " ".join(bits) or "-"
            parts.append(f'<td class="gantt-deps">{dep_text}</td>')
        parts.append("</tr>")
    parts.append("</tbody>")
    parts.append("</table>")
    parts.append("</body></html>")
    return "".join(parts)


__all__ = ["render_ascii", "render_html"]
