# 00 — Índice: Auto-Performance OS (docset canônico)

> **Categoria:** Índice navegável
> **Público:** Eu mesmo + agentes futuros
> **Localização:** `docs/auto-performance-os/`
> **Total de documentos:** 27 (4 axiomas + 8 postulados + 8 engines + 3 meta + 3 integração + este índice)

---

## §0 — Visão panorâmica

Este docset mapeia **todos os modelos matemáticos** do sistema auto-performance OS — PAV, IKIGAi, mesh — na ordem axiomática em que se compõem: axiomas → primitivas → engines → meta → integração.

**Stack conceitual:**

```
Axiomas  (4)           o que é matematicamente estável
   ↓
Postulados  (8)        como o domínio captura esses axiomas
   ↓
Engines  (8)           quem executa os postulados
   ↓
Meta-orquestração  (3) como os engines colaboram
   ↓
Integração  (3)        como o sistema se conecta ao mundo real
```

**Convenções:**
- Cada doc segue 5 seções: **intuição / enunciado formal / justificativa não-técnica / referências cruzadas / fontes**
- Notação matemática preservada verbatim (H(t), Q_HE, UEID, FSM, IKIGAi, PAV)
- Paths absolutos preservados do repo (`src/...`, `vault/...`, `vibe-ops/...`)

---

## §1 — Axiomas (4 docs)

Base matemática: tudo abaixo repousa sobre estes 4 axiomas.

| #  | Documento                                            | Conteúdo                                                                  |
|:--:|:-----------------------------------------------------|:--------------------------------------------------------------------------|
| 01 | `01-axiom-probability-foundations.md`                | E[X], Var(X), probabilidade condicional; quantização discreta HIGH/MED/LOW → {1.0, 0.6, 0.3} |
| 02 | `02-axiom-exponential-decay-growth.md`               | H(t) = 1 − exp(−λ·t), λ=0.093 dia⁻¹, Lally 2010 (66 dias mediana), marcos 7/15/66/90 |
| 03 | `03-axiom-finite-state-machines.md`                  | Tupla (S, Σ, δ, s₀, F); 7-state Pomodoro + 4-state Policy                |
| 04 | `04-axiom-ordering-relations.md`                     | Ordem parcial, monotonicidade, histerese assimétrica                      |

---

## §2 — Postulados / Primitivas de Domínio (8 docs)

Como cada axioma se **materializa** no domínio auto-performance.

| #  | Documento                                           | Conteúdo                                                                  |
|:--:|:----------------------------------------------------|:--------------------------------------------------------------------------|
| 05 | `05-postulado-recuperacao-sono.md`                  | R(s) piecewise-logarítmico, 5 buckets EXCELENTE/BOM/ACEITÁVEL/HARDCORE/CRÍTICO |
| 06 | `06-postulado-momentum-habito.md`                   | H(t) do axioma 02 aplicado a hábitos individuais; tabela de marcos        |
| 07 | `07-postulado-orcamento-energia.md`                 | Day Quadrant 4-buckets (MANHÃ_PROFUNDA/MANHÃ_RASA/TARDE_PROFUNDA/TARDE_RASA); bases 1.00/0.65/0.85/0.55 |
| 08 | `08-postulado-blocos-tempo.md`                      | BreakCalculator + Matriz ContextSwitch 9-pares                            |
| 09 | `09-postulado-ikigai-5-vetores.md`                  | V_paixão/V_habilid/V_mercado/V_receita/V_curso; pesos simétricos w=0.20 (Opção C deferida) |
| 10 | `10-postulado-ritmo-pomodoro.md`                    | SM 7 estados, cenários PERFEITO/DESVIADO/HARDCORE, HARDCORE_MAX_PER_MONTH=2 |
| 11 | `11-postulado-divida-cognitiva.md`                  | dívida(t) = decay·dívida(t-1) + Σ(1-conclusão)·custo, decay=0.7           |
| 12 | `12-postulado-consolidacao-diaria.md`               | overall = 0.3·E + 0.4·P + 0.3·S                                          |

---

## §3 — Engines (8 docs)

Implementações concretas dos postulados.

