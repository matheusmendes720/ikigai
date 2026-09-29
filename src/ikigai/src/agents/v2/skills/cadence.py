"""M162 — Shared helpers for cadence skills (daily/weekly/monthly/quarterly).

These helpers are extracted so each skill stays small and testable.
They have NO side effects on vault or taskdog (read-only).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


def _parse_iso_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def was_done_in_window(
    task: dict[str, Any], start: date, end: date
) -> bool:
    """Heuristic: was this task completed in [start, end]?

    Since our schema doesn't always have `completed_at`, we use:
    - status == "done" AND
    - created_at or last updated time within window (best effort)
    """
    if task.get("status") != "done":
        return False
    # Check created_at as proxy
    created = _parse_iso_date(task.get("created_at"))
    if created and start <= created <= end:
        return True
    # Fallback: assume yes if no timestamp but status is done
    # (better to over-include than under-include for read-only stats)
    return task.get("created_at") is None


def was_created_in_window(
    task: dict[str, Any], start: date, end: date
) -> bool:
    """Heuristic: was this task created in [start, end]?"""
    created = _parse_iso_date(task.get("created_at"))
    if not created:
        return False
    return start <= created <= end


def read_vault_note(path: str | Path) -> str:
    """Read a vault note if it exists, else return empty string."""
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def list_vault_notes_in_range(
    pattern_fn, start: date, end: date
) -> list[tuple[date, str]]:
    """List (date, content) tuples for notes matching pattern_fn(date) → Path.

    Missing files are skipped silently.
    """
    out: list[tuple[date, str]] = []
    cursor = start
    while cursor <= end:
        p = pattern_fn(cursor)
        if p and p.exists():
            out.append((cursor, p.read_text(encoding="utf-8", errors="replace")))
        cursor = cursor + timedelta(days=1)
    return out


def daily_path(d: date) -> Path:
    return Path(f"vault/daily/{d.isoformat()}.md")


def weekly_path(d: date) -> Path:
    # ISO week format: 2026-W40
    iso = d.isocalendar()
    return Path(f"vault/weekly/{iso.year}-W{iso.week:02d}.md")


def monthly_path(d: date) -> Path:
    return Path(f"vault/monthly/{d.year}-{d.month:02d}.md")


def quarterly_path(d: date) -> Path:
    quarter = (d.month - 1) // 3 + 1
    return Path(f"vault/quarterly/{d.year}-Q{quarter}.md")


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------


def render_weekly_review(
    today: date,
    daily_reports: list[tuple[date, str]],
    done_tasks: list[dict[str, Any]],
    created_tasks: list[dict[str, Any]],
) -> str:
    """Build the weekly review markdown."""
    iso = today.isocalendar()
    lines: list[str] = [
        f"# Weekly Review — {iso.year}-W{iso.week:02d}",
        "",
        f"_Generated {today.isoformat()} by ikigai-weekly skill_",
        "",
        "## Stats",
        "",
        f"- **Daily reports in window**: {len(daily_reports)}",
        f"- **Tasks done**: {len(done_tasks)}",
        f"- **Tasks created**: {len(created_tasks)}",
        "",
        "## Daily Reports",
        "",
    ]
    if daily_reports:
        for d, content in daily_reports:
            lines.append(f"### {d.isoformat()}")
            lines.append("")
            # First 5 lines of each daily
            for line in content.splitlines()[:5]:
                lines.append(f"> {line}")
            lines.append("")
    else:
        lines.append("_No daily reports found in window._")
        lines.append("")

    lines.append("## Tasks completed this week")
    lines.append("")
    if done_tasks:
        for t in done_tasks[:20]:
            ueid = t.get("ueid", "?")
            name = t.get("name", "(no name)")
            lines.append(f"- `{ueid}` — {name}")
        if len(done_tasks) > 20:
            lines.append(f"- _...and {len(done_tasks) - 20} more_")
    else:
        lines.append("_None._")
    lines.append("")

    lines.append("## Tasks created this week")
    lines.append("")
    if created_tasks:
        for t in created_tasks[:20]:
            ueid = t.get("ueid", "?")
            name = t.get("name", "(no name)")
            lines.append(f"- `{ueid}` — {name}")
        if len(created_tasks) > 20:
            lines.append(f"- _...and {len(created_tasks) - 20} more_")
    else:
        lines.append("_None._")
    lines.append("")

    return "\n".join(lines)


def render_monthly_review(
    today: date, weekly_reviews: list[tuple[date, str]]
) -> str:
    """Build the monthly review markdown."""
    lines: list[str] = [
        f"# Monthly Review — {today.year}-{today.month:02d}",
        "",
        f"_Generated {today.isoformat()} by ikigai-monthly skill_",
        "",
        "## Weekly reviews aggregated",
        "",
    ]
    if weekly_reviews:
        for d, content in weekly_reviews:
            iso = d.isocalendar()
            lines.append(f"### {iso.year}-W{iso.week:02d}")
            lines.append("")
            for line in content.splitlines()[:8]:
                lines.append(f"> {line}")
            lines.append("")
    else:
        lines.append("_No weekly reviews found._")
        lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Weekly reviews: {len(weekly_reviews)}")
    lines.append("")
    return "\n".join(lines)


def render_quarterly_review(
    today: date,
    monthly_reviews: list[tuple[date, str]],
    weekly_reviews: list[tuple[date, str]],
) -> str:
    """Build the quarterly review markdown."""
    quarter = (today.month - 1) // 3 + 1
    lines: list[str] = [
        f"# Quarterly Review — {today.year}-Q{quarter}",
        "",
        f"_Generated {today.isoformat()} by ikigai-quarterly skill_",
        "",
        "## Cadence summary",
        "",
        f"- Monthly reviews aggregated: {len(monthly_reviews)}",
        f"- Weekly reviews aggregated: {len(weekly_reviews)}",
        "",
        "## Monthly highlights",
        "",
    ]
    if monthly_reviews:
        for d, content in monthly_reviews:
            lines.append(f"### {d.year}-{d.month:02d}")
            lines.append("")
            for line in content.splitlines()[:6]:
                lines.append(f"> {line}")
            lines.append("")
    else:
        lines.append("_No monthly reviews found._")
        lines.append("")

    return "\n".join(lines)


def extract_okrs_from_review(review_md: str) -> list[dict[str, Any]]:
    """Pull 'OKR' or 'Goal' lines from review markdown.

    Very simple heuristic: any line starting with '- [ ]' or '# Goal'.
    Returns dicts with title and priority defaults.
    """
    okrs: list[dict[str, Any]] = []
    for line in review_md.splitlines():
        s = line.strip()
        if s.startswith(("- [ ]", "* [ ]", "+ [ ]")):
            title = s[5:].strip()
            if title:
                okrs.append({"title": title, "priority": 2})
        elif s.startswith("# Goal"):
            title = s[len("# Goal") :].strip(" :")
            if title:
                okrs.append({"title": title, "priority": 1})
    return okrs
