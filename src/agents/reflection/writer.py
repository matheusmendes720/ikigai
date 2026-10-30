"""reflection writer — markdown rendering for findings.

Pure formatting layer. No I/O outside the target file the caller passes.
Split out from recursive.py to keep both files under 500 lines
(project rule: split when files grow).
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from .patterns import Finding

_REFLECTIONS_DIR = Path(__file__).resolve().parents[3] / "vault" / "ikigai" / "reflections"


def render_reflection(
    findings: list[Finding],
    today: date | None = None,
    lookback_days: int = 14,
    window_end: date | None = None,
) -> str:
    """Render a markdown reflection document.

    ``today`` is the run date (document title). ``window_end`` is the last
    day of the analysed window; it defaults to ``today`` and is reported in
    the "Lookback" line so the document always describes the window the
    findings were actually derived from.
    """
    today = today or datetime.now(UTC).date()
    window_end = window_end or today
    cutoff = window_end - timedelta(days=lookback_days - 1)
    lines: list[str] = []
    lines.append(f"# Reflection — {today.isoformat()}")
    lines.append("")
    lines.append(
        f"Lookback: {cutoff.isoformat()} … {window_end.isoformat()} ({lookback_days} days)"
    )
    lines.append(f"Findings: {len(findings)}")
    lines.append("")
    if not findings:
        lines.append("No patterns detected in the window. Keep recording decisions.")
        lines.append("")
        return "\n".join(lines)
    for i, f in enumerate(findings, start=1):
        lines.append(f"## {i}. {f.pattern}  (confidence {f.confidence:.0%}, n={f.sample_size})")
        lines.append("")
        lines.append(f.suggested_adjustment)
        lines.append("")
        if f.detail:
            lines.append("```json")
            lines.append(json.dumps(f.detail, indent=2, sort_keys=True, default=str))
            lines.append("```")
            lines.append("")
    return "\n".join(lines)


def write_reflection(
    findings: list[Finding],
    target: Path | None = None,
    today: date | None = None,
    lookback_days: int = 14,
    window_end: date | None = None,
) -> Path:
    """Write the markdown reflection document to disk. Returns the path.

    ``window_end`` is forwarded to :func:`render_reflection` so the written
    "Lookback" line matches the window the findings were derived from.
    """
    today = today or datetime.now(UTC).date()
    body = render_reflection(
        findings, today=today, lookback_days=lookback_days, window_end=window_end
    )
    target = target or (_REFLECTIONS_DIR / f"{today.isoformat()}.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target
