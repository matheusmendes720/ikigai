# Folha Norte & Folha Projeto — Draft META v3 (interseção com clusters — REVISADO)

> **Status:** Working draft (v3 — método conhecido + integração com CLUSTER_PLAN/PROJ/STUDY).
> **Data:** 2026-09-21.
> **Source:** brainstorm session 2026-09-21, message 3 (pedido do Matheus) + matriz de 5 decisões travada no message 7.
> **Audiência:** Matheus + future IKIGAi agents revisando pivô data-first.
> **Convenção:** drafts em `vault/drafts/` são working drafts; só viram fonte de verdade depois de 5+ logs manuais ou aprovação explícita.
> **Mudanças desde v3.0:** reescrito §1 (Hierarquia), §2 (Separação por local), §3 (Templates), §4 (Workflow), §5 (Anti-patterns), §6 (Tensões). Adicionado §3.3 (Folha Projeto no Obsidian com Árvore Cognitiva), §3.4 (Revisão Periódica como novo componente agregador). Folha Norte NÃO entra no repo. Logs separados (backlog + reflexão) na Folha Projeto do repo.

---

## 0. Matriz travada (2026-09-21, message 7)

| # | Decisão | Resposta |
|---|---|---|
| 1 | Forma das 2 vias | **1 arquivo SOT** (planejamento); reviews em `./strategics/` (modelo conceitual) + **Revisão Periódica** (agregador cross-domain) |
| 2 | Folha Norte no repo? | **Não.** Só Folha Projeto no repo. |
| 3 | Árvore de dependências cognitivas | **Seção da Folha Projeto no Obsidian** |
| 4 | Notas diárias de discovery | **(a)** resumo inline na Folha Projeto + **(b+C)** logs separados (backlog + reflexão auto-aplicada), estilo vault SOT mas pra software |
| 5 | Relato real / re-iteração | **`./strategics/` = modelo conceitual** (existente); **`Revisão Periódica` = novo componente agregador** que cruza repo + Obsidian + IKIGAi → emite tasklist pro mesh |
| 6 (2026-09-21) | `perfil_de_uso` no frontmatter Folha Projeto | `[cognitivo | fisico | hibrido]` — define se vocabulário é software, treino, ou misto. Customização detectada validando com Folha `calistenia-campeao`. |

---

## 1. Hierarquia conceitual (atualizada)

```
┌─────────────────────────────────────────────────────────────┐
│ ./strategics/                  ← Modelo conceitual (existente)│
│   (NÃO duplicar; já existe)                                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Revisão Periódica             ← NOVO componente agregador  │
│   (cross-domain: PROJ + STUDY + IKIGAi → tasklist)          │
│   Morada: vault/revisoes/<YYYY-MM>-<sonho>-rev<N>.md         │
│          + espelhada no Obsidian                             │
└──────┬──────────────┬───────────────┬───────────────────────┘
       │ atualiza     │ atualiza      │ atualiza
       ▼              ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Folha Norte │ │ Folha       │ │ Cognitive   │
│ (vault/00-  │ │ Projeto     │ │ Tree        │
│ norte/)     │ │ (vault/ +   │ │ (seção da   │
│             │ │ repo +      │ │ Folha       │
│             │ │ Obsidian)   │ │ Projeto no  │
│             │ │             │ │ Obsidian)   │
└─────────────┘ └──────┬──────┘ └─────────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ CLUSTER_    │ │ CLUSTER_    │ │ CLUSTER_    │
│ PLAN        │ │ PROJ        │ │ STUDY       │
│ (quando)    │ │ (como exec.)│ │ (material)  │
└─────────────┘ └─────────────┘ └─────────────┘
```

---

## 2. Separação por local (matriz final)

| Local | Folha Norte | Folha Projeto | Árvore Cogn. | Relato/Review |
|---|---|---|---|---|
| **Repo (código)** | ❌ Não | ✅ Só a SOT (planejamento) + `## Discovery Log` (resumo) + 2 logs separados (backlog, reflexão) | ❌ Não | ❌ Não |
| **Vault (repo)** | ✅ SOT | ✅ SOT (espelhada) | ❌ Não (é seção da Folha Projeto) | ❌ Não (vai pra `./strategics/` + Revisão Periódica) |
| **Obsidian** | ✅ Navegável | ✅ Navegável (com seção Árvore Cognitiva) | ✅ Seção da Folha Projeto no Obsidian | ✅ Link pra `./strategics/` + Revisão Periódica |

