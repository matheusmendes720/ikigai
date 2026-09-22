"""M118 — baseline_archive.py

Weekly/historical archive of backtest baseline judgments.

Files live under reports/baselines/<YYYY-MM-DD>.json — one per calendar day
on which a full `bash scripts/backtest/run_backtest.sh` was run.

`archive_baseline(date_str, baseline_path)` — copies today's judgment into
the dated archive slot (no-op if it already exists for that day).

`list_baselines(since_days)` — returns sorted list of paths newer than N days.

`weekly_trend(since_days)` — groups baselines by ISO week and returns:
  - week_start (YYYY-MM-DD)
  - total_score_avg
  - tool_coverage_avg
  - anchor_pass_avg
  - scenario_pass_avg
  - n_runs_in_week

`trend_report(...)` — renders a markdown trend table for the report pipeline.

Honest scope:
  - The archive is per-host (each machine has its own baselines dir). This is
    fine for local-only environments; for shared CI we'd swap for S3/git-LFS.
  - No dedup across same-day runs (first one wins, rest are noise). Keeps the
    list of distinct "weekly snapshots" deterministic.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_BASELINES_DIR = REPO_ROOT / "reports" / "baselines"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _today_str() -> str:
    """Today as YYYY-MM-DD (local time)."""
    return dt.date.today().isoformat()


def archive_baseline(
    source: Path,
    baselines_dir: Path = DEFAULT_BASELINES_DIR,
    date_str: str | None = None,
) -> Path:
    """Copy `source` to baselines_dir/<date>.json. Returns the archive path.

    No-op if the date already exists — first run of the day wins.
    """
    return _archive_with_suffix(source, baselines_dir, date_str, suffix="")


def archive_llm_baseline(
    source: Path,
    baselines_dir: Path = DEFAULT_BASELINES_DIR,
    date_str: str | None = None,
) -> Path:
    """Copy `source` to baselines_dir/<date>.llm.json. First-wins same-day.

    Stored alongside the rule-based baseline but with `.llm.json` suffix so
    list_baselines() doesn't pick it up. M119: trend table reads both.
    """
    return _archive_with_suffix(source, baselines_dir, date_str, suffix=".llm")


def _archive_with_suffix(
    source: Path,
    baselines_dir: Path,
    date_str: str | None,
    suffix: str,
) -> Path:
    if date_str is None:
        date_str = _today_str()
    if not DATE_RE.match(date_str):
        raise ValueError(f"date_str must be YYYY-MM-DD, got {date_str!r}")
    baselines_dir.mkdir(parents=True, exist_ok=True)
    target = baselines_dir / f"{date_str}{suffix}.json"
    if target.exists():
        print(f"# Skipped (already archived): {target.name}")
        return target
    shutil.copy2(source, target)
    return target


def list_baselines(
    baselines_dir: Path = DEFAULT_BASELINES_DIR,
    since_days: int = 0,
) -> list[Path]:
    """Sorted list of baselines newer than `since_days` (0 = all-time sentinel)."""
    if not baselines_dir.exists():
        return []
    paths = sorted(p for p in baselines_dir.glob("*.json") if DATE_RE.match(p.stem))
    out: list[Path] = []
    for p in paths:
        if since_days == 0:
            out.append(p)  # 0 = sentinel for "all"
            continue
        d = dt.date.fromisoformat(p.stem)
        cutoff = dt.date.today() - dt.timedelta(days=since_days)
        if d >= cutoff:
            out.append(p)
    return out


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _score(j: dict[str, Any]) -> dict[str, float]:
    s = j.get("scores", {})
    return {
        "total_score": float(s.get("total_score", 0.0)),
        "tool_coverage": float(s.get("tool_coverage_pct", 0.0)),
        "anchor_pass": float(s.get("anchor_pass_rate_pct", 0.0)),
        "scenario_pass": float(s.get("scenario_pass_rate_pct", 0.0)),
    }


def _llm_score(j: dict[str, Any]) -> dict[str, float] | None:
    """Extract llm-judge aggregate from the M116 JSON shape.

    Returns None if the JSON doesn't have an aggregate (e.g. rule-based judgment).
    """
    agg = j.get("aggregate")
    if not isinstance(agg, dict):
        return None
    return {
        "llm_overall": round(float(agg.get("overall", 0.0)), 3),
        "llm_arg_quality": round(float(agg.get("argument_quality", 0.0)), 3),
        "llm_seq_coherence": round(float(agg.get("sequence_coherence", 0.0)), 3),
        "llm_cultural_fit": round(float(agg.get("cultural_fit", 0.0)), 3),
        "llm_tool_selection": round(float(agg.get("tool_selection", 0.0)), 3),
    }


def _llm_score_from_path(path: Path) -> dict[str, float] | None:
    """Load <DATE>.llm.json if present. Returns None on missing/invalid."""
    if not path.exists():
        return None
    try:
        return _llm_score(_load(path))
    except (json.JSONDecodeError, ValueError):
        return None


def weekly_trend(
    baselines_dir: Path = DEFAULT_BASELINES_DIR, since_days: int = 90
) -> list[dict[str, Any]]:
    """Group baselines by ISO week. Returns week_start, avg scores, n_runs.

    Most-recent week last. If a matching <date>.llm.json exists, also computes
    per-week llm_overall avg and includes it in the result.
    """
    by_week: dict[str, list[tuple[dt.date, dict[str, float], dict[str, float] | None]]] = (
        defaultdict(list)
    )
    for p in list_baselines(baselines_dir, since_days=since_days):
        d = dt.date.fromisoformat(p.stem)
        week_key = d.isocalendar()
        week_label = f"{week_key.year}-W{week_key.week:02d}"
        try:
            score = _score(_load(p))
        except (json.JSONDecodeError, ValueError):
            continue
        llm = _llm_score_from_path(baselines_dir / f"{p.stem}.llm.json")
        by_week[week_label].append((d, score, llm))

    weeks: list[dict[str, Any]] = []
    for label, runs in sorted(by_week.items()):
        # Earliest day's date for week_start label.
        runs.sort(key=lambda r: r[0])
        n = len(runs)
        avg = {
            "total_score": round(sum(s["total_score"] for _, s, _ in runs) / n, 2),
            "tool_coverage": round(sum(s["tool_coverage"] for _, s, _ in runs) / n, 2),
            "anchor_pass": round(sum(s["anchor_pass"] for _, s, _ in runs) / n, 2),
            "scenario_pass": round(sum(s["scenario_pass"] for _, s, _ in runs) / n, 2),
        }
        llm_runs = [l for _, _, l in runs if l is not None]
        if llm_runs:
            avg["llm_overall"] = round(sum(l["llm_overall"] for l in llm_runs) / len(llm_runs), 3)
            avg["llm_n_runs"] = len(llm_runs)
        else:
            avg["llm_overall"] = None  # marker: no llm data this week
            avg["llm_n_runs"] = 0
        weeks.append({
            "week_label": label,
            "week_start": runs[0][0].isoformat(),
            "n_runs": n,
            "avg": avg,
            "latest_run": runs[-1][0].isoformat(),
        })
    return weeks


def trend_report_markdown(
    weeks: list[dict[str, Any]],
    *,
    title: str = "Backtest weekly trend",
    include_llm: bool = True,
) -> str:
    """Render a markdown table from weekly_trend() output.

    If include_llm=True (default), add an `llm` column showing the per-week
    LLM-judge overall avg. Weeks without llm data show `—`.
    """
    out: list[str] = []
    out.append(f"# {title}\n")
    if not weeks:
        out.append("_No baselines in window._\n")
        return "\n".join(out)

    # Check whether ANY week has llm data; if not, omit the column.
    any_llm = include_llm and any(w["avg"].get("llm_overall") is not None for w in weeks)
    if any_llm:
        out.append("| Week | n_runs | total | anchor | tool | scenario | llm | latest_run |")
        out.append("|------|--------|-------|--------|------|----------|-----|------------|")
    else:
        out.append("| Week | n_runs | total | anchor | tool | scenario | latest_run |")
        out.append("|------|--------|-------|--------|------|----------|------------|")
    for w in weeks:
        a = w["avg"]
        if any_llm:
            llm_cell = "—" if a.get("llm_overall") is None else f"{a['llm_overall']:.3f}"
            out.append(
                f"| {w['week_label']} | {w['n_runs']} | {a['total_score']:.1f} | "
                f"{a['anchor_pass']:.1f} | {a['tool_coverage']:.1f} | "
                f"{a['scenario_pass']:.1f} | {llm_cell} | {w['latest_run']} |"
            )
        else:
            out.append(
                f"| {w['week_label']} | {w['n_runs']} | {a['total_score']:.1f} | "
                f"{a['anchor_pass']:.1f} | {a['tool_coverage']:.1f} | "
                f"{a['scenario_pass']:.1f} | {w['latest_run']} |"
            )
    # Per-week delta vs first week (total_score)
    if len(weeks) >= 2:
        first = weeks[0]["avg"]["total_score"]
        last = weeks[-1]["avg"]["total_score"]
        delta = round(last - first, 2)
        emoji = "📈" if delta > 0.5 else ("📉" if delta < -0.5 else "➡️")
        out.append(
            f"\n**Trend (rule-based):** {emoji} {delta:+.2f} "
            f"({weeks[0]['latest_run']} → {weeks[-1]['latest_run']})"
        )
    # LLM delta — only if at least 2 weeks have llm data
    if any_llm:
        llm_weeks = [w for w in weeks if w["avg"].get("llm_overall") is not None]
        if len(llm_weeks) >= 2:
            first = llm_weeks[0]["avg"]["llm_overall"]
            last = llm_weeks[-1]["avg"]["llm_overall"]
            delta = round(last - first, 3)
            emoji = "📈" if delta > 0.05 else ("📉" if delta < -0.05 else "➡️")
            out.append(
                f"\n**Trend (LLM-judge overall):** {emoji} {delta:+.3f} "
                f"({llm_weeks[0]['latest_run']} → {llm_weeks[-1]['latest_run']})"
            )
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Backtest baseline archive + weekly trend")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("archive", help="Archive today's judgment into baselines/<DATE>.json")
    a.add_argument("--source", type=Path, default=REPO_ROOT / "reports" / "backtest-Q1-judgment.json")
    a.add_argument("--baselines-dir", type=Path, default=DEFAULT_BASELINES_DIR)
    a.add_argument("--date", default=None)

    al = sub.add_parser(
        "archive-llm",
        help="Archive today's LLM-judge JSON into baselines/<DATE>.llm.json",
    )
    al.add_argument(
        "--source", type=Path,
        default=REPO_ROOT / "reports" / "backtest-Q1-llm-judgment.json",
    )
    al.add_argument("--baselines-dir", type=Path, default=DEFAULT_BASELINES_DIR)
    al.add_argument("--date", default=None)

    l = sub.add_parser("list", help="List baselines newer than N days")
    l.add_argument("--baselines-dir", type=Path, default=DEFAULT_BASELINES_DIR)
    l.add_argument("--since-days", type=int, default=0)

    t = sub.add_parser("weekly", help="Weekly trend (markdown)")
    t.add_argument("--baselines-dir", type=Path, default=DEFAULT_BASELINES_DIR)
    t.add_argument("--since-days", type=int, default=90)
    t.add_argument("--out", type=Path, default=REPO_ROOT / "reports" / "backtest-trend.md")

    args = p.parse_args(argv)

    if args.cmd == "archive":
        target = archive_baseline(args.source, args.baselines_dir, args.date)
        if target.exists():
            # already archived (first-wins); archive_baseline already printed skip
            pass
        else:
            print(f"# Archived {args.source.name} → {target}")
        return 0
    if args.cmd == "archive-llm":
        target = archive_llm_baseline(args.source, args.baselines_dir, args.date)
        # _archive_with_suffix prints skip if already there; print success only on new write.
        # We can detect "new write" by checking mtime vs source mtime, but simpler:
        # always print what we did (idempotent message).
        if target.exists() and target.stat().st_mtime == target.stat().st_mtime:
            pass  # archive_llm_baseline already printed; no extra noise
        return 0
    if args.cmd == "list":
        for path in list_baselines(args.baselines_dir, args.since_days):
            print(path)
        return 0
    if args.cmd == "weekly":
        weeks = weekly_trend(args.baselines_dir, args.since_days)
        md = trend_report_markdown(weeks)
        print(md)
        if not args.out.parent.exists():
            args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(f"\n# Wrote {args.out}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
