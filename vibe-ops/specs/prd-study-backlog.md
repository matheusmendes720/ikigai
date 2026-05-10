# PRD: Study Backlog (Epistemic Data Mesh)

## 1. Objective
Manage knowledge acquisition through a "Self Evolve Engineering" framework. It bridges technical study with practical project application, tracking cognitive debt and learning depth.

## 2. Core Entities
- **StudyPlan:** Continuous (7/7) learning plans anchored to Waves/Cycles.
- **StudyTopic:** Specific nodes in the knowledge graph (concepts, frameworks, libraries).
- **Cognitive Debt:** Quantification of fragile mental models vs. practical mastery (0-5 levels).

## 3. Key Features
- **Prerequisite Mapping:** Dependency trees linking study topics to project requirements.
- **Cognitive Load Ratio (CLR):** Targeting the ideal ratio of `study_hours / work_hours` (default 0.4).
- **Epistemic Prioritization:** AI-driven suggestions for "what to study next" based on project roadblocks and revenue impact.
- **Study Artifacts:** Linking Obsidian notes, Mindmaps, Flashcards, and NotebookLM exports.

## 4. Integration
- **Project Linkage:** `note-idx X proj-feats_Yx` mapping.
- **Taskwarrior:** Study sessions injected as tasks with `study_plan_id`.
- **Hybrid RAG:** Indexing study notes for cross-referencing with codebase commits and roadmaps.

## 5. Metrics & Success Criteria
- **Learning Burndown:** Progress against `target_hours` for topics.
- **Knowledge Consolidation:** Evidence of "learning closed" via task completion or permanent note creation.
- **Revenue Alignment:** Prioritizing topics linked to "Revenue" vector projects.