---

## 3. Templates REVISADOS (com matriz travada)

### 3.1 Folha Projeto (no REPO — código)

```markdown
---
tipo: folha-projeto
projeto_id: PK-<YYYY>-S<WW>-<slug>
sonho_fk: <NK-do-sonho>            # wiki-link [[🧭 Folha Norte — ...]]
criado: YYYY-MM-DD
periodo: [2026-S39 | 2026-10]
status: [verde | amarelo | vermelho]
estagio: [sonar | dream | build | ship | honor]
vetor_ikigai: [paixao | missao | vocacao | profissao]
bloco_plan_recomendado: [manha | tarde | noite]
perfil_de_uso: [cognitivo | fisico | hibrido]   # ← NOVO (2026-09-21, learn from calistenia folha)
---

# 🎯 Folha Projeto — <período> — <título do projeto>

> **Origem:** [[🧭 Folha Norte — <título>]], habilidades X, Y, Z.
> **Perfil de uso:** `<cognitivo | fisico | hibrido>` — define adaptações abaixo.
> **Discovery Coding:** link pro post-manifesto que motivou este projeto.

> **Adaptações por perfil (v3.1, 2026-09-21):**
> - **`cognitivo`:** §4 Backlog usa story points / épicos. §6 Velocity usa pomodoros/story points. §9 Hiperfoco = pomodoro 50+10.
> - **`fisico`:** §4 Backlog renomeia pra "decisões de periodização" (sem story points). §6 Velocity renomeia pra "sessões/semana + mobilidade". §9 Hiperfoco = bloco contínuo 60-90min (sem pomodoro — treino precisa de foco contínuo).
> - **`hibrido`:** mistura — usa ambos os vocabulários, marcando o que for software vs físico.

## 1. Foco Reduzido (2-4 tópicos — deliberadamente)
_(Tudo que não está aqui fica em `vault/inbox/`.)_
1. **Tópico A** → habilidade X da Folha Norte → tópico STUDY `[[topico-X]]`
2. **Tópico B** → habilidade Y → tópico STUDY `[[topico-Y]]`
3. **Tópico C** → habilidade Z → tópico STUDY `[[topico-Z]]`

## 2. Recursos Selecionados (≤5 fontes, exaurir antes de abrir outros)
- 📘 Livro/Curso: <título> — capítulos X-Y
- 🎥 Aula: <URL> — aulas 1-7
- 📄 Artigo: <URL>
- 🛠️ Doc oficial: <URL>

## 3. Entregáveis Práticos (1 por tópico — sem entrega, o tópico cai do ciclo)
| Tópico | Entregável | Deadline | Status | Liga com |
|---|---|---|---|---|
| A | Resumo Feynman (1 página) | sex | ⬜ | `vault/study/topico-X.md` |
| B | 50 questões resolvidas | qua | ⬜ | `code_space/X/` (CLUSTER_PROJ) |
| C | Mini-projeto commit | sáb | ⬜ | épico `epic-XXX` (CLUSTER_PROJ) |

## 4. Backlog (story points / prioridade / dependência)
- [ ] **M1 — <título>**: <descrição>
  - story points: 5
  - prioridade: alta (bloqueia M2)
  - dependência: nenhuma
  - épico pai: epic-<id>
- [ ] **M2 — <título>**: <descrição>
  - story points: 8
  - prioridade: alta
  - dependência: M1

## 5. Changelog vs Roadmap
| Data | Commit/Issue | Roadmap batia? | Desvio |
|---|---|---|---|
| YYYY-MM-DD | feat: M1 input-tracker | sim | — |
| YYYY-MM-DD | docs: tonelagem-formula | não | +2d (descoberta de unidade) |

## 6. Velocity & Ritmo
- Pomodoros/semana: X
- Story points entregues/sprint: Y
- Última sprint: Z pontos / W planejados

## 7. User Stories (o "pra quê" humano)
_(linkar à fonte original, ex: Jimmy Miller discovery coding)_
- Como atleta, quero registrar sets/reps pra ver evolução sem planilha.
- Como atleta, quero detecção de postura pra corrigir em tempo real.

## 8. Métricas de Progresso (KPIs)
| KPI | Meta | Atual | Δ |
|---|---|---|---|
| Módulos M1-M4 done | 100% | 25% | +25% |

## 9. Hiperfoco Diário (micro-rotina)
- [ ] Bloco dedicado: 1h/dia no `bloco_manha` (CLUSTER_PLAN §2)
- [ ] Pomodoro 50+10 com `timewarrior` tag
- [ ] Sem paralelo: 1 sessão = 1 tópico
- [ ] Sem `vault/inbox/` durante o ciclo

## 10. Pontes com os Clusters
- **CLUSTER_PLAN:** usa `bloco_<X>` + pomodoro (sem rotina nova).
- **CLUSTER_PROJ:** entregáveis viram Taskwarrior cards + commits (IDs `epic-XXX`, `task-XXX`).
- **CLUSTER_STUDY:** entregáveis viram notas atômicas + MOCs.

---

## ## Discovery Log (append-only, datado)
> Resumo diário inline. Logs estruturados detalhados em:
> - `notes/<YYYY-MM-DD>-<slug>-backlog.md` (decisões técnicas)
> - `notes/<YYYY-MM-DD>-<slug>-reflexao.md` (reflexão auto-aplicada — similar ao vault SOT mas pra software)

### YYYY-MM-DD — <título da sessão>
- **Progresso:** <1-3 bullets curtos>
- **Blockers:** <lista>
- **Proposições próx dia:** <lista>
- **Links:** <commits, issues, notas>

### YYYY-MM-DD — <próxima sessão>
...
```

