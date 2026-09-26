# Spec META-NP — Folha Norte & Folha Projeto como interseção PLAN | PROJ | STUDY

> **Domain:** Knowledge management + meta-learning methodology integrated with `CLUSTER_PLAN` / `CLUSTER_PROJ` / `CLUSTER_STUDY`.
> **Author:** Hermes (session 2026-09-21, brainstorm sobre meta-modelo de gestão do conhecimento).
> **Status:** 🟡 Draft — pre-validation, pre-implementation specification.
> **Date:** 2026-09-21 (rev. 2 — matriz de 5 decisões travada no message 7).
> **Methodology:** Pivô data-first ativo (ver `vault/ikigai/meta/AGENTS.md` §3). Esta spec **NÃO vira fonte de verdade** antes de 5+ logs manuais validando o método.
> **Companion drafts:**
> - `vault/drafts/folha-norte-projeto-META-v1-invented.md` — versão que Hermes inventou (NÃO recomendada; preservada pra contraste).
> - `vault/drafts/folha-norte-projeto-META-v2-known-method.md` — versão pura do método conhecido.
> - `vault/drafts/folha-norte-projeto-META-v3-interseccao.md` — esta versão (interseção clusters), espelhada aqui com matriz travada.

---

## 0. Sumário executivo

Esta spec formaliza a **camada de meta-learning** que conecta os três clusters
do repo (`CLUSTER_PLAN` + `CLUSTER_PROJ` + `CLUSTER_STUDY`) à metodologia
"**Folha Norte + Folha Projeto**" — uma técnica de gestão do conhecimento
que combate a "ilusão dos estudos" forçando foco semanal reduzido e
filtros de atenção explícitos.

**Problema que resolve:**

- 95% do conteúdo que aparece "interessante" não avança nenhum objetivo
  macro; sem filtro explícito, vaza pra Folha Projeto e destrói o foco.
- Planos semanais viram wishlist de 12 tópicos sem entregáveis verificáveis.
- Não existe ligação explícita entre **objetivo macro** (Folha Norte) e
  **task TW** (Cluster PROJ) e **tópico de estudo** (Cluster STUDY).

**Proposta (matriz travada):**

- Adotar 2 tipos de notas com cadência distinta (Folha Norte semestral +
  Folha Projeto semanal/mensal) **acima** dos clusters existentes.
- **Folha Norte NÃO entra no repo** — só no vault/Obsidian.
- **Árvore de dependências cognitivas** = seção da Folha Projeto **no Obsidian**.
- **Notes diárias de discovery** = (a) resumo inline + (b+C) logs separados (backlog + reflexão auto-aplicada).
- **Revisão Periódica** = novo componente agregador cross-domain (PROJ + STUDY + IKIGAi) que emite tasklist pro mesh.
- **`perfil_de_uso: [cognitivo | fisico | hibrido]`** no frontmatter da Folha Projeto (customização detectada 2026-09-21 com a Folha `calistenia-campeao` — define se vocabulário de software, treino, ou misto).

---

## 0.1 Matriz travada (2026-09-21)

| # | Decisão | Resposta |
|---|---|---|
| 1 | Forma das 2 vias | **1 arquivo SOT** (planejamento); reviews em `./strategics/` + Revisão Periódica |
| 2 | Folha Norte no repo? | **Não.** Só Folha Projeto no repo. |
| 3 | Árvore cognitiva | **Seção da Folha Projeto no Obsidian** |
| 4 | Notes de discovery | (a) inline resumo + (b+C) logs separados |
| 5 | Relato/review | `./strategics/` (existente) + Revisão Periódica (novo agregador) |

---

## 1. Estado atual (mapeado em 2026-09-21)

### 1.1 Clusters existentes

| Cluster | Doc principal | Cobertura nativa |
|---|---|---|
| `CLUSTER_PLAN` | `CLUSTER_PLAN.md` (1861 linhas) | Rotinas, blocos de tempo, pomodoro 50+10, rituais de transição, janelas de sono, regime, Q_HE, 5 templates inline. |
| `CLUSTER_PROJ` | `CLUSTER_PROJ.md` (944 linhas) | SoftwareProject, Epic, Sprint, Task (Taskwarrior UDAs), velocity/burndown/ROI, anti-patterns PMO. |
| `CLUSTER_STUDY` | `CLUSTER_STUDY.md` | Tópicos, pré-req, skill gap detection, MOCs e notas atômicas. |

### 1.2 Gap (o que os clusters NÃO cobrem)

