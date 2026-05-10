# PRD: Project Execution (Roadmap & Backlog)

## 1. Objective
Orchestrate the development lifecycle using a dual-backlog system (Software + Study). It ensures that every commit is backed by understanding and every task aligns with the strategic roadmap.

## 2. Core Clusters
- **Roadmap:** High-level feature sets, storypoints, and weekly objectives (`OBJ weekly`, `goal_id`).
- **Backlog:** Decomposition of features into tasks, commits, and code reviews.
- **Changelog:** Result of execution, test suites, telemetry, and stack traces.

## 3. Key Features
- **Dual Tracking:** Synchronizing `Task <-> Knowledge` pairs.
- **Hierarchical UDAs:** Taskwarrior projects following the `Dream.Objective.Meta.Project` schema.
- **Storypoint Valuation:** Estimating effort vs. impact for prioritization.
- **Harness Integration:** Self-evolve engineering harnesses that tag dev branches with project frontmatter.

## 4. Integration
- **GitHub/GitDash:** Tracking commits and PRs as evidence of progress.
- **Obsidian:** Index notes for projects aggregating roadmap, backlog, and study links.
- **Data Mesh:** Relational piping between SQL roadmaps and Obsidian frontmatter.

## 5. Metrics & Success Criteria
- **Velocity:** Storypoints delivered per Wave.
- **Quality:** Test coverage and code review results linked to changelogs.
- **Traceability:** 100% of commits linked to a `proj_id`.