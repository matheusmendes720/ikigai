# Algorithmic Life OS: Systemic Architecture & Tracking Framework


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

## 🌐 LangGraph Dev Runtime

> **Config:** `langgraph.json` · **Entry point:** `vibe-ops/src/langgraph_entry.py`
>
> All 5 agentic flows (1 PAE-Maintainer + 4 swarm workflows) run as a single `langgraph dev` server.
> The langgraph SDK is used only as a thin adapter — all business logic stays in
> the existing custom Python graphs.
>
> Quick start: `make install && make dev` (Studio at http://localhost:2024)
>
> 5 graphs: `pae_maintainer`, `quarterly_replan`, `test_de_fogo_rollup`, `correction_protocol`, `dream_falsification`
> See `LANGRAPH_DEV.md` for full architecture and update policy.

This document outlines the multi-layered design system for the Algorithmic Life OS, bridging abstract strategic planning with hard, code-level execution and daily knowledge tracking. It establishes a cybernetic loop of self-evolving meta-heuristics driven by OKRs, KPIs, and real-time telemetry.

---

## 1. Strategic Planning & Meta-Heuristics (The Macro Level)
At the highest level, the system is governed by the **Ikigai Planning** and **Dream** objectives. This layer relies on self-evolving meta-heuristics to align long-term vision with actionable cycles.

* **Annual & Quarterly Horizons:** Defining the broad strokes of what needs to be achieved. 
* **Self-Evolving Meta-Heuristics:** The system adjusts its own parameters (e.g., policy engine states: PUSH, MAINTAIN, REDUCE, RECOVER) based on historical performance and capacity limits.
* **Prioritization Concepts:** 
  * Difficulty vs. Importance
  * Progressions & Past Experiences

---

## 2. Timelines & Tactical Revisions (The Meso Level)
Breaking down strategic goals into manageable, trackable units.

* **Monthly & Weekly Planning:** Formulating specific *Metas* (Goals).
* **Wave Execution (3x-Waves):** 
  * 1 Cycle (Cc) = 1.5 Months / 3 Waves.
  * 3x Weeks = 15 Work-days.
  * Balancing intense execution with required audit and review phases.
* **Reviews & Reports:** Continuous feedback loops at the end of each cycle to recalibrate the tactical approach.

---

## 3. Project Management Office (PMO) & Code-Level Execution
The bridge between planning and actual software engineering or deep study execution.

### Artifacts & Backlogs
* **Roadmaps:** High-level feature timelines.
* **Study Backlogs & Code Backlogs:** A unified queue of theoretical learning and practical coding tasks.
* **Changelogs:** Automated tracking of completed milestones.

### GitHub / VCS Tracking (The Hard Execution)
* **Issues & Pull Requests:** Mapping weekly goals directly to GitHub Issues.
* **Code Reviews:** Tracking feedback loops and code quality metrics.
* **Telemetry & Execution Tracking (KPIs / OKRs):**
  * Lines of code (LOC) effectively merged.
  * Time-to-resolution for issues.
  * Test coverage progression.
  * System health metrics collected automatically via `vibe-ops` sensors.

---

## 4. Knowledge & Study Planning (The Obsidian Bridge)
The conceptual breakdown of information, ensuring that learning is structured, retrievable, and measurable.

### Organizational Hierarchy
* **Weekly Goals & Field Area:** The primary focus of the week.
* **Applications:** Real-world use cases of the knowledge.
* **Features:** Specific functional capabilities being studied.
* **Requisites:** Dependencies and required prior knowledge.
* **Main Topics & Sub-Topics:** The granular breakdown of the subject matter.

### Mental Models & Importance Relations
* **Foundational Concepts:** Core principles that do not change.
* **Abstract Theories:** Higher-level conceptual frameworks.
* **Common Applications:** Practical implementations of the theory.

---

## 5. Daily Knowledge Report Journaling & Consolidation
The micro-level tracking of daily habits, study ops, and cognitive consolidation.

* **Daily Learning Logging:** Documenting what was learned, focusing on *how* it connects to existing mental models.
* **Tracking Consolidation of Mental Models:** 
  * Spaced repetition scores.
  * Ability to apply a theoretical concept to a practical code issue (measured by linking an Obsidian note to a completed GitHub PR).
* **Timing Habits & Journaling Metrics:**
  * Tracking pomodoros, deep work hours, and focus quality.
  * Daily health and readiness checks to feed back into the cybernetic Policy Engine.
