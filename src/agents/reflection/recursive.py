"""M-TBD — recursive reflection (entry point).

The agent observes its own past decisions and surfaces patterns:

  * "I keep underestimating task X by 2x"
  * "tags {a, b} correlate with completion < 24h"

File layout
-----------

    vault/ikigai/decisions/<YYYY-MM-DD>.jsonl    # append-only log
    vault/ikigai/reflections/<YYYY-MM-DD>.md     # one per reflection run

Both directories are append-only (drift invariant d — `vault/` append-only).

Modules:
  * recursive.py — DecisionStore, Reflector (orchestrator), CLI entry
  * patterns.py  — three pattern detectors (Finding + thresholds)
  * writer.py    — markdown render / write

Per ADR-013 the agent is planner-only — this is observational memory,
not policy execution. Findings become Proposals for the human to
adjudicate, never auto-applied.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from .patterns import (
    Finding,
    detect_fast_finish,
    detect_priority_churn,
    detect_underestimation,
)
from .writer import render_reflection, write_reflection  # re-export

__all__ = [
    "Decision",
    "DecisionStore",
    "Finding",
    "Reflector",
    "main",
    "render_reflection",
    "write_reflection",
]


# ---------- paths ----------

# Repo root resolves from this file: src/agents/reflection/recursive.py → ../../../
_REPO_ROOT = Path(__file__).resolve().parents[3]
_VAULT_IKIGAI = _REPO_ROOT / "vault" / "ikigai"
_DECISIONS_DIR = _VAULT_IKIGAI / "decisions"


# ---------- dataclasses ----------


@dataclass(frozen=True)
class Decision:
    """One agent decision, appended to the JSONL log."""

    timestamp: datetime  # when the decision was made (UTC)
    action: str  # 'create' | 'done' | 'update' | 'tag_add' | ...
    ueid: str
    context: dict[str, Any] = field(default_factory=dict)


# ---------- DecisionStore ----------


class DecisionStore:
    """Append-only JSONL store for agent decisions.

    Per ADR-013 this is observational memory — the agent never reads from
    here to make *its own* choices. Findings become Proposals for the human.

    Path layout: ``<vault>/ikigai/decisions/<YYYY-MM-DD>.jsonl``

    Atomic write strategy:
      * open(path, 'a', encoding='utf-8') + flush() per decision
      * fsync optional (omit — append-only window per file is small,
        and a partial line in a daily log is recoverable from context)
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or _DECISIONS_DIR

    def append(
        self,
        action: str,
        ueid: str,
        context: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> Path:
        """Append one decision to the day's JSONL file.

        Returns the path of the file written to.
        """
        ts = timestamp or datetime.now(UTC)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        decision = Decision(
            timestamp=ts,
            action=action,
            ueid=ueid,
            context=dict(context or {}),
        )
        target = self.base_dir / f"{ts.date().isoformat()}.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        # Serialise manually so datetime uses ISO-8601 with 'T' separator.
        # json.dumps(..., default=str) yields 'YYYY-MM-DD HH:MM:SS+00:00',
        # which datetime.fromisoformat() reads fine on 3.11+ but breaks
        # for parsers expecting strict RFC-3339.
        serialised = asdict(decision)
        serialised["timestamp"] = ts.isoformat()
        payload = json.dumps(serialised, sort_keys=False)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(payload + "\n")
            fh.flush()
        return target

    def latest_decision_date(self) -> date | None:
        """Newest calendar day present in the log, or None when empty."""
        if not self.base_dir.exists():
            return None
        latest: date | None = None
        for path in self.base_dir.glob("*.jsonl"):
            try:
                file_date = date.fromisoformat(path.stem)
            except ValueError:
                continue
            if latest is None or file_date > latest:
                latest = file_date
        return latest

    def resolve_window_end(self, today: date | None = None) -> date:
        """Resolve the last day of the analysis window.

        An explicit ``today`` always wins. Otherwise the window is anchored
        on the newest day present in the log rather than on wall-clock time:
        the log is the subject of the reflection, so a log that stopped
        being written must not silently yield an empty report. The anchor
        never exceeds the current UTC date, so a future-dated log entry
        cannot drag the window past today.
        """
        if today is not None:
            return today
        now = datetime.now(UTC).date()
        latest = self.latest_decision_date()
        if latest is None:
            return now
        return min(latest, now)

    def read(
        self,
        lookback_days: int = 14,
        today: date | None = None,
    ) -> list[Decision]:
        """Read all decisions across the last ``lookback_days`` days.

        The window is ``[window_end - lookback_days + 1, window_end]``
        inclusive, where ``window_end`` is ``today`` when given, otherwise
        the newest day present in the log (see :meth:`resolve_window_end`).
        """
        window_end = self.resolve_window_end(today)
        cutoff = window_end - timedelta(days=lookback_days - 1)
        out: list[Decision] = []
        if not self.base_dir.exists():
            return out
        for path in sorted(self.base_dir.glob("*.jsonl")):
            try:
                file_date = date.fromisoformat(path.stem)
            except ValueError:
                continue
            if file_date < cutoff or file_date > window_end:
                continue
            out.extend(self._read_file(path))
        return out

    @staticmethod
    def _read_file(path: Path) -> Iterable[Decision]:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                yield Decision(
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    action=str(data["action"]),
                    ueid=str(data["ueid"]),
                    context=dict(data.get("context") or {}),
                )
            except (KeyError, ValueError):
                continue


# ---------- Reflector ----------


class Reflector:
    """Analyse a Decision log and emit Findings.

    Thin orchestrator — pattern logic lives in patterns.py.
    """

    def __init__(self, store: DecisionStore | None = None) -> None:
        self.store = store or DecisionStore()

    def analyze(
        self,
        lookback_days: int = 14,
        today: date | None = None,
    ) -> list[Finding]:
        decisions = self.store.read(lookback_days=lookback_days, today=today)
        if not decisions:
            return []
        findings: list[Finding] = []
        findings.extend(detect_underestimation(decisions))
        findings.extend(detect_fast_finish(decisions))
        findings.extend(detect_priority_churn(decisions))
        return findings


# ---------- CLI entry ----------


def main(argv: list[str] | None = None) -> int:
    """Cron-friendly entry point.

    Usage:
        python -m src.agents.reflection.recursive [--lookback-days N] [--out PATH]
    """
    import argparse

    parser = argparse.ArgumentParser(description="Recursive reflection runner")
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=int(os.environ.get("REFLECT_LOOKBACK_DAYS", "14")),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional override for the reflection markdown path.",
    )
    parser.add_argument(
        "--today",
        type=date.fromisoformat,
        default=None,
        help=(
            "Anchor the lookback window on this YYYY-MM-DD date. "
            "Defaults to the newest day present in the decision log "
            "(or today, when the log is empty)."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit findings as JSON instead of writing markdown.",
    )
    args = parser.parse_args(argv)

    today = args.today
    if today is None and os.environ.get("REFLECT_TODAY"):
        today = date.fromisoformat(os.environ["REFLECT_TODAY"])

    reflector = Reflector()
    window_end = reflector.store.resolve_window_end(today)
    findings = reflector.analyze(lookback_days=args.lookback_days, today=window_end)

    if args.json:
        payload = {
            "lookback_days": args.lookback_days,
            "window_end": window_end.isoformat(),
            "findings": [asdict(f) for f in findings],
        }
        print(json.dumps(payload, default=str, indent=2))
        return 0

    target = write_reflection(
        findings,
        target=args.out,
        lookback_days=args.lookback_days,
        window_end=window_end,
    )
    print(f"wrote reflection: {target} ({len(findings)} findings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