- **Filtros de atenção** ("dizer não" sistemático a 95% do conteúdo).
- **Foco semanal reduzido** (2-4 tópicos deliberadamente selecionados).
- **Entregáveis verificáveis por ciclo** (Feynman, 50 questões, mini-projeto).
- **Ligação explícita objetivo-macro ↔ task-granular ↔ dependência cognitiva**.
- **Agregador cross-domain** que cruza PROJ + STUDY + IKIGAi → tasklist.

---

## 2. Proposta — componentes por local

### 2.1 Por local (matriz final)

| Local | Folha Norte | Folha Projeto | Árvore Cogn. | Relato/Review |
|---|---|---|---|---|
| **Repo (código)** | ❌ | ✅ SOT + `## Discovery Log` + 2 logs separados | ❌ | ❌ |
| **Vault (repo)** | ✅ SOT | ✅ SOT (espelhada) | ❌ (é seção da Folha Projeto) | ❌ |
| **Obsidian** | ✅ | ✅ (com Árvore Cogn.) | ✅ seção | ✅ link |

### 2.2 Novos componentes

| Componente | Onde mora | Função |
|---|---|---|
| **Folha Norte** | `vault/00-norte/<slug>.md` + Obsidian | Bússola — revisão semestral. Objetivos macro + Habilidades + Filtros de Atenção. |
| **Folha Projeto (repo)** | Repo, próximo ao código | Tática semanal/mensal. Foco reduzido + Recursos + Entregáveis + Backlog + Discovery Log. |
| **Folha Projeto (Obsidian)** | Obsidian | Espelho navegável + seção Árvore Cognitiva. |
| **Revisão Periódica** | `vault/revisoes/<YYYY-MM>-<sonho>-rev<N>.md` + Obsidian | Agregador cross-domain. Coleta PROJ + STUDY + IKIGAi; você dá narrativa; emite tasklist pro mesh. |
| **`./strategics/`** | Já existe | Modelo conceitual (não duplicar). |

Templates completos (com todos os campos): ver
`vault/drafts/folha-norte-projeto-META-v3-interseccao.md` §3. Não duplicados
aqui pra evitar drift entre as duas localizações.

---

## 3. Localização proposta

| Camada | Path primário | Por quê |
|---|---|---|
| **Folha Norte** (fonte de verdade) | `vault/00-norte/<slug>.md` | Convenção Obsidian; append-only; bidirecional |
| **Folha Projeto** (fonte de verdade) | `vault/projetos/<YYYY>-S<WW>-<slug>.md` | Idem; semanal = muitas folhas |
| **Folha Projeto (repo)** | `code_space/<projeto>/folha-<slug>.md` ou similar | Onde o código vive |
| **Specs** (esta) | `code-docs/specs/2026-09-21-spec-META-NP-folha-norte-projeto.md` | ADR formal; review-by-code |
| **Drafts de brainstorm** | `vault/drafts/folha-norte-projeto-META-v{1,2,3}-*.md` | Histórico de iteração |
| **MOCs / Notas atômicas** | `vault/MOCs/` + `vault/study/` | Já cobertos por `CLUSTER_STUDY.md` |
| **`vault/inbox/`** | `vault/inbox/YYYY-MM.md` | Tentação que NÃO entra na Folha Projeto |
| **Revisão Periódica** | `vault/revisoes/<YYYY-MM>-<sonho>-rev<N>.md` | Agregador cross-domain |
| **Strategics** | `./strategics/` (existente) | Modelo conceitual — NÃO duplicar |

