# SPEC-05: Cybernetic Epistemic Mesh & Hybrid RAG Topology

## 1. Objective
Define the "Cybernetic Epistemic Mesh" that bridges the Study and Development clusters, orchestrating a Hybrid RAG (Retrieval-Augmented Generation) system across SQL, Vector, and Graph databases.

## 2. Hybrid RAG Stack Definition

### 2.1. Relational Layer (Structured Data)
- **Engine:** SQLite (Local)
- **Clusters:**
    - `study`: Skills, Topics, Materials, Sessions.
    - `development`: Roadmaps, Backlogs, Changelogs.
    - `planning`: Dreams, Objectives, Metas, Waves.
- **Role:** Source of Truth for status, storypoints, and temporal anchors.

### 2.2. Vector Layer (Unstructured Context)
- **Engine:** ChromaDB (Local)
- **Scope:** 
    - Obsidian study notes (Theoretical mental models).
    - Commit messages and Code reviews.
    - Daily journal entries.
- **Embedding Model:** SBERT or local Llama-based embeddings.
- **Role:** Semantic search across notes and code history.

### 2.3. Graph Layer (Relationship & Dependencies)
- **Engine:** Obsidian (Markdown links) + Neo4j (Optional for Software Dependency Analysis).
- **Scope:** 
    - `Topic -> Prerequisite -> Topic`.
    - `Task -> Dependent Task`.
    - `StudyNote -> [Project | Task]`.
- **Role:** Navigating the "Infinite Dependency Tree" and calculating reuse impact.

## 3. Cybernetic Feedback Design (Target/Sensor/Actuator)

### 3.1. Alvo (Target)
- **Operational Target:** Conclusion of a `BacklogTask` with high quality (telemetry success).
- **Epistemic Target:** Consolidation of the mental model (Abstraction level moves from `practical` to `theoretical`).

### 3.2. Sensor (Measurement)
- **Git Dash:** Tracks commits and PRs.
- **TW Sync:** Tracks task completion and UDAs.
- **Obsidian Watcher:** Tracks note refinement and complexity increase (word count, link density).
- **Daily Journal:** Tracks perceived energy vs. effectiveness (Energy Matrix).

### 3.3. Mecanismo de Ajuste (Actuator)
- **Epistemic Prioritization:** AI suggestions for the next 5 topics to study based on the "Revenue" vector and current roadblocks.
- **Refinement Prompts:** Triggers to move an item to `review_concept` if cognitive debt is high.
- **Burndown Orchestration:** Adjusting `CLR` (Cognitive Load Ratio) based on current `PolicyState` (PUSH/RECOVER).

## 4. Cross-Cluster Unified Entity ID (UEID)
Format: `<CLUSTER>:<ENTITY>:<ID>`
- `study:topic:st_python_01`
- `dev:proj:proj_vibe_01`
- `task:tw:81d33ec8`

## 5. Decision Matrix for Study Prioritization
| Priority Level | Trigger | Action |
|:---|:---|:---|
| **P0 (Critical)** | Roadblock in a Revenue-vector task | Halt dev, force 1h Study Session |
| **P1 (High)** | New Prerequisite found in Roadmap | Inject Study Item into Backlog |
| **P2 (Medium)** | Reuse opportunity across 2+ projects | Boost topic priority in Study Backlog |
| **P3 (Low)** | General interest/Passion | Alocated to "Buffer" time blocks |

## 6. Feedback Evidence (Learning Loop Closure)
1. Task status = `done` (TW).
2. Commit linked to task exists (Git).
3. Study note `last_refined` > Task `completed_at`.
4. `depth_level` increased (Manual or LLM evaluation).
5. No recurrence of the same bug in `Changelog`.
