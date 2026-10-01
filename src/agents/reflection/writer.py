"""reflection writer — markdown rendering for findings.

Pure formatting layer. No I/O outside the target file the caller passes.
Split out from recursive.py to keep both files under 500 lines
(project rule: split when files grow).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .recursive import Finding

_REFLECTIONS_DIR = (
    Path(__file__).resolve().parents[3] / "vault" / "ikigai" / "reflections"
)


def render_reflection(
    findings: list[Finding],
    today: date | None = None,
    lookback_days: int = 14,
) -> str:
    """Render a markdown reflection document."""
    today = today or datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=lookback_days - 1)
    lines: list[str] = []
    lines.append(f"# Reflection — {today.isoformat()}")
    lines.append("")
    lines.append(
        f"Lookback: {cutoff.isoformat()} … {today.isoformat()} ({lookback_days} days)"
    )
    lines.append(f"Findings: {len(findings)}")
    lines.append("")
    if not findings:
        lines.append("No patterns detected in the window. Keep recording decisions.")
        lines.append("")
        return "\n".join(lines)
    for i, f in enumerate(findings, start=1):
        lines.append(
            f"## {i}. {f.pattern}  (confidence {f.confidence:.0%}, n={f.sample_size})"
        )
        lines.append("")
        lines.append(f.suggested_adjustment)
        lines.append("")
        if f.detail:
            lines.append("```json")
            lines.append(
                json.dumps(f.detail, indent=2, sort_keys=True, default=str)
            )
            lines.append("```")
            lines.append("")
    return "\n".join(lines)


def write_reflection(
    findings: list[Finding],
    target: Path | None = None,
    today: date | None = None,
    lookback_days: int = 14,
) -> Path:
    """Write the markdown reflection document to disk. Returns the path."""
    today = today or datetime.now(timezone.utc).date()
    body = render_reflection(findings, today=today, lookback_days=lookback_days)
    target = target or (_REFLECTIONS_DIR / f"{today.isoformat()}.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target