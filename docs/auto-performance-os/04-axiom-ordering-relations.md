# 04 — Axioma: Relações de Ordem e Monotonicidade

> **Categoria:** §1 Base axiomática
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** testes de monotonicidade em habit_engine.py, histerese em PRD-CORE-POLICY-CONSOLIDATOR §4.4

---

## §1 — Intuição em linguagem simples

Algumas coisas podem ser **ordenadas**; outras, não. Uma sequência de 30 dias é "mais que" uma de 10 dias. Mas "quero ser engenheiro" e "quero ser designer" não têm uma ordenação clara — são apenas diferentes. **Ordens parciais** capturam "ordenado o suficiente" sem forçar comparações totais; **monotonicidade** é a propriedade de que "mais entrada → mais saída" (ou vice-versa).

## §2 — Enunciado formal

Uma **ordem parcial** `(≤)` sobre um conjunto `S` satisfaz três axiomas:

| Axioma          | Enunciado                                                  |
|:----------------|:-----------------------------------------------------------|
| Reflexividade   | `a ≤ a` para todo `a ∈ S`                                 |
| Antissimetria   | se `a ≤ b` e `b ≤ a` então `a = b`                         |
| Transitividade  | se `a ≤ b` e `b ≤ c` então `a ≤ c`                         |

Uma **ordem total** exige adicionalmente **comparabilidade**: para todo `a, b ∈ S`, ou `a ≤ b` ou `b ≤ a`.

Uma função `f: S → T` é **monotonicamente não-decrescente** em `x` sse `x ≤ y ⟹ f(x) ≤ f(y)`.

## §3 — Justificativa não-técnica

O sistema precisa acompanhar "isto ficou melhor ou pior" ao longo do tempo. Isso é **monotonicidade** — uma ordem parcial sobre o espaço de métricas. Concretamente:

- **Q_HE** é monotonicamente não-decrescente em `H_avg` (mais hábitos feitos → Q_HE maior) e em `E/E_max` (mais energia → Q_HE maior)
- **H(t)** é monotonicamente não-decrescente na sequência `t` (sequência mais longa → mais consolidação) e na taxa de aprendizado `λ`
- **Razão de eficiência** é monotonicamente não-decrescente em `H(t)` para `R` fixo
- **Tempo** é uma ordem total (quaisquer dois dias têm uma ordenação clara)

Isso garante que o sistema responda **de modo previsível** às ações do usuário: fazer mais hábitos → Q_HE sobe; dormir mais → energia sobe. Se a matemática fosse não-monotônica, pequenas melhorias poderiam paradoxalmente piorar o score — quebrando a confiança do usuário.

Na FSM de política, a **histerese assimétrica** (3 dias para subir, 2 para descer) é uma propriedade de ordem parcial sobre as transições de regime: o sistema exige evidência mais forte para promover do que para rebaixar. Isso viesa o sistema para a cautela, o que importa quando as recomendações mudam o dia do usuário.

## §4 — Referências cruzadas (consumidores downstream)

- **13-engine-habit-engine** — toda função tem provas de monotonicidade nos testes
- **14-engine-policy-engine-fsm** — histerese assimétrica = ordem parcial sobre transições de regime
- **16-meta-regime-fsm** — FSM de 4 estados do IKIGAi com o mesmo padrão de histerese
- **Todas as engines de scoring** — Q_HE, vetores, RICE: monotônicas nas suas entradas

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/habit_engine.py` — testes de monotonicidade (paramétricos sobre `H(s)` e `efficiency(H)`)
- `src/operational/docs/adr/PRD-CORE-HABIT-ENGINE.md` §4.1 — propriedades de `H(s)` (H(0)=0, H(∞)→1, monotônica)
- `src/operational/docs/adr/PRD-CORE-POLICY-CONSOLIDATOR.md` §4.4 — rationale do design da "histerese assimétrica"
- `src/ikigai/src/ikigai/core/heuristics/regime.py` — constantes de histerese do IKIGAi: `HYSTERESIS_UPGRADE_DAYS=3`, `HYSTERESIS_DOWNGRADE_DAYS=2`
- Davey, B. A., & Priestley, H. A. (2002). *Introduction to Lattices and Order*. 2ª ed. Cambridge University Press.
