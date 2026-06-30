# Algorithmic Life OS: Design Systems & Knowledge Tracking


---

## 🔌 Central Engine Reference

> **Path:** `strategics/planning-with-files/` · **Update:** `cd strategics/planning-with-files && git pull`

All long-running agentic tasks in this repo use the canonical planning engine
(planning-with-files v3.1.3, 279+ commits) cloned at `strategics/planning-with-files/`.

**Route map:**
- `skills/` — SKILL.md standard for 60+ agents (Claude Code, Codex, Cursor, Kiro, OpenCode, Hermes, etc.)
- `commands/` — slash commands (`/plan-goal`, `/plan-loop`, `/plan-status`, `/plan-attest`)
- `templates/` — task_plan.md, loop.md, autonomous variants
- `docs/` — evals.md, perf-notes.md, attestation-locking.md, integration guides
- `examples/` — real-world usage examples

**Update policy:** Run `git pull` in `strategics/planning-with-files/` monthly or when
a new version is announced. The engine is source-of-truth for the planning loop
semantics (completion gate, hash attestation, parallel isolation, etc.).

---

This document maps the many layers of the Algorithmic Life OS design system. It drills down from high-level strategic planning and meta-heuristics, through tactical timelines and Project Management Office (PMO) structures, down to granular code execution and daily knowledge consolidation.

## 1. Strategic Planning & Meta-Heuristics
At the highest level, the system defines the broad strokes of personal and professional objectives.
- **Ikigai Alignment:** All actions map to a core life-purpose vector.
- **Self-Evolving Meta-Heuristics:** The cybernetic policy engine dynamically adjusts states (e.g., `PUSH`, `MAINTAIN`, `RECOVER`) based on historical performance, preventing burnout and ensuring sustainable momentum.
- **Strategic Horizons:** Annual and quarterly objectives that serve as the "North Star".

## 2. Tactical Revisions & Timelines
Goals are broken down into actionable timeframes, ensuring steady progress and regular course correction.
- **Cycles & Waves:** 
  - 1 Cycle = 1.5 Months (3 Waves).
  - 1 Wave = 3 Weeks (15 Work-days).
- **Reviews:** End-of-cycle audits to review KPIs and adjust the next wave's targets.

## 3. Project Management Office (PMO) & Code Execution
This layer bridges planning with hard engineering execution.

### PMO Artifacts
- **Roadmaps & Study-Backlogs:** Unified queues for both theoretical learning and practical engineering tasks.
- **Code-Backlogs & Changelogs:** Automated tracking of completed milestones.

### Hard Execution Tracking (VCS)
Tracking execution in real code via GitHub integration.
- **Issues & PRs:** Mapping weekly tactical goals directly to GitHub Issues.
- **Code Reviews:** Capturing feedback loops.
- **KPIs & OKRs (Telemetry):**
  - Commit velocity and Lines of Code (LOC) effectively merged.
  - Time-to-resolution for issues.
  - Identification of Mental Models applied in commits (e.g., `[MM: Cybernetics]`).

## 4. Knowledge Planning & Study (The Obsidian Vault)
The Obsidian vault is the structured brain where learning is mapped and connected.

### Level of Study Hierarchy
- **Weekly-Goals & Field Area:** The primary learning focus of the week.
- **Applications:** Real-world use cases of the knowledge.
- **Feature:** Specific functional capabilities being studied.
- **Requisites:** Dependencies and prior knowledge required.
- **Main-Topics & Subject-Related Sub-Topics:** Granular breakdown of the subject matter.

## 5. Daily Knowledge Report Journaling & Consolidation
The micro-level tracking of daily habits, study ops, and cognitive consolidation, bridging the gap between theory (Obsidian) and practice (GitHub).

### Daily Journaling
- **Logging Learnings:** Documenting the day's insights and how they connect to existing mental models.
- **Consolidation Tracking:** Tracking spaced repetition and active recall.

### Code Execution Telemetry
The true test of knowledge consolidation is its application in code.
- **Telemetry Hooks:** Using git hooks (e.g., `post-commit` or `pre-push`) to parse commit messages for Mental Model tags.
- **Data Model Pipeline:** The `KnowledgeTelemetryPipeline` extracts models (e.g., `#mental-model:xyz`) from `git log` and generates `DailyKnowledgeReport` entities.
- **KPI Mapping:** By measuring how often a studied mental model appears in merged code, the system generates a definitive KPI of *Knowledge Consolidation*.
