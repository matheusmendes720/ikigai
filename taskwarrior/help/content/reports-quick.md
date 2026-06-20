# Reports - Quick Reference

## Workflow Reports

| Report | Filter | Columns | Alias |
|--------|--------|---------|-------|
| `narrativa` | `+narrativa due:today` | id, bloco_tempo, priority, description, due | `tm` |
| `relatorios` | `+relatorios modified.after:today-7d` | id, tarefa_microciclo, description, status, due | `twk` |
| `revisao` | `+revisao meta_ciclo:` | id, meta_ciclo, description, status, due, barreira | `tmeta` |
| `supervisao` | `+supervisao modified.after:today-30d` | id, sonho_id, objetivo_id, description, status | `tsonho` |

## Hierarchy Reports

| Report | Filter | Columns | Alias |
|--------|--------|---------|-------|
| `sonho` | `status:pending` | id, active, sonho_id, description, due, priority | `tsonho` |
| `objetivo` | `status:pending` | id, objetivo_id, objetivo_trimestre, meta_ciclo, description, urgency | `tobj` |
| `meta` | `status:pending meta_ciclo:` | id, meta_ciclo, description, due, priority | `tmeta` |
| `tarefa` | `status:pending tarefa_microciclo:` | id, tarefa_microciclo, description, due, priority | `tmicro` |
| `blocos` | `status:pending bloco_tempo: due:today` | id, bloco_tempo, priority, description, due | `tbloco` |

## Status Reports

| Report | Filter | Alias |
|--------|--------|-------|
| `ready` | `status:pending +READY` | `tready` |
| `blocked` | `status:pending +BLOCKED` | `tblocked` |
| `active` | `status:pending +ACTIVE` | `tactive` |
| `waiting` | `status:waiting` | `tw` |
| `overdue` | `status:pending +OVERDUE` | `tlo` |
| `teste_fogo` | `status:pending +teste_fogo` | - |

## Built-in Reports

| Report | Filter | Alias |
|--------|--------|-------|
| `list` | `status:pending` | `tl` |
| `next` | `status:pending` (sorted by urgency) | `tn` |
| `summary` | - | `ts` |
| `stats` | - | `tst` |
