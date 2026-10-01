---
name: vault-intent-extract
description: Extract task candidates from a daily vault note via regex patterns (PT-BR "amanhã eu faço X" / EN "TODO: X" / explicit "deadline YYYY-MM-DD Z") and emit review-queue CREATE proposals (NEVER auto-executes). Cron 22:00, slash /extract.
version: 1.0.0
created: 2026-10-01
tier: production-ready
entry_point: agents.v2.skills.vault_intent_extract.run_skill
actor: cron | user
triggers:
  - cron: "0 22 * * *"       # 22:00 local — end of day
  - slash: "/extract"
  - slash: "/skill vault-intent-extract"
inputs:
  - file: vault/daily/{date}.md  (default today; configurable)
  - cache: vault embeddings cache (M159) — optional, for LLM-augmented extraction
outputs:
  - review_queue: data/review_queue/*.json (action: "create_task", source: "vault_intent")
---

# vault-intent-extract

Reads the day's vault note (PT-BR or EN) and extracts natural-language task
intents into CREATE proposals. **Emits proposals only — never executes
changes directly.** User approves via `--approve` and only then are
TaskChange events written to the review queue.

## What it detects

| Pattern (regex, case-insensitive) | Inferred due | Example |
|-----------------------------------|--------------|---------|
| `amanhã (eu )?(vou \|farei \|faço )?X` | today + 1 d | "amanhã eu faço o relatório" |
| `próxima semana X`                | today + 7 d | "próxima semana vou revisar docs" |
| `deadline YYYY-MM-DD X`           | explicit    | "deadline 2026-10-15 fechar Q3" |
| `TODO: X` / `FIXME: X` / `XXX: X` | none        | "TODO: limpar inbox" |
| `lembrar de X`                    | none        | "lembrar de pagar conta" |

Each match produces a `CREATE` candidate with `ueid = tsk:intention:<sha256[:8]>:<sha256[8:16]>:<sha256[16:24]>`
(deterministic per task text → idempotent across runs) and a `rationale`
noting which pattern matched.

## Algorithm (pseudocode)

```
def extract_candidates(markdown, today=None):
    today = today or date.today()
    seen = set()
    candidates = []

    for pattern, due_offset, due_explicit in INTENT_PATTERNS:
        for m in re.finditer(pattern, markdown, re.IGNORECASE | re.MULTILINE):
            task = _clean(m.group("task"))
            if len(task) < 5: continue
            if task.lower() in seen: continue
            seen.add(task.lower())

            if due_explicit == "date":
                due = date.fromisoformat(m.group("date"))
            elif due_offset is not None:
                due = today + timedelta(days=due_offset)
            else:
                due = None

            candidates.append({
                "action": "create_task",
                "source": "vault_intent",
                "ueid": _gen_ueid(task),
                "fields": {"title": task, "priority": 3, "due": due},
                "rationale": f"matched: {pattern[:40]}...",
            })

    return candidates
```

## Inputs and outputs

**Inputs:**
- `markdown: str` OR `file_path: str | Path` (use `propose_from_file`)
- `today: date | None` — defaults to `date.today()`. Override for testing.

**Outputs:**
- `Proposal` with `approval_state="pending"`, `changes[].action == "create_task"`,
  `changes[].source == "vault_intent"`. The skill NEVER calls
  `queue.enqueue` directly.

## Cron and slash

```bash
# Cron entry (22:00 local)
0 22 * * *  cd <repo> && uv run python -m interfaces.cli.main v2 daily --skill vault-intent-extract

# Manual slash command
/extract
```

## Constraints (NON-NEGOTIABLE)

1. **NEVER auto-execute** — every CREATE goes through the proposal → review queue pipeline.
2. **Cron preserved** — `0 22 * * *`.
3. **Idempotent** — running twice on the same note produces identical candidates
   (UEIDs are SHA-256-derived from task text; `seen` set dedupes within a run).
4. **Dedupe within note** — multiple matches of the same task text → 1 candidate.
5. **Audit attribution** — every change carries `rationale: "matched pattern: ..."`
   so the agent consumer can see which pattern fired.

## Embeddings-augmented mode (M159)

When the vault embeddings cache is available, the skill can additionally:
- Embed the note
- Query for "task-like" sentences above cosine threshold
- LLM-augment extraction with a prompt like
  `Extract pt-BR task intents from: {sentence} → JSON {task, due}`

This mode is **opt-in** — the regex extractor runs by default and produces
the baseline candidates. Embeddings/LLM add high-precision candidates
without dropping any regex hits.

## Error handling

| Failure | Behavior |
|---------|----------|
| File not found | Returns empty `Proposal` with `reasoning="vault note not found: <path>"` |
| Empty markdown | Returns empty `Proposal`, no crash |
| Malformed date in `deadline YYYY-MM-DD X` | Match skipped silently |
| Embeddings cache unavailable | Falls back to regex-only mode |

## Tests

Tests at `src/ikigai/tests/skills/test_vault_intent_extract.py`:
- Each pattern (`amanhã`, `próxima semana`, `deadline YYYY-MM-DD`, `TODO:`, `lembrar de`)
  produces the expected `due` offset
- Case-insensitive matching works (EN + PT-BR)
- Duplicates within note dedupe to 1 candidate
- UEIDs are deterministic across runs (idempotency)
- `propose_from_file` returns empty proposal when file missing
- Empty markdown → empty proposal, no crash
- Review-queue integration: approved proposal → `TaskChange` lands in queue
- `Proposal.validate()` passes for every candidate

## Implementation

```python
from agents.v2.skills.vault_intent_extract import (
    SKILL_NAME,            # "vault-intent-extract"
    INTENT_PATTERNS,       # tuple of (regex, due_offset_days, due_explicit_group)
    extract_candidates,    # pure function on markdown string
    propose,               # builds Proposal from markdown
    propose_from_file,     # convenience: reads path then calls propose
    run_skill,             # entry point for /skill vault-intent-extract
)
```

See `src/ikigai/src/agents/v2/skills/vault_intent_extract.py` for the
canonical implementation.

## Provenance

Skill shipped in M161 (Sep 2026) as a stub. Implementation fleshed out per
M162 — added `_clean_task_text` normalization (trim connectors, cap length),
deterministic UEID generation, and review-queue integration tests.
