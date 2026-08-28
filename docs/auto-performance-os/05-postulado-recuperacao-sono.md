# 05 — Postulado: Recuperação pelo Sono

> **Categoria:** §2 Primitivos de domínio
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** PRD-CORE-SLEEP-VALIDATION §3, sleep_calculator.py, Walker (2017)

---

## §1 — Intuição em linguagem simples

O sono é a fundação. Sem ele, todo o resto falha — mas a curva é íngreme: 6h vs 9h não é linear, é a diferença entre exausto e recuperado.

## §2 — Enunciado formal

Função de recuperação (PRD-CORE-SLEEP-VALIDATION):

```
R(s) = ⎧  1.0                       se s ≥ 9      (recuperação plena)
       ⎨  0.5 + 0.5·(s − 6)/3       se 6 ≤ s < 9  (rampa linear)
       ⎩  0.5·(s / 6)               se s < 6       (degradada)
```

onde `s` é a duração do sono em horas e `R ∈ [0, 1]`.

**Faixas de qualidade (5 buckets do classificador):**

| Faixa         | Regra              | Cor         |
|:-------------:|:------------------:|:-----------:|
| EXCELENTE     | `s ≥ 9`            | Verde       |
| BOM           | `8 ≤ s < 9`        | Verde-claro |
| ACEITÁVEL     | `7 ≤ s < 8`        | Amarelo     |
| HARDCORE      | `4 ≤ s < 7`        | Laranja     |
| CRÍTICO       | `s < 4`            | Vermelho    |

## §3 — Justificativa não-técnica

Por que piecewise-logarítmica: as primeiras 6 horas recuperam o déficit fisiológico mais profundo (ciclos de sono profundo N3), as 3 horas seguintes consolidam memória e aprendizado motor (REM), e além de 9 horas há retorno decrescente (estamos próximos da assíntota). Abaixo de 6 horas o corpo não consegue sono profundo suficiente e a **dívida** se acumula de modo não-linear.

O classificador de 5 faixas adiciona a categoria **HARDCORE** como válvula de escape: mesmo quem dormiu só 4h pode ainda atingir um nível de execução mínimo, contanto que o faça de modo intencional e limitado. É a diferença entre "dormiu pouco porque estava em emergência" (HARDCORE legítimo) e "dormiu pouco porque negligenciou" (CRÍTICO patológico).

## §4 — Referências cruzadas (consumidores downstream)

- **13-engine-habit-engine** — `R(s)` entra como modificador de `E_sleep`
- **16-engine-sleep-validator** — classificador de 5 faixas + matriz de decisão 5×4
- **22-meta-consolidacao-diaria** — compõe o sub-score de saúde
- **23-meta-qhe-policy-mapping** — peso 0.35 no Q_HE do IKIGAi

## §5 — Fontes

- `src/operational/docs/adr/PRD-CORE-SLEEP-VALIDATION.md` §3 — função R(s) e classificador
- `src/operational/packages/core/src/operational/core/sleep_calculator.py` — implementação
- Walker, M. (2017). *Por Que Nós Dormimos*. Cap. 2 — "O Relógio Despertador da Regulagem do Sono".
- `vibe-ops/base/Produtividade Algorítmica Visual.md` §4 — modelo de energia