---

### 3.2 Folha Norte (no VAULT — SOT)

```markdown
---
tipo: folha-norte
norte_id: NK-<YYYYMMDD>-<slug>
criado: YYYY-MM-DD
ultima_revisao: YYYY-MM-DD
proxima_revisao: YYYY-MM-DD        # +6 meses
status: [ativa | pausada | concluida]
vetores_ikigai: []                # paixão, missão, vocação, profissão
---

# 🧭 Folha Norte — <título do objetivo macro>

> **Declaração de Norte (1 frase, presente do indicativo):**
> _"Eu quero <resultado observável concreto>, até <data/idade/marco>."_

## 1. Objetivos Principais (3-5)
1. <Objetivo 1>
2. <Objetivo 2>
3. <Objetivo 3>

## 2. Habilidades Requeridas (por objetivo)
_(Estas são as habilidades — Study topics derivam daqui.)_

### Objetivo 1: <título>
- Habilidade A → tópico STUDY `[[topico-A]]`
- Habilidade B → tópico STUDY `[[topico-B]]`

## 3. Filtros de Atenção (o "não" sistemático)
_(**Não** vive em nenhum cluster — exclusivo da Folha Norte.)_
- ❌ Não consumo conteúdo que não está numa habilidade declarada acima.
- ❌ Não abro > 3 fontes simultâneas sobre o mesmo tema (anti-overload).
- ❌ Não assisto/leo sem entregar algo em ≤7 dias.
- ✅ Só entra na Folha Projeto o que avança ≥ 1 Habilidade Requerida.
- ✅ Se conteúdo não avança objetivo macro, anoto em `vault/inbox/` e reviso mensalmente.

## 4. Mapeamento pros Clusters
- **PLAN** (`CLUSTER_PLAN.md`): quais blocos/rituais dedicam tempo a este Norte?
- **PROJ** (`CLUSTER_PROJ.md`): quais SoftwareProjects materializam este Norte?
- **STUDY** (`CLUSTER_STUDY.md`): quais tópicos/skills gap estão sendo fechados?

## 5. Folha(s) Projeto Ativas
- [[Folha Projeto — 2026-S39 — <foco>]]
- [[Folha Projeto — 2026-S40 — <foco>]]

## 6. Estratégia conceitual (link → ./strategics/)
> O **relato real** e a reflexão moram em `./strategics/<sonho>.md`.
> A **revisão periódica** (agregador cross-domain) emite tasklist pro mesh.

## 7. Revisão Semestral (próxima em YYYY-MM-DD)
Perguntas:
- Algum objetivo macro mudou? (realocação, adição, remoção)
- Alguma habilidade virou irrelevante?
- Algum filtro de atenção não está sendo respeitado?
- Algum cluster precisa atualizar a forma como serve este Norte?
```

