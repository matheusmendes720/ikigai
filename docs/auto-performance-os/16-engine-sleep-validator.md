# 16 — Engine: Sleep Validator

> **Categoria:** §3 Engines
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** sleep_calculator.py, PRD-CORE-SLEEP-VALIDATION

---

## §1 — Intuição em linguagem simples

Classifica a noite dormida em 5 faixas de qualidade e decide o **modo de execução** do dia seguinte. A classificação não é só "dormiu pouco" — é uma matriz 5×4 que cruza hora de dormir com duração para detectar padrões problemáticos (ex: dormir 23h + 4h é HARDCORE legítimo; dormir 03h + 4h é CRÍTICO).

## §2 — Enunciado formal

**Classificador de 5 faixas (PRD-CORE-SLEEP-VALIDATION §3.2):**

| Faixa         | Regra              | Modo de execução    |
|:-------------:|:------------------:|:-------------------:|
| EXCELENTE     | `s ≥ 9`            | PERFEITO            |
| BOM           | `8 ≤ s < 9`        | PERFEITO            |
| ACEITÁVEL     | `7 ≤ s < 8`        | PERFEITO            |
| HARDCORE      | `4 ≤ s < 7`        | HARDCORE (50/10/30) |
| CRÍTICO       | `s < 4`            | RECOVER (forçado)   |

**Matriz 5×4 (hora_de_deitar × duração):**

```
              │ 3/9h │ 4/8h │ 5/7h │ 3/4h (HARDCORE)
──────────────┼──────┼──────┼──────┼───────────────
18:00 – 21:00 │ EXC  │ BOM  │ ACEI │ HARDCORE
21:00 – 23:00 │ EXC  │ BOM  │ ACEI │ HARDCORE
23:00 – 01:00 │ BOM  │ BOM  │ ACEI │ HARDCORE
01:00 – 04:00 │ ACEI │ ACEI │ HARDCORE│ CRÍTICO
04:00 – 06:00 │ HARDCORE│ CRÍTICO│ CRÍTICO│ CRÍTICO
```

A diagonal **9h ideal** passa por EXCELENTE em horário saudável, degradando até CRÍTICO quando muito tarde ou muito curta.

## §3 — Justificativa não-técnica

Por que **6 camadas** no classificador (5 buckets + matriz 5×4): o bucket sozinho (EXCELENTE/BOM/...) é burro — não distingue "dormiu 8h começando 22h" de "dormiu 8h começando 03h". A matriz **adiciona contexto temporal**: dormir 8h começando 03h é pior que dormir 8h começando 22h, mesmo sendo a mesma duração.

A categoria **HARDCORE** é válvula de escape intencional: permite operação mínima mesmo com sono ruim. Mas o engine força **RECOVER** quando CRÍTICO (s < 4h) — não há modo "executar bem" com menos de 4h de sono.

## §4 — Referências cruzadas (consumidores downstream)

- **05-postulado-recuperacao-sono** — função R(s) base
- **10-postulado-ritmo-pomodoro** — modo HARDCORE/RECOVER do dia
- **14-engine-policy-engine-fsm** — sono ruim acelera transição para REDUCE/RECOVER
- **18-engine-consolidator** — sono entra no sub-score de saúde

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/sleep_calculator.py` — classificador de 5 buckets + matriz 5×4
- `src/operational/docs/adr/PRD-CORE-SLEEP-VALIDATION.md` §3 — função R(s), classificador, matriz
- `vibe-ops/base/Produtividade Algorítmica Visual.md` §4 — modelo de sono
