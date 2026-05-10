# PRD: Metrics & Health (Consolidation)

## 1. Objective
Provide a unified view of system performance by consolidating physiological, behavioral, and technical metrics. It serves as the "Sensor" in the cybernetic loop.

## 2. Core Entities
- **DailyMetrics:** Consolidation of Sleep, Energy, Focus, and Task completion.
- **Telemetry:** Automated data points from Timewarrior, Git, and Linter logs.
- **Journaling:** Qualitative input (energy used vs. effectiveness) from Obsidian daily logs.

## 3. Key Features
- **Energy vs. Effectiveness Matrix:** Mapping perceived energy to actual output.
- **Automated Dataview:** Obsidian dashboards that query the SQLite data mesh for real-time visualization.
- **Gap Analysis:** Identifying discrepancies between planned effort and actual execution.

## 4. Integration
- **Reverse Sync:** Pulling "Done" tasks and "Intervals" into the Daily consolidation.
- **Obsidian Frontmatter:** Scanning daily notes for energy and mood tags.
- **Policy Engine:** Feeding the "Energy Ratio" into the Q_HE model.

## 5. Metrics & Success Criteria
- **Metric Integrity:** No gaps in daily data for active Waves.
- **Correlation Tracking:** Identifying which habits most strongly impact dev velocity.
- **Alerting:** Triggering a `RECOVER` policy if health metrics drop below thresholds.