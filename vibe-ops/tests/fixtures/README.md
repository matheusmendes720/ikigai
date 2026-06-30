# Fixture Vault — Test Data

This directory holds a representative slice of the user's Obsidian vault
for the vault-bidirectional-sync integration tests.

## Layout

```
vault/
├── 2_projeto/
│   ├── p1.md           # project — all 9 vault fields populated
│   ├── p2.md           # project — milestone + deliverable focus
│   ├── dream1.md       # dream with falsification_criteria
│   └── broken.md       # intentionally malformed YAML
├── 5_atomicas/
│   └── a1.md           # atomic with mastery_level + tech_stack
├── 3_indice/
│   └── m1.md           # MOC with hub_details
└── 4_leitura/
    └── l1.md           # literature note with language + exam_type
```

## Counts

- 7 total .md files
- 6 valid (p1, p2, dream1, a1, m1, l1)
- 1 broken (broken.md) for error tolerance tests

## Entity Types

| File | entity_type | Notes |
|------|-------------|-------|
| p1.md | project | full enrichment surface |
| p2.md | project | minimal enrichment |
| dream1.md | dream | pre-cursor to FalsifiableHypothesis evaluator |
| a1.md | atomic | tracks single deliverables |
| m1.md | moc | hub linking projects |
| l1.md | literature_note | reading notes |
| broken.md | project | YAML parse error |

## Sync Expectations

After `pav sync vault --json` against this fixture:

```json
{
  "ingested": 6,
  "skipped": 0,
  "errors": 1,
  "conflicts": 0
}
```

After re-running:

```json
{
  "ingested": 0,
  "skipped": 6,
  "errors": 1,
  "conflicts": 0
}
```

(The errors counter is idempotent — broken.md still fails on every sync.)