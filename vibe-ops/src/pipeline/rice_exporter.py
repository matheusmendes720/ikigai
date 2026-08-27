"""RICE scoring + priority ranking.

Source: .omo/plans/vault-bidirectional-sync.md (T5)

Pure arithmetic — no LLM, no I/O, fully unit-testable.

RICE = (Reach × Impact × Confidence) / Effort

Edge cases:
  - effort_h == 0  → guard with max(effort_h, 0.1) to avoid div-by-zero
  - negative values -> clamped to 0 (RICE components are non-negative by spec)
  - empty list    -> returns {} (no ranks to assign)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, runtime_checkable


@runtime_checkable
class _RiceProtocol(Protocol):
    """Any object with these attributes can be RICE-ranked."""
    reach: float
    impact: float
    confidence: float
    effort_h: float


@dataclass
class RiceInput:
    """Concrete RICE input - convenient wrapper for dict payloads."""
    id: str
    reach: float
    impact: float
    confidence: float
    effort_h: float


def compute_rice_score(
    reach: float,
    impact: float,
    confidence: float,
    effort_h: float,
) -> float:
    """Return the RICE score for the four given components.

    Components are clamped to non-negative. Effort is clamped at 0.1
    to avoid div-by-zero.
    """
    r = max(0.0, float(reach))
    i = max(0.0, float(impact))
    c = max(0.0, float(confidence))
    e = max(0.1, float(effort_h))
    return (r * i * c) / e


def compute_priority_rank(tasks: List[Any]) -> Dict[str, int]:
    """Sort tasks by RICE descending; assign dense rank 1..N by `id` attr.

    Ties: equal RICE scores receive equal rank, then next integer skips
    forward (1, 1, 2 ...). This is "dense ranking" - gap-free.

    Each task must expose `.id`, `.reach`, `.impact`, `.confidence`, `.effort_h`.
    Accepts dicts with matching keys.
    """
    if not tasks:
        return {}

    def _extract(task: Any) -> tuple[str, float]:
        if isinstance(task, dict):
            tid = str(task["id"])
            score = compute_rice_score(
                task.get("reach", 0.0),
                task.get("impact", 0.0),
                task.get("confidence", 0.0),
                task.get("effort_h", 0.0),
            )
        else:
            tid = str(getattr(task, "id"))
            score = compute_rice_score(
                getattr(task, "reach", 0.0),
                getattr(task, "impact", 0.0),
                getattr(task, "confidence", 0.0),
                getattr(task, "effort_h", 0.0),
            )
        return tid, score

    scored = [_extract(t) for t in tasks]
    # Sort by score desc, then by id asc for deterministic ties.
    scored.sort(key=lambda x: (-x[1], x[0]))

    ranks: Dict[str, int] = {}
    current_rank = 0
    prev_score = None
    for tid, score in scored:
        if prev_score is None or score < prev_score:
            current_rank += 1
            prev_score = score
        ranks[tid] = current_rank
    return ranks