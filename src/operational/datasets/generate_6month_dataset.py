"""6-Month Synthetic Dataset Generator for PAV Operational.

Generates a 180-day synthetic dataset (2025-12-23 → 2026-06-22) covering
all PAV scenarios from struggling-beginner to mastery.

Usage:
    python datasets/generate_6month_dataset.py           # full 180-day run
    python datasets/generate_6month_dataset.py --days 30 # first 30 days only
    python datasets/generate_6month_dataset.py --dry-run # print only, no files written
"""
from __future__ import annotations

import csv
import json
import math
import random
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

# ── Ensure packages/core is on path ──────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]  # operational/
_PACKAGES = _ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(_PACKAGES))

from operational.constants import DEFAULT
from operational.core.habit_engine import (
    compute_habit_avg,
    compute_habit_level,
    compute_consistency,
    compute_streak_bonus,
)
from operational.core.policy_engine import PolicyEngine
from operational.entities.habit import Habit, HabitState, QHEMetrics
from operational.entities.policy import PolicyDecision, PolicySetpoints
from operational.enums import HabitCategory, Period, PolicyState

# ── Constants ────────────────────────────────────────────────────────────────

START_DATE = date(2025, 12, 23)
# 180 days exactly: Dec 23 2025 (day 1) → Jun 21 2026 (day 180)
END_DATE = date(2026, 6, 21)
TOTAL_DAYS = 180
SEED = 42

LAMBDA_LEARNING = 0.093
ETA = 0.5
STREAK_MAX = 90
E_MAX = 10.0

# UEID prefixes (oper cluster)
UEID_SLEEP = "oper_sle"
UEID_HABIT = "oper_hab"
UEID_HST = "oper_hst"
UEID_QHE = "oper_qhe"
UEID_ROU = "oper_rou"
UEID_RLG = "oper_rlg"
UEID_BLK = "oper_blk"
UEID_JRN = "oper_jrn"
UEID_POM = "oper_pom"
UEID_CTX = "oper_ctx"
UEID_REF = "oper_ref"
UEID_LUN = "oper_lun"
UEID_TRN = "oper_trn"
UEID_ADJ = "oper_adj"
UEID_POL = "oper_pol"
UEID_SET = "oper_set"

# ── Scenario definitions ──────────────────────────────────────────────────────

@dataclass
class Scenario:
    name: str
    tipo_dia: str
    sleep_hours: float
    sleep_quality: int  # 1-10
    pomodoros: int
    hardwork_min: int
    policy: PolicyState
    completion_prob: float  # probability each habit is completed
    energia: int  # 1-10
    foco: int  # 1-10
    lunch_pesado: bool = False
    infractions: int = 0
    deep_pct: float = 0.22
    rem_pct: float = 0.22
    interruptions: int = 0

SCENARIOS: dict[str, Scenario] = {
    "Padrao_Ouro": Scenario(
        name="Padrao_Ouro", tipo_dia="CURSO", sleep_hours=8.0, sleep_quality=9,
        pomodoros=11, hardwork_min=240, policy=PolicyState.PUSH,
        completion_prob=0.98, energia=8, foco=9,
    ),
    "Desvio_Leve": Scenario(
        name="Desvio_Leve", tipo_dia="CURSO", sleep_hours=6.5, sleep_quality=6,
        pomodoros=8, hardwork_min=200, policy=PolicyState.REDUCE,
        completion_prob=0.75, energia=6, foco=7,
    ),
    "Hardcore": Scenario(
        name="Hardcore", tipo_dia="HARDCORE", sleep_hours=4.0, sleep_quality=4,
        pomodoros=10, hardwork_min=480, policy=PolicyState.RECOVER,
        completion_prob=0.60, energia=5, foco=6, infractions=1,
        deep_pct=0.15, rem_pct=0.15, interruptions=2,
    ),
    "Recuperacao": Scenario(
        name="Recuperacao", tipo_dia="DESCANSO", sleep_hours=10.0, sleep_quality=10,
        pomodoros=3, hardwork_min=90, policy=PolicyState.MAINTAIN,
        completion_prob=0.90, energia=7, foco=5,
    ),
    "Lunch_Pesado": Scenario(
        name="Lunch_Pesado", tipo_dia="CURSO", sleep_hours=7.5, sleep_quality=8,
        pomodoros=7, hardwork_min=210, policy=PolicyState.REDUCE,
        completion_prob=0.85, energia=7, foco=7, lunch_pesado=True,
    ),
    "Fim_de_Semana": Scenario(
        name="Fim_de_Semana", tipo_dia="LIVRE", sleep_hours=8.0, sleep_quality=9,
        pomodoros=8, hardwork_min=360, policy=PolicyState.PUSH,
        completion_prob=0.95, energia=9, foco=8,
    ),
    "Feriado": Scenario(
        name="Feriado", tipo_dia="LIVRE", sleep_hours=9.0, sleep_quality=8,
        pomodoros=2, hardwork_min=120, policy=PolicyState.MAINTAIN,
        completion_prob=0.80, energia=8, foco=5,
    ),
    "Doente": Scenario(
        name="Doente", tipo_dia="DESCANSO", sleep_hours=11.0, sleep_quality=5,
        pomodoros=0, hardwork_min=30, policy=PolicyState.RECOVER,
        completion_prob=0.40, energia=3, foco=2, infractions=2,
    ),
    "Visita_Inesperada": Scenario(
        name="Visita_Inesperada", tipo_dia="LIVRE", sleep_hours=7.5, sleep_quality=7,
        pomodoros=6, hardwork_min=300, policy=PolicyState.MAINTAIN,
        completion_prob=0.70, energia=7, foco=5,
    ),
    "Vigilia": Scenario(
        name="Vigilia", tipo_dia="HARDCORE", sleep_hours=3.0, sleep_quality=3,
        pomodoros=8, hardwork_min=540, policy=PolicyState.RECOVER,
        completion_prob=0.50, energia=4, foco=5, infractions=3,
        deep_pct=0.12, rem_pct=0.12, interruptions=4,
    ),
}

