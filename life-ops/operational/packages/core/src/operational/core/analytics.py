"""PAV Analytics Engine — pure arithmetic analytics on 180-day CSV dataset.

No LLM, no I/O in the core functions. All statistics are computed directly
from the loaded CSV rows.

Usage:
    from operational.core.analytics import load_dataset, weekly_trend, regime_timeline
    data = load_dataset(Path("datasets/6month/csv"))
    trend = weekly_trend(data, metric="qhe")
"""
from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

# ── Types ───────────────────────────────────────────────────────────────────────

Scalar = float | int | bool
Series = list[Scalar]
Dates = list[date]

# ── CSV row types (dict-of-dict, keyed by entity) ──────────────────────────────

DayRow = dict[str, Any]
QHERow = dict[str, Any]
SleepRow = dict[str, Any]
PolicyRow = dict[str, Any]
HabitStateRow = dict[str, Any]
DayContextRow = dict[str, Any]
JournalRow = dict[str, Any]
PomodoroRow = dict[str, Any]
HabitRow = dict[str, Any]
RoutineLogRow = dict[str, Any]
RoutineRow = dict[str, Any]
TimeBlockRow = dict[str, Any]
DailyReflectionRow = dict[str, Any]
LunchRow = dict[str, Any]
AjusteRow = dict[str, Any]
TransicaoRow = dict[str, Any]

Dataset = dict[str, list[dict[str, Any]]]


# ── Loading ──────────────────────────────────────────────────────────────────────

def load_dataset(csv_dir: Path | str) -> Dataset:
    """Load all 15 CSV entity files from a directory.

    Returns a dict keyed by entity name, each value is a list of dicts
    with the original CSV columns.
    """
    base = Path(csv_dir).resolve()
    files = {
        "qhe_metrics": "qhe_metrics.csv",
        "sleep_record": "sleep_record.csv",
        "policy_decision": "policy_decision.csv",
        "habit_state": "habit_state.csv",
        "day_context": "day_context.csv",
        "journal_entry": "journal_entry.csv",
        "pomodoro_round": "pomodoro_round.csv",
        "habit": "habit.csv",
        "routine_log": "routine_log.csv",
        "routine": "routine.csv",
        "time_block": "time_block.csv",
        "daily_reflection": "daily_reflection.csv",
        "lunch_record": "lunch_record.csv",
        "ajuste_fino": "ajuste_fino.csv",
        "transicao": "transicao.csv",
    }
    out: Dataset = {}
    for entity, fname in files.items():
        fpath = base / fname
        if fpath.exists():
            with fpath.open(newline="", encoding="utf-8") as fp:
                out[entity] = list(csv.DictReader(fp))
        else:
            out[entity] = []
    return out


def date_col(rows: list[dict[str, Any]], col: str = "date") -> Dates:
    """Extract sorted date list from a row list."""
    raw = sorted(set(r[col] for r in rows if r.get(col)))
    return [date.fromisoformat(d) for d in raw]


def numeric(rows: list[dict[str, Any]], key: str) -> Series:
    """Extract numeric values, returning 0.0 for missing/bad entries."""
    out: Series = []
    for r in rows:
        try:
            v = r.get(key, "")
            if v == "" or v is None:
                out.append(0.0)
            else:
                out.append(float(v))
        except (ValueError, TypeError):
            out.append(0.0)
    return out


def float_col(rows: list[dict[str, Any]], date_key: str, val_key: str) -> tuple[Dates, Series]:
    """Return (dates, values) sorted by date for a numeric column."""
    pairs = [(date.fromisoformat(r[date_key]), float(r.get(val_key, 0) or 0))
             for r in rows if r.get(date_key)]
    pairs.sort(key=lambda x: x[0])
    return [p[0] for p in pairs], [p[1] for p in pairs]


# ── TimeSeriesSlice ─────────────────────────────────────────────────────────────