---

### 3.3 Folha Projeto (no OBSIDIAN — com Árvore Cognitiva)

```markdown
---
tipo: folha-projeto-obsidian
projeto_id: PK-<YYYY>-S<WW>-<slug>
folha_norte_fk: <NK-do-sonho>
criado: YYYY-MM-DD
espelho_repo: <link pro folha-projeto no repo>
---

# 📅 Folha Projeto (Obsidian) — <período> — <foco>

> **Espelho navegável** da Folha Projeto no repo.
> Origem: [[🧭 Folha Norte — <título>]].

## 1. Foco Reduzido (espelho)
_(ver repo §1)_

## 2. Recursos Selecionados (espelho)
_(ver repo §2)_

## 3. Entregáveis (espelho)
_(ver repo §3)_

## 4. 🌳 Árvore de Dependências Cognitivas
_(Exclusivo do Obsidian. Captura requisitos de estudo derivados dos BLOCKERS
do código. Resposta à pergunta: "o que eu REALMENTE preciso saber pra
desbloquear, vs. o que eu posso resolver com prompt?")_

### 4.1 Blockers do código (vindos do repo `## Discovery Log`)
- **Blocker B1** (YYYY-MM-DD): <descrição>
  - Pode ser resolvido com prompt? [sim/não]
  - Se não, requer saber: <habilidade cognitiva>
  - Tópico STUDY relacionado: [[topico-X]]
  - Status: [pendente | em estudo | resolvido]

### 4.2 Grafo de dependências
```
[Blocker B1]
  ↓ requer saber
[Habilidade H1]
  ↓ ensina via
[Tópico STUDY T1]
  ↓ pratica em
[Code-task C1]
```

### 4.3 Heurística "prompt vs. cognição"
- Se a resposta cabe em ≤1 prompt bem-anexado: **prompt**, não estude.
- Se a resposta exige modelo mental novo: **cognição**, Folha Projeto STUDY.

## 5. Links cruzados
- Repo: [[<folha-projeto-no-repo>]]
- Strategics: [[<sonho-em-strategics>]]
- Study topics: [[topico-X]], [[topico-Y]]
- Próxima revisão periódica: [[revisoes/<YYYY-MM>-<sonho>-rev<N>]]

## 6. Próxima Revisão
Quando a Árvore Cognitiva ficar estável (3+ iterações sem novos blockers), promover pra nota separada `cognitive-tree-<TOPIC>.md`.
```

---

### 3.4 Revisão Periódica (NOVO componente — agregador cross-domain)

```markdown
---
tipo: revisao-periodica
revisao_id: REV-<YYYY-MM>-<sonho>-rev<N>
periodo_coberto: YYYY-MM-DD a YYYY-MM-DD
folha_norte_fk: <NK-do-sonho>
proxima_revisao: YYYY-MM-DD
fontes_agregadas:
  - vault/projetos/<folha-projeto>.md
  - vault/study/<topicos>.md
  - data/ikigai/<metricas>.md
---

# 🔄 Revisão Periódica — <sonho> — rev<N>

> **Agregador cross-domain.** Coleta dados de PROJ + STUDY + IKIGAi;
> você dá a narrativa por cima; emite tasklist pro mesh (data/review_queue/).

## 1. Dados Coletados (auto-agregados — NÃO editar manualmente)

### 1.1 Do PROJ (repo)
- Story points entregues: X / Y planejados
- Backlog atualizado: <lista de M's>
- Blockers abertos: <lista>
- Velocity semanal: <X pomodoros/sem>

### 1.2 Do STUDY (Obsidian)
- Tópicos estudados: <lista>
- Notas Feynman entregues: X / N
- Árvore cognitiva atualizada: <sim/não + quais dependências>

### 1.3 Do IKIGAi (métricas)
- Vetor paixão: <Δ>
- Vetor missão: <Δ>
- Vetor vocação: <Δ>
- Vetor profissão: <Δ>
- Q_HE: <valor>

## 2. Narrativa (você escreve)
> "O que senti nesta janela? O que mudou? O que ficou travado? O que
> aprendi sobre mim vs. sobre o problema?"

<texto livre, 1-3 parágrafos>

