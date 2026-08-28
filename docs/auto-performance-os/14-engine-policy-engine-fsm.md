# 14 — Engine: Policy Engine FSM

> **Categoria:** §3 Engines
> **Público:** Eu mesmo + agentes futuros
> **Material de origem:** policy_engine.py, PRD-CORE-POLICY-CONSOLIDATOR

---

## §1 — Intuição em linguagem simples

A Policy Engine decide **quão agressivamente** carregar o seu dia. Mais carga em PUSH, menos em RECOVER. A histerese assimétrica (3 dias para subir, 2 para descer) impede que um único dia bom dispare sobrecarga — e permite reação rápida a dias ruins.

## §2 — Enunciado formal

**4 estados:** `PUSH`, `MAINTAIN`, `REDUCE`, `RECOVER`.

**Regras de transição:**

| Transição              | Dias sustentados | Condição extra                          |
|:----------------------:|:---------------:|:----------------------------------------|
| RECOVER → REDUCE       | 3               | —                                       |
| REDUCE → MAINTAIN      | 3               | —                                       |
| MAINTAIN → PUSH        | 3               | —                                       |
| PUSH → MAINTAIN        | 2               | —                                       |
| MAINTAIN → REDUCE      | 2               | —                                       |
| REDUCE → RECOVER       | 2               | —                                       |
| qualquer → RECOVER     | 1 (emergência)  | Q_HE < 0.30 **ou** infrações ≥ 3        |

**Invariantes:**
- PUSH → RECOVER direto é **proibido** (passa por MAINTAIN e REDUCE)
- REDUCE nunca é escolhido por Q_HE sozinho — exige sinal de infração

**Orçamento por regime:**

| Regime   | Horas produtivas | Pomodoros |
|:--------:|:----------------:|:---------:|
| PUSH     | 8h               | 10        |
| MAINTAIN | 6h               | 8         |
| REDUCE   | 4h               | 5         |
| RECOVER  | 2h               | 2         |

## §3 — Justificativa não-técnica

Por que **3 dias para subir / 2 para descer** (histerese assimétrica): promover intensidade é mais arriscado que reduzir — um dia bom pode ser anomalia, mas um dia ruim geralmente é sinal. A assimetria embute um viés conservador: o sistema protege contra picos de otimismo.

O canal de **emergência** (1 dia para RECOVER) existe para crises reais: se Q_HE despenca abaixo de 0.30 ou infrações explodem, o sistema reage **imediatamente** sem esperar histerese. Isso é a válvula de segurança.

A regra "PUSH → RECOVER direto proibido" é constitucional: garante que sair de carga alta nunca pula a fase de **descompressão**. Sem essa regra,次日 carga alta → dia péssimo → RECOVER puniria sem transição.

## §4 — Referências cruzadas (consumidores downstream)

- **Axioma 03** (FSMs) — base matemática de estados/transições
- **Axioma 04** (ordens parciais / monotonicidade) — assimetria = ordem parcial
- **13-engine-habit-engine** — Q_HE é o input primário
- **22-meta-consolidacao-diaria** — `overall` do Consolidator alimenta o input
- **16-meta-regime-fsm** — versão IKIGAi com histerese análoga

## §5 — Fontes

- `src/operational/packages/core/src/operational/core/policy_engine.py` — `transition(state, qhe, infractions)`
- `src/operational/docs/adr/PRD-CORE-POLICY-CONSOLIDATOR.md` §4 — FSM evaluation rules
- `src/ikigai/src/ikigai/core/heuristics/regime.py` — constantes de histerese (`HYSTERESIS_UPGRADE_DAYS=3`, `HYSTERESIS_DOWNGRADE_DAYS=2`)
- `vault/ikigai/meta/algorithm-issues-registry.md` — debate A02 (emergency threshold 0.30)
