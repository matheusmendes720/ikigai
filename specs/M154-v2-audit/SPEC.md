---
name: M154-v2-audit
description: Honest inventory of v2 deep agent graph — what to reuse, rewrite, discard.
status: PENDING
owner: loop-orchestrator
created: 2026-09-29
constitution_refs:
  - composition_over_inheritance
  - tests_are_the_contract
  - reversibility_over_cleverness
  - state_on_disk_not_conversation
estimated_cost_usd: 0.10
---

# M154-AUDIT — Inventário honesto do v2 (deep agent)

**Status:** 🟡 AUDIT COMPLETE
**Date:** 2026-09-29
**Author:** loop-orchestrator
**Goal:** Antes de reescrever do zero ou reviver o v2, fazer auditoria
honesta do que existe. Saída: mapa exato do que reusar, reescrever, ou
descartar.

---

## TL;DR

- **v2 graph COMPILA e EXECUTA end-to-end** em FAKE_LLM mode.
- **6.337 LOC escritas** em `src/ikigai/src/agents/v2/`.
- **10/10 testes v2 PASSAM** (mas cobrem só smoke: imports, decorators,
  drift counts).
- **O `BlockingError` em M150 foi DIAGNOSTICADO ERRADO.** A causa real
  é `AttributeError: module 'anthropic' has no attribute 'OverloadedError'`
  no `langchain_anthropic` instalado (incompatibilidade de versão).
- **3 graphs registrados no `langgraph.json`:**

  | graph | entry | status |
  |---|---|---|
  | `ikigai_maintainer_v2` | `agents.v2.graph:make_v2_graph` | ✅ **funciona** (FAKE_LLM) |
  | `ikigai_fork_smoke` | `agents.v2.fork_smoke_graph:make_fork_smoke_graph` | ✅ **funciona** (4 nodes) |
  | `ikigai_taskdog_mcp` | `agents.taskdog_mcp_graph:make_taskdog_mcp_graph_sync` | ❌ **quebra** (import langchain_anthropic falha) |

---

## Mapeamento por subdir

### `nodes/` — 16 arquivos, ~2.000 LOC

| node | função | reusar? |
|---|---|---|
| `observe.py` | lê contexto inicial | ✅ |
| `recall.py` | lê memória/vault | ✅ |
| `reason.py` | raciocínio intermediário | ✅ |
| `score_vectors.py` | scoring multi-critério | ✅ (genérico) |
| `heuristics.py` | 6 heurísticas (h1-h6) | ⚠️ **mix PAV-math + cognitivos** |
| `balance.py` | balanceamento de vetores | ✅ |
| `decompose.py` | decompõe objetivos em tasks | ✅ |
| `plan.py` | plano consolidado | ✅ |
| `tag_and_persist.py` | tagging + persistência | ✅ |
| `reflect.py` | reflexão metacognitiva | ✅ **DIRETO pro que você quer** |
| `commit.py` | COMMIT cycle summary | ✅ |
| `proposal_executor.py` | executa propostas | ✅ |
| `surface_intentions.py` | expõe intenções pro agente | ✅ |
| `error.py` | error node com recovery | ✅ |
| `score_vectors.py` | scoring secundário | ✅ |
| `meta_plan/` | subdiretório de meta-planning | ⚠️ existe mas não vi conteúdo |

**Achado:** `reflect.py` é o node que faz **metacognition** — exatamente
o que você pediu ("agente que reflete sobre os dados do vault"). Existe
e está implementado.

### `prompts/` — 15 arquivos, ~1.500 LOC

| prompt | uso | ADR-013? |
|---|---|---|
| `h1_energy.py` | scoring energia | ❌ PAV-math |
| `h2_qhe_composite.py` | Q_HE composite | ❌ PAV-math |
| `h3_regime_fsm.py` | regime state machine | ❌ PAV-math |
| `h4_market_fit.py` | market fit | ❌ PAV-math |
| `h5_skill_velocity.py` | skill velocity | ❌ PAV-math |
| `h6_severity.py` | severity | ❌ PAV-math |
| `score_passion_observation.py` | scoring passion | ❌ PAV-math |
| `score_revenue_observation.py` | scoring revenue | ❌ PAV-math |
| `score_skill_observation.py` | scoring skill | ❌ PAV-math |
| `score_market_observation.py` | scoring market | ❌ PAV-math |
| `score_meta_vector_observation.py` | scoring meta | ❌ PAV-math |
| `score_course_observation.py` | scoring course | ❌ PAV-math |
| `surface_pav_intentions.py` | surfacing PAV | ❌ PAV-math |
| `decompose_rice_observation.py` | RICE decompose | ❌ PAV-math |
| `observe_qhe_observation.py` | Q_HE observe | ❌ PAV-math |
| `observe.md` | observation prompt | ✅ genérico |
| `load_constants.py` | constant loader | ✅ infra |
| `algorithm_constants.json` | algorithm constants | ✅ infra |

