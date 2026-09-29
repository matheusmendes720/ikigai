"""M161 — vault-intent-extract skill.

Reads `vault/daily/{date}.md` (today's note) and extracts task candidates
from natural-language intents like:
  - "amanhã eu faço X"        → due = today + 1 day
  - "próxima semana vou Y"    → due = today + 7 days
  - "deadline 2026-10-15 Z"   → due = 2026-10-15
  - "TODO: W"                 → due = None
  - "lembrar de V"            → due = None

Emits a Proposal with CREATE actions. NUNCA executes. User approves via
--approve, then changes are applied via review_queue (M148 path intact).

Cron: 0 22 * * *
Slash: /extract
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from agents.v2.proposals import Proposal


# Patterns: (regex, due_offset_days_or_None, due_explicit_group_or_None)
INTENT_PATTERNS: list[tuple[str, int | None, str | None]] = [
    # "amanhã eu faço X" / "amanhã X" — due in 1 day
    (
        r"amanh[ãa]\s+(?:eu\s+)?(?:vou\s+|vai\s+|farei\s+|fa[çc]o\s+|faço\s+)?(?P<task>[^.;\n]+)",
        1,
        None,
    ),
    # "próxima semana X" — due in 7 days
    (
        r"pr[óo]xima\s+semana\s+(?:eu\s+)?(?:vou\s+|vai\s+|farei\s+|fa[çc]o\s+|faço\s+)?(?P<task>[^.;\n]+)",
        7,
        None,
    ),
    # "deadline 2026-10-15 X" — explicit date
    (
        r"deadline\s+(?:[ée]\s+)?(?P<date>\d{4}-\d{2}-\d{2})\s+(?:para\s+|pro\s+)?(?P<task>[^.;\n]+)",
        None,
        "date",
    ),
    # "TODO: X" / "FIXME: X" / "XXX: X"
    (
        r"(?:TODO|FIXME|XXX)\s*:?\s*(?P<task>[^.;\n]+)",
        None,
        None,
    ),
    # "lembrar de X" — no due
    (
        r"lembrar\s+de\s+(?P<task>[^.;\n]+)",
        None,
        None,
    ),
]


def _clean_task_text(raw: str) -> str:
    """Trim and normalize a captured task fragment."""
    s = raw.strip()
    # Remove trailing connectors
    for tail in [", e", ", depois", " depois", " em seguida"]:
        if s.lower().endswith(tail):
            s = s[: -len(tail)]
    # Cap length
    if len(s) > 80:
        s = s[:77] + "..."
    return s.strip()


def _gen_ueid(task_text: str) -> str:
    """Generate a deterministic 5-part UEID for an extracted intent."""
    h = hashlib.sha256(task_text.encode("utf-8")).hexdigest()
    # 5-part: tsk:intention:<hash8>:<hash8>:<hash8>
    return f"tsk:intention:{h[:8]}:{h[8:16]}:{h[16:24]}"


def extract_candidates(
    markdown: str, today: date | None = None
) -> list[dict[str, Any]]:
    """Scan markdown text and return a list of CREATE-candidate dicts."""
    today = today or date.today()
    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []

    for pattern, due_offset, due_explicit_group in INTENT_PATTERNS:
        for m in re.finditer(pattern, markdown, re.IGNORECASE | re.MULTILINE):
            task_raw = m.group("task")
            task = _clean_task_text(task_raw)
            if len(task) < 5:
                continue
            if task.lower() in seen:
                continue
            seen.add(task.lower())

            # Determine due date
            if due_explicit_group == "date":
                try:
                    due = date.fromisoformat(m.group("date"))
                except (ValueError, IndexError):
                    due = None
            elif due_offset is not None:
                due = today + timedelta(days=due_offset)
            else:
                due = None

            ueid = _gen_ueid(task)
            candidates.append(
                {
                    "action": "CREATE",
                    "ueid": ueid,
                    "fields": {
                        "title": task,
                        "priority": 3,
                        "due": due.isoformat() if due else None,
                    },
                    "rationale": f"matched pattern: {pattern[:40]}...",
                }
            )

    return candidates


def propose(
    markdown: str, today: date | None = None, source_fork: str = "vault-intent-extract"
) -> Proposal:
    """Build a Proposal from intent extraction on a single markdown note."""
    today = today or date.today()
    candidates = extract_candidates(markdown, today=today)
    reasoning = (
        f"vault-intent-extract scanned today's note ({today.isoformat()}, "
        f"{len(markdown)} chars). Found {len(candidates)} candidate task(s)."
    )
    return Proposal(
        skill=source_fork,
        reasoning=reasoning,
        changes=candidates,
    )


def propose_from_file(
    file_path: str | Path, today: date | None = None
) -> Proposal:
    """Read a vault note and propose from it. Empty note → empty proposal."""
    p = Path(file_path)
    if not p.exists():
        return Proposal(
            skill="vault-intent-extract",
            reasoning=f"vault note not found: {file_path}",
            changes=[],
        )
    text = p.read_text(encoding="utf-8", errors="replace")
    return propose(text, today=today)


SKILL_NAME = "vault-intent-extract"


def run_skill(markdown: str = "") -> Proposal:
    """Entry point invoked by /skill vault-intent-extract."""
    return propose(markdown)