| #  | Documento                                           | Conteúdo                                                                  |
|:--:|:----------------------------------------------------|:--------------------------------------------------------------------------|
| 13 | `13-engine-habit-engine.md`                         | H_nível(t) + eficiência + bônus_seq + Q_HE multiplicativo                |
| 14 | `14-engine-policy-engine-fsm.md`                    | 4 estados PUSH/MAINTAIN/REDUCE/RECOVER, histerese 3/2/1, transições      |
| 15 | `15-engine-pomodoro-machine.md`                     | SM 7 estados, 11 transições, 10 eventos auditáveis                       |
| 16 | `16-engine-sleep-validator.md`                      | Classificador 5 buckets + matriz 5×4 (hora_de_deitar × duração)          |
| 17 | `17-engine-budget-classifier.md`                    | 4 quadrantes (MANHÃ/TARDE × PROFUNDA/RASA) + custo base 1-10             |
| 18 | `18-engine-consolidator.md`                         | 4 sub-scores (energia/produtividade/saúde/overall); veredito PASS/PARTIAL/FAIL |
| 19 | `19-engine-ikigai-vector-scorer.md`                 | 5 vetores + meta-vetor geo+harmônico (0.6/0.4)                          |
| 20 | `20-engine-ucb-recalibrator.md`                     | UCB1: Q_HE_médio + c·√(2·ln(N_total)/N_regime)                            |

---

## §4 — Meta-orquestração (3 docs)

Como os engines colaboram.

| #  | Documento                                           | Conteúdo                                                                  |
|:--:|:----------------------------------------------------|:--------------------------------------------------------------------------|
| 21 | `21-meta-qhe-policy-mapping.md`                     | Faixas Q_HE → regime alvo (sem/com histerese)                            |
| 22 | `22-meta-ikigai-meta-vector.md`                     | Composição híbrida 0.6·geo + 0.4·harm para IKIGAi                       |
| 23 | `23-meta-decision-flow.md`                          | Pipeline 4 etapas: Observar → Recomendar → Decidir → Executar            |

---

## §5 — Integração (3 docs)

Como o sistema se conecta ao mundo real.

| #  | Documento                                           | Conteúdo                                                                  |
|:--:|:----------------------------------------------------|:--------------------------------------------------------------------------|
| 24 | `24-integration-mesh-ueid-propagation.md`           | UEID 4-part regex + queue append-only + 3 adapters (Cli/Taskdog/Solverforge) |
| 25 | `25-integration-deep-agent-sync.md`                 | Deep Agent ↔ vault ↔ data/ sync bidirecional; 8 tools MCP; 5 contratos  |
| 26 | `26-integration-cybernetic-loop.md`                 | Target → Sensor → Adjuster → Persist → Sync → Index; 3 frequências      |

---

## §6 — Mapa de dependências (resumo)

```
Axiomas → Postulados → Engines → Meta → Integração

02 (exponential) ───▶ 06 (momentum) ──▶ 13 (habit) ──┐
                                                       ├──▶ 21 (Q_HE→regime) ──▶ 23 (decision) ──▶ 26 (cybernetic loop)
03 (FSM)        ───▶ 10 (pomodoro)  ──▶ 15 (machine) ─┤
03 (FSM)        ───▶ 14 (policy FSM)                  │
04 (ordens)     ───▶ 14 (histerese assimétrica)       │
                                                       │
Axioma 02 ───────▶ 09 (5 vetores) ──▶ 19 (scorer) ──▶ 22 (meta-vetor)
                                                       │
Postulados 5-12 ──▶ Engines 13-20                       │
                                                       └──▶ 18 (consolidator) ──▶ 24/25 (sync)

Engines 13-20 ───▶ Meta 21-23 ───▶ Integração 24-26 ──▶ Mundo real (forks/interfaces)
```

---

## §7 — Como usar este índice

- **Quero entender X conceitualmente**: comece pelo axioma, depois postulado, depois engine.
- **Quero implementar X**: pule para o engine; volte ao axioma só se a fórmula for opaca.
- **Quero saber quem depende de quem**: use o **mapa de dependências** (§6) + as **referências cruzadas** (seção 4 de cada doc).
- **Quero citar uma fonte primária**: cada doc lista os arquivos verbatim em **§5 Fontes** — paths absolutos preservados.

---

## §8 — Convenções do docset

- **Idioma**: PT-BR (todo o prosa explicativa); notação matemática em símbolos Unicode / ASCII puro
- **Naming de arquivos**: `NN-categoria-nome-kebab.md` (zero-padded 2-digit)
- **Estrutura interna**: 5 seções numeradas (§1-§5), dentro de cada doc
- **Math notation**: H(t), Q_HE, UEID, FSM preservados verbatim (não traduzidos)
- **Code references**: paths absolutos do repo preservados sem tradução

---

*Auto-Performance OS — Índice — 2026-08-28*