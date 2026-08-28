# 15 — Engine: Pomodoro Machine

> **Categoria:** §3 Engines
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** pomodoro_machine.py, PRD-CORE-POMODORO-SCENARIO

---

## §1 — Intuição em linguagem simples

Implementa a SM do postulado 10. Cada sessão é um ciclo discreto que produz eventos para auditoria. 11 transições cobrem o ciclo completo (4 pomodoros + pausas) mais estados excepcionais (pausa do usuário, pulo por timeout).

## §2 — Enunciado formal

**Diagrama de estados (7 estados, 11 transições):**

```
                    ┌─────────┐
        ┌──────────▶│ OCIOSO  │◀──────────┐
        │           └────┬────┘           │
        │                │ iniciar        │
        │           ┌────▼────┐           │
        │      ┌───▶│TRABALHO │──┐        │
        │      │    └────┬────┘  │        │
        │      │         │       │ timeout│
        │      │    ┌────▼────┐  │        │
        │      │    │ PAUSADO │  │        │
        │      │    └────┬────┘  │        │
        │      │         │       │        │
        │   retomar      │    ┌──▼─────┐  │
        │      │    ┌────▼────┐│ PULADO │  │
        │      │    │  PAUSA  │└────────┘  │
        │      │    └────┬────┘            │
        │      │         │ rodada 4        │
        │      │    ┌────▼────────┐        │
        │      └───│ PAUSA LONGA │        │
        │           └────┬────────┘        │
        │                │                 │
        │           ┌────▼────┐            │
        └───────────│COMPLETO │────────────┘
                    └─────────┘
```

**Eventos emitidos:** `STARTED`, `WORK_COMPLETED`, `BREAK_COMPLETED`, `LONG_BREAK_COMPLETED`, `PAUSED`, `RESUMED`, `SKIPPED`, `COMPLETED`, `ABANDONED` (10 eventos por sessão completa).

## §3 — Justificativa não-técnica

Por que SM em vez de contador regressivo simples: o sistema precisa distinguir **intenção** (PAUSADO pelo usuário) de **timeout** (PULADO pelo sistema). Um pomodoro PULADO conta como incompleto para o Consolidator; um PAUSADO pode voltar a TRABALHO sem perder a contagem.

Cada evento emitido vira um registro auditável — você pode reconstruir a sessão olhando só os eventos. Isso é crítico para debugging e para validação dos 134 testes do PRD-CORE-POMODORO-SCENARIO.

## §4 — Referências cruzadas (consumidores downstream)

- **Axioma 03** (FSMs) — base matemática de estados/transições
- **10-postulado-ritmo-pomodoro** — claim de domínio construído sobre este engine
- **16-engine-scenario-classifier** — classifica PERFEITO/DESVIADO/HARDCORE
- **18-engine-consolidator** — pomodoros concluídos alimentam `bônus_foco`

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/pomodoro_machine.py` — SM com 7 estados, 11 transições, 134 testes
- `src/operational/docs/adr/PRD-CORE-POMODORO-SCENARIO.md` §3.1 — diagrama de estados + tabela de transição
- `src/operational/packages/core/src/operational/core/scenario_classifier.py` — classificador de cenário
