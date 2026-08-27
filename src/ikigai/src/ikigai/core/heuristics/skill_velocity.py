"""H5: Skill velocity — should_promote_skill + detect_stagnation."""

from __future__ import annotations

from ikigai.entities.skill import SkillLevel


LEVEL_ORDER = {
    SkillLevel.BEGINNER: 0,
    SkillLevel.INTERMEDIATE: 1,
    SkillLevel.ADVANCED: 2,
    SkillLevel.EXPERT: 3,
}


def should_promote_skill(
    current_level: SkillLevel,
    target_level: SkillLevel,
    hours_invested: float,
    target_hours: float,
    days_in_phase: int,
    retention_score_avg: float,
    days_threshold: int = 45,
    hours_pct_threshold: float = 0.80,
    retention_threshold: float = 0.75,
) -> bool:
    """Decide if a skill should be promoted to the next level.

    Args:
        current_level: current skill level.
        target_level: target level.
        hours_invested: total hours practiced.
        target_hours: hours needed for target level.
        days_in_phase: days in current phase.
        retention_score_avg: 0-1.
    """
    if LEVEL_ORDER[current_level] >= LEVEL_ORDER[target_level]:
        return False  # already at or beyond target

    if target_hours <= 0:
        hours_pct = 1.0
    else:
        hours_pct = hours_invested / target_hours

    return (
        hours_pct >= hours_pct_threshold
        and days_in_phase >= days_threshold
        and retention_score_avg >= retention_threshold
    )


def detect_stagnation(
    levels_promoted_last_180d: int,
    stagnation_threshold: float = 0.3,
) -> bool:
    """Detect stagnation: less than `stagnation_threshold` levels in 180 days.

    Per meta_heuristics.md §5.3: target >= 1 level per PHASE (180d).
    If < 0.3 levels in 6 months: stagnation.
    """
    return levels_promoted_last_180d < stagnation_threshold


__all__ = ["should_promote_skill", "detect_stagnation", "LEVEL_ORDER"]
