"""IkigaiScorer — DB readers preserved; compute_score() archived per attribution §3.

Canonical modules (PRD-07 / ADR-002) — NOT IMPORTED here anymore:
  - ikigai.core.scoring.vector_scores: compute_vector_scores(passion, skill, market, revenue, course)
  - ikigai.core.scoring.qhe: compute_qhe(h_sono, h_med, h_workout, h_lunch, s_streak)

Per attribution §3, IKIGAI agent / CLI / orchestrator layers must NOT execute
algo math. The ``compute_score`` method is archived-in-place — DB reader
helpers remain callable (pure I/O, no algo math) but the algo entry point
raises NotImplementedError. Callers that need the canonical implementation
should import directly from ``ikigai.core.scoring.vector_scores``.

Vibe-ops DB schema (read-only):
  study_sessions(date, duration_minutes, subject, notes)
  habit_states(date, habit_id, executed, streak_current, streak_broken)
  metrics(date, qhe, energy, sleep_hours)
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any

from ikigai.enums import VectorType


# Canonical vector names (strings — for dict key conversion)
_VECTORS_IKIGAI = [v.value for v in VectorType]


def _db_connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _read_streak(db_path: str) -> float:
    """Read longest current streak from habit_states."""
    conn = _db_connect(db_path)
    try:
        cursor = conn.cursor()
        # Most recent habit with executed=1, not broken
        cursor.execute("""
            SELECT MAX(streak_current) as streak
            FROM habit_states
            WHERE streak_broken = 0 AND executed = 1
        """)
        row = cursor.fetchone()
        return float(row["streak"]) if row and row["streak"] is not None else 0.0
    finally:
        conn.close()


def _read_skill_inputs(db_path: str) -> tuple[list[float], list[float], float, float]:
    """Read skill inputs from study_sessions.

    Returns (skill_level_scores, market_demand_weights, learning_momentum, project_completion).
    learning_momentum = sessions in last 30d / target (14 sessions/month → ~0.5 at target).
    project_completion = sessions with 'project' in notes or subject.
    """
    conn = _db_connect(db_path)
    try:
        cursor = conn.cursor()
        cutoff = (date.today() - timedelta(days=30)).isoformat()

        # Count sessions last 30d
        cursor.execute(
            "SELECT COUNT(*) FROM study_sessions WHERE date >= ?",
            (cutoff,)
        )
        session_count = cursor.fetchone()[0]

        # Sum duration as proxy for engagement level
        cursor.execute(
            "SELECT COALESCE(SUM(duration_minutes), 0) FROM study_sessions WHERE date >= ?",
            (cutoff,)
        )
        total_minutes = cursor.fetchone()[0]

        # Project-related sessions (proxy for project completion)
        cursor.execute(
            "SELECT COUNT(*) FROM study_sessions WHERE date >= ? AND (subject LIKE '%project%' OR notes LIKE '%project%')",
            (cutoff,)
        )
        project_sessions = cursor.fetchone()[0]

        # skill_level_scores: use duration-based engagement (0-100)
        # market_demand_weights: assume 70 for all (medium-high demand)
        learning_momentum = min(session_count / 14.0, 1.0) * 100.0  # target ~14/month
        engagement = min(total_minutes / (30 * 60), 1.0) * 100.0  # 30h/month target
        project_completion = (project_sessions / max(session_count, 1)) * 100.0

        # Fake level scores from engagement — real impl would read skill_nodes table
        skill_levels = [engagement]
        demand_weights = [70.0]

        return skill_levels, demand_weights, learning_momentum, project_completion
    finally:
        conn.close()


def _read_market_inputs(db_path: str) -> tuple[float, float, float]:
    """Read market inputs. Placeholder — returns 50s until market data exists."""
    return (50.0, 50.0, 0.0)  # fit_avg, skills_demand_avg, opportunities_pipeline


def _read_revenue_inputs(db_path: str) -> tuple[float, float, float]:
    """Read revenue inputs. Placeholder — returns 0 until revenue data exists."""
    return (0.0, 1.0, 0.0)  # revenue_actual, revenue_target, pipeline_health


def _read_course_inputs(db_path: str) -> tuple[float, float, float]:
    """Read course inputs. Placeholder — returns 50s until course data exists."""
    return (100.0, 50.0, 0.0)  # attendance_rate, assignments_on_time, exam_avg


class IkigaiScorer:
    """Computes IKIGAI vector scores from vibe-ops DB.

    Wraps ikigai.core.scoring.vector_scores.compute_vector_scores.
    Returns dict compatible with the old {study, dev, health, global} keys
    PLUS the canonical 5-vector breakdown.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def compute_score(self) -> dict[str, Any]:
        """Main entry point — ARCHIVED per attribution §3.

        Vector-score math (geometric mean across 5 vectors, legacy 0-1 scaling)
        is the algorithm layer's responsibility, not the orchestrator /
        agent layer's. DB reader helpers below are pure I/O and remain
        callable; only the algo composition path raises.

        Callers that need the canonical implementation should import
        directly from ``ikigai.core.scoring.vector_scores``:
            compute_vector_scores(passion_streak_days=..., skill_inputs=..., ...)
        """
        raise NotImplementedError(
            "IkigaiScorer.compute_score math archived per attribution §3 — "
            "see ikigai.core.scoring.vector_scores for the canonical "
            "compute_vector_scores implementation. DB reader helpers "
            "(_read_streak, _read_skill_inputs, etc.) remain available."
        )

    def _read_qhe_avg(self) -> float:
        """Read Q_HE average from metrics table (0-1 scale)."""
        conn = _db_connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT AVG(qhe) FROM metrics WHERE date >= date('now', '-7 days')"
            )
            row = cursor.fetchone()
            return float(row[0]) if row and row[0] is not None else 0.0
        finally:
            conn.close()


def _count_study_sessions(db_path: str) -> int:
    conn = _db_connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM study_sessions WHERE date >= date('now', '-7 days')"
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()
