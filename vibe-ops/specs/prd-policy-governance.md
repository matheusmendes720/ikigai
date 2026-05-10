# PRD: Policy & Governance (Hypervisor)

## 1. Objective
The "Brain" of the "Memory Machine". It makes autonomous decisions about the operational regime based on performance data and health metrics, preventing burnout and maximizing output.

## 2. Operational Regimes (PolicyState)
- **PUSH:** Maximize output (9h hardwork), high intensity.
- **MAINTAIN:** Standard budget and rhythm.
- **REDUCE:** Lower intensity (-25% budget), increased breaks.
- **RECOVER:** Cancel hardwork, focus on sleep and reviews.

## 3. Decision Matrix (Hypervisor)
- **Inputs:** Q_HE, Consistency (`c_comp`), Infra-day violations, and Day Type (Workday/Holiday).
- **Hysteresis:** Logic to prevent rapid switching (requires 3 days for upgrade, 2 days for downgrade).
- **Output:** `PolicyDecision` with hardwork budget, sleep target, and recommendations.

## 4. Key Features
- **Dynamic Budgeting:** Adjusting Taskwarrior due dates and priorities based on current Policy.
- **Epistemic Effort Allocation:** Adjusting the `CLR` (Study/Work ratio) based on the regime.
- **Safety Triggers:** Forced `RECOVER` on critical health drops.

## 5. Integration
- **CLI/TUI:** Displaying current regime and budgets.
- **Middleware:** Filtering Task payloads based on current regime.
- **Telemetry:** Logging policy transitions for long-term optimization.