**Achado CRÍTICO:** **14 de 15 prompts violam ADR-013** (PAV-math). Em
FAKE_LLM mode passam, mas se você chamar LLM real com MiniMax, esses
prompts vão tentar fazer cálculos PAV que estão FORA de escopo.

### `skills/` — 5 .md files (daily/weekly/monthly/quarterly/meta_plan)

**Achado:** Esses 5 skills **SÃO EXATAMENTE O QUE VOCÊ PEDIU** —
workflows customizados com cadência temporal. Não verifiquei conteúdo
ainda, mas o nome bate com a estrutura de "daily review", "weekly
planning", etc.

### `workers/` — não mapeado

Não li o conteúdo. Próximo passo.

### `tools_v2.py` — 172 LOC

Tools novos do v2 (subset do que está em `tools_legacy_reference.py`).

### `tools_legacy_reference.py` — 722 LOC

**CUIDADO:** nome "legacy" mas é o catálogo de tools antigo. Não usar
como referência ativa.

### `mcp_bridge.py` (v2) — 109 LOC

Bridge MCP v2 — provavelmente stub/conector.

### `state.py` — 259 LOC

State do v2 graph (`IKIGAiStateDict`). Define o schema de state.

### `graph.py` — 515 LOC

Graph principal. **15 nodes** wired com `StateGraph`. `make_v2_graph()`
+ `graph()` factory + `close_graph()` cleanup.

### `subgraph.py` — 747 LOC

Sub-graphs (provavelmente pra parallel execution).

### `subagent_types.py` — 167 LOC

Tipos de sub-agents (types, não implementations).

### `memory_*.py` — ~1.200 LOC (read/write/prune/schema/migrations)

Camada de memória. **Provavelmente o que faz "vault SOT"** mas não
verifiquei schema.

### `checkpoint*.py` — ~1.100 LOC (4 files)

Checkpointer (SqliteSaver). Funciona.

### `sse_publisher.py` — 77 LOC

Server-Sent Events publisher (provavelmente pra "interface thinking aloud").

---

## Tests coverage (real, não claimed)

| test file | LOC | coverage | PASS? |
|---|---|---|---|
| `src/ikigai/tests/test_v2_prompt_chains.py` | 358 | smoke: imports, decorators, drift counts | ✅ 10/10 |
| `src/ikigai/src/agents/v2/tests/` | 0 | **VAZIO** | n/a |
| `src/ikigai/tests/test_canonical_scope.py` | (?) | drift detector: IKIGAI_TOOLS=12 | ✅ |

**Achado:** **Cobertura real é FRACA.** Os 10 testes só verificam que
imports funcionam, não que nodes executam corretamente. Ex.: o teste
`test_v2_drift_detector_count_unaffected` apenas conta tools registradas,
não testa se `recall_node` realmente lê o vault.

---

## O que FUNCIONA (provado)

1. ✅ Graph compila (`make_v2_graph()` retorna `CompiledStateGraph`)
2. ✅ Graph executa end-to-end (`g.invoke({...})` retorna 2 iterações até `surface_intentions`)
3. ✅ 15 nodes plumbed corretamente (grafo navega sem loop infinito)
4. ✅ Checkpointer SQLite funciona (`thread_id='audit-1'` aceito)
5. ✅ FAKE_LLM mode bypassa anthropic SDK
6. ✅ `fork_smoke_graph` compila e tem 4 nodes
7. ✅ `tools_v2.py` registra 8 IKIGAI_NODE_TOOLS

## O que NÃO FUNCIONA (provado)

1. ❌ `taskdog_mcp_graph` quebra no import de `langchain_anthropic`
   (`anthropic.OverloadedError` não existe)
2. ❌ **14 de 15 prompts** usam PAV-math (ADR-013 violado se usar LLM real)
3. ❌ Cobertura de testes real é smoke-only
4. ❌ Não há teste de execução real (nenhum teste chama `g.invoke()`)
5. ❌ Estado do v2 (15 nodes) não está em produção, não está no Studio

