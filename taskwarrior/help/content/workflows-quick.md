# Workflows - Quick Reference

## Workflow Summary

| Workflow | Frequency | Tag | Report | Command |
|----------|-----------|-----|--------|---------|
| **Daily (#narrativa)** | Every day | `+narrativa`, `+execucao-diaria` | `narrativa` | `tm` (morning), `te` (evening) |
| **Weekly (#relatórios)** | Once per week | `+relatorios` | `relatorios` | `twk` |
| **15-day (#revisão)** | Every 15 working days | `+revisao` | `revisao` | `task revisao` |
| **Monthly (#supervisão)** | Once per month | `+supervisao` | `supervisao` | `task supervisao` |

## Daily Workflow

**Morning (`tm`):**
```bash
tm              # Narrativa, due:today, blocos
tld             # Tasks due today
tbloco          # Time blocks
```

**Evening (`te`):**
```bash
te              # Completed today, plan tomorrow
tldt            # Tasks due tomorrow
```

## Weekly Workflow

```bash
twk             # Weekly review (relatorios + summary)
task relatorios # Weekly report
ts              # Summary
```

## 15-Day Workflow

```bash
task revisao    # 15-day review
tmeta           # View all metas
task meta_ciclo:1 list  # Specific meta
```

## Monthly Workflow

```bash
task supervisao # Monthly supervision
tsonho          # View all sonhos
tobj            # View objetivos
```
^tr-q4soigl3p