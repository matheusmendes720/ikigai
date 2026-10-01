"""reflection patterns — pattern detectors consumed by Reflector.

Three pattern families ship in v1:
  * underestimation_2x — actual took >2x estimated
  * fast_finish_tag_combo — tag set finishes within 24h with >=70% rate
  * priority_churn — priority bumped >=2x on the same ueid

Split out from recursive.py to keep both files under 500 lines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Finding:
    """One reflection finding.

    pattern — short slug ("underestimation_2x", "fast_finish_tag_combo")
    confidence — 0.0..1.0 — what fraction of the sample supports the pattern
    sample_size — number of decisions in the supporting set
    suggested_adjustment — human-readable, one paragraph
    detail — structured payload (extending keys look like {"tags": [...],"ratio":...})
    """

    pattern: str
    confidence: float
    sample_size: int
    suggested_adjustment: str
    detail: dict[str, Any] = field(default_factory=dict)


# Pattern-detection thresholds. Keep these as module-level constants so
# tests can pin exact behaviour without magic numbers.
UNDERESTIMATION_RATIO = 2.0
UNDERESTIMATION_MIN_SAMPLE = 3
FAST_FINISH_HOURS = 24.0
FAST_FINISH_MIN_SAMPLE = 3
FAST_FINISH_MIN_RATIO = 0.7  # 70% of decisions with this tag combo finish <24h


def detect_underestimation(decisions: list) -> list[Finding]:
    """Compare estimated vs actual duration per ueid.

    The agent provides ``context['estimated_minutes']`` on ``create``
    and ``context['actual_minutes']`` on ``done``. If the ratio of
    actual / estimated exceeds UNDERESTIMATION_RATIO for at least
    UNDERESTIMATION_MIN_SAMPLE ueids, surface a finding.
    """
    creates: dict[str, int] = {}
    dones: dict[str, int] = {}
    titles: dict[str, str] = {}
    for d in decisions:
        ctx = d.context
        if d.action == "create":
            est = ctx.get("estimated_minutes")
            if isinstance(est, (int, float)) and est > 0:
                creates[d.ueid] = int(est)
                title = ctx.get("title")
                if isinstance(title, str):
                    titles[d.ueid] = title
        elif d.action == "done":
            act = ctx.get("actual_minutes")
            if isinstance(act, (int, float)) and act > 0:
                dones[d.ueid] = int(act)
    offenders: list[tuple[str, int, int, float]] = []
    for ueid, est in creates.items():
        if ueid in dones:
            act = dones[ueid]
            ratio = act / est
            if ratio >= UNDERESTIMATION_RATIO:
                offenders.append((ueid, est, act, ratio))
    if len(offenders) < UNDERESTIMATION_MIN_SAMPLE:
        return []
    # confidence = fraction of decisions that hit the threshold
    confidence = min(1.0, len(offenders) / max(1, len(creates)))
    # suggested adjustment uses the average overrun
    avg_ratio = sum(r for _, _, _, r in offenders) / len(offenders)
    avg_est = sum(e for _, e, _, _ in offenders) / len(offenders)
    avg_act = sum(a for _, _, a, _ in offenders) / len(offenders)
    adjustment = (
        f"You underestimated by ~{avg_ratio:.1f}x across "
        f"{len(offenders)} task(s). Average estimate: {avg_est:.0f}min, "
        f"actual: {avg_act:.0f}min. Next time, multiply similar task "
        f"estimates by ~{avg_ratio:.1f}x or break them down."
    )
    detail = {
        "offenders": [
            {
                "ueid": ueid,
                "title": titles.get(ueid, ""),
                "estimated_minutes": est,
                "actual_minutes": act,
                "ratio": round(ratio, 2),
            }
            for ueid, est, act, ratio in offenders[:10]
        ],
        "avg_ratio": round(avg_ratio, 2),
        "total_decisions": len(creates),
    }
    return [
        Finding(
            pattern="underestimation_2x",
            confidence=round(confidence, 3),
            sample_size=len(offenders),
            suggested_adjustment=adjustment,
            detail=detail,
        )
    ]


def detect_fast_finish(decisions: list) -> list[Finding]:
    """Find tag combos where >=70% of tasks finish within 24h."""
    # Build per-ueid lifecycle
    per_ueid: dict[str, dict[str, Any]] = {}
    for d in decisions:
        ctx = d.context
        entry = per_ueid.setdefault(
            d.ueid, {"tags": set(), "create_ts": None, "done_ts": None}
        )
        if d.action == "create":
            tags = ctx.get("tags") or []
            if isinstance(tags, list):
                entry["tags"].update(t for t in tags if isinstance(t, str))
            entry["create_ts"] = d.timestamp
        elif d.action == "done":
            entry["done_ts"] = d.timestamp
    # Count outcomes per tag combo
    combo_total: dict[frozenset, int] = {}
    combo_fast: dict[frozenset, int] = {}
    for ueid, info in per_ueid.items():
        create = info["create_ts"]
        done = info["done_ts"]
        if not create or not done:
            continue
        tags = info["tags"]
        if not tags:
            continue
        key = frozenset(tags)
        combo_total[key] = combo_total.get(key, 0) + 1
        elapsed = (done - create).total_seconds() / 3600.0
        if elapsed <= FAST_FINISH_HOURS:
            combo_fast[key] = combo_fast.get(key, 0) + 1
    findings: list[Finding] = []
    for key, total in combo_total.items():
        if total < FAST_FINISH_MIN_SAMPLE:
            continue
        fast = combo_fast.get(key, 0)
        ratio = fast / total
        if ratio < FAST_FINISH_MIN_RATIO:
            continue
        confidence = ratio
        tag_sorted = sorted(key)
        adjustment = (
            f"Tag combo {tag_sorted!r} finishes in <24h with "
            f"{ratio:.0%} rate ({fast}/{total}). These are quick wins — "
            f"consider pairing them with longer tasks in the same sprint."
        )
        findings.append(
            Finding(
                pattern="fast_finish_tag_combo",
                confidence=round(confidence, 3),
                sample_size=total,
                suggested_adjustment=adjustment,
                detail={
                    "tags": tag_sorted,
                    "fast": fast,
                    "total": total,
                    "ratio": round(ratio, 3),
                },
            )
        )
    return findings


def detect_priority_churn(decisions: list) -> list[Finding]:
    """Flag ueids where priority was bumped >=2 times."""
    per_ueid: dict[str, list[int]] = {}
    for d in decisions:
        if d.action in ("update", "create"):
            p = d.context.get("priority")
            if isinstance(p, (int, float)):
                per_ueid.setdefault(d.ueid, []).append(int(p))
    churners = [(u, vals) for u, vals in per_ueid.items() if len(vals) >= 3]
    if len(churners) < 2:
        return []
    return [
        Finding(
            pattern="priority_churn",
            confidence=round(min(1.0, len(churners) / 10.0), 3),
            sample_size=len(churners),
            suggested_adjustment=(
                f"{len(churners)} task(s) had their priority changed >=2x "
                f"in the last window — these may have been mis-prioritised "
                f"at intake. Review the priority rubric."
            ),
            detail={"ueids": [u for u, _ in churners[:10]]},
        )
    ]


__all__ = [
    "Finding",
    "UNDERESTIMATION_RATIO",
    "UNDERESTIMATION_MIN_SAMPLE",
    "FAST_FINISH_HOURS",
    "FAST_FINISH_MIN_SAMPLE",
    "FAST_FINISH_MIN_RATIO",
    "detect_underestimation",
    "detect_fast_finish",
    "detect_priority_churn",
]