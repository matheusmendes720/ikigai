"""Add central engine reference to all strategics docs - fixed for filenames with spaces."""
from pathlib import Path

STRATEGICS_DIR = Path(r"C:\Users\mathe\code_space\life-oss\life\strategics")

# Header to insert after the H1 title
ENGINE_REFERENCE = (
    "\n\n---\n\n"
    "## 🔌 Central Engine: `planning-with-files` (v3.1.3)\n\n"
    "> **Path:** `strategics/planning-with-files/` · "
    "**Update:** `cd strategics/planning-with-files && git pull`\n\n"
    "This document is part of the **PAE framework**. The canonical planning engine for all\n"
    "long-running agentic tasks (`.omo/plans/*.md`, `.omo/drafts/*.md`, `.omo/evidence/*.txt`)\n"
    "is the cloned `planning-with-files` repo. See `00-ÍNDICE-PROGRESSIVO.md` § 🔌 Central\n"
    "Engine for the full route map.\n"
    "\n---\n"
)

POLICY_REFERENCE = (
    "\n\n---\n\n"
    "## 🔌 Central Engine Reference\n\n"
    "> **Path:** `strategics/planning-with-files/` · "
    "**Update:** `cd strategics/planning-with-files && git pull`\n\n"
    "All long-running agentic tasks in this repo use the canonical planning engine\n"
    "(planning-with-files v3.1.3, 279+ commits) cloned at `strategics/planning-with-files/`.\n\n"
    "**Route map:**\n"
    "- `skills/` — SKILL.md standard for 60+ agents\n"
    "- `commands/` — slash commands (`/plan-goal`, `/plan-loop`, `/plan-status`, `/plan-attest`)\n"
    "- `templates/` — task_plan.md, loop.md, autonomous variants\n"
    "- `docs/` — evals.md, perf-notes.md, attestation-locking.md, integration guides\n"
    "- `examples/` — real-world usage examples\n\n"
    "**Update policy:** Run `git pull` in `strategics/planning-with-files/` monthly or when\n"
    "a new version is announced. The engine is source-of-truth for the planning loop\n"
    "semantics (completion gate, hash attestation, parallel isolation, etc.).\n"
    "\n---\n"
)

POLICY_FILES = {
    "system_architecture_and_tracking_framework.md",
    "design_system_and_knowledge_tracking.md",
}

files = [
    "Modelagem Operacional.md",
    "Planejamento (Estratégico e Tático).md",
    "Hierarquia de Objetivos.md",
    "Desempenho Subjacente.md",
    "Integracao_Tatica.md",
    "Análise (Tático e Operacional).md",
    "system_architecture_and_tracking_framework.md",
    "design_system_and_knowledge_tracking.md",
]

for filename in files:
    path = STRATEGICS_DIR / filename
    if not path.exists():
        print(f"SKIP (not found): {filename}")
        continue

    content = path.read_text(encoding="utf-8")

    # Skip if already has engine reference
    if "Central Engine" in content and "planning-with-files" in content:
        print(f"SKIP (already has engine ref): {filename}")
        continue

    # Find the H1 line (first line starting with "# ")
    lines = content.split("\n")
    h1_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("# "):
            h1_idx = i
            break

    if h1_idx == -1:
        print(f"SKIP (no H1): {filename}")
        continue

    # Choose reference based on file type
    if filename in POLICY_FILES:
        ref = POLICY_REFERENCE
    else:
        ref = ENGINE_REFERENCE

    # Find the right insertion point: skip the immediate empty line after H1
    insert_idx = h1_idx + 1
    # Skip exactly one empty line after H1
    if insert_idx < len(lines) and lines[insert_idx].strip() == "":
        insert_idx += 1

    # Insert the reference
    lines.insert(insert_idx, ref.rstrip())

    new_content = "\n".join(lines)
    path.write_text(new_content, encoding="utf-8")
    print(f"UPDATED: {filename}")

print("\nDone.")