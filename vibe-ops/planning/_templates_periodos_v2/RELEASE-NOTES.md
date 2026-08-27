# Release Notes — Period Templates v2

> **Mirror source:** `notas_estudo/_templates_periodos/`
> **Mirror target:** `vibe-ops/planning/_templates_periodos_v2/`
> **Sync mechanism:** bidirectional via `period-reports-sync` plan (T2 + T4 of that plan)
> **Source of truth:** codebase (this folder). Vault edits require re-sync.

## Version Map

| v1.0 filename (vault) | v2.0 filename (codebase) | Schema | Verdict enum | Status |
|----------------------|---------------------------|--------|-------------|--------|
| `00-README.md` | `_schema_contract.md` (TBD) | ADR-006 | — | pending |
| `01-sonho.md` | `01-sonho.md` | ADR-006 | ACTIVE/VALIDATED/FALSIFIED/PIVOTED/ABANDONED | copied |
| `02-avaliacao-trimestral.md` | `02-avaliacao-trimestral.md` | ADR-006 | PASS/PARTIAL/FAIL | copied |
| `03-onda.md` | `03-onda.md` | ADR-006 | CONTINUE_WAVE/CORRECT_TRAJECTORY/KILL_WAVE | copied |
| `04-revisao-semanal.md` | `04-revisao-semanal.md` | ADR-006 | PASS/PARTIAL/FAIL | copied |
| `05-relatorio-diario.md` | `05-relatorio-diario.md` | ADR-006 | PASS/PARTIAL/FAIL | copied |

## v2.0 Additions (this release)

| Filename | Period | Status |
|----------|--------|--------|
| `00-quartely-planning.md` | quarterly | new (T1) |
| `06-quartely-review.md` | quarterly | new (T2) |
| `07-sprint-kickoff.md` | onda | new (T3) |
| `08-sprint-retrospective.md` | onda | new (T4) |
| `RELEASE-NOTES.md` | — | this file (T5) |

## Sync Workflow

```bash
# Codebase → Vault (one-shot)
life sync vault --folder vibe-ops/planning/_templates_periodos_v2

# Vault → Codebase (one-shot, requires human approval)
life sync code --folder _templates_periodos
```

## Compatibility Notes

- v1.0 templates (vault) remain readable
- v2.0 templates (codebase) have identical frontmatter schemas
- Existing period-sync layer handles both versions identically
- New templates (00, 06, 07, 08) extend the period axis with quarterly + sprint-specific