@dataclass
class TimeSeriesSlice:
    """A time-windowed view of a scalar time series."""
    dates: Dates
    values: Series
    label: str = ""

    def __post_init__(self):
        if not self.dates:
            self.dates, self.values = [], []

    @classmethod
    def from_rows(
        cls,
        rows: list[dict[str, Any]],
        date_key: str = "date",
        val_key: str = "value",
        label: str = "",
    ) -> TimeSeriesSlice:
        d, v = float_col(rows, date_key, val_key)
        return cls(dates=d, values=v, label=label)

    def window(self, start: date, end: date) -> TimeSeriesSlice:
        """Return a new slice covering [start, end]."""
        pairs = [(d, v) for d, v in zip(self.dates, self.values) if start <= d <= end]
        if not pairs:
            return TimeSeriesSlice(dates=[], values=[], label=self.label)
        return TimeSeriesSlice(
            dates=[p[0] for p in pairs],
            values=[p[1] for p in pairs],
            label=self.label,
        )

    def last_n(self, n: int) -> TimeSeriesSlice:
        """Return the last n points."""
        if n >= len(self.values):
            return self
        return TimeSeriesSlice(
            dates=self.dates[-n:],
            values=self.values[-n:],
            label=self.label,
        )

    def rolling(self, window: int) -> Series:
        """Simple moving average (centered where possible)."""
        if len(self.values) < window:
            return []
        out: Series = []
        for i in range(len(self.values) - window + 1):
            chunk = self.values[i : i + window]
            out.append(sum(chunk) / window)
        return out

    def diff(self) -> Series:
        """First difference (delta between consecutive points)."""
        if len(self.values) < 2:
            return []
        return [self.values[i] - self.values[i - 1] for i in range(1, len(self.values))]

    def pct_change(self) -> Series:
        """Percentage change (returns 0.0 where division would be zero)."""
        if len(self.values) < 2:
            return []
        out: Series = []
        for i in range(1, len(self.values)):
            prev = self.values[i - 1]
            if prev == 0:
                out.append(0.0)
            else:
                out.append((self.values[i] - prev) / abs(prev) * 100)
        return out

    def trend_direction(self) -> int:
        """Linear regression slope sign: 1 = up, -1 = down, 0 = flat."""
        slope = _linear_slope(self.values)
        if slope > 0.001:
            return 1
        elif slope < -0.001:
            return -1
        return 0

    def mean(self) -> float:
        return statistics.mean(self.values) if self.values else 0.0

    def stdev(self) -> float:
        return statistics.stdev(self.values) if len(self.values) > 1 else 0.0

    def min(self) -> float:
        return min(self.values) if self.values else 0.0

    def max(self) -> float:
        return max(self.values) if self.values else 0.0

    def median(self) -> float:
        return statistics.median(self.values) if self.values else 0.0


# ── Internal helpers ───────────────────────────────────────────────────────────