## 3. Atualização da SOT
- **Folha Norte:** <mudanças em Objetivos / Habilidades / Filtros?>
- **Folha Projeto (próxima):** <carry-over de tópicos / entregáveis>
- **Cognitive Tree:** <novos blockers / novas dependências>

## 4. Próxima Tasklist (output pro mesh)
> Esta tasklist alimenta `data/review_queue/` via `TaskChange`.

```yaml
tasklist:
  - id: id-<ulid>
    descricao: "<ação concreta>"
    cluster: [PROJ | STUDY | PLAN]
    folha_projeto_fk: <PK-do-projeto>
    prazo: YYYY-MM-DD
    bloqueadores_cognitivos: [<lista de dependências>]
```

## 5. Auto-questionamento socrático
- Esta tasklist é REALMENTE a próxima? Ou é wishful?
- Algum item é "ilusão de produtividade" (estudo sem entrega)?
- O que NÃO vou fazer nesta janela (e por quê é OK)?
```

---

## 4. Workflow integrado (atualizado)

### 4.1 Cadência semanal (Folha Projeto no repo)

```
[Dom/Seg]  Abrir Folha Projeto (repo)
            ↓
           Olhar Folha Norte (vault) — prioridades desta semana
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

### 4.2 Cadência semestral (Folha Norte)

A cada 6 meses: revisar Objetivos + Habilidades + Filtros. Mover o que não serve pra `vault/00-norte/arquivados/`.

### 4.3 Cadência da Revisão Periódica

- **Mensal** (recomendado): fecha janela de 30 dias.
- **Trigger alternativo:** quando Árvore Cognitiva atinge 3+ blockers novos.

```
[Mês]      Coleta auto de PROJ + STUDY + IKIGAi
            ↓
           Você escreve narrativa (§2)
            ↓
           Atualiza SOT (§3)
            ↓
           Emite tasklist (§4) → data/review_queue/
            ↓
           IKIGAi agent (Phase 3 mesh) consome + propaga
```

---

## 5. Anti-patterns (atualizado)

- ❌ **Folha Norte no repo:** ilegal (decisão #2). Vai só no vault/Obsidian.
- ❌ **2 arquivos SOT paralelos:** ilegal (decisão #1). É 1 arquivo SOT + review externo.
- ❌ **Folha Projeto com > 4 tópicos:** foco perdido.
- ❌ **Cognitive Tree sem blockers reais:** vira "lista de tópicos de estudo" e perde a amarração com o código.
- ❌ **Revisão Periódica sem narrativa:** vira dashboard morto. A narrativa é o que fecha o loop.
- ❌ **Tasklist sem `folha_projeto_fk`:** task órfã.
- ❌ **Misturar camadas:** Cognitive Tree na Folha Norte, backlog na Folha Norte, etc.

---

## 6. Tensões conhecidas (atualizado)

| Tensão | Status | Próximo passo |
|---|---|---|
| Sincronização repo ↔ vault ↔ Obsidian | Mecanismo já existe (`vault-bidirectional-sync-completion.md`) | Validar que sync suporta 3 vias (repo → vault → Obsidian) |
| Onde mora `vault/inbox/` | Pressuposto pelo método | Criar `vault/inbox/YYYY-MM.md` na primeira semana |
| IKIGAi agent consumindo Revisão Periódica | Phase 3 mesh já tem `agent_consumer` + `agent_propagator` | Especificar adapter que lê §4 (tasklist) e emite `TaskChange` |
| Frontmatter drift | Pivô data-first ativo | Não adicionar chave YAML sem remover outra |

---

## 7. Onde as três versões vivem

- v1 (inventada, não recomendada): `vault/drafts/folha-norte-projeto-META-v1-invented.md`.
- v2 (método conhecido puro): `vault/drafts/folha-norte-projeto-META-v2-known-method.md`.
- **v3 (esta, interseção clusters com matriz travada):** `vault/drafts/folha-norte-projeto-META-v3-interseccao.md`.
- **Spec formal:** `code-docs/specs/2026-09-21-spec-META-NP-folha-norte-projeto.md` (a ser reescrita com matriz travada).

Nenhuma vira fonte de verdade antes de 5+ logs manuais ou aprovação
explícita. **Pivô data-first ativo** (ver `vault/ikigai/meta/AGENTS.md` §3).