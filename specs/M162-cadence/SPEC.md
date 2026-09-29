# M162 — Cadência adaptada (daily/weekly/monthly/quarterly sem PAV-math)

**Status:** 🟡 PLANNED
**Date:** 2026-09-29
**Author:** loop-orchestrator + user
**Builds on:** M156 (stubs PAV), M161 (skills + proposals), M168 (roadmap)
**Goal:** Substituir a dependência de PAV-math em 4 skills existentes
(`ikigai-daily/weekly/monthly/quarterly`) por agregação pura do vault +
taskdog. Manter comportamento: cada skill emite Proposal, espera
`--approve`, escreve vault_log.

---

## TL;DR

| Skill | Cron | Substitui PAV por | Output |
|---|---|---|---|
| `ikigai-daily` | 08:57 | counts done/pending/cancelled nas últimas 24h | 3-5 sugestões pt-BR (read-only, NO vault write) |
| `ikigai-weekly` | seg 09:00 | agrega 7 daily reports (count tasks, status breakdown) | `vault/weekly-review/{date}.md` (com approval) |
| `ikigai-monthly` | dia 1 10:00 | agrega 4 weekly reviews | `vault/monthly-review/{date}.md` |
| `ikigai-quarterly` | jan/abr/jul/out dia 1 11:00 | agrega 3 monthly + 13 weekly | `vault/quarterly-review/{date}.md` + taskdog OKRs |

**Todos NUNCA auto-exec.** meta_plan pattern (M161).

---

## Skill 1: ikigai-daily

### Cron: `57 8 * * *` (08:57 local)
### Slash: `/ikigai-daily`
### Manual: `td chat /skill ikigai-daily`

### Comportamento novo (sem PAV)

```python
def run_skill(today: date | None = None) -> Proposal:
    today = today or date.today()
    yesterday = today - timedelta(days=1)

    # 1. Read yesterday's daily report (if exists)
    daily_path = Path(f"vault/daily/{yesterday.isoformat()}.md")
    yesterday_text = daily_path.read_text() if daily_path.exists() else ""

    # 2. Aggregate taskdog state for last 24h
    adapter = TaskdogAdapter()
    tasks = adapter.list_all()
    done_24h = [t for t in tasks if _was_done_in_window(t, yesterday, today)]
    pending = [t for t in tasks if t.get("status") == "planned"]
    cancelled = [t for t in tasks if t.get("status") == "cancelled"]

    # 3. Generate 3-5 pt-BR suggestions (NO PAV scoring)
    suggestions = []
    if done_24h:
        names = ", ".join(t.get("name", "?") for t in done_24h[:3])
        suggestions.append(f"Ontem você fechou: {names}. Continue o ritmo.")
    if pending and len(pending) > 5:
        suggestions.append(f"Você tem {len(pending)} tasks pendentes. Considere priorizar as 3 mais importantes hoje.")
    if cancelled:
        suggestions.append(f"{len(cancelled)} task(s) foram canceladas. Reveja se algo importante ficou de fora.")
    if not yesterday_text and not done_24h:
        suggestions.append("Dia sem registro. Considere escrever em vault/daily/ antes do fim do dia.")

    # Daily skill READ-ONLY: emit Proposal with vault_log path only,
    # no changes
    return Proposal(
        skill="ikigai-daily",
        reasoning=f"daily reflection for {today.isoformat()}",
        changes=[],  # read-only
        metadata={"suggestions": suggestions, "stats": {
            "done_24h": len(done_24h),
            "pending": len(pending),
            "cancelled": len(cancelled),
        }},
    )
```

### Output

- **Read-only skill** — emits Proposal with `changes=[]` and `metadata.suggestions`
- User types `/ikigai-daily` and sees suggestions printed to stdout
- NO vault write (per original `outputs: []` in daily.md)

---

## Skill 2: ikigai-weekly

### Cron: `0 9 * * 1` (segunda 09:00)
### Slash: `/ikigai-weekly`

### Comportamento novo

```python
def run_skill(today: date | None = None) -> Proposal:
    today = today or date.today()
    week_start = today - timedelta(days=7)

    # 1. Aggregate 7 daily reports
    daily_reports = []
    for i in range(7):
        day = today - timedelta(days=i)
        path = Path(f"vault/daily/{day.isoformat()}.md")
        if path.exists():
            daily_reports.append((day, path.read_text()))

    # 2. Aggregate taskdog state
    adapter = TaskdogAdapter()
    tasks = adapter.list_all()
    done_week = [t for t in tasks if _was_done_in_window(t, week_start, today)]
    created_week = [t for t in tasks if _was_created_in_window(t, week_start, today)]

    # 3. Build weekly review markdown
    md = _render_weekly_review(
        today=today,
        daily_reports=daily_reports,
        done=done_week,
        created=created_week,
    )

    # 4. Emit Proposal with CREATE for vault_write (via review_queue)
    review_path = f"vault/weekly-review/{today.isoformat()}.md"
    return Proposal(
        skill="ikigai-weekly",
        reasoning=f"weekly review for week ending {today.isoformat()}",
        changes=[{
            "action": "WRITE_FILE",
            "ueid": f"vault:weekly-review:{today.isoformat()}",
            "fields": {"path": review_path, "content": md},
            "rationale": "weekly aggregation of 7 daily reports + taskdog state",
        }],
        approval_state="pending",
    )
```

### Output

- Proposal with 1 WRITE_FILE change (review_queue will route to vault writer)
- After `--approve`, file is written to `vault/weekly-review/{date}.md`
- `vault_write` MCP tool is the canonical writer (per M155)

---

## Skill 3: ikigai-monthly

### Cron: `0 10 1 * *` (dia 1 10:00)
### Slash: `/ikigai-monthly`

