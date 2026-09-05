---
name: meta_plan
description: "Meta-planner — opt-in intent-aware proposal generator (Plan D)"
entry_point: meta_plan
actor: agent
outputs: []
inputs:
  - user_request
adrs_consulted:
  - ADR-013
  - ADR-014
  - ADR-025
  - ADR-029
  - ADR-030
  - ADR-031
approval_required: true
---

# meta_plan skill

**Opt-in skill** invoked via `/plan <request>` or `invoke_skill("meta_plan", …)`.

**Flow:** classify_intent → fetch_context → generate_proposal

Produces a typed `Proposal` (Pydantic v2 strict, ADR-009) with `approval_state="pending"`.
**NEVER auto-executes.** User must reply `--approve` or `--reject X.field` before any write.

**Reuses shipped infrastructure:**
- `wrap_vault_write` (ADR-029) for all vault ops
- `taskdog_create_task` (W3.6 Path 1) for all taskdog ops
- `recall_memory` (ADR-028 B-N12) for memory fetch
- `external_folder_read` (Plan B) for folder reads

**Out of scope:**
- Auto-approval (PROPOSTAS only by Decision #3)
- Real-time vault watching
- Proposal versioning (Proposal v1 only)
- New IKIGAI_TOOLS (R2 ADR-030)

See spec: docs/superpowers/specs/2026-09-04-meta-planner-design.md
