# SCALAR DECOMPOSITION: life-ops/planner/ .md Files

**Document:** Living Backlog — Scalar Breakdown of All Subsystems
**Scope:** `Points_of_premisses-task-habits.md`, `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md`, `2026-01-11-study-plan.md`
**Date:** 2026-05-09
**Status:** Living document — commit to repo, update as implementations land

---

## TABLE OF CONTENTS

1. [Mathematical Models (27 total)](#1-mathematical-models)
2. [Entity Types (16 total)](#2-entity-types)
3. [Backlog Items (35 total)](#3-backlog-items)
4. [Module/File Map](#4-modulefile-map)
5. [Integration Matrix](#5-integration-matrix)

---

## 1. MATHEMATICAL MODELS

### MODEL-001: Habit Formation Curve H(t)
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 9.2

**Exact Formula:**
```
H(t) = 1 - e^(-λt)
```
Where λ ≈ 0.1 (learning rate), t in days. At t=15 (WAVE end), H ≈ 0.78. At t=45 (CYCLE end), H ≈ 0.99.

**Python Signature:**
```python
def habit_formation(t: float, lambda_rate: float = 0.1) -> float:
    """Return habit automation level [0, 1] after t days."""
    return 1.0 - math.exp(-lambda_rate * t)
```

**Input/Output:**
- Input: `t: float` (elapsed days, ≥0), `lambda_rate: float` (learning rate, >0)
- Output: `float` in [0, 1]

**Module:** `life/vibe-ops/src/models/habit_engine.py`

**Dependencies:** `math.exp`

---

### MODEL-002: Energy Model E(t)
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 9.5

**Exact Formula:**
```
E(t) = t * e^(-kt)
```
Where k ≈ 0.05 (fatigue coefficient), t in days. Peak occurs at t = 1/k ≈ 20 days (but WAVE closes at t=15 before collapse).

**Python Signature:**
```python
def energy_curve(t: float, k: float = 0.05) -> float:
    """Return available energy at day t of a WAVE. Asymmetric: rises then falls."""
    return t * math.exp(-k * t)
```

**Input/Output:**
- Input: `t: float` (day within WAVE, ≥0), `k: float` (fatigue rate, >0)
- Output: `float` (unscaled energy units)

**Module:** `life/vibe-ops/src/models/habit_engine.py`

**Dependencies:** `math.exp`

---

### MODEL-003: Performance Function P(t)
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 9.6, 14.1

**Exact Formula:**
```
P(t) = E(t) * H(t) / R
     = (t * e^(-kt)) * (1 - e^(-λt)) / R
```
Where R = task resistance/difficulty (1-10 scale).

**Python Signature:**
```python
def performance(t: float, k: float = 0.05, lambda_rate: float = 0.1, resistance: float = 1.0) -> float:
    """Return expected performance output at day t, scaled by task resistance."""
    e_t = energy_curve(t, k)
    h_t = habit_formation(t, lambda_rate)
    return (e_t * h_t) / resistance
```

**Input/Output:**
- Input: `t, k, lambda_rate, resistance`
- Output: `float` (performance units)

**Module:** `life/vibe-ops/src/models/habit_engine.py`

**Dependencies:** MODEL-001, MODEL-002

---

### MODEL-004: Supercompensation Energy Model
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 15

**Exact Formula:**
```
E_super(t) = t * e^(-kt) + A * e^(-(t - t0)^2 / (2σ^2))
```
Where A = supercompensation amplitude, t0 = peak day of recovery boost, σ = width of Gaussian recovery window.

**Python Signature:**
```python
def energy_with_supercompensation(
    t: float,
    k: float = 0.05,
    A: float = 30.0,
    t0: float = 15.0,
    sigma: float = 3.0
) -> float:
    """Energy curve with Gaussian supercompensation bump after rest."""
    base = t * math.exp(-k * t)
    supercomp = A * math.exp(-((t - t0) ** 2) / (2 * sigma ** 2))
    return base + supercomp
```

**Input/Output:**
- Input: `t` plus supercompensation params
- Output: `float`

**Module:** `life/vibe-ops/src/models/habit_engine.py`

**Dependencies:** `math.exp`

---

### MODEL-005: Q_HE — Habit-Efficiency Quotient
**Source:** `Points_of_premisses-task-habits.md` Sec 3

**Exact Formula:**
```
Q_HE(t) = (Σ(w_i * H_i(t)) / Σw_i) * (E(t) / E_max) * (1 + η * S_streak / S_max)
```

Weights: w_sono=0.35, w_med=0.20, w_workout=0.25, w_lunch=0.10. η=0.15. S_max = reference streak (e.g., 30).

**Python Signature:**
```python
def calculate_qhe(
    habits: list[HabitState],
    energy_ratio: float,
    streak: int,
    streak_max: int = 30,
    eta: float = 0.15
) -> float:
    """Compute Habit-Efficiency Quotient in [0, 1+]."""
    weighted_habit = sum(h.weight * h.level for h in habits) / sum(h.weight for h in habits)
    streak_bonus = 1.0 + eta * (streak / streak_max)
    return weighted_habit * energy_ratio * streak_bonus
```

**Input/Output:**
- Input: `habits: list[HabitState]`, `energy_ratio: float` (E(t)/E_max), `streak: int`
- Output: `float` in [0, ~1.15]

**Module:** `life/vibe-ops/src/models/policy_engine.py`

**Dependencies:** MODEL-001 (for H_i(t)), MODEL-002 (for E(t) ratio)

---

### MODEL-006: Review Operator R_n
**Source:** `Points_of_premisses-task-habits.md` Sec 2

**Exact Formula:**
```
R_n(s_t) = {
  H_{n+1} = H_n + α * C_comp * (1 - H_n) - β * σ_E
  k_{n+1} = k_n * (1 - γ * R_qual)
  λ_{n+1} = λ_n * (1 + δ * ΔS_streak)
}
```

Parameters: α∈[0.1,0.3], β∈[0.05,0.15], γ∈[0.1,0.25], δ∈[0.02,0.08].

**Python Signature:**
```python
def review_operator(
    state: HabitState,
    review_quality: ReviewQuality,
    consistency: float,
    energy_variance: float,
    streak_delta: int,
    params: ReviewParams = DEFAULT_REVIEW_PARAMS
) -> HabitState:
    """Apply renormalization operator at review checkpoint."""
    new_h = state.habit_level + params.alpha * consistency * (1 - state.habit_level) - params.beta * energy_variance
    new_k = state.fatigue_k * (1 - params.gamma * review_quality.value)
    new_lambda = state.learning_lambda * (1 + params.delta * streak_delta)
    return state.evolve(habit_level=new_h, fatigue_k=new_k, learning_lambda=new_lambda)
```

**Input/Output:**
- Input: `HabitState`, `ReviewQuality` enum, `consistency: float`, `energy_variance: float`, `streak_delta: int`
- Output: `HabitState` (updated)

**Module:** `life/vibe-ops/src/models/habit_engine.py`

**Dependencies:** `HabitState` dataclass, `ReviewQuality` enum

---

### MODEL-007: Policy Matrix π(s_t)
**Source:** `Points_of_premisses-task-habits.md` Sec 4

**Exact Formula (table-driven):**
```
π(s_t) = f(Q_HE, C_comp, Infrações, TipoDia)
```

| Q_HE | C_comp | Infrações | TipoDia | Policy |
|------|--------|-----------|---------|--------|
| ≥0.85 | ≥0.90 | 0 | Livre/Curso | PUSH |
| [0.70,0.85) | [0.80,0.90) | ≤1 | Any | MAINTAIN |
| [0.60,0.70) | [0.70,0.80) | ≤2 | Any | REDUCE |
| <0.60 | <0.70 | ≥2 | Any | RECOVER |

**Python Signature:**
```python
def policy_matrix(
    qhe: float,
    consistency: float,
    infractions_24h: int,
    day_type: DayType
) -> Policy:
    """Return policy decision based on state vector."""
    if qhe >= 0.85 and consistency >= 0.90 and infractions_24h == 0:
        return Policy.PUSH
    elif qhe >= 0.70 and consistency >= 0.80 and infractions_24h <= 1:
        return Policy.MAINTAIN
    elif qhe >= 0.60 and consistency >= 0.70 and infractions_24h <= 2:
        return Policy.REDUCE
    else:
        return Policy.RECOVER
```

**Input/Output:**
- Input: `qhe: float`, `consistency: float`, `infractions_24h: int`, `day_type: DayType`
- Output: `Policy` enum

**Module:** `life/vibe-ops/src/models/policy_engine.py`

**Dependencies:** MODEL-005 (for Q_HE), `DayType` enum, `Policy` enum

---

### MODEL-008: Hysteresis Function
**Source:** `Points_of_premisses-task-habits.md` Sec 4

**Exact Formula:**
```
π_{t+1} = UPGRADE   if Q_HE ≥ θ_up for 3 consecutive days
          DOWNGRADE if Q_HE ≤ θ_down for 2 consecutive days
          HOLD      otherwise
```
θ_up = 0.80, θ_down = 0.65.

**Python Signature:**
```python
def hysteresis_transition(
    qhe_history: list[float],
    current_policy: Policy,
    theta_up: float = 0.80,
    theta_down: float = 0.65,
    window_upgrade: int = 3,
    window_downgrade: int = 2
) -> PolicyTransition:
    """Determine policy transition with hysteresis to filter noise."""
    recent = qhe_history[-max(window_upgrade, window_downgrade):]
    if len(recent) >= window_upgrade and all(q >= theta_up for q in recent[-window_upgrade:]):
        return PolicyTransition.UPGRADE
    elif len(recent) >= window_downgrade and all(q <= theta_down for q in recent[-window_downgrade:]):
        return PolicyTransition.DOWNGRADE
    return PolicyTransition.HOLD
```

**Input/Output:**
- Input: `qhe_history: list[float]`, `current_policy: Policy`
- Output: `PolicyTransition` enum

**Module:** `life/vibe-ops/src/models/policy_engine.py`

**Dependencies:** MODEL-005, MODEL-007

---

### MODEL-009: Consistency Index C_comp
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 4.1

**Exact Formula:**
```
C_comp = dias_estudados / dias_totais_da_WAVE
```

**Python Signature:**
```python
def consistency_index(days_completed: int, total_days: int = 15) -> float:
    """Return behavioral consistency ratio [0, 1]. Target: >0.90."""
    return days_completed / total_days if total_days > 0 else 0.0
```

**Input/Output:**
- Input: `days_completed: int`, `total_days: int`
- Output: `float`

**Module:** `life/vibe-ops/src/models/analytics.py`

**Dependencies:** None

---

### MODEL-010: Calendar Alignment A_cal
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 4.2

**Exact Formula:**
```
A_cal = entregas_realizadas / workdays_disponiveis
```

**Python Signature:**
```python
def calendar_alignment(deliveries_done: int, workdays_available: int) -> float:
    """Return calendar alignment ratio for work deliverables."""
    return deliveries_done / workdays_available if workdays_available > 0 else 0.0
```

**Input/Output:**
- Input: `deliveries_done: int`, `workdays_available: int`
- Output: `float`

**Module:** `life/vibe-ops/src/models/analytics.py`

**Dependencies:** None

---

### MODEL-011: Consistency Index IC (generic)
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 6.3

**Exact Formula:**
```
IC = days_completed / days_planned
```
Target: IC ≥ 0.85.

**Python Signature:**
```python
def ic_index(completed: int, planned: int) -> float:
    """Generic consistency index."""
    return completed / planned if planned > 0 else 0.0
```

**Input/Output:**
- Input: `completed: int`, `planned: int`
- Output: `float`

**Module:** `life/vibe-ops/src/models/analytics.py`

**Dependencies:** None

---

### MODEL-012: Adaptation Quotient AQ
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 11.1

**Exact Formula:**
```
AQ = (L_final - L_initial) / CYCLE
```
Where L = load level, CYCLE = 45 days.

**Python Signature:**
```python
def adaptation_quotient(load_initial: float, load_final: float, cycle_days: int = 45) -> float:
    """Rate of load absorption between cycles."""
    return (load_final - load_initial) / cycle_days
```

**Input/Output:**
- Input: `load_initial: float`, `load_final: float`, `cycle_days: int`
- Output: `float`

**Module:** `life/vibe-ops/src/models/analytics.py`

**Dependencies:** None

---

### MODEL-013: Cognitive Load Ratio CLR
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 11.2

**Exact Formula:**
```
CLR = Σ Study Hours / Σ Work Hours
```
Target: 0.3 ≤ CLR ≤ 0.5.

**Python Signature:**
```python
def cognitive_load_ratio(study_hours: float, work_hours: float) -> float:
    """Return ratio of learning vs delivery effort."""
    return study_hours / work_hours if work_hours > 0 else float('inf')
```

**Input/Output:**
- Input: `study_hours: float`, `work_hours: float`
- Output: `float`

**Module:** `life/vibe-ops/src/models/analytics.py`

**Dependencies:** None

---

### MODEL-014: Supercompensation Factor SF
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 11.3

**Exact Formula:**
```
SF = P(Segunda) / P(Sexta anterior)
```
Where P = performance proxy (e.g., pomodoros completed, energy self-rating).

**Python Signature:**
```python
def supercompensation_factor(monday_metric: float, friday_metric: float) -> float:
    """Ratio of Monday readiness vs Friday fatigue. SF > 1.0 = good recovery."""
    return monday_metric / friday_metric if friday_metric > 0 else 0.0
```

**Input/Output:**
- Input: `monday_metric: float`, `friday_metric: float`
- Output: `float`

**Module:** `life/vibe-ops/src/models/analytics.py`

**Dependencies:** None

---

### MODEL-015: Cycle Efficiency EC
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 11.4

**Exact Formula:**
```
EC = Resultados_Obtidos / (Energia_Gasta * Tempo)
```

**Python Signature:**
```python
def cycle_efficiency(results: float, energy_spent: float, time_spent: float) -> float:
    """Output per unit of energy-time."""
    denominator = energy_spent * time_spent
    return results / denominator if denominator > 0 else 0.0
```

**Input/Output:**
- Input: `results: float`, `energy_spent: float`, `time_spent: float`
- Output: `float`

**Module:** `life/vibe-ops/src/models/analytics.py`

**Dependencies:** None

---

### MODEL-016: Kaizen Factor κ(t)
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 11.5

**Exact Formula:**
```
κ(t) = (1 + r)^t
```
Where r = daily refinement rate (e.g., 0.01 = 1% improvement/day).

**Python Signature:**
```python
def kaizen_factor(t: int, daily_rate: float = 0.01) -> float:
    """Cumulative marginal improvement over t days."""
    return (1.0 + daily_rate) ** t
```

**Input/Output:**
- Input: `t: int` (days), `daily_rate: float`
- Output: `float`

**Module:** `life/vibe-ops/src/models/analytics.py`

**Dependencies:** None

---

### MODEL-017: Efficiency Index I (Habit Selection)
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 12.2

**Exact Formula:**
```
I = H(s) * Δs / (R * (1 - H(s)))
```
Where H(s) = habit level at streak s, Δs = s - s_prev (streak momentum), R = resistance.

**Python Signature:**
```python
def efficiency_index(habit_level: float, streak: int, prev_streak: int, resistance: float) -> float:
    """Cost-benefit of focusing on a habit today. Higher = better ROI."""
    delta_s = streak - prev_streak
    deficit = 1.0 - habit_level
    if deficit <= 0 or resistance <= 0:
        return float('inf')
    return (habit_level * delta_s) / (resistance * deficit)
```

**Input/Output:**
- Input: `habit_level: float`, `streak: int`, `prev_streak: int`, `resistance: float`
- Output: `float`

**Module:** `life/vibe-ops/src/models/habit_engine.py`

**Dependencies:** None

---

### MODEL-018: UCB Multi-Armed Bandit Score
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 16.2

**Exact Formula:**
```
Score_i = I_i + c * sqrt(ln(T) / n_i)
```
Where I_i = efficiency index, T = total selections across all habits, n_i = times habit i selected, c = exploration constant (~1.414).

**Python Signature:**
```python
def ucb_score(
    efficiency: float,
    total_selections: int,
    habit_selections: int,
    exploration_constant: float = 1.414
) -> float:
    """Upper Confidence Bound score for habit selection."""
    if habit_selections == 0:
        return float('inf')
    bonus = exploration_constant * math.sqrt(math.log(total_selections) / habit_selections)
    return efficiency + bonus
```

**Input/Output:**
- Input: `efficiency: float`, `total_selections: int`, `habit_selections: int`
- Output: `float`

**Module:** `life/vibe-ops/src/models/habit_engine.py`

**Dependencies:** `math.log`, `math.sqrt`, MODEL-017

---

### MODEL-019: Bellman Equation V(S_t)
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 20.1

**Exact Formula:**
```
V(S_t) = max_{a_t} [ R(S_t, a_t) + γ * V(S_{t+1}) ]
R(S_t, a_t) = P_i(t) = E(t) * H_i(t) / R_i
```
Where γ = discount factor (~0.95).

**Python Signature:**
```python
def bellman_value(
    state: SystemState,
    actions: list[Action],
    gamma: float = 0.95,
    depth: int = 0,
    max_depth: int = 10
) -> tuple[Action, float]:
    """Approximate optimal action via Bellman recursion."""
    if depth >= max_depth:
        best = max(actions, key=lambda a: immediate_reward(state, a))
        return best, immediate_reward(state, best)
    best_action, best_value = None, -float('inf')
    for action in actions:
        r = immediate_reward(state, action)
        next_state = state.transition(action)
        _, future_v = bellman_value(next_state, actions, gamma, depth + 1, max_depth)
        total = r + gamma * future_v
        if total > best_value:
            best_value = total
            best_action = action
    return best_action, best_value
```

**Input/Output:**
- Input: `SystemState`, `actions: list[Action]`, `gamma: float`, `max_depth: int`
- Output: `tuple[Action, float]` (best action, its value)

**Module:** `life/vibe-ops/src/models/mdp_engine.py`

**Dependencies:** MODEL-002, MODEL-003

---

### MODEL-020: Knapsack Resource Allocation
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 21.1

**Exact Formula:**
```
max Σ(x_i * P_i(t))
s.t. Σ(x_i * E_req,i) ≤ E_total
x_i ∈ {0, 1}
```

**Python Signature:**
```python
def knapsack_habits(
    habits: list[HabitItem],
    energy_budget: float
) -> list[HabitItem]:
    """Select habits to maximize performance given energy budget."""
    # Greedy by efficiency ratio P_i / E_req,i
    scored = [(h, h.performance / h.energy_required) for h in habits]
    scored.sort(key=lambda x: x[1], reverse=True)
    selected, remaining = [], energy_budget
    for habit, ratio in scored:
        if habit.energy_required <= remaining:
            selected.append(habit)
            remaining -= habit.energy_required
    return selected
```

**Input/Output:**
- Input: `habits: list[HabitItem]`, `energy_budget: float`
- Output: `list[HabitItem]` (selected subset)

**Module:** `life/vibe-ops/src/models/mdp_engine.py`

**Dependencies:** MODEL-003 (for P_i)

---

### MODEL-021: Load Function L(t)
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 9.7

**Exact Formula:**
```
L(t) = (B + α * floor(t / 7)) * 𝟙_work(t)
```
Where B = base load, α = weekly increment, 𝟙_work = indicator (1 on workdays, 0 on rest days).

**Python Signature:**
```python
def load_function(t: int, base_load: float, alpha: float, is_workday: bool) -> float:
    """Step-function load with weekly progression."""
    if not is_workday:
        return 0.0
    return base_load + alpha * (t // 7)
```

**Input/Output:**
- Input: `t: int` (day), `base_load: float`, `alpha: float`, `is_workday: bool`
- Output: `float`

**Module:** `life/vibe-ops/src/models/habit_engine.py`

**Dependencies:** None

---

### MODEL-022: Fitness-Fatigue Model
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 9.7

**Exact Formula:**
```
P(t) = F(t) - f(t)
```
Where F(t) = fitness (positive adaptation), f(t) = fatigue (negative residual).

**Python Signature:**
```python
def fitness_fatigue(fitness: float, fatigue: float) -> float:
    """Net performance = fitness minus fatigue."""
    return fitness - fatigue
```

**Input/Output:**
- Input: `fitness: float`, `fatigue: float`
- Output: `float`

**Module:** `life/vibe-ops/src/models/habit_engine.py`

**Dependencies:** None

---

### MODEL-023: Streak Markov Chain E[s]
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 19.2

**Exact Formula:**
```
E[s] ≈ P(execute) / (1 - P(execute))
P(s → s+1) = 1 - e^(-μs)
```

**Python Signature:**
```python
def expected_streak(execution_probability: float) -> float:
    """Expected streak length given daily execution probability."""
    if execution_probability >= 1.0:
        return float('inf')
    return execution_probability / (1.0 - execution_probability)

def streak_transition_probability(streak: int, mu: float = 0.1) -> float:
    """Probability of maintaining/growing streak."""
    return 1.0 - math.exp(-mu * streak)
```

**Input/Output:**
- Input: `execution_probability: float` or `streak: int, mu: float`
- Output: `float`

**Module:** `life/vibe-ops/src/models/habit_engine.py`

**Dependencies:** `math.exp`

---

### MODEL-024: Newton-Raphson for t* (Optimal Peak)
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 18

**Exact Formula:**
```
f(t) = (1 - e^(-λt))(1 - kt) + λt * e^(-λt) = 0
t_{n+1} = t_n - f(t_n) / f'(t_n)
```

**Python Signature:**
```python
def find_optimal_peak_t(
    k: float = 0.05,
    lambda_rate: float = 0.1,
    t0: float = 10.0,
    tolerance: float = 1e-6,
    max_iter: int = 100
) -> float:
    """Find t* where P(t) is maximized via Newton-Raphson."""
    t = t0
    for _ in range(max_iter):
        exp_term = math.exp(-lambda_rate * t)
        f = (1 - exp_term) * (1 - k * t) + lambda_rate * t * exp_term
        # Derivative f'(t)
        df = lambda_rate * exp_term * (1 - k * t) - k * (1 - exp_term) + lambda_rate * exp_term - lambda_rate**2 * t * exp_term
        if abs(df) < 1e-12:
            break
        t_new = t - f / df
        if abs(t_new - t) < tolerance:
            return t_new
        t = t_new
    return t
```

**Input/Output:**
- Input: `k: float`, `lambda_rate: float`, `t0: float`
- Output: `float` (optimal day t*)

**Module:** `life/vibe-ops/src/models/habit_engine.py`

**Dependencies:** `math.exp`

---

### MODEL-025: WORK_RATIO Conversion
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 1.2

**Exact Formula:**
```
WORK_RATIO = 22 / 30 ≈ 0.7333
f(t) = t * WORK_RATIO
```

**Python Signature:**
```python
WORK_RATIO: float = 22.0 / 30.0

def corridos_to_workdays(total_days: float) -> float:
    return total_days * WORK_RATIO

def workdays_to_corridos(total_workdays: float) -> float:
    return total_workdays / WORK_RATIO
```

**Input/Output:**
- Input: `total_days: float` or `total_workdays: float`
- Output: `float`

**Module:** `life/vibe-ops/src/models/temporal.py`

**Dependencies:** None

---

### MODEL-026: Temporal State S(t)
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 9.4

**Exact Formula:**
```
S(t) = (t mod 7, t mod 45)
```
Note: gcd(7, 45) = 1, ensuring checkpoints never fall on the same weekday.

**Python Signature:**
```python
def temporal_state(t: int) -> tuple[int, int]:
    """Return (day_of_week, day_of_cycle) for t."""
    return (t % 7, t % 45)
```

**Input/Output:**
- Input: `t: int` (elapsed days)
- Output: `tuple[int, int]`

**Module:** `life/vibe-ops/src/models/temporal.py`

**Dependencies:** None

---

### MODEL-027: Wave/Cycle/Phase Progress Tracking
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 6

**Exact Formulas:**
```
REMAINING_WAVE_DAYS = 15 - elapsed_days
REMAINING_WAVE_WORK = 11 - elapsed_workdays
CYCLE_PROGRESS = (elapsed_days / 45) * 100%
```

**Python Signature:**
```python
def wave_progress(elapsed_days: int) -> dict[str, int]:
    return {
        "remaining_days": 15 - elapsed_days,
        "remaining_workdays": 11 - int(elapsed_days * WORK_RATIO),
        "progress_pct": (elapsed_days / 15) * 100
    }

def cycle_progress(elapsed_days: int) -> dict[str, float]:
    return {
        "progress_pct": (elapsed_days / 45) * 100,
        "remaining_days": 45 - elapsed_days
    }
```

**Input/Output:**
- Input: `elapsed_days: int`
- Output: `dict`

**Module:** `life/vibe-ops/src/models/temporal.py`

**Dependencies:** MODEL-025

---

## 2. ENTITY TYPES

### ENTITY-001: Wave
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 2.1

**Pydantic Model:**
```python
class Wave(BaseModel):
    id: str = Field(pattern=r'^W\d+_[A-Za-z]{3}_\d{4}$')  # e.g., W2_Jul_2026
    entity_type: Literal["wave"] = "wave"
    start_date: date
    duration_days: int = Field(default=15, ge=1, le=30)
    status: Literal["active", "completed", "aborted"] = "active"
    habit_focus: list[str] = Field(default_factory=list)  # habit IDs targeted
    target_consistency: float = Field(default=0.90, ge=0.0, le=1.0)
    
    @property
    def end_date(self) -> date:
        return self.start_date + timedelta(days=self.duration_days)
    
    @property
    def mid_wave_date(self) -> date:
        return self.start_date + timedelta(days=7)
```

**Validation Rules:**
- `id` must match pattern `W{N}_{Mmm}_{YYYY}`
- `duration_days` must be 15 (standard) or custom 1-30
- `start_date` must not be in future by more than 1 day (allow same-day creation)

**Relationships:**
- Parent: `Cycle` (FK: `cycle_id`)
- Children: `Habit` (many, via `habit_focus` list)
- Contains: `ReviewEvent` at day 7 (MID_WAVE) and day 15 (WAVE_END)

**CRUD Operations:**
- Create: Auto-generated at CYCLE start or manual via CLI
- Read: Query by date range, by habit, by status
- Update: Only `status` and `habit_focus` mutable after creation
- Delete: Soft-delete (status → "aborted")

**Lifecycle State Machine:**
```
[PLANNED] → [ACTIVE] → {MID_WAVE review} → [ACTIVE] → {WAVE_END review} → [COMPLETED]
                ↓                                              ↓
            [ABORTED] (if IC < 0.60 at MID_WAVE)         [ABORTED] (if IC < 0.85)
```

---

### ENTITY-002: Cycle
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 2.1

**Pydantic Model:**
```python
class Cycle(BaseModel):
    id: str = Field(pattern=r'^C\d+_[A-Za-z]{3}_\d{4}$')
    entity_type: Literal["cycle"] = "cycle"
    start_date: date
    duration_days: int = Field(default=45, ge=30, le=90)
    status: Literal["active", "completed", "aborted"] = "active"
    parent_phase: str = Field(pattern=r'^P\d+$')  # FK → Phase
    waves: list[str] = Field(default_factory=list)  # FKs → Wave.ids
    
    @property
    def half_quarter_date(self) -> date:
        return self.start_date + timedelta(days=22)
    
    @property
    def end_date(self) -> date:
        return self.start_date + timedelta(days=self.duration_days)
```

**Validation Rules:**
- `duration_days` must be 45 (standard) or 30-90 (custom)
- Must contain exactly 3 Waves for standard 45-day cycle
- `parent_phase` must exist in Phase registry

**Relationships:**
- Parent: `Phase` (FK: `parent_phase`)
- Children: `Wave` (3 per standard cycle)
- Contains: `ReviewEvent` at day 30 (MID_CYCLE) and day 45 (CYCLE_END)

**CRUD Operations:**
- Create: Auto-generated at PHASE start or manual
- Read: By date, by phase, by status
- Update: `waves` list append-only, `status` mutable
- Delete: Soft-delete cascades to Waves

**Lifecycle State Machine:**
```
[PLANNED] → [ACTIVE] → {WAVE 1} → {WAVE 2} → {WAVE 3} → {CYCLE_END review} → [COMPLETED]
                ↓ (if Q_HE < 0.60)
            [RECOVER] → [ACTIVE] (after recovery period)
```

---

### ENTITY-003: Phase
**Source:** `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 2.1

**Pydantic Model:**
```python
class Phase(BaseModel):
    id: str = Field(pattern=r'^P\d+$')
    entity_type: Literal["phase"] = "phase"
    start_date: date
    duration_days: int = Field(default=180, ge=90, le=365)
    status: Literal["active", "completed", "aborted"] = "active"
    cycles: list[str] = Field(default_factory=list)  # FKs → Cycle.ids
    mastery_target: str  # e.g., "Python Data Engineering"
    
    @property
    def end_date(self) -> date:
        return self.start_date + timedelta(days=self.duration_days)
    
    @property
    def mid_phase_date(self) -> date:
        return self.start_date + timedelta(days=90)
```

**Validation Rules:**
- `duration_days` must be 180 (standard) or 90-365
- Must contain exactly 4 Cycles for standard 180-day phase
- `mastery_target` required, min 5 chars

**Relationships:**
- Children: `Cycle` (4 per standard phase)
- Linked to: `StudyTopic` (many, via `mastery_target` domain)
- Contains: `ReviewEvent` at day 90 (MID_PHASE) and day 180 (PHASE_END)

**CRUD Operations:**
- Create: Manual at strategic planning time
- Read: By domain, by date range
- Update: `cycles` append-only
- Delete: Soft-delete (rare — phases are strategic)

**Lifecycle State Machine:**
```
[PLANNED] → [ACTIVE] → {CYCLE 1-4} → {MID_PHASE review} → {CYCLE 4} → {PHASE_END} → [COMPLETED]
```

---

### ENTITY-004: Habit
**Source:** `Points_of_premisses-task-habits.md` Sec 3, `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 12

**Pydantic Model:**
```python
class Habit(BaseModel):
    id: str = Field(pattern=r'^habit_[a-z0-9_]+$')
    name: str = Field(min_length=3, max_length=100)
    entity_type: Literal["habit"] = "habit"
    category: Literal["sleep", "meditation", "workout", "nutrition", "study", "work"]
    resistance: float = Field(ge=1.0, le=10.0, default=5.0)
    lambda_learning: float = Field(gt=0.0, default=0.1)
    streak_current: int = Field(ge=0, default=0)
    streak_previous: int = Field(ge=0, default=0)
    streak_max: int = Field(ge=0, default=0)
    habit_level: float = Field(ge=0.0, le=1.0, default=0.0)
    weight_in_qhe: float = Field(ge=0.0, le=1.0, default=0.1)
    status: Literal["active", "paused", "archived"] = "active"
    created_at: date
    
    @property
    def deficit(self) -> float:
        return 1.0 - self.habit_level
    
    @property
    def energy_required(self) -> float:
        return self.resistance * self.deficit
    
    @property
    def efficiency_index(self) -> float:
        delta_s = self.streak_current - self.streak_previous
        if self.deficit <= 0:
            return float('inf')
        return (self.habit_level * delta_s) / (self.resistance * self.deficit)
```

**Validation Rules:**
- `id` unique across all habits
- `weight_in_qhe` sum across all active habits should be ≤ 1.0 (warn if >1.0)
- `habit_level` auto-computed from streak via H(t), but can be overridden

**Relationships:**
- Belongs to: `Wave` (via wave's `habit_focus`)
- Generates: `DecisionRecord` (daily check-in)
- Consumed by: `Q_HE` calculator

**CRUD Operations:**
- Create: Manual or from template
- Read: By category, by level, by streak
- Update: Streak auto-incremented by daily check-in; level auto-recalculated
- Delete: Archive (preserve history)

**Lifecycle State Machine:**
```
[FORMING] → [ACTIVE] → {streak maintained} → [CONSOLIDATED] (H > 0.95)
    ↓ (missed day)                        ↓ (missed day after consolidation)
[RESET] → [FORMING]                   [DEGRADED] → [ACTIVE]
    ↓ (paused intentionally)
[PAUSED] → [ACTIVE]
```

---

### ENTITY-005: StudySession
**Source:** `2026-01-11-study-plan.md` (implicit), `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 3.1

**Pydantic Model:**
```python
class StudySession(BaseModel):
    id: str = Field(pattern=r'^ss_[a-z0-9_]+$')
    entity_type: Literal["study_session"] = "study_session"
    topic_id: str  # FK → StudyTopic
    date: date
    start_time: time
    end_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    material_refs: list[str] = Field(default_factory=list)  # FKs → StudyMaterial
    pomodoros_completed: int = Field(ge=0, default=0)
    notes: str = ""
    energy_level_before: Optional[int] = Field(ge=1, le=10, default=None)
    energy_level_after: Optional[int] = Field(ge=1, le=10, default=None)
    
    @model_validator(mode='after')
    def compute_duration(self):
        if self.end_time and self.start_time and not self.duration_minutes:
            start = datetime.combine(self.date, self.start_time)
            end = datetime.combine(self.date, self.end_time)
            self.duration_minutes = int((end - start).total_seconds() / 60)
        return self
```

**Validation Rules:**
- `end_time` must be after `start_time`
- `duration_minutes` auto-computed or must match time range
- `topic_id` must exist in StudyTopic registry

**Relationships:**
- Parent: `StudyTopic` (FK: `topic_id`)
- Uses: `StudyMaterial` (many, via `material_refs`)
- Tracked by: `TimewarriorInterval` (external, via tags)

**CRUD Operations:**
- Create: Auto on `timew start` with study tag, or manual
- Read: By topic, by date range, by material
- Update: Notes, end_time, energy levels
- Delete: Soft-delete (preserve for analytics)

**Lifecycle State Machine:**
```
[PLANNED] → [IN_PROGRESS] → [COMPLETED] (if duration ≥ planned) / [PARTIAL] (if < planned)
                ↓ (interrupted)
            [INTERRUPTED] → [RESUMED] or [ABANDONED]
```

---

### ENTITY-006: StudyTopic
**Source:** `2026-01-11-study-plan.md` Sec "Material de estudos"

**Pydantic Model:**
```python
class StudyTopic(BaseModel):
    id: str = Field(pattern=r'^st_[a-z0-9_]+$')
    name: str = Field(min_length=3, max_length=200)
    entity_type: Literal["study_topic"] = "study_topic"
    category: Literal["programming", "ai_agents", "frontend", "productivity", "soft_skills"]
    difficulty: Literal["beginner", "intermediate", "advanced"] = "beginner"
    priority: Literal["P0", "P1", "P2", "P3"] = "P2"
    status: Literal["active", "paused", "completed", "backlog"] = "backlog"
    parent_skill: Optional[str] = None  # FK → Skill/Competency
    estimated_hours: float = Field(ge=0.5, default=10.0)
    completed_hours: float = Field(ge=0.0, default=0.0)
    materials: list[str] = Field(default_factory=list)  # FKs → StudyMaterial
    created_at: date
    target_completion: Optional[date] = None
    
    @property
    def progress_pct(self) -> float:
        return min((self.completed_hours / self.estimated_hours) * 100, 100.0) if self.estimated_hours > 0 else 0.0
    
    @property
    def is_overdue(self) -> bool:
        return self.target_completion is not None and date.today() > self.target_completion and self.status != "completed"
```

**Validation Rules:**
- `completed_hours` ≤ `estimated_hours` (warn if exceeded)
- `target_completion` must be after `created_at`
- `priority` P0 = urgent, P3 = backlog

**Relationships:**
- Parent: `Skill` (FK: `parent_skill`)
- Children: `StudyMaterial` (many)
- Generates: `StudySession` (many)
- Linked to: `Wave` (when topic is WAVE focus)

**CRUD Operations:**
- Create: Manual or from curriculum template
- Read: By category, by priority, by progress
- Update: `completed_hours`, `status`, `priority`
- Delete: Archive (preserve for portfolio)

**Lifecycle State Machine:**
```
[BACKLOG] → [ACTIVE] → {sessions accumulate} → [COMPLETED] (progress = 100%)
    ↓ (deprioritized)              ↓ (stalled > 30 days)
[PAUSED] → [ACTIVE]            [STALLED] → [ACTIVE] or [ARCHIVED]
```

---

### ENTITY-007: StudyMaterial
**Source:** `2026-01-11-study-plan.md` Sec "Material de estudos"

**Pydantic Model:**
```python
class StudyMaterial(BaseModel):
    id: str = Field(pattern=r'^sm_[a-z0-9_]+$')
    title: str = Field(min_length=3, max_length=300)
    entity_type: Literal["study_material"] = "study_material"
    material_type: Literal["book", "course", "video", "article", "documentation", "project"]
    url: Optional[str] = None
    file_path: Optional[str] = None
    topic_id: str  # FK → StudyTopic
    status: Literal["unread", "reading", "completed", "reference"] = "unread"
    priority: Literal["P0", "P1", "P2", "P3"] = "P2"
    estimated_minutes: Optional[int] = None
    completed_minutes: int = Field(ge=0, default=0)
    notes: str = ""
    tags: list[str] = Field(default_factory=list)
    
    @property
    def progress_pct(self) -> float:
        if not self.estimated_minutes:
            return 0.0
        return min((self.completed_minutes / self.estimated_minutes) * 100, 100.0)
```

**Validation Rules:**
- At least one of `url` or `file_path` must be provided
- `completed_minutes` ≤ `estimated_minutes`
- `topic_id` must exist

**Relationships:**
- Parent: `StudyTopic` (FK: `topic_id`)
- Used in: `StudySession` (via `material_refs`)

**CRUD Operations:**
- Create: Manual or auto-import from bookmarks
- Read: By topic, by type, by status
- Update: `completed_minutes`, `status`, `notes`
- Delete: Hard-delete allowed (materials are references)

---

### ENTITY-008: ReviewEvent
**Source:** `Points_of_premisses-task-habits.md` Sec 2, `81d33ec8-c354-44c4-b846-575f26cb7ca3_time-lenghts_reviews.md` Sec 5.2

**Pydantic Model:**
```python
class ReviewEvent(BaseModel):
    id: str = Field(pattern=r'^rev_[a-z0-9_]+$')
    entity_type: Literal["review_event"] = "review_event"
    review_type: Literal["MID_WAVE", "WAVE_END", "MID_CYCLE", "CYCLE_END", "MID_PHASE", "PHASE_END"]
    target_id: str  # FK → Wave, Cycle, or Phase
    target_type: Literal["wave", "cycle", "phase"]
    scheduled_date: date
    completed_date: Optional[date] = None
    status: Literal["scheduled", "completed", "skipped", "overdue"] = "scheduled"
    qhe_at_review: Optional[float] = None
    consistency_at_review: Optional[float] = None
    narrative: str = ""  # "O que aprendi?"
    adjustments: list[str] = Field(default_factory=list)  # e.g., ["reduce_load_25%"]
    
    @property
    def is_overdue(self) -> bool:
        return self.status == "scheduled" and date.today() > self.scheduled_date
```

**Validation Rules:**
- `scheduled_date` must align with target's temporal boundaries
- `target_id` + `target_type` must resolve to existing entity
- `narrative` required for status = "completed"

**Relationships:**
- Targets: `Wave`, `Cycle`, or `Phase`
- Triggers: `R_n` operator (MODEL-006)
- Generates: `PolicyDecision` (if Q_HE crosses thresholds)

**CRUD Operations:**
- Create: Auto-generated when parent entity starts
- Read: By date, by status, by target
- Update: All fields mutable until archived
- Delete: Not allowed (append-only audit trail)

**Lifecycle State Machine:**
```
[SCHEDULED] → {date reached} → [DUE] → [COMPLETED] (with narrative) / [SKIPPED] (with reason)
                    ↓
                [OVERDUE] (auto if > 2 days past scheduled)
```

---

### ENTITY-009: PolicyDecision
**Source:** `Points_of_premisses-task-habits.md` Sec 4

**Pydantic Model:**
```python
class PolicyDecision(BaseModel):
    id: str = Field(pattern=r'^pd_[a-z0-9_]+$')
    entity_type: Literal["policy_decision"] = "policy_decision"
    date: date
    policy: Literal["PUSH", "MAINTAIN", "REDUCE", "RECOVER"]
    previous_policy: Optional[Literal["PUSH", "MAINTAIN", "REDUCE", "RECOVER"]] = None
    transition: Literal["UPGRADE", "DOWNGRADE", "HOLD"]
    qhe: float
    consistency: float
    infractions_24h: int
    day_type: Literal["workday_with_course", "workday_free", "weekend", "holiday"]
    setpoints: dict[str, float]  # e.g., {"deep_work": 90, "laborative": 240}
    actions: list[str] = Field(default_factory=list)
    triggered_by: Optional[str] = None  # FK → ReviewEvent or manual
    
    @property
    def is_recover_mode(self) -> bool:
        return self.policy == "RECOVER"
```

**Validation Rules:**
- `qhe` in [0, 1.5]
- `setpoints` must contain at least "deep_work" and "laborative"
- `transition` must be consistent with `policy` vs `previous_policy`

**Relationships:**
- Triggered by: `ReviewEvent` or daily check-in
- Consumed by: Dashboard, daily plan generator
- Affects: `TimeBlock` allocations

**CRUD Operations:**
- Create: Auto by policy engine each morning
- Read: By date, by policy type
- Update: None (immutable record)
- Delete: None (append-only)

---

### ENTITY-010: TimeBlock
**Source:** `life-ops/life_tatics/domain/time_blocks.py`, `vibe-ops/base/IKIGAi.md`

**Pydantic Model:**
```python
class TimeBlock(BaseModel):
    id: str = Field(pattern=r'^tb_[a-z0-9_]+$')
    name: str = Field(min_length=3, max_length=50)
    entity_type: Literal["time_block"] = "time_block"
    block_type: Literal["deep_work", "laborative", "training", "content_lab", "data_review", "kernel"]
    start_time: time
    end_time: time
    day_type: Literal["course_day", "free_day", "weekend"]
    setpoint_minutes: int = Field(ge=15, le=600)
    actual_minutes: Optional[int] = None
    status: Literal["planned", "in_progress", "completed", "skipped"] = "planned"
    policy_id: Optional[str] = None  # FK → PolicyDecision
    
    @property
    def efficiency(self) -> Optional[float]:
        if self.actual_minutes is None or self.setpoint_minutes == 0:
            return None
        return self.actual_minutes / self.setpoint_minutes
```

**Validation Rules:**
- `end_time` > `start_time`
- `actual_minutes` ≤ `setpoint_minutes * 1.5` (warn if exceeded — overclock)
- `block_type` maps to IKIGAi phase (see Data-Mesh enrichment doc)

**Relationships:**
- Constrained by: `PolicyDecision` (FK: `policy_id`)
- Tracked by: `TimewarriorInterval` (external)
- Aggregated into: `DailyMetrics`

**CRUD Operations:**
- Create: Auto-generated from policy each morning
- Read: By day, by type, by status
- Update: `actual_minutes`, `status`
- Delete: Not needed (daily ephemeral)

---

### ENTITY-011: HealthMetrics
**Source:** `Points_of_premisses-task-habits.md` Sec 3 ( SleepRecord, HealthMetrics)

**Pydantic Model:**
```python
class HealthMetrics(BaseModel):
    id: str = Field(pattern=r'^hm_[a-z0-9_]+$')
    date: date
    sleep_hours: float = Field(ge=0.0, le=24.0)
    sleep_quality: Optional[int] = Field(ge=1, le=10, default=None)
    meditation_minutes: int = Field(ge=0, default=0)
    workout_minutes: int = Field(ge=0, default=0)
    workout_type: Optional[str] = None
    lunch_duration_minutes: Optional[int] = Field(ge=0, default=None)
    lunch_light: Optional[bool] = None  # True if ≤ 35min
    energy_morning: Optional[int] = Field(ge=1, le=10, default=None)
    energy_afternoon: Optional[int] = Field(ge=1, le=10, default=None)
    
    @property
    def is_sleep_adequate(self) -> bool:
        return self.sleep_hours >= 6.0
    
    @property
    def is_lunch_optimal(self) -> bool:
        return self.lunch_light is True
```

**Validation Rules:**
- `sleep_hours` 0-24
- `meditation_minutes` + `workout_minutes` ≤ 300 (sanity cap)
- `date` unique per day (one record per day)

**Relationships:**
- Consumed by: `Q_HE` calculator (MODEL-005)
- Source for: `DecisionRecord` (daily check-in)
- Aggregated into: `DailyMetrics`

**CRUD Operations:**
- Create: Manual morning input or from wearable API
- Read: By date range, by metric type
- Update: Same-day only (next day = new record)
- Delete: Not allowed (medical/health audit trail)

---

### ENTITY-012: SleepRecord
**Source:** `Points_of_premisses-task-habits.md` Sec 3

**Pydantic Model:**
```python
class SleepRecord(BaseModel):
    id: str = Field(pattern=r'^sr_[a-z0-9_]+$')
    date: date  # wake-up date
    bed_time: datetime
    wake_time: datetime
    sleep_hours: float = Field(ge=0.0, le=24.0)
    deep_sleep_hours: Optional[float] = None
    rem_sleep_hours: Optional[float] = None
    awakenings: int = Field(ge=0, default=0)
    source: Literal["manual", "wearable", "inferred"] = "manual"
    
    @property
    def is_window_compliant(self) -> bool:
        """True if bed_time in 18-21h and wake_time in 3-5am."""
        bed_hour = self.bed_time.hour
        wake_hour = self.wake_time.hour
        return 18 <= bed_hour <= 21 and 3 <= wake_hour <= 5
```

**Validation Rules:**
- `wake_time` > `bed_time` (or bed_time is previous day)
- `sleep_hours` ≈ (wake_time - bed_time).total_seconds() / 3600 (warn if diff > 1h)

**Relationships:**
- Embedded in: `HealthMetrics` (via `sleep_hours`)
- Source for: `H_sono(t)` habit level

**CRUD Operations:**
- Create: Morning input
- Read: By date, by compliance
- Update: Same-day corrections only
- Delete: Not allowed

---

### ENTITY-013: DecisionRecord
**Source:** `Points_of_premisses-task-habits.md` Sec 3, `vibe-ops/base/IKIGAi.md`

**Pydantic Model:**
```python
class DecisionRecord(BaseModel):
    id: str = Field(pattern=r'^dr_[a-z0-9_]+$')
    date: date
    time_of_day: Literal["morning", "evening"]
    # Morning: "O que preciso fazer hoje?"
    # Evening: "O que fiz ontem que preciso fazer sempre?"
    question: str
    answer: str = Field(min_length=10)
    streak_anchor: Optional[str] = None  # FK → Habit (the "always" habit)
    big_win: Optional[str] = None
    stop_start_continue: Optional[dict] = None  # {"stop": "", "start": "", "continue": ""}
    mood: Optional[int] = Field(ge=1, le=10, default=None)
    
    @property
    def has_streak_insight(self) -> bool:
        return self.streak_anchor is not None
```

**Validation Rules:**
- `answer` minimum 10 characters
- `date` + `time_of_day` unique (one morning, one evening per day)
- `streak_anchor` must exist in Habit registry if provided

**Relationships:**
- References: `Habit` (via `streak_anchor`)
- Source for: Streak mechanics, narrative review quality
- Aggregated into: Weekly review

**CRUD Operations:**
- Create: Manual via CLI prompt
- Read: By date, by habit anchor
- Update: None (immutable after submission)
- Delete: None (journal archive)

---

### ENTITY-014: Project
**Source:** `2026-01-11-study-plan.md` Sec "PROJETOS Gestao / Planejamento"

**Pydantic Model:**
```python
class Project(BaseModel):
    id: str = Field(pattern=r'^proj_[a-z0-9_]+$')
    title: str = Field(min_length=5, max_length=200)
    entity_type: Literal["project"] = "project"
    project_type: Literal["result", "skill", "portfolio", "job_search"]
    status: Literal["backlog", "planning", "active", "paused", "completed", "archived"] = "backlog"
    parent_meta: Optional[str] = None  # FK → MetaEntity (from schema-pydantic-models)
    parent_objective: Optional[str] = None  # FK → ObjectiveEntity
    parent_dream: Optional[str] = None  # FK → DreamEntity
    estimated_size: str = Field(default="8h")  # '4h', '2d', '1w'
    revenue_impact: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"] = "MEDIUM"
    due_date: Optional[date] = None
    tags: list[str] = Field(default_factory=list)
    created_at: date
    completed_at: Optional[date] = None
    
    @property
    def tw_project_key(self) -> Optional[str]:
        if self.parent_dream and self.parent_objective and self.parent_meta:
            return f"{self.parent_dream}.{self.parent_objective}.{self.parent_meta}.{self.id}"
        return None
    
    @property
    def is_overdue(self) -> bool:
        return self.due_date is not None and date.today() > self.due_date and self.status not in ("completed", "archived")
```

**Validation Rules:**
- If any parent FK provided, all three must be provided (full chain)
- `due_date` > `created_at`
- `estimated_size` pattern: `^\d+[hdw]$`

**Relationships:**
- Parents: `DreamEntity`, `ObjectiveEntity`, `MetaEntity` (from Data-Mesh hierarchy)
- Children: `TaskPayload` (many, via upstream_id)
- Linked to: `StudyTopic` (when project is learning-focused)

**CRUD Operations:**
- Create: Manual in Markdown or via CLI
- Read: By status, by hierarchy, by due date
- Update: `status`, `due_date`, `estimated_size`
- Delete: Archive (preserve for portfolio)

---

### ENTITY-015: Skill / Competency
**Source:** `2026-01-11-study-plan.md` Sec "Competencias / habilidades"

**Pydantic Model:**
```python
class Skill(BaseModel):
    id: str = Field(pattern=r'^skill_[a-z0-9_]+$')
    name: str = Field(min_length=3, max_length=100)
    entity_type: Literal["skill"] = "skill"
    category: Literal["programming", "ai_ml", "data_engineering", "frontend", "soft_skills", "language"]
    current_level: Literal["beginner", "intermediate", "advanced", "expert"] = "beginner"
    target_level: Literal["beginner", "intermediate", "advanced", "expert"] = "intermediate"
    status: Literal["active", "paused", "mastered"] = "active"
    study_topics: list[str] = Field(default_factory=list)  # FKs → StudyTopic
    projects_applied: list[str] = Field(default_factory=list)  # FKs → Project
    hours_invested: float = Field(ge=0.0, default=0.0)
    hours_target: float = Field(ge=0.5, default=100.0)
    created_at: date
    
    @property
    def progress_pct(self) -> float:
        level_map = {"beginner": 0, "intermediate": 25, "advanced": 50, "expert": 75}
        current_val = level_map.get(self.current_level, 0)
        target_val = level_map.get(self.target_level, 25)
        if target_val == current_val:
            return 100.0
        return min((current_val / target_val) * 100, 100.0)
```

**Validation Rules:**
- `target_level` must be ≥ `current_level` in progression
- `hours_invested` auto-aggregated from StudySessions
- `name` unique

**Relationships:**
- Parents: None (top-level competency)
- Children: `StudyTopic` (many)
- Applied in: `Project` (many)

**CRUD Operations:**
- Create: Manual during career planning
- Read: By category, by level, by progress
- Update: `current_level`, `hours_invested`, `status`
- Delete: Not allowed (skills are permanent records)

---

### ENTITY-016: DailyMetrics
**Source:** `vibe-ops/specs/schema-pydantic-models.md` Sec 4.1

**Pydantic Model:**
```python
class DailyMetrics(BaseModel):
    date: date
    sleep_hours: Optional[float] = Field(ge=0, le=24, default=None)
    energy_level: Optional[int] = Field(ge=1, le=10, default=None)
    pomodoros_completed: int = Field(ge=0, default=0)
    tasks_completed: int = Field(ge=0, default=0)
    tasks_created: int = Field(ge=0, default=0)
    orphan_tasks_detected: int = Field(ge=0, default=0)
    hours_learn: float = Field(ge=0, default=0.0)
    hours_earn: float = Field(ge=0, default=0.0)
    hours_train: float = Field(ge=0, default=0.0)
    hours_share: float = Field(ge=0, default=0.0)
    hours_review: float = Field(ge=0, default=0.0)
    qhe: Optional[float] = None
    policy: Optional[str] = None
    
    @property
    def total_hardwork_hours(self) -> float:
        return self.hours_learn + self.hours_earn + self.hours_train + self.hours_share + self.hours_review
    
    @property
    def efficiency_ratio(self) -> Optional[float]:
        # η = hardwork_real / setpoint_previsto (setpoint injected at runtime)
        return None
    
    @property
    def clr(self) -> Optional[float]:
        if self.hours_earn == 0:
            return None
        return self.hours_learn / self.hours_earn
```

**Validation Rules:**
- `date` unique (one record per day)
- Sum of all hours ≤ 24
- `qhe` in [0, 1.5] if provided

**Relationships:**
- Aggregates: `HealthMetrics`, `TimewarriorInterval`, `TaskSnapshot`
- Source for: Weekly review, trend analysis
- Consumed by: `PolicyDecision` generator

**CRUD Operations:**
- Create: Auto by nightly cron (reverse sync)
- Read: By date range, by metric
- Update: Manual corrections for morning inputs
- Delete: Not allowed (analytics audit trail)

---

## 3. BACKLOG ITEMS

### BL-001: Discretize H(t) and E(t) for Delta-t = 1 day
**Description:** Convert continuous habit formation and energy curves to daily discrete operators for CLI computation.
**Priority:** P0
**Effort:** S
**Dependencies:** None
**Files Affected:** `life/vibe-ops/src/models/habit_engine.py`
**Integration Points:** Data-Mesh (daily metrics), Obsidian (daily note frontmatter)

---

### BL-002: Implement Review Operator R_n with Triggers at 7/15/30/45
**Description:** Build the renormalization operator that recalibrates lambda, k, and state vector at review checkpoints.
**Priority:** P0
**Effort:** M
**Dependencies:** BL-001
**Files Affected:** `life/vibe-ops/src/models/habit_engine.py`, `life/vibe-ops/src/decorators/scheduler.py`
**Integration Points:** Data-Mesh (review events), Obsidian (review note templates)

---

### BL-003: Calculate Q_HE with Base Weights + UCB Adaptation
**Description:** Implement the Habit-Efficiency Quotient calculator with fixed weights and optional UCB-driven weight evolution.
**Priority:** P0
**Effort:** M
**Dependencies:** BL-001
**Files Affected:** `life/vibe-ops/src/models/policy_engine.py`
**Integration Points:** Data-Mesh (daily metrics), TW (urgency modifier)

---

### BL-004: Policy Matrix π(s_t) with 2-3 Day Hysteresis
**Description:** Build the state-to-policy mapper with hysteresis to prevent oscillation.
**Priority:** P0
**Effort:** M
**Dependencies:** BL-003
**Files Affected:** `life/vibe-ops/src/models/policy_engine.py`
**Integration Points:** Data-Mesh (policy decisions), Obsidian (daily plan template)

---

### BL-005: Map "O que fazer sempre?" → Streak Index
**Description:** Connect evening decision records to streak mechanics, creating/updating streak anchors.
**Priority:** P1
**Effort:** S
**Dependencies:** None
**Files Affected:** `life/vibe-ops/src/models/decision.py`
**Integration Points:** Data-Mesh (decision records), Obsidian (journal entries)

---

### BL-006: Prepare Data-Mesh Schema for Cross-Domain
**Description:** Define the SQLite/DuckDB schema for cross-domain analytics (habits → work → finance).
**Priority:** P1
**Effort:** L
**Dependencies:** None
**Files Affected:** `life/vibe-ops/src/mesh/schema.py`
**Integration Points:** Data-Mesh (core), TW (reverse sync), Timewarrior (intervals)

---

### BL-007: Implement Wave/Cycle/Phase Temporal Engine
**Description:** Build the fractal temporal model with automatic checkpoint scheduling.
**Priority:** P0
**Effort:** M
**Dependencies:** BL-002
**Files Affected:** `life/vibe-ops/src/models/temporal.py`
**Integration Points:** Data-Mesh (entity registry), Obsidian (progress dashboards)

---

### BL-008: Build Study Topic Tracker
**Description:** Implement CRUD for StudyTopic, StudyMaterial, and StudySession with progress aggregation.
**Priority:** P1
**Effort:** M
**Dependencies:** None
**Files Affected:** `life/vibe-ops/src/models/study.py`
**Integration Points:** Data-Mesh (topic registry), Obsidian (study notes)

---

### BL-009: Build Skill/Competency Tracker
**Description:** Map study topics and projects to skill progression with level advancement logic.
**Priority:** P2
**Effort:** M
**Dependencies:** BL-008
**Files Affected:** `life/vibe-ops/src/models/skills.py`
**Integration Points:** Data-Mesh (skill registry), Obsidian (competency map)

---

### BL-010: Implement Newton-Raphson t* Solver
**Description:** Numerical solver for optimal peak day within a WAVE.
**Priority:** P2
**Effort:** S
**Dependencies:** BL-001
**Files Affected:** `life/vibe-ops/src/models/habit_engine.py`
**Integration Points:** Data-Mesh (analytics), Obsidian (WAVE planning notes)

---

### BL-011: Implement UCB Multi-Armed Bandit for Habit Selection
**Description:** Rank habits by UCB score to balance exploration vs exploitation.
**Priority:** P2
**Effort:** S
**Dependencies:** BL-003
**Files Affected:** `life/vibe-ops/src/models/habit_engine.py`
**Integration Points:** Data-Mesh (habit rankings), TW (daily priority tag)

---

### BL-012: Implement Knapsack Daily Habit Selector
**Description:** Given energy budget E_total, select optimal habit subset maximizing performance.
**Priority:** P1
**Effort:** M
**Dependencies:** BL-003, BL-011
**Files Affected:** `life/vibe-ops/src/models/mdp_engine.py`
**Integration Points:** Data-Mesh (daily plan), Obsidian (habit checklist)

---

### BL-013: Implement Bellman MDP Approximation
**Description:** Approximate optimal habit focus using Bellman equation with finite horizon.
**Priority:** P2
**Effort:** L
**Dependencies:** BL-012
**Files Affected:** `life/vibe-ops/src/models/mdp_engine.py`
**Integration Points:** Data-Mesh (policy optimization), Obsidian (strategy notes)

---

### BL-014: Build HealthMetrics Input CLI
**Description:** Morning survey CLI for sleep, energy, meditation, workout inputs.
**Priority:** P0
**Effort:** S
**Dependencies:** None
**Files Affected:** `life/vibe-ops/src/cli/health_input.py`
**Integration Points:** Data-Mesh (health store), Obsidian (daily note)

---

### BL-015: Build Daily Dashboard Generator
**Description:** Generate daily plan with setpoints based on policy, Q_HE, and day type.
**Priority:** P0
**Effort:** M
**Dependencies:** BL-003, BL-004, BL-014
**Files Affected:** `life/vibe-ops/src/cli/daily_plan.py`
**Integration Points:** Data-Mesh (metrics), Obsidian (daily note), TW (task list)

---

### BL-016: Build Reverse Sync Pipeline
**Description:** Nightly cron that exports TW + Timewarrior data, computes metrics, updates analytics DB.
**Priority:** P0
**Effort:** L
**Dependencies:** BL-006
**Files Affected:** `life/vibe-ops/src/pipeline/reverse_sync.py`
**Integration Points:** Data-Mesh (analytics DB), TW (export), Timewarrior (export)

---

### BL-017: Build Orphan Task Triager
**Description:** Detect TW tasks without upstream_id, generate triagem.md proposals.
**Priority:** P1
**Effort:** M
**Dependencies:** BL-016
**Files Affected:** `life/vibe-ops/src/pipeline/triager.py`
**Integration Points:** Data-Mesh (orphan detection), Obsidian (triagem.md)

---

### BL-018: Implement Streak Markov Chain Analytics
**Description:** Compute expected streak length and transition probabilities.
**Priority:** P2
**Effort:** S
**Dependencies:** BL-005
**Files Affected:** `life/vibe-ops/src/models/habit_engine.py`
**Integration Points:** Data-Mesh (streak analytics), Obsidian (habit dashboard)

---

### BL-019: Build Supercompensation Tracker
**Description:** Track recovery quality via SF (Monday vs Friday performance ratio).
**Priority:** P2
**Effort:** S
**Dependencies:** BL-014
**Files Affected:** `life/vibe-ops/src/models/analytics.py`
**Integration Points:** Data-Mesh (weekly metrics), Obsidian (weekly review)

---

### BL-020: Implement Cognitive Load Ratio Monitor
**Description:** Alert when CLR drops below 0.3 (obsolescence risk) or exceeds 0.6 (OKR risk).
**Priority:** P1
**Effort:** S
**Dependencies:** BL-016
**Files Affected:** `life/vibe-ops/src/models/analytics.py`
**Integration Points:** Data-Mesh (alerts), Obsidian (weekly review), TW (tag suggestions)

---

### BL-021: Build IKIGAi ROI Calculator
**Description:** Cross time spent with IKIGAi vectors to compute multidimensional ROI.
**Priority:** P2
**Effort:** M
**Dependencies:** BL-016
**Files Affected:** `life/vibe-ops/src/models/ikigai.py`
**Integration Points:** Data-Mesh (ROI analytics), GnuCash/fin_ops (financial ROI)

---

### BL-022: Implement TimeBlock Scheduler
**Description:** Generate time blocks based on policy, day type, and setpoints.
**Priority:** P0
**Effort:** M
**Dependencies:** BL-004
**Files Affected:** `life/vibe-ops/src/models/scheduler.py`
**Integration Points:** Data-Mesh (schedule store), Timewarrior (block tags)

---

### BL-023: Build Weekly Review Generator
**Description:** Aggregate daily metrics, compute trends, generate weekly_review.md.
**Priority:** P1
**Effort:** M
**Dependencies:** BL-016
**Files Affected:** `life/vibe-ops/src/cli/weekly_review.py`
**Integration Points:** Data-Mesh (aggregations), Obsidian (weekly review note)

---

### BL-024: Implement Project Hierarchy Validator
**Description:** Validate FK chains (Dream → Objective → Meta → Project) before TW push.
**Priority:** P0
**Effort:** M
**Dependencies:** None
**Files Affected:** `life/vibe-ops/src/pipeline/validator.py`
**Integration Points:** Data-Mesh (entity registry), TW (project hierarchy)

---

### BL-025: Build Task Payload Generator
**Description:** Convert Markdown planning entities to TaskPayload for TW injection.
**Priority:** P0
**Effort:** M
**Dependencies:** BL-024
**Files Affected:** `life/vibe-ops/src/pipeline/payload_generator.py`
**Integration Points:** Data-Mesh (payload contract), TW (tasklib injection)

---

### BL-026: Implement YAML Frontmatter Parser
**Description:** Parse Markdown files, extract YAML frontmatter, route to correct Pydantic model.
**Priority:** P0
**Effort:** M
**Dependencies:** None
**Files Affected:** `life/vibe-ops/src/pipeline/frontmatter_parser.py`
**Integration Points:** Data-Mesh (entity ingestion), Obsidian (vault files)

---

### BL-027: Build Streamlit BI Dashboard
**Description:** Localhost dashboard for burndown, IKIGAi balance, habit radar, energy curves.
**Priority:** P2
**Effort:** L
**Dependencies:** BL-016, BL-021
**Files Affected:** `life/vibe-ops/src/bi/dashboard.py`
**Integration Points:** Data-Mesh (analytics DB), SQLite/DuckDB

---

### BL-028: Implement WORK_RATIO Temporal Conversions
**Description:** Convert between calendar days and workdays throughout the pipeline.
**Priority:** P1
**Effort:** XS
**Dependencies:** None
**Files Affected:** `life/vibe-ops/src/models/temporal.py`
**Integration Points:** Data-Mesh (all date computations), Obsidian (progress tracking)

---

### BL-029: Build Curriculum Template for Programming + AI Agents
**Description:** Structured study plan template with topics, materials, and milestones.
**Priority:** P1
**Effort:** M
**Dependencies:** BL-008
**Files Affected:** `life-ops/planner/curriculum_programming_ai.md`
**Integration Points:** Obsidian (curriculum vault), Data-Mesh (topic registry)

---

### BL-030: Build Job Search Tracker
**Description:** Track applications, companies, stages, and outcomes with outreach metrics.
**Priority:** P1
**Effort:** M
**Dependencies:** None
**Files Affected:** `life/vibe-ops/src/models/job_search.py`
**Integration Points:** Data-Mesh (opportunity registry), Obsidian (job pipeline note)

---

### BL-031: Implement Infraction Detection Engine
**Description:** Auto-detect policy violations (sleep < 6h, missed meditation, etc.) from HealthMetrics.
**Priority:** P1
**Effort:** S
**Dependencies:** BL-014
**Files Affected:** `life/vibe-ops/src/models/infractions.py`
**Integration Points:** Data-Mesh (infraction log), Obsidian (daily note alerts)

---

### BL-032: Build Recovery Mode Handler
**Description:** When policy = RECOVER, generate recovery protocol (cancel hardwork, 9h sleep, review).
**Priority:** P0
**Effort:** S
**Dependencies:** BL-004, BL-031
**Files Affected:** `life/vibe-ops/src/cli/recovery_handler.py`
**Integration Points:** Data-Mesh (recovery log), TW (task rescheduling), Obsidian (recovery note)

---

### BL-033: Implement Hypervisor Setpoint Calculator
**Description:** Core engine that computes daily setpoints from context (course day, energy, deadlines).
**Priority:** P0
**Effort:** M
**Dependencies:** BL-003, BL-004
**Files Affected:** `life/vibe-ops/src/models/hypervisor.py`
**Integration Points:** Data-Mesh (setpoint store), Obsidian (daily plan), TW (priority injection)

---

### BL-034: Build Content Lab Workflow
**Description:** Capture 1 learning/day, auto-generate post/outline from study sessions.
**Priority:** P2
**Effort:** M
**Dependencies:** BL-008
**Files Affected:** `life/vibe-ops/src/cli/content_lab.py`
**Integration Points:** Obsidian (content draft), Data-Mesh (content metrics)

---

### BL-035: Implement Kaizen Factor Tracking
**Description:** Track daily 1% improvement rate across processes.
**Priority:** P3
**Effort:** XS
**Dependencies:** BL-016
**Files Affected:** `life/vibe-ops/src/models/analytics.py`
**Integration Points:** Data-Mesh (trend analytics), Obsidian (quarterly review)

---

## 4. MODULE/FILE MAP

```
life/vibe-ops/src/
├── models/
│   ├── habit_engine.py       # MODEL-001 through MODEL-004, MODEL-006, MODEL-017, MODEL-018, MODEL-021, MODEL-022, MODEL-023, MODEL-024
│   ├── policy_engine.py      # MODEL-005, MODEL-007, MODEL-008
│   ├── temporal.py           # MODEL-025, MODEL-026, MODEL-027, BL-007, BL-028
│   ├── analytics.py          # MODEL-009 through MODEL-016, MODEL-019, MODEL-020, BL-019, BL-020, BL-035
│   ├── mdp_engine.py         # MODEL-019, MODEL-020, BL-012, BL-013
│   ├── study.py              # ENTITY-005, ENTITY-006, ENTITY-007, BL-008
│   ├── skills.py             # ENTITY-015, BL-009
│   ├── decision.py           # ENTITY-013, BL-005
│   ├── health.py             # ENTITY-011, ENTITY-012, BL-014
│   ├── infractions.py        # BL-031
│   ├── hypervisor.py         # BL-033
│   └── ikigai.py             # BL-021
├── cli/
│   ├── daily_plan.py         # BL-015
│   ├── weekly_review.py      # BL-023
│   ├── recovery_handler.py   # BL-032
│   ├── content_lab.py        # BL-034
│   └── health_input.py       # BL-014
├── pipeline/
│   ├── frontmatter_parser.py # BL-026
│   ├── validator.py          # BL-024
│   ├── payload_generator.py  # BL-025
│   ├── reverse_sync.py       # BL-016
│   └── triager.py            # BL-017
├── mesh/
│   └── schema.py             # BL-006
├── bi/
│   └── dashboard.py          # BL-027
└── models/ (entities)
    ├── wave.py               # ENTITY-001
    ├── cycle.py              # ENTITY-002
    ├── phase.py              # ENTITY-003
    ├── habit.py              # ENTITY-004
    ├── review_event.py       # ENTITY-008
    ├── policy_decision.py    # ENTITY-009
    ├── time_block.py         # ENTITY-010
    ├── daily_metrics.py      # ENTITY-016
    ├── project.py            # ENTITY-014
    └── job_search.py         # BL-030
```

---

## 5. INTEGRATION MATRIX

| Component | Data-Mesh | Taskwarrior | Timewarrior | Obsidian | GnuCash/fin_ops |
|-----------|-----------|-------------|-------------|----------|-----------------|
| Q_HE Calculator | Writes daily metrics | Reads urgency | Reads intervals | Writes daily note frontmatter | — |
| Policy Engine | Writes policy decisions | Injects priority tags | — | Writes plan note | — |
| Review Operator | Writes review events | Reschedules tasks | — | Creates review note | — |
| Habit Engine | Writes habit states | — | Tags habit intervals | Updates habit dashboard | — |
| Temporal Engine | Manages WAVE/CYCLE/PHASE entities | Sets project deadlines | — | Creates progress charts | — |
| Study Tracker | Manages topic registry | Creates study tasks | Tracks study time | Manages study notes | — |
| Reverse Sync | Reads TW export, TW intervals | Exports data | Exports data | Updates metrics | — |
| Hypervisor | Computes setpoints | Adjusts daily task list | Suggests time blocks | Generates daily plan | — |
| IKIGAi ROI | Computes ROI scores | — | Reads time by tag | Displays balance chart | Reads financial data |
| Orphan Triager | Detects orphans | Proposes project fixes | — | Generates triagem.md | — |

---

## APPENDIX A: Trigger Calendar

| Day | Trigger | Operator | Output |
|-----|---------|----------|--------|
| 7 | MID_WAVE | R_n partial | Adjust load if C_comp < 0.90 |
| 15 | WAVE_END | R_n full + C_comp eval | Wave complete / abort decision |
| 30 | MID_CYCLE | R_n + AQ calc | Cycle health check |
| 45 | CYCLE_END | R_n + full analytics | Cycle report + next cycle plan |
| 90 | MID_PHASE | Strategic review | Phase adjustment |
| 180 | PHASE_END | Maestria assessment | Phase report + next phase plan |
| Daily 04:30 | Morning survey | HealthMetrics input | Q_HE + Policy + Setpoints |
| Daily 19:00 | Evening review | DecisionRecord + Reverse Sync | Feedback loop closure |
| Nightly | Cron | Reverse Sync pipeline | DailyMetrics update |

---

## APPENDIX B: Formula Quick Reference

| Symbol | Formula | Module |
|--------|---------|--------|
| H(t) | 1 - e^(-λt) | habit_engine.py |
| E(t) | t * e^(-kt) | habit_engine.py |
| P(t) | E(t) * H(t) / R | habit_engine.py |
| Q_HE | (Σw_i*H_i/Σw_i) * (E/E_max) * (1 + η*S/S_max) | policy_engine.py |
| R_n | H+α*C*(1-H)-β*σ_E, k*(1-γ*R), λ*(1+δ*ΔS) | habit_engine.py |
| π(s_t) | Table-driven by Q_HE, C_comp, Infrações | policy_engine.py |
| C_comp | dias_estudados / dias_totais | analytics.py |
| IC | days_completed / days_planned | analytics.py |
| AQ | (L_final - L_initial) / CYCLE | analytics.py |
| CLR | ΣStudy / ΣWork | analytics.py |
| SF | P(Mon) / P(Fri_prev) | analytics.py |
| I | H(s)*Δs / (R*(1-H(s))) | habit_engine.py |
| UCB | I_i + c*√(ln(T)/n_i) | habit_engine.py |
| Bellman | V(S_t) = max[R(S_t,a_t) + γ*V(S_{t+1})] | mdp_engine.py |
| Knapsack | max Σx_i*P_i s.t. Σx_i*E_req,i ≤ E_total | mdp_engine.py |
| WORK_RATIO | 22/30 ≈ 0.7333 | temporal.py |
| κ(t) | (1 + r)^t | analytics.py |

---

*End of Scalar Decomposition. This document is append-only. Update status fields as backlog items are completed.*