### Comportamento novo

Same pattern as weekly but:
- Aggregate 4 weekly reviews (last 4 weeks)
- Output: `vault/monthly-review/{date}.md`
- One WRITE_FILE change

### Logic

```python
monthly_md = _render_monthly_review(
    today=today,
    weekly_reviews=last_4_weekly_reviews,
    tasks=taskdog_state,
)
return Proposal(
    skill="ikigai-monthly",
    changes=[{
        "action": "WRITE_FILE",
        "ueid": f"vault:monthly-review:{today.isoformat()}",
        "fields": {"path": f"vault/monthly-review/{today.isoformat()}.md",
                   "content": monthly_md},
    }],
)
```

---

## Skill 4: ikigai-quarterly

### Cron: `0 11 1 1,4,7,10 *` (jan/abr/jul/out dia 1 11:00)
### Slash: `/ikigai-quarterly`

### Comportamento novo

Same pattern but:
- Aggregate 3 monthly + 13 weekly reviews
- Output: `vault/quarterly-review/{date}.md` + taskdog_create OKRs
- Multiple WRITE_FILE + CREATE changes in same proposal

### Logic

```python
quarterly_md = _render_quarterly_review(...)
okr_tasks = _extract_okrs_from_review(quarterly_md)  # list of dicts

return Proposal(
    skill="ikigai-quarterly",
    changes=[
        {"action": "WRITE_FILE", "ueid": f"vault:quarterly-review:{today}",
         "fields": {"path": f"vault/quarterly-review/{today}.md",
                    "content": quarterly_md}},
        *[{
            "action": "CREATE",
            "ueid": f"tsk:okr:{today}:{i:04d}",
            "fields": {"title": okr["title"], "priority": okr.get("priority", 2),
                       "due": okr.get("due")},
        } for i, okr in enumerate(okr_tasks)],
    ],
)
```

---

## Out of scope (explícito)

- ❌ PAV-math reativação (ADR-013, M156 stubs ficam)
- ❌ Cycle state files (`vault/meta/cycle_state/`) — não escrevemos
- ❌ Habit state files (`vault/meta/habit_state/`) — não escrevemos
- ❌ Regime detection / scoring (PAV)
- ❌ Cron runner real (M163+)
- ❌ LLM refinement das sugestões (M164+ opcional)

---

## Architecture

### File layout

```
src/ikigai/src/agents/v2/skills/
├── cadence.py            # NEW: shared helpers (was_done_in_window, render_*)
├── ikigai_daily.py       # NEW: extracted from daily.md
├── ikigai_weekly.py      # NEW: extracted from weekly.md
├── ikigai_monthly.py     # NEW: extracted from monthly.md
└── ikigai_quarterly.py   # NEW: extracted from quarterly.md
```

Each skill module exposes:
- `SKILL_NAME = "ikigai-daily"` (etc.)
- `run_skill(today=None) -> Proposal`

`cadence.py` provides:
- `_was_done_in_window(task, start, end)` — heuristic check
- `_was_created_in_window(task, start, end)` — heuristic check
- `_render_weekly_review(...)` → markdown string
- `_render_monthly_review(...)` → markdown string
- `_render_quarterly_review(...)` → markdown string

### Vault schema (M155 OPÇÃO B)

```
vault/
├── daily/
│   ├── 2026-09-29.md
│   ├── 2026-09-30.md
│   └── ...
├── weekly/
│   ├── 2026-W40.md
│   └── ...
├── monthly/
│   ├── 2026-10.md
│   └── ...
├── quarterly/
│   └── 2026-Q4.md
└── proposals/   # already exists (M161)
```

(Use `vault/weekly-review/{date}.md` format consistent with original `.md` specs.)

---

## LOC budget

| File | LOC | Notas |
|---|---|---|
| `cadence.py` | ~150 | shared helpers + render fns |
| `ikigai_daily.py` | ~80 | read-only proposal with suggestions |
| `ikigai_weekly.py` | ~80 | aggregate + propose WRITE_FILE |
| `ikigai_monthly.py` | ~80 | aggregate + propose WRITE_FILE |
| `ikigai_quarterly.py` | ~100 | aggregate + propose WRITE_FILE + OKR CREATE |
| `taskdog_chat.py` (patch) | ~30 | /ikigai-{daily,weekly,monthly,quarterly} shortcuts |
| Tests (~5 per skill) | ~200 | aggregate logic, render output, proposal shape |
| **Total** | **~720 LOC** | |

---

## Critério de done

- [ ] 4 skill modules implementados + `cadence.py` helpers
- [ ] Cada skill roda sem LLM real (PAV stubs já feitos em M156)
- [ ] Cada skill emite Proposal com `approval_state="pending"`
- [ ] `ikigai-daily` é read-only (changes=[])
- [ ] `ikigai-weekly/monthly/quarterly` emitem WRITE_FILE change (com path + content)
- [ ] `ikigai-quarterly` emite também CREATE OKRs
- [ ] `td chat` reconhece `/ikigai-daily`, `/ikigai-weekly`, etc.
- [ ] 16+ testes novos passam, zero regressão nos 92 existentes
- [ ] Cada skill testada com fixtures (vault file mock + taskdog list mock)

## Riscos

| Risco | Mitigação |
|---|---|
| Vault path não existe (no tests) | Helper lê com fallback pra string vazia |
| `TaskdogAdapter.list_all()` lento | Mock em testes |
| Render output inconsistente | Tests verificam sections obrigatórias |
| User aprova quarterly e cria 10 OKRs | User revisa Proposal antes de `--approve` |
| Cadência roda em paralelo (race) | Locks no filesystem (M163+ quando cron real) |