# 26-week calendar (day_index 0-based → scenario name)
_WEEKLY_CALENDAR: list[tuple[str, int, int, int, int, int, int, int]] = [
    #  week   Mon   Tue   Wed   Thu   Fri   Sat   Sun
    (1,     "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Desvio_Leve", "Fim_de_Semana", "Fim_de_Semana"),
    (2,     "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana", "Desvio_Leve"),
    (3,     "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Lunch_Pesado", "Fim_de_Semana", "Fim_de_Semana"),
    (4,     "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Desvio_Leve", "Desvio_Leve", "Fim_de_Semana", "Fim_de_Semana"),
    (5,     "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Feriado", "Fim_de_Semana", "Fim_de_Semana"),
    (6,     "Padrao_Ouro", "Hardcore", "Recuperacao", "Padrao_Ouro", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (7,     "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Lunch_Pesado", "Fim_de_Semana", "Fim_de_Semana"),
    (8,     "Padrao_Ouro", "Padrao_Ouro", "Desvio_Leve", "Desvio_Leve", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (9,     "Padrao_Ouro", "Feriado", "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (10,    "Padrao_Ouro", "Padrao_Ouro", "Hardcore", "Recuperacao", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (11,    "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Lunch_Pesado", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (12,    "Padrao_Ouro", "Padrao_Ouro", "Desvio_Leve", "Desvio_Leve", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (13,    "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Doente", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (14,    "Padrao_Ouro", "Feriado", "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (15,    "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Lunch_Pesado", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (16,    "Padrao_Ouro", "Padrao_Ouro", "Desvio_Leve", "Desvio_Leve", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (17,    "Padrao_Ouro", "Hardcore", "Recuperacao", "Padrao_Ouro", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (18,    "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Visita_Inesperada", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (19,    "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Lunch_Pesado", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (20,    "Padrao_Ouro", "Feriado", "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (21,    "Padrao_Ouro", "Padrao_Ouro", "Desvio_Leve", "Padrao_Ouro", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (22,    "Padrao_Ouro", "Hardcore", "Recuperacao", "Padrao_Ouro", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (23,    "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Lunch_Pesado", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (24,    "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Doente", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (25,    "Padrao_Ouro", "Feriado", "Padrao_Ouro", "Padrao_Ouro", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
    (26,    "Padrao_Ouro", "Padrao_Ouro", "Desvio_Leve", "Vigilia", "Padrao_Ouro", "Fim_de_Semana", "Fim_de_Semana"),
]

# Build day_index → scenario mapping
def _build_calendar() -> list[str]:
    """Map 0-based day index to scenario name for 180 days."""
    calendar: list[str] = []
    for week_data in _WEEKLY_CALENDAR:
        week_num, *days = week_data
        for day_idx, scenario_name in enumerate(days):  # 7 days
            calendar.append(scenario_name)
    return calendar[:TOTAL_DAYS]  # cap at 180

CALENDAR = _build_calendar()  # 180 entries

# ── Habits ───────────────────────────────────────────────────────────────────

@dataclass
class HabitDef:
    slug: str
    name: str
    category: HabitCategory
    resistance: float
    weight: float
    effort_minutes: int
    start_day: int  # day index (0-based) when habit starts

HABITS: list[HabitDef] = [
    HabitDef("beber_2l_de_agua",  "Beber 2L Água",     HabitCategory.PHYSIOLOGICAL,  2.0, 0.15, 2,  0),
    HabitDef("meditar_10min",     "Meditar 10min",      HabitCategory.PHYSIOLOGICAL,  3.0, 0.10, 10, 0),
    HabitDef("alongamento",        "Alongamento",         HabitCategory.PHYSIOLOGICAL,  4.0, 0.10, 10, 0),
    HabitDef("ler_30min",         "Ler 30min",           HabitCategory.COGNITIVE,       6.0, 0.15, 30, 7),
    HabitDef("caminhada_20min",  "Caminhada 20min",    HabitCategory.PHYSIOLOGICAL,  4.0, 0.10, 20, 14),
    HabitDef("ligar_familia",     "Ligar Família",        HabitCategory.SOCIAL,         5.0, 0.10, 15, 21),
    HabitDef("escrever_diario",  "Escrever Diário",      HabitCategory.COGNITIVE,       5.0, 0.15, 15, 0),
    HabitDef("planejar_dia",      "Planejar Dia",         HabitCategory.COGNITIVE,       3.0, 0.15, 10, 0),
]

# Break points: (habit_slug, list of day indices where streak resets)
HABIT_BREAKS: dict[str, list[int]] = {
    "beber_2l_de_agua":  [],
    "meditar_10min":     [46, 47, 48, 102, 103],
    "alongamento":       [20, 21, 22, 88, 89, 90, 150, 151],
    "ler_30min":        [45, 46, 47, 48, 49, 50, 51, 52, 120, 121, 122, 123, 124, 125],
    "caminhada_20min":  [60, 61, 62, 63, 64, 65, 140, 141, 142],
    "ligar_familia":    [70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140],
    "escrever_diario":  [10, 11, 12, 95, 96, 97],
    "planejar_dia":     [],
}

# ── Routines ─────────────────────────────────────────────────────────────────

@dataclass
class RoutineDef:
    idx: str
    name: str
    period: Period
    routine_type: str  # ENTRY, CORE, EXIT, TRANSITION
    start_hour: int
    start_min: int
    end_hour: int
    end_min: int
    mandatory: bool = True

ROUTINES: list[RoutineDef] = [
    RoutineDef("001", "Despertar + higiene",          Period.MANHA, "ENTRY",     5, 0,  5, 30, True),
    RoutineDef("002", "Meditar 10min",                Period.MANHA, "ENTRY",     5, 30, 5, 45, True),
    RoutineDef("003", "Alongamento 10min",            Period.MANHA, "ENTRY",     5, 45, 6, 0,  True),
    RoutineDef("004", "Beber 500ml água",             Period.MANHA, "ENTRY",     6, 0,  6, 5,  True),
    RoutineDef("005", "Lanche leve pré-treino",       Period.MANHA, "ENTRY",     6, 5,  6, 15, False),
    RoutineDef("006", "Caminhada 20min",             Period.MANHA, "CORE",      6, 15, 6, 45, True),
    RoutineDef("007", "Banho + preparação",           Period.MANHA, "CORE",      6, 45, 7, 30, True),
    RoutineDef("008", "Foco profundo #1 (90min)",     Period.TARDE, "CORE",      8, 0,  9, 30, True),
    RoutineDef("009", "Pausa ativa + água",          Period.TARDE, "TRANSITION",9, 30, 9, 45, True),
    RoutineDef("010", "Foco profundo #2 (90min)",      Period.TARDE, "CORE",      9, 45, 11, 15, True),
    RoutineDef("011", "Almoço pesado",               Period.TARDE, "CORE",      12, 0, 13, 0, True),
    RoutineDef("012", "Digestão + descanso",          Period.TARDE, "TRANSITION",13, 0, 13, 30, False),
    RoutineDef("013", "Foco profundo #3 (90min)",      Period.TARDE, "CORE",      13, 30, 15, 0, True),
    RoutineDef("014", "Pausa ativa",                  Period.TARDE, "TRANSITION",15, 0, 15, 20, True),
    RoutineDef("015", "Tarefas leves admin",           Period.TARDE, "CORE",      15, 20, 16, 30, False),
    RoutineDef("016", "Jantar leve",                  Period.NOITE, "ENTRY",      18, 30, 19, 15, True),
    RoutineDef("017", "Tempo com família",            Period.NOITE, "CORE",      19, 15, 20, 0, True),
    RoutineDef("018", "Leitura 30min",               Period.NOITE, "CORE",      20, 0,  20, 35, True),
    RoutineDef("019", "Planejamento amanhã",          Period.NOITE, "CORE",      20, 35, 20, 50, True),
    RoutineDef("020", "Higiene do sono",              Period.NOITE, "EXIT",      21, 0,  21, 30, True),
    RoutineDef("021", "Luzes off",                    Period.NOITE, "EXIT",      21, 30, 22, 0, True),
    RoutineDef("022", "Escrita diária",               Period.NOITE, "ENTRY",     21, 0,  21, 20, True),
]

# ── Transição Registry ────────────────────────────────────────────────────────

TRANSOES = [
    ("T1", "Sessão despertar",      5),
    ("T2", "Entrada MANHA",        3),
    ("T3", "Início foco #1",       2),
    ("T4", "Pausa manhã",          10),
    ("T5", "Entrada TARDE",        3),
    ("T6", "Almoço",               45),
    ("T7", "Pós-almoço",           20),
    ("T8", "Entrada NOITE",        3),
    ("T9", "Sessão dormir",        10),
]

# ── Seeded RNG ────────────────────────────────────────────────────────────────

random.seed(SEED)
rng = random.Random(SEED)

def rr() -> float:
    return rng.random()

# ── Core simulation ────────────────────────────────────────────────────────────

class HabitSimulator:
    """Tracks streak state for each habit across the 180-day run."""

    def __init__(self) -> None:
        self._streak: dict[str, int] = {h.slug: 0 for h in HABITS}
        self._broken: dict[str, int] = {h.slug: 0 for h in HABITS}

    def on_day(self, day_idx: int, scenario: Scenario) -> dict[str, HabitState]:
        """Return HabitState dict for all habits on this day."""
        states = {}
        for hd in HABITS:
            if day_idx < hd.start_day:
                # Habit not started yet — skip
                continue
            breaks = HABIT_BREAKS.get(hd.slug, [])
            # Check if streak broken on this day
            if day_idx in breaks:
                self._streak[hd.slug] = 0
                self._broken[hd.slug] += 1
            # Determine completion
            if scenario.completion_prob >= rr():
                self._streak[hd.slug] += 1
                completed = True
            else:
                completed = False
            streak = self._streak[hd.slug]
            states[hd.slug] = HabitState(
                id=f"{UEID_HST}_{hd.slug}_{(START_DATE + timedelta(days=day_idx)).strftime('%Y%m%d')}",
                habit_id=f"{UEID_HABIT}_{hd.slug}",
                date=START_DATE + timedelta(days=day_idx),
                completed=completed,
                streak_current=streak,
                streak_broken_count=self._broken[hd.slug],
                effort_minutes=hd.effort_minutes if completed else 0,
            )
        return states


class SyntheticEngine:
    def __init__(self) -> None:
        self.habit_sim = HabitSimulator()
        self.policy_engine = PolicyEngine(max_history=365)
        self.day_data: list[dict[str, Any]] = []
        self._scenarios_dist: dict[str, int] = {}

    def run(self, max_days: int | None = None) -> None:
        n = max_days if max_days is not None else TOTAL_DAYS
        for day_idx in range(n):
            d = self._simulate_day(day_idx)
            self.day_data.append(d)
            sc = d["scenario"]
            self._scenarios_dist[sc.name] = self._scenarios_dist.get(sc.name, 0) + 1

    def _simulate_day(self, day_idx: int) -> dict[str, Any]:
        cal_date = START_DATE + timedelta(days=day_idx)
        scenario_name = CALENDAR[day_idx]
        scenario = SCENARIOS[scenario_name]

        # ── Sleep ────────────────────────────────────────────────────────────
        sleep_hours = scenario.sleep_hours
        # Bedtime 21:30 + variance
        bed_hour = int(21.5 + (rr() - 0.5) * 0.5)
        bed_min = int(rr() * 59)
        # Wake: derived from sleep hours
        wake_hour = (bed_hour + int(sleep_hours)) % 24
        wake_min = int(rr() * 59)

        sleep_record = {
            "id": f"{UEID_SLEEP}_{cal_date.strftime('%Y%m%d')}",
            "date": cal_date.isoformat(),
            "cluster": "oper",
            "bedtime": f"{bed_hour:02d}:{bed_min:02d}",
            "wake_time": f"{wake_hour:02d}:{wake_min:02d}",
            "sleep_hours": round(sleep_hours, 2),
            "quality_score": scenario.sleep_quality,
            "deep_sleep_pct": scenario.deep_pct,
            "rem_sleep_pct": scenario.rem_pct,
            "interruptions": scenario.interruptions,
            "notes": f"Synthetic {scenario.name} day",
            "source": "SYNTHETIC",
        }

        # ── Habit States ─────────────────────────────────────────────────────
        habit_states = self.habit_sim.on_day(day_idx, scenario)

        # ── QHEMetrics ──────────────────────────────────────────────────────
        habit_list = [
            Habit(
                id=f"{UEID_HABIT}_{hd.slug}",
                name=hd.name,
                category=hd.category,
                resistance=hd.resistance,
                lambda_learning=LAMBDA_LEARNING,
                weight_in_qhe=hd.weight,
                created_at=datetime(2025, 12, 23),
            )
            for hd in HABITS
        ]

        # Build Habit objects keyed by habit_id
        habit_map: dict[str, Habit] = {h.id: h for h in habit_list}

        active_states = [hs for hs in habit_states.values() if hs.date == cal_date]
        active_habits = [habit_map[hs.habit_id] for hs in active_states if hs.habit_id in habit_map]

        habit_avg = compute_habit_avg(active_states, active_habits)
        consistency = compute_consistency(active_states)

        avg_streak = sum(s.streak_current for s in active_states) / max(len(active_states), 1)
        streak_bonus = compute_streak_bonus(int(avg_streak), STREAK_MAX)

        energy_ratio = min(sleep_hours / 9.0, 1.0)

        qhe_value = habit_avg * energy_ratio * (1.0 + ETA * streak_bonus)
        qhe_value = max(0.0, min(1.0, qhe_value))  # clamp

        qhe_metrics = {
            "id": f"{UEID_QHE}_{cal_date.strftime('%Y%m%d')}",
            "date": cal_date.isoformat(),
            "cluster": "oper",
            "habit_avg": round(habit_avg, 4),
            "consistency": round(consistency, 4),
            "streak_bonus": round(streak_bonus, 4),
            "energy_ratio": round(energy_ratio, 4),
            "qhe": round(qhe_value, 4),
            "regime_predicted": scenario.policy.value,
        }

        # ── Policy Decision ───────────────────────────────────────────────────
        # Build QHEMetrics object for policy engine
        qhe_obj = QHEMetrics(
            id=f"qhe_{cal_date.strftime('%Y%m%d')}",
            date=cal_date,
            habit_avg=habit_avg,
            consistency=consistency,
            streak_bonus=streak_bonus,
            energy_ratio=energy_ratio,
            eta=ETA,
        )

        policy_decision = self.policy_engine.evaluate(
            qhe_metrics=qhe_obj,
            infraction_count=scenario.infractions,
            on_date=cal_date,
        )

        pd_dict = {
            "id": f"{UEID_POL}_{cal_date.strftime('%Y%m%d')}",
            "date": cal_date.isoformat(),
            "cluster": "oper",
            "state": policy_decision.state.value,
            "severity": policy_decision.severity,
            "rationale": policy_decision.rationale,
            "days_in_state": policy_decision.days_in_state,
            "previous_state": policy_decision.previous_state.value if policy_decision.previous_state else None,
            "qhe_input": round(policy_decision.qhe_input or 0.0, 4),
            "infraction_count": policy_decision.infraction_count,
            "hardwork_budget_hours": policy_decision.setpoints.hardwork_budget_hours,
            "max_pomodoros_per_day": policy_decision.setpoints.max_pomodoros_per_day,
            "sleep_target_hours": policy_decision.setpoints.sleep_target_hours,
        }

        # ── Day Context ──────────────────────────────────────────────────────
        day_context = {
            "id": f"{UEID_CTX}_{cal_date.strftime('%Y%m%d')}",
            "date": cal_date.isoformat(),
            "cluster": "oper",
            "tipo_dia": scenario.tipo_dia,
            "hardwork_orcado_min": scenario.hardwork_min,
            "hardwork_realizado_min": int(scenario.hardwork_min * (0.8 + rr() * 0.2)),
            "pomodoros_meta": scenario.pomodoros,
            "pomodoros_realizados": max(0, scenario.pomodoros + int((rr() - 0.5) * 2)),
            "tem_curso": scenario.tipo_dia == "CURSO",
            "tem_deadline": scenario.name in ("Hardcore", "Vigilia"),
            "observacoes": f"Synthetic {scenario.name}",
        }

        # ── Journal Entry (AM + PM) ───────────────────────────────────────────
        humor = min(10, max(1, scenario.energia + int((rr() - 0.5) * 2)))
        humor_pm = min(10, max(1, scenario.energia - 1 + int((rr() - 0.5) * 3)))

        desvios = []
        if scenario.name == "Desvio_Leve":
            desvios = ["Soneca à tarde", "Rede social manhã"]
        elif scenario.name in ("Hardcore", "Vigilia"):
            desvios = ["Sono deficitário", "Excesso de cafeina"]
        elif scenario.name == "Doente":
            desvios = ["Não consegui fazer nada"]

        journal_am = {
            "id": f"{UEID_JRN}_{cal_date.strftime('%Y%m%d')}_AM",
            "date": cal_date.isoformat(),
            "cluster": "oper",
            "period": "AM",
            "entry_text": f"[AM] {scenario.name} — energia={scenario.energia}/10, foco={scenario.foco}/10",
            "energia_nivel": scenario.energia,
            "focus_nivel": scenario.foco,
            "humor_morning": humor,
            "humor_evening": None,
            "pomodoros_completos": max(0, scenario.pomodoros // 2 + int(rr() * 2)),
            "periods_covered": "MANHA",
            "desvios": desvios,
            "licoes_aprendidas": [],
        }
        journal_pm = {
            "id": f"{UEID_JRN}_{cal_date.strftime('%Y%m%d')}_PM",
            "date": cal_date.isoformat(),
            "cluster": "oper",
            "period": "PM",
            "entry_text": f"[PM] {scenario.name} — final do dia",
            "energia_nivel": max(1, scenario.energia - 1),
            "focus_nivel": max(1, scenario.foco - 1),
            "humor_morning": None,
            "humor_evening": humor_pm,
            "pomodoros_completos": max(0, scenario.pomodoros - journal_am["pomodoros_completos"]),
            "periods_covered": "TARDE,NOITE",
            "desvios": [],
            "licoes_aprendidas": [],
        }

        # ── Pomodoro Rounds ──────────────────────────────────────────────────
        pomodoros = []
        for p_num in range(1, scenario.pomodoros + 1):
            started_hour = 8 + (p_num - 1) * 1  # simplified 50min on, 10min off
            started_min = 0
            completed_hour = started_hour
            completed_min = started_min + 50
            if completed_min >= 60:
                completed_hour += 1
                completed_min -= 60
            pomodoros.append({
                "id": f"{UEID_POM}_{cal_date.strftime('%Y%m%d')}_{p_num:04d}",
                "date": cal_date.isoformat(),
                "cluster": "oper",
                "round_number": p_num,
                "state": "COMPLETE" if rr() > 0.1 else "INTERRUPTED",
                "started_at": f"{started_hour:02d}:{started_min:02d}",
                "completed_at": f"{completed_hour:02d}:{completed_min:02d}",
                "paused_duration_seconds": int(rr() * 120) if rr() > 0.8 else 0,
            })

        # ── Daily Reflection ────────────────────────────────────────────────
        reflection = {
            "id": f"{UEID_REF}_{cal_date.strftime('%Y%m%d')}",
            "date": cal_date.isoformat(),
            "cluster": "oper",
            "parar_de_fazer": ["Procrastinar no telemóvel"] if scenario.name == "Desvio_Leve" else [],
            "repetir": ["Meditar todas as manhãs"] if scenario.energia >= 7 else [],
            "sempre_fazer": ["Beber 2L de água"] if scenario.sleep_quality >= 8 else [],
            "big_win": f"Completou {scenario.pomodoros} pomodoros" if scenario.pomodoros >= 8 else f"Sobreviveu {scenario.name}",
            "deu_certo": ["Foco profundo"] if scenario.foco >= 7 else [],
            "deu_errado": ["Soneca longa"] if scenario.name == "Desvio_Leve" else [],
            "maior_aprendizado": "Consistência supera intensidade" if scenario.name == "Padrao_Ouro" else f"{scenario.name} exige ajuste",
            "ajustes_para_amanha": "Manter ritmo" if scenario.name == "Padrao_Ouro" else "Recuperar com sono",
            "estado_geral": scenario.policy.value,
        }

        # ── Lunch Record ─────────────────────────────────────────────────────
        lunch = {
            "id": f"{UEID_LUN}_{cal_date.strftime('%Y%m%d')}",
            "date": cal_date.isoformat(),
            "cluster": "oper",
            "eat_min": 45 if scenario.lunch_pesado else 25 + int(rr() * 10),
            "rest_min": 60 if scenario.lunch_pesado else 30 + int(rr() * 15),
            "pesado": scenario.lunch_pesado,
            "notas": f"Pesado: {scenario.lunch_pesado}" if scenario.lunch_pesado else "",
        }

        # ── Transições ─────────────────────────────────────────────────────
        transicoes = []
        for t_code, t_name, t_dur in TRANSOES:
            completed = rr() < scenario.completion_prob
            transicoes.append({
                "id": f"{UEID_TRN}_{t_code}_{cal_date.strftime('%Y%m%d')}",
                "date": cal_date.isoformat(),
                "cluster": "oper",
                "codigo": t_code,
                "ritual": t_name,
                "duracao_min": t_dur,
                "completed": completed,
                "notas": f"Synthetic {scenario.name}",
            })

        # ── Ajuste Fino (only on REDUCE/RECOVER days) ───────────────────────
        ajuste_fino = []
        if scenario.policy in (PolicyState.REDUCE, PolicyState.RECOVER):
            ajuste_fino.append({
                "id": f"{UEID_ADJ}_{cal_date.strftime('%Y%m%d')}_01",
                "date": cal_date.isoformat(),
                "cluster": "oper",
                "period": Period.TARDE.value,
                "minutos": 20 if scenario.policy == PolicyState.REDUCE else 40,
                "reason": f"Policy {scenario.policy.value}: {scenario.name}",
            })

        # ── Time Blocks ─────────────────────────────────────────────────────
        time_blocks = [
            {
                "id": f"{UEID_BLK}_001_{cal_date.strftime('%Y%m%d')}",
                "date": cal_date.isoformat(),
                "cluster": "oper",
                "start": "08:00",
                "end": "11:30",
                "period": Period.TARDE.value,
                "label": "Bloco foco profundo MANHÃ",
            },
            {
                "id": f"{UEID_BLK}_002_{cal_date.strftime('%Y%m%d')}",
                "date": cal_date.isoformat(),
                "cluster": "oper",
                "start": "13:30",
                "end": "15:00",
                "period": Period.TARDE.value,
                "label": "Bloco foco profundo TARDE #1",
            },
            {
                "id": f"{UEID_BLK}_003_{cal_date.strftime('%Y%m%d')}",
                "date": cal_date.isoformat(),
                "cluster": "oper",
                "start": "15:00",
                "end": "16:30",
                "period": Period.TARDE.value,
                "label": "Bloco foco profundo TARDE #2",
            },
        ]

        # ── Routine Logs ────────────────────────────────────────────────────
        routine_logs = []
        for rou in ROUTINES[:6]:  # ~6 routines per day
            routine_logs.append({
                "id": f"{UEID_RLG}_{rou.idx}_{cal_date.strftime('%Y%m%d')}",
                "date": cal_date.isoformat(),
                "cluster": "oper",
                "routine_id": f"{UEID_ROU}_{rou.idx}",
                "period": rou.period.value,
                "routine_type": rou.routine_type,
                "text": f"Routine {rou.name} — {scenario.name}",
                "energia_nivel": scenario.energia,
                "focus_nivel": scenario.foco,
                "humor": humor,
            })

        return {
            "day_idx": day_idx,
            "scenario": scenario,
            "sleep_record": sleep_record,
            "habit_states": habit_states,
            "qhe_metrics": qhe_metrics,
            "policy_decision": pd_dict,
            "day_context": day_context,
            "journal_am": journal_am,
            "journal_pm": journal_pm,
            "pomodoros": pomodoros,
            "reflection": reflection,
            "lunch": lunch,
            "transicoes": transicoes,
            "ajuste_fino": ajuste_fino,
            "time_blocks": time_blocks,
            "routine_logs": routine_logs,
        }


# ── Output Writers ─────────────────────────────────────────────────────────────

def write_csvs(engine: SyntheticEngine, out_dir: Path) -> None:
    """Write one CSV per entity type + master CSV."""
    csved: dict[str, list[dict]] = {}

    for ent_type, writer_fn in [
        ("sleep_record", _csv_sleep),
        ("habit", _csv_habit),
        ("habit_state", _csv_habit_state),
        ("qhe_metrics", _csv_qhe),
        ("routine", _csv_routine),
        ("routine_log", _csv_routine_log),
        ("time_block", _csv_time_block),
        ("journal_entry", _csv_journal),
        ("pomodoro_round", _csv_pomodoro),
        ("day_context", _csv_day_context),
        ("daily_reflection", _csv_reflection),
        ("lunch_record", _csv_lunch),
        ("transicao", _csv_transicao),
        ("ajuste_fino", _csv_ajuste_fino),
        ("policy_decision", _csv_policy),
    ]:
        rows = writer_fn(engine)
        csved[ent_type] = rows
        _write_csv(out_dir / "csv" / f"{ent_type}.csv", _CSV_HEADERS.get(ent_type, []), rows)

    # Master CSV
    _write_master_csv(out_dir / "synthetic_180d.csv", engine)

    # Manifest
    _write_manifest(out_dir / "synthetic_180d_manifest.json", engine, csved)


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    if not headers:
        headers = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _write_master_csv(path: Path, engine: SyntheticEngine) -> None:
    """Flatten all entities into one master CSV with entity_type column."""
    rows: list[dict] = []
    for d in engine.day_data:
        sc = d["scenario"]
        cd = d["day_idx"]
        for hs in d["habit_states"].values():
            rows.append({
                "entity_type": "habit_state",
                "id": hs.id,
                "date": hs.date.isoformat(),
                "cluster": "oper",
                "habit_id": hs.habit_id,
                "completed": hs.completed,
                "streak_current": hs.streak_current,
                "streak_broken_count": hs.streak_broken_count,
                "effort_minutes": hs.effort_minutes,
            })
        rows.append({**d["sleep_record"], "entity_type": "sleep_record"})
        rows.append({**d["qhe_metrics"], "entity_type": "qhe_metrics"})
        rows.append({**d["policy_decision"], "entity_type": "policy_decision"})
        rows.append({**d["day_context"], "entity_type": "day_context"})
        rows.append({**d["journal_am"], "entity_type": "journal_entry"})
        rows.append({**d["journal_pm"], "entity_type": "journal_entry"})
        for pom in d["pomodoros"]:
            rows.append({**pom, "entity_type": "pomodoro_round"})
        rows.append({**d["reflection"], "entity_type": "daily_reflection"})
        rows.append({**d["lunch"], "entity_type": "lunch_record"})
        for trn in d["transicoes"]:
            rows.append({**trn, "entity_type": "transicao"})
        for adj in d["ajuste_fino"]:
            rows.append({**adj, "entity_type": "ajuste_fino"})
        for blk in d["time_blocks"]:
            rows.append({**blk, "entity_type": "time_block"})
        for rlg in d["routine_logs"]:
            rows.append({**rlg, "entity_type": "routine_log"})
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["entity_type", "id", "date", "cluster"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _write_manifest(path: Path, engine: SyntheticEngine, csved: dict[str, list]) -> None:
    manifest = {
        "version": "1.0",
        "date_range": {"start": START_DATE.isoformat(), "end": END_DATE.isoformat()},
        "total_days": TOTAL_DAYS,
        "generator": "generate_6month_dataset.py v1.0",
        "seed": str(SEED),
        "entities": {k: {"count": len(v)} for k, v in csved.items()},
        "scenarios": dict(engine._scenarios_dist),
        "policy_distribution": _policy_dist(engine),
    }
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _policy_dist(engine: SyntheticEngine) -> dict[str, int]:
    dist: dict[str, int] = {}
    for d in engine.day_data:
        s = d["policy_decision"]["state"]
        dist[s] = dist.get(s, 0) + 1
    return dist


# ── CSV field headers ─────────────────────────────────────────────────────────

_csv_sleep_h = ["id", "date", "cluster", "bedtime", "wake_time", "sleep_hours",
                  "quality_score", "deep_sleep_pct", "rem_sleep_pct",
                  "interruptions", "notes", "source"]

_csv_habit_h = ["id", "name", "category", "resistance", "lambda_learning",
                  "weight_in_qhe", "frequency", "created_at", "archived"]

_csv_hst_h = ["id", "date", "cluster", "habit_id", "completed",
                "streak_current", "streak_broken_count", "effort_minutes"]

_csv_qhe_h = ["id", "date", "cluster", "habit_avg", "consistency",
                "streak_bonus", "energy_ratio", "qhe", "regime_predicted"]

_csv_rou_h = ["id", "name", "period", "routine_type", "start_time",
               "end_time", "mandatory", "created_at"]

_csv_rlg_h = ["id", "date", "cluster", "routine_id", "period",
               "routine_type", "text", "energia_nivel", "focus_nivel", "humor"]

_csv_blk_h = ["id", "date", "cluster", "start", "end", "period", "label"]

_csv_jrn_h = ["id", "date", "cluster", "period", "entry_text",
               "energia_nivel", "focus_nivel", "humor_morning", "humor_evening",
               "pomodoros_completos", "periods_covered", "desvios", "licoes_aprendidas"]

_csv_pom_h = ["id", "date", "cluster", "round_number", "state",
               "started_at", "completed_at", "paused_duration_seconds"]

_csv_ctx_h = ["id", "date", "cluster", "tipo_dia", "hardwork_orcado_min",
               "hardwork_realizado_min", "pomodoros_meta", "pomodoros_realizados",
               "tem_curso", "tem_deadline", "observacoes"]

_csv_ref_h = ["id", "date", "cluster", "parar_de_fazer", "repetir",
               "sempre_fazer", "big_win", "deu_certo", "deu_errado",
               "maior_aprendizado", "ajustes_para_amanha", "estado_geral"]

_csv_lun_h = ["id", "date", "cluster", "eat_min", "rest_min",
               "pesado", "notas"]

_csv_trn_h = ["id", "date", "cluster", "codigo", "ritual",
               "duracao_min", "completed", "notas"]

_csv_adj_h = ["id", "date", "cluster", "period", "minutos", "reason"]

_csv_pol_h = ["id", "date", "cluster", "state", "severity", "rationale",
               "days_in_state", "previous_state", "qhe_input", "infraction_count",
               "hardwork_budget_hours", "max_pomodoros_per_day", "sleep_target_hours"]

_csv_habit_h_all = ["id", "name", "category", "resistance", "lambda_learning",
                      "weight_in_qhe", "frequency", "created_at", "archived"]

_CSV_HEADERS: dict[str, list[str]] = {
    "sleep_record": _csv_sleep_h,
    "habit": _csv_habit_h_all,
    "habit_state": _csv_hst_h,
    "qhe_metrics": _csv_qhe_h,
    "routine": _csv_rou_h,
    "routine_log": _csv_rlg_h,
    "time_block": _csv_blk_h,
    "journal_entry": _csv_jrn_h,
    "pomodoro_round": _csv_pom_h,
    "day_context": _csv_ctx_h,
    "daily_reflection": _csv_ref_h,
    "lunch_record": _csv_lun_h,
    "transicao": _csv_trn_h,
    "ajuste_fino": _csv_adj_h,
    "policy_decision": _csv_pol_h,
}

# ── CSV writer functions ──────────────────────────────────────────────────────

def _csv_sleep(engine: SyntheticEngine) -> list[dict]:
    return [d["sleep_record"] for d in engine.day_data]


def _csv_habit(_engine: SyntheticEngine) -> list[dict]:
    rows = []
    for hd in HABITS:
        rows.append({
            "id": f"{UEID_HABIT}_{hd.slug}",
            "name": hd.name,
            "category": hd.category.value,
            "resistance": hd.resistance,
            "lambda_learning": LAMBDA_LEARNING,
            "weight_in_qhe": hd.weight,
            "frequency": "DAILY",
            "created_at": START_DATE.isoformat(),
            "archived": False,
        })
    return rows


def _csv_habit_state(engine: SyntheticEngine) -> list[dict]:
    rows = []
    for d in engine.day_data:
        for hs in d["habit_states"].values():
            rows.append({
                "id": hs.id,
                "date": hs.date.isoformat(),
                "cluster": "oper",
                "habit_id": hs.habit_id,
                "completed": hs.completed,
                "streak_current": hs.streak_current,
                "streak_broken_count": hs.streak_broken_count,
                "effort_minutes": hs.effort_minutes,
            })
    return rows


def _csv_qhe(engine: SyntheticEngine) -> list[dict]:
    return [d["qhe_metrics"] for d in engine.day_data]


def _csv_routine(_engine: SyntheticEngine) -> list[dict]:
    rows = []
    for rou in ROUTINES:
        rows.append({
            "id": f"{UEID_ROU}_{rou.idx}",
            "name": rou.name,
            "period": rou.period.value,
            "routine_type": rou.routine_type,
            "start_time": f"{rou.start_hour:02d}:{rou.start_min:02d}",
            "end_time": f"{rou.end_hour:02d}:{rou.end_min:02d}",
            "mandatory": rou.mandatory,
            "created_at": START_DATE.isoformat(),
        })
    return rows


def _csv_routine_log(engine: SyntheticEngine) -> list[dict]:
    rows = []
    for d in engine.day_data:
        for rlg in d["routine_logs"]:
            rows.append(rlg)
    return rows


def _csv_time_block(engine: SyntheticEngine) -> list[dict]:
    rows = []
    for d in engine.day_data:
        for blk in d["time_blocks"]:
            rows.append(blk)
    return rows


def _csv_journal(engine: SyntheticEngine) -> list[dict]:
    rows = []
    for d in engine.day_data:
        rows.append(d["journal_am"])
        rows.append(d["journal_pm"])
    return rows


def _csv_pomodoro(engine: SyntheticEngine) -> list[dict]:
    rows = []
    for d in engine.day_data:
        for pom in d["pomodoros"]:
            rows.append(pom)
    return rows


def _csv_day_context(engine: SyntheticEngine) -> list[dict]:
    return [d["day_context"] for d in engine.day_data]


def _csv_reflection(engine: SyntheticEngine) -> list[dict]:
    return [d["reflection"] for d in engine.day_data]


def _csv_lunch(engine: SyntheticEngine) -> list[dict]:
    return [d["lunch"] for d in engine.day_data]


def _csv_transicao(engine: SyntheticEngine) -> list[dict]:
    rows = []
    for d in engine.day_data:
        for trn in d["transicoes"]:
            rows.append(trn)
    return rows


def _csv_ajuste_fino(engine: SyntheticEngine) -> list[dict]:
    rows = []
    for d in engine.day_data:
        for adj in d["ajuste_fino"]:
            rows.append(adj)
    return rows


def _csv_policy(engine: SyntheticEngine) -> list[dict]:
    return [d["policy_decision"] for d in engine.day_data]


# ── Weekly Report Writer ───────────────────────────────────────────────────────

def write_weekly_reports(engine: SyntheticEngine, out_dir: Path) -> None:
    """Write 26 weekly markdown narrative reports."""
    WEEKLY_STARTS = [
        (1,  date(2025, 12, 23)),
        (2,  date(2025, 12, 30)),
        (3,  date(2026, 1, 6)),
        (4,  date(2026, 1, 13)),
        (5,  date(2026, 1, 20)),
        (6,  date(2026, 1, 27)),
        (7,  date(2026, 2, 3)),
        (8,  date(2026, 2, 10)),
        (9,  date(2026, 2, 17)),
        (10, date(2026, 2, 24)),
        (11, date(2026, 3, 3)),
        (12, date(2026, 3, 10)),
        (13, date(2026, 3, 17)),
        (14, date(2026, 3, 24)),
        (15, date(2026, 3, 31)),
        (16, date(2026, 4, 7)),
        (17, date(2026, 4, 14)),
        (18, date(2026, 4, 21)),
        (19, date(2026, 4, 28)),
        (20, date(2026, 5, 5)),
        (21, date(2026, 5, 12)),
        (22, date(2026, 5, 19)),
        (23, date(2026, 5, 26)),
        (24, date(2026, 6, 2)),
        (25, date(2026, 6, 9)),
        (26, date(2026, 6, 16)),
    ]

    for week_num, week_start in WEEKLY_STARTS:
        week_end = week_start + timedelta(days=6)
        # Gather week data
        week_data = [d for d in engine.day_data
                      if week_start <= (START_DATE + timedelta(days=d["day_idx"])) <= week_end]

        if not week_data:
            continue

        # Aggregate stats
        qhe_vals = [d["qhe_metrics"]["qhe"] for d in week_data]
        avg_qhe = sum(qhe_vals) / len(qhe_vals)
        sleep_vals = [d["sleep_record"]["sleep_hours"] for d in week_data]
        avg_sleep = sum(sleep_vals) / len(sleep_vals)
        pom_vals = [d["day_context"]["pomodoros_realizados"] for d in week_data]
        total_pom = sum(pom_vals)
        policy_states = [d["policy_decision"]["state"] for d in week_data]
        scenarios = [d["scenario"].name for d in week_data]

        lines = [
            f"# Weekly Report — Week {week_num:02d}",
            f"**{week_start.isoformat()} → {week_end.isoformat()}**",
            "",
            "## Summary",
            f"- Avg Q_HE: **{avg_qhe:.3f}**",
            f"- Avg Sleep: **{avg_sleep:.1f}h**",
            f"- Total Pomodoros: **{total_pom}**",
            f"- Policy: **{policy_states[0]}** (dominant)",
            "",
            "## Daily Breakdown",
            "| Day | Scenario | Q_HE | Sleep | Pomodoros | Policy |",
            "|------|----------|------|-------|-----------|--------|",
        ]

        for d in week_data:
            day_date = START_DATE + timedelta(days=d["day_idx"])
            dow = day_date.strftime("%a")
            lines.append(
                f"| {dow} {day_date.strftime('%Y-%m-%d')} "
                f"| {d['scenario'].name} "
                f"| {d['qhe_metrics']['qhe']:.3f} "
                f"| {d['sleep_record']['sleep_hours']:.1f}h "
                f"| {d['day_context']['pomodoros_realizados']} "
                f"| {d['policy_decision']['state']} |"
            )

        lines.append("")
        lines.append("## Scenario Distribution")
        from collections import Counter
        sc_dist = Counter(scenarios)
        for sc_name, count in sc_dist.most_common():
            lines.append(f"- {sc_name}: {count} days")

        report_path = out_dir / "reports" / f"weekly_{week_num:02d}.md"
        report_path.write_text("\n".join(lines), encoding="utf-8")


# ── CLI Entry Point ───────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="6-Month Synthetic PAV Dataset Generator")
    ap.add_argument("--days", type=int, default=None, help="Limit to first N days")
    ap.add_argument("--dry-run", action="store_true", help="Print stats only, no files")
    ap.add_argument("--out", type=str, default=None, help="Output directory")
    args = ap.parse_args()

    out_str = args.out or str(_ROOT / "datasets" / "6month")
    out_dir = Path(out_str)

    print("=" * 60)
    print("PAV 6-Month Synthetic Dataset Generator")
    print(f"Range: {START_DATE} → {END_DATE} ({TOTAL_DAYS} days)")
    print(f"Output: {out_dir}")
    print(f"Days: {args.days or TOTAL_DAYS}")
    print(f"Seed: {SEED}")
    print("=" * 60)

    print("\n[1/4] Running simulation …")
    engine = SyntheticEngine()
    engine.run(max_days=args.days)

    print(f"      {len(engine.day_data)} days simulated")
    print(f"      Scenarios: {dict(engine._scenarios_dist)}")

    qhe_vals = [d["qhe_metrics"]["qhe"] for d in engine.day_data]
    print(f"      Q_HE range: {min(qhe_vals):.3f} – {max(qhe_vals):.3f} (avg {sum(qhe_vals)/len(qhe_vals):.3f})")

    if args.dry_run:
        print("\n(dry-run — no files written)")
        return

    print(f"\n[2/4] Writing CSV files …")
    write_csvs(engine, out_dir)
    print(f"      csv/ directory ready")

    print(f"\n[3/4] Writing weekly reports …")
    write_weekly_reports(engine, out_dir)
    print(f"      26 weekly reports written")

    print(f"\n[4/4] Validation checklist …")
    checks = [
        ("180 days simulated", len(engine.day_data) == 180),
        ("All days have SleepRecord", all("sleep_record" in d for d in engine.day_data)),
        ("All days have QHEMetrics", all("qhe_metrics" in d for d in engine.day_data)),
        ("All days have PolicyDecision", all("policy_decision" in d for d in engine.day_data)),
        ("Q_HE in [0,1]", all(0 <= d["qhe_metrics"]["qhe"] <= 1 for d in engine.day_data)),
        ("Policy FSM populated", len(engine.policy_engine.history) == 180),
    ]
    all_pass = True
    for name, result in checks:
        status = "✅" if result else "❌"
        print(f"      {status} {name}")
        if not result:
            all_pass = False

    print(f"\n{'='*60}")
    print(f"Done — {'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'}")
    print(f"Output: {out_dir}")
    print(f"Files:")
    for f in sorted(out_dir.glob("*")):
        if f.is_dir():
            for ff in sorted(f.glob("*")):
                print(f"  {f.name}/{ff.name}")
        else:
            print(f"  {f.name}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