def _linear_slope(values: Series) -> float:
    """Ordinary least-squares slope for a uniformly-sampled series."""
    n = len(values)
    if n < 2:
        return 0.0
    t = list(range(n))
    t_mean = sum(t) / n
    v_mean = sum(values) / n
    num = sum((t[i] - t_mean) * (values[i] - v_mean) for i in range(n))
    den = sum((t[i] - t_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    return num / den


def _pearson(xs: Series, ys: Series) -> float:
    """Pearson correlation coefficient. Returns 0.0 if stdev is zero."""
    n = len(xs)
    if n != len(ys) or n < 3:
        return 0.0
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    sx = statistics.stdev(xs) if n > 1 else 0.0
    sy = statistics.stdev(ys) if n > 1 else 0.0
    if sx == 0 or sy == 0:
        return 0.0
    cov = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / n
    return cov / (sx * sy)


def _week_index(d: date, start: date) -> int:
    """Zero-based week index from a start date."""
    delta = (d - start).days
    return delta // 7 if delta >= 0 else -1


# ── Aggregations ──────────────────────────────────────────────────────────────

@dataclass
class Aggregations:
    """Pre-computed summary statistics for a dataset window."""
    n_days: int
    # QHE
    qhe_mean: float
    qhe_std: float
    qhe_min: float
    qhe_max: float
    qhe_trend: int  # -1 / 0 / +1
    # Sleep
    sleep_mean: float
    sleep_std: float
    sleep_trend: int
    # Energy
    energia_mean: float
    energia_std: float
    # Foco
    foco_mean: float
    foco_std: float
    # Pomodoros
    pomodoros_mean: float
    pomodoros_total: float
    # Habits
    habit_completion_rate: float
    streak_avg: float
    # Hardwork
    hardwork_budget_mean: float
    hardwork_actual_mean: float
    hardwork_adherence_pct: float
    # Regime
    regime_distribution: dict[str, int]
    regime_dominant: str
    # Scenario
    scenario_distribution: dict[str, int]
    scenario_dominant: str


def compute_aggregations(ds: Dataset) -> Aggregations:
    """Compute Aggregations from a full dataset (all 180 days)."""
    qhe_rows = ds.get("qhe_metrics", [])
    sleep_rows = ds.get("sleep_record", [])
    policy_rows = ds.get("policy_decision", [])
    context_rows = ds.get("day_context", [])
    habit_state_rows = ds.get("habit_state", [])
    pom_rows = ds.get("pomodoro_round", [])
    ajuste_rows = ds.get("ajuste_fino", [])

    # QHE
    qhe_vals = numeric(qhe_rows, "qhe")
    qhe_slice = TimeSeriesSlice(dates=date_col(qhe_rows), values=qhe_vals)

    # Sleep
    sleep_vals = numeric(sleep_rows, "sleep_hours")
    sleep_slice = TimeSeriesSlice(dates=date_col(sleep_rows), values=sleep_vals)

    # Day context — energia/foco from context or fallback to QHE
    energia_vals = numeric(context_rows, "energia")
    foco_vals = numeric(context_rows, "foco")
    if not energia_vals:
        energia_vals = numeric(qhe_rows, "energy_ratio")
    if not foco_vals:
        foco_vals = numeric(qhe_rows, "habit_avg")

    # Pomodoros per day
    pom_per_day: dict[str, float] = {}
    for r in pom_rows:
        d = r.get("date", "")
        try:
            pom_per_day[d] = pom_per_day.get(d, 0) + 1
        except (ValueError, TypeError):
            pass
    pom_vals = [pom_per_day.get(str(d), 0.0) for d in date_col(pom_rows)]
    pom_total = sum(pom_vals)

    # Habit completion rate
    completed = sum(1 for r in habit_state_rows if str(r.get("completed", "")).lower() in ("true", "1", "yes"))
    total = len(habit_state_rows)
    habit_rate = completed / total if total > 0 else 0.0
    streaks = numeric(habit_state_rows, "streak_current")
    streak_avg = statistics.mean(streaks) if streaks else 0.0

    # Hardwork adherence
    budget = numeric(context_rows, "hardwork_orcado_min")
    actual = numeric(context_rows, "hardwork_realizado_min")
    adherence_vals = []
    for b, a in zip(budget, actual):
        if b > 0:
            adherence_vals.append(min(a / b, 1.0))
    hardwork_adh = statistics.mean(adherence_vals) * 100 if adherence_vals else 0.0

    # Regime distribution
    regime_dist: dict[str, int] = {}
    for r in policy_rows:
        s = r.get("state", "")
        regime_dist[s] = regime_dist.get(s, 0) + 1

    # Scenario from ajuste_fino or day_context
    scenario_dist: dict[str, int] = {}
    for r in ajuste_rows:
        s = r.get("cenario", r.get("scenario", ""))
        if s:
            scenario_dist[s] = scenario_dist.get(s, 0) + 1
    if not scenario_dist:
        # Fall back to tipo_dia
        for r in context_rows:
            s = r.get("tipo_dia", "")
            scenario_dist[s] = scenario_dist.get(s, 0) + 1

    regime_dom = max(regime_dist, key=regime_dist.get) if regime_dist else ""
    scenario_dom = max(scenario_dist, key=scenario_dist.get) if scenario_dist else ""

    return Aggregations(
        n_days=len(qhe_vals) or 1,
        qhe_mean=qhe_slice.mean(),
        qhe_std=qhe_slice.stdev(),
        qhe_min=qhe_slice.min(),
        qhe_max=qhe_slice.max(),
        qhe_trend=qhe_slice.trend_direction(),
        sleep_mean=sleep_slice.mean(),
        sleep_std=sleep_slice.stdev(),
        sleep_trend=sleep_slice.trend_direction(),
        energia_mean=statistics.mean(energia_vals) if energia_vals else 0.0,
        energia_std=statistics.stdev(energia_vals) if len(energia_vals) > 1 else 0.0,
        foco_mean=statistics.mean(foco_vals) if foco_vals else 0.0,
        foco_std=statistics.stdev(foco_vals) if len(foco_vals) > 1 else 0.0,
        pomodoros_mean=statistics.mean(pom_vals) if pom_vals else 0.0,
        pomodoros_total=pom_total,
        habit_completion_rate=habit_rate,
        streak_avg=streak_avg,
        hardwork_budget_mean=statistics.mean(budget) if budget else 0.0,
        hardwork_actual_mean=statistics.mean(actual) if actual else 0.0,
        hardwork_adherence_pct=hardwork_adh,
        regime_distribution=regime_dist,
        regime_dominant=regime_dom,
        scenario_distribution=scenario_dist,
        scenario_dominant=scenario_dom,
    )


# ── Weekly Trend ──────────────────────────────────────────────────────────────

@dataclass
class WeeklyTrend:
    """Weekly aggregated trajectory for one metric."""
    week: int
    week_start: date
    week_end: date
    values: Series
    mean: float
    std: float
    min_val: float
    max_val: float
    trend: int  # +1 / 0 / -1  (slope sign within the week)


def weekly_trend(ds: Dataset, metric: str = "qhe") -> list[WeeklyTrend]:
    """Group a numeric metric into weekly buckets (Mon→Sun)."""
    # Map metric name → entity + column
    _METRIC_MAP: dict[str, tuple[str, str]] = {
        "qhe": ("qhe_metrics", "qhe"),
        "habit_avg": ("qhe_metrics", "habit_avg"),
        "consistency": ("qhe_metrics", "consistency"),
        "energy_ratio": ("qhe_metrics", "energy_ratio"),
        "sleep_hours": ("sleep_record", "sleep_hours"),
        "sleep_quality": ("sleep_record", "quality_score"),
        "energia": ("day_context", "energia"),
        "foco": ("day_context", "foco"),
        "pomodoros_realizados": ("day_context", "pomodoros_realizados"),
        "hardwork_actual": ("day_context", "hardwork_realizado_min"),
        "hardwork_budget": ("day_context", "hardwork_orcado_min"),
    }

    entity, val_key = _METRIC_MAP.get(metric, ("qhe_metrics", metric))
    rows = ds.get(entity, [])

    if not rows:
        return []

    pairs = []
    for r in rows:
        try:
            d = date.fromisoformat(r["date"])
            v = float(r.get(val_key, 0) or 0)
            pairs.append((d, v))
        except (ValueError, KeyError):
            pass

    if not pairs:
        return []

    pairs.sort(key=lambda x: x[0])
    start_date = pairs[0][0]

    # Group by week
    weeks: dict[int, list[float]] = {}
    for d, v in pairs:
        w = _week_index(d, start_date)
        if w >= 0:
            weeks.setdefault(w, []).append(v)

    out = []
    for w in sorted(weeks.keys()):
        vals = weeks[w]
        if not vals:
            continue
        # Week boundaries: day start + w*7 through day start + (w+1)*7 - 1
        w_start = start_date + timedelta(weeks=w)
        w_end = w_start + timedelta(days=6)
        week_slice = TimeSeriesSlice(dates=[w_start] * len(vals), values=vals)
        out.append(WeeklyTrend(
            week=w,
            week_start=w_start,
            week_end=w_end,
            values=vals,
            mean=statistics.mean(vals),
            std=statistics.stdev(vals) if len(vals) > 1 else 0.0,
            min_val=min(vals),
            max_val=max(vals),
            trend=week_slice.trend_direction(),
        ))

    return out


# ── Trajectory ─────────────────────────────────────────────────────────────────

@dataclass
class TrajectorySegment:
    """One contiguous segment of the trajectory (flat/rising/falling)."""
    start: date
    end: date
    direction: int  # +1 rising, 0 flat, -1 falling
    start_val: float
    end_val: float
    delta: float
    days: int


@dataclass
class Trajectory:
    """Full trajectory analysis for a metric."""
    metric: str
    full_series: TimeSeriesSlice
    overall_slope: float
    overall_direction: int
    segments: list[TrajectorySegment]


def build_trajectory(ds: Dataset, metric: str = "qhe") -> Trajectory:
    """Detect rising/falling/flat segments using rolling OLS slope."""
    weekly = weekly_trend(ds, metric)
    if not weekly:
        return Trajectory(
            metric=metric,
            full_series=TimeSeriesSlice(dates=[], values=[]),
            overall_slope=0.0,
            overall_direction=0,
            segments=[],
        )

    week_means = [(w.week_start, w.mean) for w in weekly]
    dates = [d for d, _ in week_means]
    vals = [v for _, v in week_means]
    series = TimeSeriesSlice(dates=dates, values=vals)
    slope = _linear_slope(vals)

    segments: list[TrajectorySegment] = []
    if len(week_means) >= 2:
        i = 0
        while i < len(week_means) - 1:
            seg_start = week_means[i][0]
            seg_dir = 0
            seg_vals = [week_means[i][1]]
            j = i + 1
            while j < len(week_means):
                w = weekly[j]
                chunk = TimeSeriesSlice(dates=[w.week_start], values=[w.mean])
                direction = chunk.trend_direction()
                if seg_dir == 0:
                    seg_dir = direction
                    seg_vals.append(w.mean)
                elif direction == seg_dir or direction == 0:
                    seg_vals.append(w.mean)
                else:
                    break
                j += 1
            if len(seg_vals) >= 1:
                segments.append(TrajectorySegment(
                    start=seg_start,
                    end=week_means[j - 1][0],
                    direction=seg_dir,
                    start_val=seg_vals[0],
                    end_val=seg_vals[-1],
                    delta=seg_vals[-1] - seg_vals[0],
                    days=(j - i) * 7,
                ))
            i = max(j, i + 1)

    return Trajectory(
        metric=metric,
        full_series=series,
        overall_slope=slope,
        overall_direction=series.trend_direction(),
        segments=segments,
    )


# ── Correlation Matrix ────────────────────────────────────────────────────────

@dataclass
class CorrelationPair:
    metric_a: str
    metric_b: str
    r: float  # Pearson r
    strength: str  # "strong_pos" / "moderate_pos" / "weak" / "moderate_neg" / "strong_neg"


def correlation_matrix(ds: Dataset, metrics: list[str] | None = None) -> list[CorrelationPair]:
    """Compute pairwise Pearson correlations for all numeric metrics."""
    if metrics is None:
        metrics = [
            "qhe", "habit_avg", "consistency", "energy_ratio",
            "sleep_hours", "sleep_quality", "energia", "foco",
            "pomodoros_realizados", "hardwork_realizado_min",
        ]

    # Build aligned series per metric
    _METRIC_MAP: dict[str, tuple[str, str]] = {
        "qhe": ("qhe_metrics", "qhe"),
        "habit_avg": ("qhe_metrics", "habit_avg"),
        "consistency": ("qhe_metrics", "consistency"),
        "energy_ratio": ("qhe_metrics", "energy_ratio"),
        "sleep_hours": ("sleep_record", "sleep_hours"),
        "sleep_quality": ("sleep_record", "quality_score"),
        "energia": ("day_context", "energia"),
        "foco": ("day_context", "foco"),
        "pomodoros_realizados": ("day_context", "pomodoros_realizados"),
        "hardwork_realizado_min": ("day_context", "hardwork_realizado_min"),
    }

    # Collect (date, value) pairs per metric, aligned by date
    series_by_metric: dict[str, list[tuple[date, float]]] = {}
    for m in metrics:
        if m not in _METRIC_MAP:
            continue
        entity, col = _METRIC_MAP[m]
        rows = ds.get(entity, [])
        pairs = []
        for r in rows:
            try:
                d = date.fromisoformat(r["date"])
                v = float(r.get(col, 0) or 0)
                pairs.append((d, v))
            except (ValueError, KeyError):
                pass
        pairs.sort()
        series_by_metric[m] = pairs

    # Build date → index map
    all_dates = sorted(set(d for pairs in series_by_metric.values() for d, _ in pairs))
    min_len = 3

    out = []
    metric_list = list(series_by_metric.keys())
    for i, ma in enumerate(metric_list):
        for mb in metric_list[i + 1:]:
            pa = series_by_metric[ma]
            pb = series_by_metric[mb]
            # Align
            common_dates = sorted(set(d for d, _ in pa) & set(d for d, _ in pb))
            if len(common_dates) < min_len:
                continue
            xa = [v for d, v in pa if d in common_dates]
            xb = [v for d, v in pb if d in common_dates]
            r = _pearson(xa, xb)
            abs_r = abs(r)
            if abs_r >= 0.7:
                strength = "strong_pos" if r > 0 else "strong_neg"
            elif abs_r >= 0.4:
                strength = "moderate_pos" if r > 0 else "moderate_neg"
            else:
                strength = "weak"
            out.append(CorrelationPair(metric_a=ma, metric_b=mb, r=r, strength=strength))

    # Sort by absolute correlation descending
    out.sort(key=lambda x: abs(x.r), reverse=True)
    return out


# ── Scenario Analyzer ───────────────────────────────────────────────────────────

@dataclass
class ScenarioStats:
    name: str
    days: int
    pct: float
    qhe_avg: float
    sleep_avg: float
    energia_avg: float
    pomodoros_avg: float
    hardwork_adh: float


def scenario_analysis(ds: Dataset) -> list[ScenarioStats]:
    """Per-scenario aggregated statistics."""
    ctx_rows = ds.get("day_context", [])
    qhe_rows = ds.get("qhe_metrics", [])
    sleep_rows = ds.get("sleep_record", [])
    pom_rows = ds.get("pomodoro_round", [])

    # Group by tipo_dia
    by_scenario: dict[str, list[dict[str, Any]]] = {}
    for r in ctx_rows:
        s = r.get("tipo_dia", "UNKNOWN")
        by_scenario.setdefault(s, []).append(r)

    # QHE by date
    qhe_by_date: dict[str, float] = {}
    for r in qhe_rows:
        qhe_by_date[r["date"]] = float(r.get("qhe", 0) or 0)
    sleep_by_date: dict[str, float] = {}
    for r in sleep_rows:
        sleep_by_date[r["date"]] = float(r.get("sleep_hours", 0) or 0)

    # Pomodoros by date
    pom_by_date: dict[str, float] = {}
    for r in pom_rows:
        pom_by_date[r["date"]] = pom_by_date.get(r["date"], 0) + 1

    total = len(ctx_rows) or 1
    out = []
    for name, rows in sorted(by_scenario.items(), key=lambda x: len(x[1]), reverse=True):
        dates = [r["date"] for r in rows]
        qhe_vals = [qhe_by_date.get(d, 0) for d in dates]
        sleep_vals = [sleep_by_date.get(d, 0) for d in dates]
        energia_vals = [float(r.get("energia", 0) or 0) for r in rows]
        pom_vals = [pom_by_date.get(d, 0) for d in dates]
        budget = [float(r.get("hardwork_orcado_min", 0) or 0) for r in rows]
        actual = [float(r.get("hardwork_realizado_min", 0) or 0) for r in rows]
        adh_vals = [min(a / b, 1.0) if b > 0 else 0.0 for a, b in zip(actual, budget)]

        n = len(rows)
        out.append(ScenarioStats(
            name=name,
            days=n,
            pct=n / total * 100,
            qhe_avg=statistics.mean(qhe_vals) if qhe_vals else 0.0,
            sleep_avg=statistics.mean(sleep_vals) if sleep_vals else 0.0,
            energia_avg=statistics.mean(energia_vals) if energia_vals else 0.0,
            pomodoros_avg=statistics.mean(pom_vals) if pom_vals else 0.0,
            hardwork_adh=statistics.mean(adh_vals) * 100 if adh_vals else 0.0,
        ))
    return out


# ── Regime Analyzer ─────────────────────────────────────────────────────────────

@dataclass
class RegimeTransition:
    from_state: str
    to_state: str
    date: date
    days_in_previous: int


@dataclass
class RegimeStats:
    state: str
    days: int
    pct: float
    qhe_avg: float
    avg_days_in_state: float
    transitions: list[RegimeTransition]


def regime_analysis(ds: Dataset) -> list[RegimeStats]:
    """Per-regime statistics and transition log."""
    policy_rows = ds.get("policy_decision", [])
    qhe_rows = ds.get("qhe_metrics", [])

    # Sort by date
    sorted_pol = sorted(policy_rows, key=lambda r: r["date"])
    qhe_by_date: dict[str, float] = {r["date"]: float(r.get("qhe", 0) or 0) for r in qhe_rows}

    # Group by state
    by_state: dict[str, list[dict[str, Any]]] = {}
    for r in sorted_pol:
        s = r.get("state", "UNKNOWN")
        by_state.setdefault(s, []).append(r)

    transitions: list[RegimeTransition] = []
    prev_state = ""
    prev_date = ""
    for r in sorted_pol:
        s = r.get("state", "")
        d_str = r["date"]
        if prev_state and s != prev_state:
            try:
                days_in_prev = (date.fromisoformat(d_str) - date.fromisoformat(prev_date)).days
            except (ValueError, TypeError):
                days_in_prev = 0
            transitions.append(RegimeTransition(
                from_state=prev_state,
                to_state=s,
                date=date.fromisoformat(d_str),
                days_in_previous=days_in_prev,
            ))
        prev_state = s
        prev_date = d_str

    total = len(sorted_pol) or 1
    out = []
    for state, rows in sorted(by_state.items(), key=lambda x: len(x[1]), reverse=True):
        dates = [r["date"] for r in rows]
        qhe_vals = [qhe_by_date.get(d, 0) for d in dates]
        days_in_state_vals = [float(r.get("days_in_state", 0) or 0) for r in rows]
        out.append(RegimeStats(
            state=state,
            days=len(rows),
            pct=len(rows) / total * 100,
            qhe_avg=statistics.mean(qhe_vals) if qhe_vals else 0.0,
            avg_days_in_state=statistics.mean(days_in_state_vals),
            transitions=[
                t for t in transitions
                if t.from_state == state or t.to_state == state
            ],
        ))
    return out


def regime_timeline(ds: Dataset) -> list[tuple[date, str]]:
    """Chronological regime state log: (date, state)."""
    rows = ds.get("policy_decision", [])
    pairs = []
    for r in rows:
        try:
            d = date.fromisoformat(r["date"])
            s = r.get("state", "")
            pairs.append((d, s))
        except (ValueError, KeyError):
            pass
    pairs.sort()
    return [(d, s) for d, s in pairs]


# ── Forecast Engine ────────────────────────────────────────────────────────────

@dataclass
class ForecastPoint:
    date: date
    predicted: float
    lower_ci: float
    upper_ci: float


def linear_forecast(series: TimeSeriesSlice, horizon: int = 7) -> list[ForecastPoint]:
    """Simple OLS linear forecast with ±1 std confidence band."""
    if len(series.values) < 4:
        return []
    slope = _linear_slope(series.values)
    intercept = statistics.mean(series.values) - slope * statistics.mean(range(len(series.values)))
    residual_std = statistics.stdev(series.diff()) if len(series.values) > 2 else 0.0

    last_date = series.dates[-1]
    last_idx = len(series.values) - 1
    out = []
    for h in range(1, horizon + 1):
        pred = intercept + slope * (last_idx + h)
        ci = 1.96 * residual_std
        out.append(ForecastPoint(
            date=last_date + timedelta(days=h),
            predicted=pred,
            lower_ci=pred - ci,
            upper_ci=pred + ci,
        ))
    return out


# ── Habit Analytics ────────────────────────────────────────────────────────────

@dataclass
class HabitStats:
    habit_id: str
    habit_name: str
    category: str
    completion_rate: float
    current_streak: int
    longest_streak: int
    avg_effort_minutes: float
    total_completions: int


def habit_analytics(ds: Dataset) -> list[HabitStats]:
    """Per-habit completion analytics."""
    habit_rows = ds.get("habit", [])
    hs_rows = ds.get("habit_state", [])

    habit_by_id: dict[str, dict[str, Any]] = {}
    for r in habit_rows:
        habit_by_id[r["id"]] = r

    by_habit: dict[str, list[dict[str, Any]]] = {}
    for r in hs_rows:
        hid = r.get("habit_id", "")
        by_habit.setdefault(hid, []).append(r)

    out = []
    for hid, rows in sorted(by_habit.items(), key=lambda x: len(x[1]), reverse=True):
        completed = sum(1 for r in rows if str(r.get("completed", "")).lower() in ("true", "1", "yes"))
        total = len(rows)
        streaks = [int(r.get("streak_current", 0) or 0) for r in rows]
        efforts = [float(r.get("effort_minutes", 0) or 0) for r in rows]
        habit_def = habit_by_id.get(hid, {})
        out.append(HabitStats(
            habit_id=hid,
            habit_name=habit_def.get("name", hid),
            category=habit_def.get("category", "unknown"),
            completion_rate=completed / total if total > 0 else 0.0,
            current_streak=max(streaks) if streaks else 0,
            longest_streak=max(streaks) if streaks else 0,
            avg_effort_minutes=statistics.mean(efforts) if efforts else 0.0,
            total_completions=completed,
        ))
    return out


# ── Growth Score ───────────────────────────────────────────────────────────────

@dataclass
class GrowthScore:
    score: float          # 0–100
    qhe_delta_30d: float   # delta in last 30 days
    qhe_delta_90d: float  # delta in last 90 days
    sleep_delta: float
    consistency_delta: float
    regime_health_score: float  # 0–100: % of days in PUSH or MAINTAIN
    habit_improvement: float   # completion rate trend


def growth_score(ds: Dataset) -> GrowthScore:
    """Compute a 0–100 growth score from multiple signals."""
    qhe_rows = ds.get("qhe_metrics", [])
    sleep_rows = ds.get("sleep_record", [])
    policy_rows = ds.get("policy_decision", [])
    habit_state_rows = ds.get("habit_state", [])

    all_dates = sorted(set(r["date"] for r in qhe_rows))
    if not all_dates:
        return GrowthScore(score=0, qhe_delta_30d=0, qhe_delta_90d=0,
                          sleep_delta=0, consistency_delta=0,
                          regime_health_score=0, habit_improvement=0)

    qhe_by_date = {r["date"]: float(r.get("qhe", 0) or 0) for r in qhe_rows}
    cons_by_date = {r["date"]: float(r.get("consistency", 0) or 0) for r in qhe_rows}
    sleep_by_date = {r["date"]: float(r.get("sleep_hours", 0) or 0) for r in sleep_rows}

    def _window_avg(mapping: dict[str, float], days: int) -> float:
        recent = all_dates[-days:] if len(all_dates) >= days else all_dates
        vals = [mapping.get(d, 0) for d in recent]
        return statistics.mean(vals) if vals else 0.0

    def _window_delta(mapping: dict[str, float], days: int) -> float:
        if len(all_dates) < days:
            return 0.0
        old_vals = [mapping.get(d, 0) for d in all_dates[:days]]
        new_vals = [mapping.get(d, 0) for d in all_dates[-days:]]
        return statistics.mean(new_vals) - statistics.mean(old_vals)

    # Regime health
    healthy = sum(1 for r in policy_rows if r.get("state") in ("PUSH", "MAINTAIN"))
    regime_hs = healthy / len(policy_rows) * 100 if policy_rows else 0.0

    # Habit improvement: completion rate last 30d vs previous 30d
    completed = sum(1 for r in habit_state_rows if str(r.get("completed", "")).lower() in ("true", "1", "yes"))
    total = len(habit_state_rows)
    completion_rate = completed / total if total > 0 else 0.0

    qhe_delta30 = _window_delta(qhe_by_date, 30)
    qhe_delta90 = _window_delta(qhe_by_date, 90)
    sleep_delta = _window_delta(sleep_by_date, 30)
    cons_delta = _window_delta(cons_by_date, 30)

    # Weighted composite score
    qhe_w = 40
    sleep_w = 20
    regime_w = 25
    habit_w = 15

    qhe_norm = min(max(qhe_delta90 + 0.5, 0), 1) * 100
    sleep_norm = min(max((sleep_delta + 4) / 8, 0), 1) * 100
    habit_norm = completion_rate * 100

    score = (
        qhe_w * qhe_norm / 100 +
        sleep_w * sleep_norm / 100 +
        regime_w * regime_hs / 100 +
        habit_w * habit_norm / 100
    )

    return GrowthScore(
        score=round(score, 1),
        qhe_delta_30d=round(qhe_delta30, 4),
        qhe_delta_90d=round(qhe_delta90, 4),
        sleep_delta=round(sleep_delta, 2),
        consistency_delta=round(cons_delta, 4),
        regime_health_score=round(regime_hs, 1),
        habit_improvement=round(completion_rate * 100, 1),
    )


# ── Period Comparison ──────────────────────────────────────────────────────────

@dataclass
class PeriodComparison:
    label_a: str
    label_b: str
    metrics: dict[str, tuple[float, float, float]]  # metric → (val_a, val_b, delta_pct)


def compare_periods(
    ds: Dataset,
    metric: str,
    period_a: tuple[date, date],
    period_b: tuple[date, date],
) -> PeriodComparison:
    """Compare a metric between two date windows."""
    pom_rows = ds.get("pomodoro_round", [])

    _METRIC_MAP: dict[str, tuple[str, str]] = {
        "qhe": ("qhe_metrics", "qhe"),
        "sleep_hours": ("sleep_record", "sleep_hours"),
        "sleep_quality": ("sleep_record", "quality_score"),
        "energia": ("day_context", "energia"),
        "foco": ("day_context", "foco"),
        "habit_avg": ("qhe_metrics", "habit_avg"),
        "consistency": ("qhe_metrics", "consistency"),
        "pomodoros": ("pomodoro_round", "count"),
        "hardwork": ("day_context", "hardwork_realizado_min"),
    }

    entity, col = _METRIC_MAP.get(metric, ("qhe_metrics", metric))
    rows = ds.get(entity, [])

    def _avg(window: tuple[date, date]) -> float:
        vals = []
        for r in rows:
            try:
                d = date.fromisoformat(r["date"])
                if window[0] <= d <= window[1]:
                    vals.append(float(r.get(col, 0) or 0))
            except (ValueError, KeyError):
                pass
        return statistics.mean(vals) if vals else 0.0

    def _pomodoros_avg(window: tuple[date, date]) -> float:
        counts: dict[str, int] = {}
        for r in pom_rows:
            try:
                d = date.fromisoformat(r["date"])
                if window[0] <= d <= window[1]:
                    counts[r["date"]] = counts.get(r["date"], 0) + 1
            except (ValueError, KeyError):
                pass
        vals = list(counts.values())
        return statistics.mean(vals) if vals else 0.0

    def _delta(a: float, b: float) -> float:
        if a == 0:
            return 0.0
        return (b - a) / abs(a) * 100

    if metric == "pomodoros":
        va = _pomodoros_avg(period_a)
        vb = _pomodoros_avg(period_b)
    else:
        va = _avg(period_a)
        vb = _avg(period_b)

    return PeriodComparison(
        label_a=f"{period_a[0]}–{period_a[1]}",
        label_b=f"{period_b[0]}–{period_b[1]}",
        metrics={metric: (va, vb, _delta(va, vb))},
    )