**Espelhamento Obsidian:** via `vault-bidirectional-sync-completion.md`
(mecanismo já documentado). Pressupõe que `vault/00-norte/` é o source-of-truth
e o Obsidian (em `G:\Other computers\...\mandarin-learning\`) é o espelho
read-only navegável.

---

## 4. Integração com cada cluster (delimitação explícita)

### 4.1 Com `CLUSTER_PLAN.md` (QUANDO)

| Folha Norte / Projeto usa | Cluster PLAN oferece |
|---|---|
| `bloco_plan_recomendado` no frontmatter | Bloco de Tempo (§2.5) |
| Hiperfoco Diário (Folha Projeto §9) | Pomodoro 50+10 (§2.5) + Ritual de Transição (§2.5) |
| Cadência semanal de revisão | Mid-Wave-Review (§3.5) + Wave-End-Review (§3.5) |

**NÃO duplicar:** a Folha Projeto **não redefine** rotinas.

### 4.2 Com `CLUSTER_PROJ.md` (COMO EXECUTAR)

| Folha Projeto usa | Cluster PROJ oferece |
|---|---|
| Backlog (story points) | Taskwarrior cards + UDAs (`folha_projeto_fk` proposto) |
| Mini-projeto commit | SoftwareProject + Epic + Sprint + Task + GitCommit link |
| Velocity semanal implícita | Velocity / Burndown / ROI §9 do PROJ |
| Changelog vs Roadmap | Cross-check com commits |

**NÃO duplicar:** a Folha Projeto **não redefine** épicos/sprints.

### 4.3 Com `CLUSTER_STUDY.md` (MATERIAL)

| Folha Norte / Projeto usa | Cluster STUDY oferece |
|---|---|
| Habilidades Requeridas (Folha Norte §2) | Tópicos + pré-req + skill gap detection |
| Tópico do Foco Reduzido (Folha Projeto §1) | Notas atômicas + MOCs |
| Entregável "resumo Feynman" / "mapa mental" | Output canônico de STUDY |
| Árvore Cognitiva (Folha Projeto Obsidian §4) | **Nova ponte**: blocker → cognição → tópico STUDY |

**NÃO duplicar:** a Folha Projeto **não substitui** notas atômicas; ela **aponta** qual nota cada entregável vai popular.

---

## 5. Componentes novos (Revisão Periódica, Árvore Cognitiva, Discovery Log)

### 5.1 Revisão Periódica (agregador cross-domain)

**Função:** Fecha o loop entre PROJ + STUDY + IKIGAi → tasklist pro mesh.

**Localização:** `vault/revisoes/<YYYY-MM>-<sonho>-rev<N>.md` + espelhada no Obsidian.

**Cadência:** mensal (recomendado) ou quando `Árvore Cognitiva` atinge 3+ blockers novos.

**Input (coletado):**
- Story points entregues / Backlog atualizado / Blockers abertos / Velocity (do PROJ).
- Tópicos estudados / Notas Feynman entregues / Árvore cognitiva atualizada (do STUDY).
- Vetores IKIGAi / Q_HE (do IKIGAi).

**Output:**
- **Narrativa** (texto livre, 1-3 parágrafos) — você escreve.
- **Atualização da SOT** (Folha Norte + Folha Projeto + Cognitive Tree).
- **Tasklist YAML** → alimenta `data/review_queue/` via `TaskChange` (Phase 3 mesh).

### 5.2 Árvore de Dependências Cognitivas (Folha Projeto Obsidian §4)

**Função:** Captura requisitos de estudo derivados dos BLOCKERS do código.

**Pergunta-âncora:** "O que eu REALMENTE preciso saber pra desbloquear, vs. o que eu posso resolver com prompt?"

**Estrutura:** por Blocker → Habilidade Cognitiva → Tópico STUDY → Code-task.

**Heurística "prompt vs. cognição":**
- Se a resposta cabe em ≤1 prompt bem-anexado: **prompt**, não estude.
- Se a resposta exige modelo mental novo: **cognição**, Folha Projeto STUDY.

**Promoção opcional:** quando estável (3+ iterações sem novos blockers), vira nota separada `cognitive-tree-<TOPIC>.md`.

### 5.3 Discovery Log (Folha Projeto repo)

**Função:** Append-only do progresso diário.

**Estrutura:**
- **Resumo inline** (na própria Folha Projeto, seção `## Discovery Log`): 1-3 bullets por dia (progresso / blockers / proposições próx dia).
- **Log de backlog estruturado** (`notes/<YYYY-MM-DD>-<slug>-backlog.md`): decisões técnicas detalhadas.
- **Log de reflexão auto-aplicada** (`notes/<YYYY-MM-DD>-<slug>-reflexao.md`): reflexão sobre o processo + dificuldades — similar ao vault SOT mas pra software.

---

## 6. Workflow integrado

### 6.1 Cadência semanal (Folha Projeto no repo)

```
[Dom/Seg]  Abrir Folha Projeto (repo)
            ↓
           Olhar Folha Norte (vault) — prioridades
            ↓
           Selecionar 2-4 tópicos → foco da semana
            ↓
[Dia]      Executar: tasks no PROJ, notas no STUDY, blocos no PLAN
            ↓
           Append no `## Discovery Log` (resumo diário)
           + criar `notes/<date>-<slug>-backlog.md` (decisões técnicas)
           + criar `notes/<date>-<slug>-reflexao.md` (reflexão)
            ↓
[Sábado]   Atualizar Árvore Cognitiva no Obsidian (blockers → cognição)
            ↓
[Dom]      Revisar entregáveis → carry-over
```

### 6.2 Cadência semestral (Folha Norte)

A cada 6 meses: revisar Objetivos + Habilidades + Filtros. Mover o que não serve pra `vault/00-norte/arquivados/`.

### 6.3 Cadência mensal (Revisão Periódica)

```
[Mês]      Coleta auto de PROJ + STUDY + IKIGAi
            ↓
           Você escreve narrativa
            ↓
           Atualiza SOT (Folha Norte + Projeto + Cognitive Tree)
            ↓
           Emite tasklist YAML → data/review_queue/
            ↓
           IKIGAi agent (Phase 3 mesh) consome + propaga
```

---

## 7. Anti-patterns (específicos desta spec)

- ❌ **Folha Norte no repo:** ilegal (decisão #2).
- ❌ **2 arquivos SOT paralelos:** ilegal (decisão #1). É 1 arquivo SOT + review externo.
- ❌ **Folha Projeto com > 4 tópicos:** foco perdido.
- ❌ **Cognitive Tree sem blockers reais:** vira "lista de tópicos" e perde a amarração.
- ❌ **Revisão Periódica sem narrativa:** vira dashboard morto.
- ❌ **Tasklist sem `folha_projeto_fk`:** task órfã.
- ❌ **Misturar camadas:** Cognitive Tree na Folha Norte, backlog na Folha Norte, etc.
- ❌ **Duplicar `./strategics/`:** já existe; não criar novo lugar pra modelo conceitual.

---

## 8. Critérios de aceitação (pivô data-first)

Esta spec **NÃO vira implementação** (código, CLI, parser, dashboard) antes
de TODOS os critérios abaixo serem satisfeitos:

- [ ] ≥ 5 instâncias reais de Folha Norte preenchidas manualmente.
- [ ] ≥ 4 semanas de Folhas Projeto semanais preenchidas.
- [ ] ≥ 1 ciclo completo de revisão semestral da Folha Norte.
- [ ] ≥ 1 Revisão Periódica completa (com narrativa + tasklist emitida pro mesh).
- [ ] Decisão registrada: 95% das Tentação foram descartadas pelos Filtros de Atenção?
- [ ] Decisão registrada: Folha Projeto sustentou o foco (≥50% dos entregáveis cumpridos)?

---

## 9. Tensões conhecidas (a resolver antes de promoção)

| Tensão | Status | Próximo passo |
|---|---|---|
| Sincronização repo ↔ vault ↔ Obsidian | Mecanismo já existe (`vault-bidirectional-sync-completion.md`) | Validar que sync suporta 3 vias |
| Onde mora `vault/inbox/` | Pressuposto pelo método | Criar `vault/inbox/YYYY-MM.md` na primeira semana |
| IKIGAi agent consumindo Revisão Periódica | Phase 3 mesh tem `agent_consumer` + `agent_propagator` | Especificar adapter que lê §4 da Revisão Periódica e emite `TaskChange` |
| Frontmatter drift | Pivô data-first ativo | Não adicionar chave YAML sem remover outra |
| Onde mora o `folha-projeto-<slug>.md` no repo | Decidir se fica em `code_space/<projeto>/` ou em `vault/projetos/` espelhado | Pendente |

---

## 10. Próximos passos

### 10.1 Imediato (esta sprint)

- [ ] Ler esta spec + os 3 drafts.
- [ ] Decidir se quer começar com a Folha Norte "calistenia-campeão".

### 10.2 Próximas 4 semanas (validação manual)

- [ ] Criar 1 Folha Norte concreta (`vault/00-norte/calistenia-campeao.md`).
- [ ] Criar 4 Folhas Projeto semanais consecutivas linkadas a ela.
- [ ] Preencher entregáveis e revisar cada fim-de-semana.

### 10.3 Após 5+ logs (potencial promoção)

- [ ] Promover esta spec de 🟡 Draft → 🟢 Aprovada (1 commit atômico).
- [ ] Mover templates de `vault/drafts/` pra `vault/00-norte/_TEMPLATE-norte.md` e `vault/projetos/_TEMPLATE-projeto.md`.
- [ ] Especificar adapter IKIGAi que consome Revisão Periódica.
- [ ] Decidir se vale CLI (`life folha add <projeto>`) ou se markdown puro basta.

---

## 11. Referências cruzadas

- **Drafts:** `vault/drafts/folha-norte-projeto-META-v{1,2,3}-*.md` (esta spec espelha v3).
- **Clusters:** `CLUSTER_PLAN.md`, `CLUSTER_PROJ.md`, `CLUSTER_STUDY.md`.
- **Conceitual:** `CONCEPTUAL_MODEL.md` (IKIGAi vectors).
- **Sync:** `vault/drafts/vault-bidirectional-sync-completion.md`.
- **Data-first pivot:** `vault/ikigai/meta/AGENTS.md` §3.
- **Templates existentes:** `vault/ikigai/templates/sonho-log.md`.

---

**Esta spec permanece 🟡 Draft até que §8 seja integralmente cumprida.**