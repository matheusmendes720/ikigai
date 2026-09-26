# META-NP — Índice de Navegação (Folha Norte & Folha Projeto)

> **Status:** 🟡 Draft — pivô data-first ativo.
> **Data:** 2026-09-21.
> **Propósito:** Centraliza a navegação entre os 4 documentos do brainstorm META-NP, evitando drift entre eles.

---

## Os 4 documentos

| Doc | Path | Conteúdo | Status |
|---|---|---|---|
| **Draft v1** | `vault/drafts/folha-norte-projeto-META-v1-invented.md` | Versão que **Hermes inventou** na sessão 2026-09-21 (8 campos, FK rígido, web app). **NÃO recomendada** — preservada pra contraste e pra mostrar a diferença entre inventar e aderir a um método conhecido. | 🟡 Draft (histórico) |
| **Draft v2** | `vault/drafts/folha-norte-projeto-META-v2-known-method.md` | Versão **pura do método conhecido** apresentado pelo Matheus (Folha Norte com filtros + Folha Projeto 2-4 tópicos). É a base pros templates do Obsidian. | 🟡 Draft (base) |
| **Draft v3** | `vault/drafts/folha-norte-projeto-META-v3-interseccao.md` | v2 + **delimitação explícita** com `CLUSTER_PLAN` / `CLUSTER_PROJ` / `CLUSTER_STUDY` + matriz travada de 5 decisões + templates completos (4 tipos: Folha Projeto repo, Folha Norte vault, Folha Projeto Obsidian, Revisão Periódica). | 🟡 Draft (interseção) |
| **Spec META-NP** | `code-docs/specs/2026-09-21-spec-META-NP-folha-norte-projeto.md` | A **"face rica que indexa outros"** — spec formal (ADR) com §0 sumário executivo + matriz travada + §1-§4 (estado atual, proposta, localização, integração com clusters) + §5 (componentes novos) + §6 workflow + §7 anti-patterns + §8 critérios de aceitação (data-first) + §9 tensões + §10 próximos passos + §11 referências. | 🟡 Draft (ADR) |

---

## Qual ler quando

| Situação | Ler |
|---|---|
| Quero entender o método conhecido (Folha Norte + Folha Projeto) | **v2** |
| Quero implementar/integrar com os clusters do repo | **v3** + **Spec META-NP** |
| Quero revisar a evolução do brainstorm | **v1** (pra contraste) → **v2** → **v3** |
| Quero promover a spec pra 🟢 Aprovada | **Spec META-NP §8** (critérios de aceitação) |
| Quero ver templates concretos para preencher | **v3 §3** (4 templates: Folha Projeto repo, Folha Norte vault, Folha Projeto Obsidian, Revisão Periódica) |
| Quero entender o fluxo semanal / mensal / semestral | **v3 §4** ou **Spec META-NP §6** |

---

## Onde cada componente mora (matriz final)

| Componente | Repo (código) | Vault (repo) | Obsidian |
|---|---|---|---|
| Folha Norte | ❌ não entra | ✅ `vault/00-norte/<slug>.md` (SOT) | ✅ navegável |
| Folha Projeto | ✅ SOT + `## Discovery Log` + 2 logs separados (`notes/<date>-<slug>-backlog.md` + `notes/<date>-<slug>-reflexao.md`) | ✅ `vault/projetos/<YYYY>-S<WW>-<slug>.md` (espelhada) | ✅ navegável + 🌳 Árvore Cognitiva (seção §4) |
| Revisão Periódica | ❌ | ✅ `vault/revisoes/<YYYY-MM>-<sonho>-rev<N>.md` | ✅ link |
| `./strategics/` (modelo conceitual) | já existe — não duplicar | já existe | link |

---

## Decisões travadas (não revogar sem motivo)

| # | Decisão | Resposta | Origem |
|---|---|---|---|
| 1 | Forma das 2 vias | **1 arquivo SOT** (planejamento); reviews em `./strategics/` + Revisão Periódica | message 7 |
| 2 | Folha Norte no repo? | **Não.** Só Folha Projeto no repo. | message 7 |
| 3 | Árvore cognitiva | **Seção da Folha Projeto no Obsidian** | message 7 |
| 4 | Notes de discovery | (a) inline resumo + (b+C) logs separados | message 7 |
| 5 | Relato/review | `./strategics/` (existente) + Revisão Periódica (novo agregador) | message 7 |
| 6 | `perfil_de_uso` no frontmatter | `[cognitivo | fisico | hibrido]` — define se vocabulário é software, treino, ou misto | customização 2026-09-21 (Folha calistenia-campeao) |

---

## Pivô data-first (regra de promoção)

Nenhum dos 4 docs vira fonte de verdade antes de **todos** os critérios da **Spec META-NP §8**:

- [ ] ≥ 5 instâncias reais de Folha Norte preenchidas manualmente.
- [ ] ≥ 4 semanas de Folhas Projeto semanais preenchidas.
- [ ] ≥ 1 ciclo completo de revisão semestral da Folha Norte.
- [ ] ≥ 1 Revisão Periódica completa (com narrativa + tasklist emitida pro mesh).
- [ ] Decisão registrada: 95% das Tentação foram descartadas pelos Filtros de Atenção?
- [ ] Decisão registrada: Folha Projeto sustentou o foco (≥50% dos entregáveis cumpridos)?

---

## Anti-patterns consolidados (das 3 versões + spec)

- ❌ **Folha Norte no repo.** Ilegal (decisão #2).
- ❌ **2 arquivos SOT paralelos.** Ilegal (decisão #1).
- ❌ **Folha Projeto com > 4 tópicos.** Foco perdido.
- ❌ **Folha Norte sem Filtros de Atenção concretos.** Vira wishlist.
- ❌ **Cognitive Tree sem blockers reais.** Vira "lista de tópicos de estudo".
- ❌ **Revisão Periódica sem narrativa.** Vira dashboard morto.
- ❌ **Tasklist sem `folha_projeto_fk`.** Task órfã.
- ❌ **Misturar camadas.** Cognitive Tree na Folha Norte, backlog na Folha Norte, etc.
- ❌ **Duplicar `./strategics/`.** Já existe.
- ❌ **Tratar Folha Norte como lista de desejos.** É bússola, não bucket list.
- ❌ **Frontmatter drift.** Adicionar chave YAML sem remover outra.
- ❌ **Implementar CLI / parser / dashboard antes de 5+ logs.** Viola pivô data-first.

---

## Próximo passo imediato

- [ ] Ler este índice.
- [ ] Confirmar matriz travada (§ "Decisões travadas" acima) ou ajuste o registro.
- [ ] Decidir se quer começar com a Folha Norte "calistenia-campeão" (sonho mencionado em 2026-09-21, ainda não registrado em vault).
- [ ] Aguardar fim do brainstorm antes de promover qualquer fonte de verdade.