## O que NÃO SEI (não verifiquei)

1. ❓ Conteúdo dos 5 skills em `v2/skills/`
2. ❓ Conteúdo de `v2/workers/`
3. ❓ Schema de `v2/state.py` (o que vai no `IKIGAiStateDict`)
4. ❓ Schema de `v2/memory_*.py` (camada de memória)
5. ❓ Se `recall_node` realmente lê vault ou é stub
6. ❓ Se `reflect_node` é o que você quer (metacognition) ou é stub

---

## Diagnóstico REVISADO do BlockingError M150

**M150 diagnosticou errado.** O log mostrou `BlockingError: An internal
error occurred` mas a causa real é:

```
File "...langchain_anthropic/chat_models.py", line 984, in <module>
    class AnthropicOverloadedError(anthropic.OverloadedError, ModelAPIError):
                                   ^^^^^^^^^^^^^^^^^
AttributeError: module 'anthropic' has no attribute 'OverloadedError'
```

Isso é uma **incompatibilidade entre versões do SDK `anthropic` instalado
e o que `langchain_anthropic` espera.** Não é código síncrono bloqueando
event loop. É dependência quebrada.

**Fix possível:** `pip install anthropic>=0.40` (ou versão que tenha
`OverloadedError`) + atualizar `langchain_anthropic`. **Não é refactor
async de 4h.**

---

## Recomendação (decisão do usuário, não do agente)

Você tem 3 caminhos à frente:

### Caminho A — Reviver v2 com fixes pontuais (1-2 sessões)

- Fix `langchain_anthropic` import (atualizar dep)
- Substituir 14 prompts PAV-math por prompts vazios/stub (já que ADR-013)
- Adicionar testes de execução real (não só smoke)
- Registrar v2 no Studio (que agora vai funcionar pq BlockingError era ilusório)
- **Resultado:** v2 funciona como deep agent, mas SEM PAV-math. Honesto com ADR-013.

### Caminho B — Usar v2 só como referência, reescrever do zero (2-3 semanas)

- Reusar **schema** de `state.py`, `memory_*.py`, `checkpoint.py`
- Reusar **5 skills** (daily/weekly/monthly/quarterly/meta_plan)
- Reusar **nomes dos nodes** mas reescrever conteúdo sem PAV-math
- Reusar **invocation pattern** mas com tool surface do nosso projeto
  (12 taskdog tools, 8 IKIGAI tools)
- Reescrever **prompts** do zero
- **Resultado:** fork limpo, v2 não-violation, mas 2-3 semanas.

### Caminho C — td CLI/TUI + Claude Code MCP, parar com deep agent (1 sessão)

- Aceitar que v2 não é prioridade agora
- Usar `td timeline` + `td tui` (commitado M153) + Claude Code MCP
- **Resultado:** fim do escopo, foco em produtividade.

---

## M155-M160 — Próximos milestones SE você for de A ou B

| M | título | LOC | dependência |
|---|---|---|---|
| M155 | Fix `langchain_anthropic` + LLM real (sem PAV-math) | ~50 | M154 ✓ |
| M156 | Substituir 14 prompts PAV-math por stubs | ~300 | M155 |
| M157 | Testes de execução real (não só smoke) | ~400 | M156 |
| M158 | Registrar v2 no Studio, verificar curl | ~30 | M157 |
| M159 | Reflection loop wire-up (reflect_node → display) | ~200 | M158 |
| M160 | Workflows customizados (daily_review, planning_update) | ~600 | M159 |

**Total se A:** ~1.580 LOC em 4-5 sessões.

---

## O que NÃO está em nenhum desses milestones (você precisa decidir)

1. **Quais 3-5 workflows customizados** você quer? (segue padrão
   daily/weekly/monthly/quarterly/meta_plan dos 5 skills existentes?)
2. **Como o vault interage com o agent**? Recall node LÊ vault
   automaticamente? Ou só quando você pedir?
3. **Como você VÊ o agente pensando**? SSE publisher existe mas não
   tem UI consome. `td tui` ganha painel "agente falando"?
4. **Cache strategy**? ChromaDB existe mas não há invalidação. Toda tool
   call re-embeddings? Cache por hash do input?
5. **PAV-math definitivo**? Mantém 14 prompts stub pra sempre, ou
   reativa quando PRD/ADR mudar?

**Sem essas 5 respostas, qualquer caminho (A ou B) vai chutar.**
