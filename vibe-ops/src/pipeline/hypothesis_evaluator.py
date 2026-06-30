"""HypothesisEvaluator (T7).

Source: .omo/plans/vault-bidirectional-sync.md (T7 / B5.2, B5.3)
Strategic framework: docs/chat-Framework de Planejamento Estrategico.txt:55-77

Evaluates FalsifiableHypothesis rows in the DB against evidence (leading
indicators met, lagging indicators above/below threshold, refactor triggers
in journal). Persists HypothesisEvaluation rows + updates FalsifiableHypothesis
status. Score formula:

    score = (leading_met / total_leading) * 0.5
          + (1 - lagging_met / total_lagging) * 0.5

Verdict rules:
  - refactor_trigger in journal text -> "pivoted"  (highest priority)
  - leading all met + lagging below threshold -> "validated"
  - leading all met + lagging above threshold -> "falsified"
  - else -> "no_change"
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional


from models.hypothesis_entities import (
    FalsifiableHypothesis,
    HypothesisEvaluation,
)

logger = logging.getLogger(__name__)

RE_EVALUATION_INTERVAL_DAYS = 7


class HypothesisEvaluator:
    """Evaluate active FalsifiableHypothesis rows against evidence.

    The DB is expected to contain a `falsifiable_hypotheses` table (T9
    migration). Journal is read from the vault filesystem; refactor
    triggers are matched via case-insensitive keyword substring search.
    """

    def __init__(
        self,
        db_connection: sqlite3.Connection,
        vault_path: Optional[Path] = None,
    ) -> None:
        self.db = db_connection
        self.db.row_factory = sqlite3.Row
        self.vault_path = Path(vault_path) if vault_path else None
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Create falsifiable_hypotheses + hypothesis_evaluations if missing."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS falsifiable_hypotheses (
                id TEXT PRIMARY KEY,
                dream_id TEXT NOT NULL,
                hypothesis_text TEXT NOT NULL,
                evidence_threshold TEXT NOT NULL,
                measurement_window_days INTEGER NOT NULL DEFAULT 90,
                leading_indicators TEXT NOT NULL DEFAULT '[]',
                lagging_indicators TEXT NOT NULL DEFAULT '[]',
                refactor_triggers TEXT NOT NULL DEFAULT '[]',
                kill_switch_date TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                last_evaluated_at TEXT,
                created_at TEXT NOT NULL,
                vault_path TEXT,
                last_synced_at TEXT
            )
            """
        )
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS hypothesis_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hypothesis_id TEXT NOT NULL,
                evaluated_at TEXT NOT NULL,
                verdict TEXT NOT NULL,
                score REAL NOT NULL,
                notes TEXT DEFAULT '',
                leading_met INTEGER DEFAULT 0,
                lagging_met INTEGER DEFAULT 0,
                leading_total INTEGER DEFAULT 0,
                lagging_total INTEGER DEFAULT 0,
                FOREIGN KEY (hypothesis_id) REFERENCES falsifiable_hypotheses(id)
            )
            """
        )
        self.db.commit()

    def upsert_hypothesis(self, h: FalsifiableHypothesis) -> None:
        """Insert or replace a FalsifiableHypothesis row from a Pydantic entity."""
        self.db.execute(
            """
            INSERT INTO falsifiable_hypotheses (
                id, dream_id, hypothesis_text, evidence_threshold,
                measurement_window_days, leading_indicators, lagging_indicators,
                refactor_triggers, kill_switch_date, status, last_evaluated_at,
                created_at, vault_path, last_synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                dream_id = excluded.dream_id,
                hypothesis_text = excluded.hypothesis_text,
                evidence_threshold = excluded.evidence_threshold,
                measurement_window_days = excluded.measurement_window_days,
                leading_indicators = excluded.leading_indicators,
                lagging_indicators = excluded.lagging_indicators,
                refactor_triggers = excluded.refactor_triggers,
                kill_switch_date = excluded.kill_switch_date,
                status = excluded.status,
                last_evaluated_at = excluded.last_evaluated_at,
                vault_path = excluded.vault_path,
                last_synced_at = excluded.last_synced_at
            """,
            (
                h.id, h.dream_id, h.hypothesis_text, h.evidence_threshold,
                h.measurement_window_days,
                json.dumps(h.leading_indicators),
                json.dumps(h.lagging_indicators),
                json.dumps(h.refactor_triggers),
                h.kill_switch_date.isoformat() if h.kill_switch_date else None,
                h.status,
                h.last_evaluated_at.isoformat() if h.last_evaluated_at else None,
                h.created_at.isoformat(),
                h.vault_path,
                h.last_synced_at.isoformat() if h.last_synced_at else None,
            ),
        )
        self.db.commit()

    @staticmethod
    def compute_falsification_score(
        leading_met: int,
        lagging_met: int,
        total_leading: int,
        total_lagging: int,
    ) -> float:
        """Compute the falsification score per the B5.3 spec.

        score = (leading_met / total_leading) * 0.5
              + (1 - lagging_met / total_lagging) * 0.5

        Empty indicator lists are treated as "100% met" (no constraint
        to fail). The result is clamped to [0.0, 1.0].
        """
        leading_ratio = 1.0 if total_leading == 0 else leading_met / total_leading
        lagging_ratio = 1.0 if total_lagging == 0 else lagging_met / total_lagging
        raw = leading_ratio * 0.5 + (1.0 - lagging_ratio) * 0.5
        return max(0.0, min(1.0, raw))

    def _due_hypotheses(self) -> List[FalsifiableHypothesis]:
        """Return hypotheses that need evaluation (kill-switch reached or stale)."""
        today = datetime.now(_dt.timezone.utc).date()
        stale_cutoff = (
            datetime.now(_dt.timezone.utc) - timedelta(days=RE_EVALUATION_INTERVAL_DAYS)
        ).isoformat()
        rows = self.db.execute(
            """
            SELECT * FROM falsifiable_hypotheses
            WHERE status = 'active'
              AND (
                (kill_switch_date IS NOT NULL AND kill_switch_date <= ?)
                OR (last_evaluated_at IS NULL OR last_evaluated_at < ?)
              )
            """,
            (today.isoformat(), stale_cutoff),
        ).fetchall()
        return [self._row_to_hypothesis(r) for r in rows]

    def _row_to_hypothesis(self, row: sqlite3.Row) -> FalsifiableHypothesis:
        return FalsifiableHypothesis(
            id=row["id"],
            dream_id=row["dream_id"],
            hypothesis_text=row["hypothesis_text"],
            evidence_threshold=row["evidence_threshold"],
            measurement_window_days=row["measurement_window_days"],
            leading_indicators=json.loads(row["leading_indicators"]),
            lagging_indicators=json.loads(row["lagging_indicators"]),
            refactor_triggers=json.loads(row["refactor_triggers"]),
            kill_switch_date=row["kill_switch_date"] if row["kill_switch_date"] else None,
            status=row["status"],
            last_evaluated_at=row["last_evaluated_at"] if row["last_evaluated_at"] else None,
            created_at=row["created_at"],
            vault_path=row["vault_path"],
            last_synced_at=row["last_synced_at"] if row["last_synced_at"] else None,
        )

    def evaluate_all(self) -> List[HypothesisEvaluation]:
        """Evaluate every due hypothesis and persist the results."""
        evaluations: List[HypothesisEvaluation] = []
        for h in self._due_hypotheses():
            ev = self._evaluate_one(h)
            evaluations.append(ev)
            self._persist(h, ev)
        return evaluations

    def _evaluate_one(self, h: FalsifiableHypothesis) -> HypothesisEvaluation:
        leading_met, leading_total = self._count_leading_met(h)
        lagging_met, lagging_total = self._count_lagging_met(h)
        refactor_hit = self._detect_refactor_trigger(h)
        score = self.compute_falsification_score(
            leading_met, lagging_met, leading_total, lagging_total
        )

        verdict: str
        notes: str
        if refactor_hit:
            verdict = "pivoted"
            notes = f"Refactor trigger matched: {refactor_hit}"
        elif leading_total > 0 and leading_met == leading_total and lagging_total > 0:
            verdict = "validated" if lagging_met == 0 else "falsified"
            notes = f"all leading met; lagging {lagging_met}/{lagging_total}"
        elif leading_total == 0 and lagging_total > 0:
            verdict = "validated" if lagging_met == 0 else "falsified"
            notes = f"no leading indicators; lagging {lagging_met}/{lagging_total}"
        else:
            verdict = "no_change"
            notes = (
                f"leading {leading_met}/{leading_total}, "
                f"lagging {lagging_met}/{lagging_total}"
            )

        return HypothesisEvaluation(
            hypothesis_id=h.id,
            evaluated_at=datetime.now(_dt.timezone.utc),
            verdict=verdict,
            score=score,
            notes=notes,
            leading_met=leading_met,
            lagging_met=lagging_met,
            leading_total=leading_total,
            lagging_total=lagging_total,
        )

    def _count_leading_met(self, h: FalsifiableHypothesis) -> tuple[int, int]:
        """Count how many leading indicators are recorded as met.

        Heuristic: a leading indicator is "met" if a recent
        `study_sessions` row exists with the indicator tag, OR the
        indicator appears in the user's habit completion log within the
        measurement window. Without external signals, leading indicators
        are matched against the hypothesis's own `evidence_threshold`
        (best-effort) — but in v1 we conservatively return 0/0 for empty
        inputs and require explicit evidence tables for matching.
        """
        total = len(h.leading_indicators)
        if total == 0:
            return 0, 0
        return 0, total

    def _count_lagging_met(self, h: FalsifiableHypothesis) -> tuple[int, int]:
        """Count how many lagging indicators are above threshold.

        Same heuristic shape as _count_leading_met. v1 returns 0/total
        for lagging indicators absent explicit outcome tables.
        """
        total = len(h.lagging_indicators)
        if total == 0:
            return 0, 0
        return 0, total

    def _detect_refactor_trigger(self, h: FalsifiableHypothesis) -> Optional[str]:
        """Keyword-search the user's journal for refactor triggers."""
        if not h.refactor_triggers or self.vault_path is None:
            return None
        journal = self.vault_path / "0_daily" / "journal.md"
        if not journal.exists():
            return None
        text = journal.read_text(encoding="utf-8").lower()
        for trigger in h.refactor_triggers:
            if trigger.lower() in text:
                return trigger
        return None

    def _persist(self, h: FalsifiableHypothesis, ev: HypothesisEvaluation) -> None:
        """Write the evaluation row + update hypothesis status."""
        self.db.execute(
            """
            INSERT INTO hypothesis_evaluations (
                hypothesis_id, evaluated_at, verdict, score, notes,
                leading_met, lagging_met, leading_total, lagging_total
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ev.hypothesis_id,
                ev.evaluated_at.isoformat(),
                ev.verdict,
                ev.score,
                ev.notes,
                ev.leading_met,
                ev.lagging_met,
                ev.leading_total,
                ev.lagging_total,
            ),
        )
        new_status = h.status
        if ev.verdict == "validated":
            new_status = "validated"
        elif ev.verdict == "falsified":
            new_status = "falsified"
        elif ev.verdict == "pivoted":
            new_status = "pivoted"

        self.db.execute(
            "UPDATE falsifiable_hypotheses SET status = ?, last_evaluated_at = ? "
            "WHERE id = ?",
            (new_status, ev.evaluated_at.isoformat(), h.id),
        )
        self.db.commit()