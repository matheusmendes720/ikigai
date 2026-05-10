# PRD: Habit Tracker (Cybernetic Behavior)

## 1. Objective
Quantify and optimize behavioral patterns using the Q_HE (Habitual Efficiency Quotient) model. It aims to reduce cognitive friction and automate routines to free up energy for deep work.

## 2. Core Entities
- **Habit:** Behavioral routines with parameters like Resistance (R), Learning Rate (λ), and Energy Cost.
- **HabitState:** Daily record of execution, current streak, and calculated H(t).
- **QHEMetrics:** Daily aggregation of efficiency, adjusted by energy ratio and streak bonuses.

## 3. Mathematical Model
- **Consolidation:** `H(t) = 1 - e^(-λ * streak)`
- **Energy Required:** `E_req = R * (1 - H(t))`
- **Efficiency Index:** `I = (H(t) * Δs) / (R * (1 - H(t)))`
- **Q_HE:** Weighted average of critical habits (Sleep, Meditation, Workout, etc.).

## 4. Key Features
- **Streak Management:** Tracking streaks across Waves and Cycles.
- **Energy Budgeting:** Estimating today's available "Hardwork Budget" based on Q_HE.
- **Reverse Sync:** Detecting habit completion from logged activities (e.g., "Sleep" from journal, "Workout" from TW).

## 5. Integration
- **Hypervisor:** Q_HE is the primary input for `PolicyDecision` (PUSH/RECOVER).
- **IKIGAI:** Habits are tagged with vectors (Passion, Skill, etc.).
- **Obsidian:** Dataview visualizations of H(t) curves and streak heatmaps.