# PRD: Temporal Engine (Wave/Cycle/Phase)

## 1. Objective
Orchestrate the time-based fractal hierarchy (Wave -> Cycle -> Phase) to provide stable rhythm and scheduled reviews for the "Memory Machine". It ensures alignment between strategic goals (Dreams/Objectives) and operational execution (Metas/Tasks).

## 2. Core Entities
- **Wave (15 days):** The atomic unit of habit consolidation and sprint execution.
- **Cycle (45 days):** Three waves forming a half-quarter for performance stabilization.
- **Phase (180 days):** Four cycles (two quarters) for competency mastery and high-level strategic alignment.

## 3. Key Features
- **Review Operator (Rn):** Automated triggers for Mid-Wave (Day 8), Wave-End (Day 15), Mid-Cycle (Day 30), and Cycle-End (Day 45) reviews.
- **Dynamic Scheduling:** Alignment with HQ (Half-Quarters) and Quarters.
- **Consistency Tracking:** Computation of `c_comp` (Consistency Score) and `ic` (Index of Consistency) to feed the Hypervisor.

## 4. Integration
- **Foreign Keys:** `wave_id` used in Meta and Habit entities to anchor them in time.
- **Reverse Sync:** Updates `WaveMetrics` based on Taskwarrior and Timewarrior logs.
- **Obsidian:** Triggers periodic review notes based on temporal boundaries.

## 5. Metrics & Success Criteria
- 100% of Meta entities must be anchored to a valid `wave_id`.
- Automated detection of "Wave Drift" if `expected_end` shifts.
- Review completion rate > 90%.