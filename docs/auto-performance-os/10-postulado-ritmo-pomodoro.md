# 10 — Postulado: Ritmo Pomodoro

> **Categoria:** §2 Primitivos de domínio
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** PRD-CORE-POMODORO-SCENARIO §3, §4, pomodoro_machine.py, scenario_classifier.py

---

## §1 — Intuição em linguagem simples

Um pomodoro é uma sessão de 25 minutos de trabalho focado, seguida de 5 minutos de pausa, com 15 minutos de pausa longa a cada 4 sessões. No modo HARDCORE (pós-infração), os intervalos dobram.

## §2 — Enunciado formal

**Máquina de estados (SM) de 7 estados** (PRD-CORE-POMODORO-SCENARIO):

```
S = {OCIOSO, TRABALHO, PAUSA, PAUSA_LONGA, PAUSADO, PULADO, COMPLETO}
δ: 11 transições (TRABALHO → PAUSA após DURAÇÃO_TRABALHO, etc.)
```

**Tabela de decisão de cenário:**

| Cenário      | Condição                                  | Trabalho | Pausa | Pausa Longa | Max/mês |
|:------------:|:-----------------------------------------:|:--------:|:-----:|:-----------:|:-------:|
| PERFEITO     | caso padrão                               | 25 min   | 5 min | 15 min      | —       |
| DESVIADO     | sono < 7h **ou** razão_foco < 0.7         | 30 min   | 5 min | 15 min      | —       |
| HARDCORE     | sono < 5h **ou** infrações ≥ 3            | 50 min   | 10 min| 30 min      | 2       |

`HARDCORE_MAX_PER_MONTH = 2` — limite de saúde que impede HARDCORE virando padrão.

## §3 — Justificativa não-técnica

Por que **7 estados** (e não 8): o modelo canônico de pomodoro tem 7 estados porque PAUSADO (iniciado pelo usuário) e PULADO (iniciado pelo sistema por timeout) são **distintos** em intenção. O claim de "8 estados" em alguns docs é incorreto; PRD-CORE-POMODORO-SCENARIO §3.1 é a fonte autoritativa.

O cenário HARDCORE **não é奖励**; é uma válvula de escape que reconhece que em modo de crise (sono < 5h, muitas infrações), sessões mais longas focadas podem ser mais úteis que 25 minutos interrompidos a cada 5. Mas o cap de 2/mês impede que isso vire padrão destrutivo.

## §4 — Referências cruzadas (consumidores downstream)

- **Axioma 03** (FSMs) — base matemática de estados/transições
- **15-engine-pomodoro-machine** — implementação da SM de 7 estados
- **16-engine-scenario-classifier** — classificador PERFEITO/DESVIADO/HARDCORE
- **22-meta-consolidacao-diaria** — pomodoros concluídos alimentam produtividade
- **23-meta-qhe-policy-mapping** — pomodoros alimentam `focus_bonus`

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/pomodoro_machine.py` — SM de 7 estados, 11 transições
- `src/operational/packages/core/src/operational/core/scenario_classifier.py` — classificador de cenário
- `src/operational/docs/adr/PRD-CORE-POMODORO-SCENARIO.md` §3.1 — diagrama de estados + tabela de transição
- `src/operational/docs/adr/PRD-CORE-POMODORO-SCENARIO.md` §4 — tabela de decisão de cenário
