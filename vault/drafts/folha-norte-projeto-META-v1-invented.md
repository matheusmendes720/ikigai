# Folha Norte & Folha Projeto — Draft META v1 (inverted model)

> **Status:** Working draft (v1 — invented by Hermes).
> **Data:** 2026-09-21.
> **Source:** brainstorm session 2026-09-21, message 1.
> **Audiência:** Matheus + future IKIGAi agents revisando pivô data-first.
> **Convenção:** drafts em `vault/drafts/` são working drafts; só viram fonte de verdade depois de 5+ logs manuais ou aprovação explícita.

---

## 0. Origem deste draft

Na sessão de brainstorm de 2026-09-21, o Matheus pediu um meta-modelo que
funcionasse como **adhoc para os outros sub-sistemas** — uma "visão de cima
do tabuleiro" onde cada peça do quebra-cabeça (projeto) tem seu estado de
progresso visível em direção à missão designada.

Como resposta inicial, **Hermes inventou** um modelo Folha Norte + Folha
Projeto baseado no que parecia razoável para um framework PMO já existente
em `CLUSTER_PROJ.md`. Este draft preserva aquela primeira tentativa **antes
do método conhecido** chegar, para comparação posterior.

> **Atenção:** este modelo **NÃO é a versão recomendada**. Foi superado pelo
> método descrito em `folha-norte-projeto-META-v2-known-method.md` (v2) e
> pela interseção com clusters em `folha-norte-projeto-META-v3-interseccao.md` (v3).
> Mantido aqui apenas para histórico e para mostrar a diferença entre
> **inventar** e **aderir a uma metodologia conhecida**.

---

## 1. Hierarquia conceitual (v1, inventada)

```
┌──────────────────────────────────────────────────────┐
│ SONHO (1 por sonho-realização-pessoal)               │
│   vault/00-norte/<slug-do-sonho>.md                  │
│   - chave primária do meta-modelo                    │
└──────────────┬───────────────────────────────────────┘
               │ FK: sonho
       ┌───────┴───────┐
               ▼               ▼
┌──────────────┐  ┌──────────────┐
│ Folha        │  │ Folha        │  (1 projeto = 1 nota)
│ Projeto #1   │  │ Projeto #N   │
└──────┬───────┘  └──────┬───────┘
       │ FK: projeto     │
       ▼                 ▼
┌──────────────┐  ┌──────────────┐
│ Backlog      │  │ Backlog      │  (estrutura já existe em
│ Épico/Sprint │  │              │   CLUSTER_PROJ.md §2)
│ Task TW      │  │              │
└──────────────┘  └──────────────┘
```

**Princípios desta versão:**

- Folha Norte = chave primária (sonho + chave estrangeira que ancora tudo).
- Folha Projeto = chave estrangeira prática (1 nota por SoftwareProject).
- Status semáforo (verde/amarelo/vermelho).
- Campos extensos (8 por folha) com métricas PMO (RICE, velocity, ROI R$/ano).
- Dashboard web renderizado a partir do parse do frontmatter.

---

## 2. Template Folha Norte (v1)

```markdown
---
tipo: folha-norte
sonho_id: NK-<YYYYMMDD>-<slug>          # chave primária
criado: YYYY-MM-DD
vetor_ikigai: [paixao | missao | vocacao | profissao]
status: [verde | amarelo | vermelho]
estagio: [sonar | dream | build | ship | honor]
ultima_atualizacao: YYYY-MM-DD
projetos_vinculados: [] # FKs → Folha Projeto
---

# 🌟 Sonho: <título humano>

> **Pergunta-âncora** (declarar em 1 frase no presente do indicativo, como se já
> estivesse acontecendo — técnica do "sonho acordado"):
> _"Até <data>, eu <ação concreta que demonstra o sonho realizado>."_

## 1. Declaração de Propósito (o "porquê" visceral)
Por que esse sonho? O que dói hoje que ele resolve? O que se ganha em 1 ano,
3 anos, 10 anos? **Quantificar o custo de não-agir em R$/ano ou unidade
concreta** (saúde, tempo, renda, reconhecimento).

## 2. Vetor IKIGAi predominante
Qual(is) dos 4 vetores? Se múltiplos, ordenar por peso. **Justificar em 2-3
linhas** cada.

## 3. Anti-visão (o que acontece se eu NÃO agir)
3 bullets do pior cenário realista em 1, 3 e 10 anos. Incluir custo mensurável.

## 4. Marcos-Farol (3-5 faróis de longo prazo)
Datas aproximadas + descrição do estado observável que confirma o sonho vivo.

## 5. Estado Atual (snapshot a cada revisão)
| Métrica | Valor | Δ vs última |
|---|---|---|
| Estágio | build | ↑ dream → build |
| Velocity 90d | X.X pomodoros/sem | +0.3 |
| Última sessão | YYYY-MM-DD | -2d |
| Saúde (subj.) | 7/10 | = |

## 6. Projetos Vinculados
(Lista de FKs que apontam pra Folha Projeto; cada uma é uma frente de ataque
concreta ao sonho)

- [[folha-projeto-<slug-1>]] — descrição de 1 linha
- [[folha-projeto-<slug-2>]] — descrição de 1 linha

## 7. Custo de Inação (R$/ano ou unidade concreta)
> A maior alavanca de persuasão. Atualizar a cada 90 dias com dados reais.

## 8. Próxima Revisão
Data + ritual (sugestão: semanal d7 + wave-end d15 + mensal d30).
```

---

## 3. Template Folha Projeto (v1)

```markdown
---
tipo: folha-projeto
projeto_id: PK-<YYYYMMDD>-<slug>          # chave primária
sonho_fk: <NK-do-sonho-vinculado>         # FK obrigatória → Folha Norte
criado: YYYY-MM-DD
estagio: [sonar | dream | build | ship | honor]
status: [verde | amarelo | vermelho]
vetor_ikigai: [paixao | missao | vocacao | profissao]
ultima_sessao: YYYY-MM-DD
proximo_marco: YYYY-MM-DD
custo_nao_agir_r$: <valor_estimado>/ano
---

# 🎯 Projeto: <título>

> **Discovery Coding** (a motivação real por trás — link ao post do Jimmy Miller
> ou ao seu próprio texto-manifesto): por que esse projeto EXISTE? O que ele
> destrava no sonho-raiz?

## 1. Declaração de Propósito
Frase de 1 linha em presente do indicativo. O "quê" concreto.

## 2. Estado Atual vs Roadmap (o coração da folha)
### 2.1 Status por Módulo
| Módulo | Status | Última | Próxima |
|---|---|---|---|
| input-tracker (sets/reps/tonelagem) | build | YYYY-MM-DD | YYYY-MM-DD |
| postura-cv (visão computacional) | dream | — | — |
| simulador-3d (biomecânica) | sonar | — | — |

### 2.2 Backlog (story points / prioridade / dependência)
- [ ] **M1 — input-tracker**: registrar sets, reps, tempo, RPE → CSV/SQLite
  - story points: 5
  - prioridade: alta (bloqueia M2)
  - dependência: nenhuma
  - épico pai: epic-periodizacao
- [ ] **M2 — tonelagem-diária**: subtotais tensão + sobrecarga em kg·reps
  - story points: 8
  - prioridade: alta
  - dependência: M1
- [ ] **M3 — postura-cv**: classificar movimentos calistênicos
  - story points: 21
  - prioridade: média
  - dependência: nenhuma
- [ ] **M4 — simulador-3d**: rig biomecânico Three.js
  - story points: 34
  - prioridade: baixa
  - dependência: M3

### 2.3 Changelog vs Roadmap
| Data | Commit/Issue | Roadmap batia? | Desvio |
|---|---|---|---|
| YYYY-MM-DD | feat: input-tracker M1 | sim | — |
| YYYY-MM-DD | docs: tonelagem-formula | não | +2d (descoberta de unidade) |

### 2.4 Velocity & Ritmo
- Pomodoros/semana: X
- Story points entregues/sprint: Y
- Última sprint: Z pontos / W planejados

## 3. User Stories (o "pra quê" humano)
_(linkar à fonte original, ex: Jimmy Miller discovery coding)_
- Como atleta, quero registrar sets/reps pra ver evolução sem planilha.
- Como atleta, quero detecção de postura pra corrigir em tempo real.
- Como atleta, quero simulação biomecânica pra entender overloading.

## 4. Métricas de Progresso (KPIs)
| KPI | Meta | Atual | Δ |
|---|---|---|---|
| Módulos M1-M4 done | 100% | 25% | +25% |
| Tonelagem/semana média | Xkg | Ykg | +Z% |
| Sessões de CV anotadas | 30 | 8 | +8 |

## 5. Risco Atual (1-2 frases)
O que pode travar? Qual decisão precisa ser tomada?

## 6. Próximo Marco (data + entrega observável)
> "Até YYYY-MM-DD, M2 (tonelagem-diária) está funcional, com 1 semana de
> dados reais persistidos e curva de sobrecarga plotada."

## 7. Custo de Inação (R$/ano ou unidade concreta)
> Quantificar: "Sem isso, fico X meses/anos sem saber se overtraining está
> corroendo articulação. Custo: 1 cirurgia joelho ≈ R$15k + 6mo parado."

## 8. Próxima Sessão (link → primeira entrada no dataset entre sessões)
_(link para `data/session-YYYY-MM-DD.md` ou note da sessão)_
```

---

## 4. Web App (dashboard de visão de cima) — proposto na v1

| Camada | Tech | Justificativa |
|---|---|---|
| Frontend | Svelte + Vite OU HTML+CSS cru (Tailwind CDN) | Mobile + desktop, sem build pesado |
| Backend | FastAPI (Python) | Já existe `life` em Python; 1 rota `/projetos` lê YAML/markdown |
| Fonte da verdade | `vault/00-norte/*.md` + `vault/00-norte/projetos/*.md` (parse frontmatter) | Append-only do Obsidian + leitura pelo app |
| Deploy local | `uvicorn` em background; nginx/cloudflared pro mobile | Custo zero |

**Mínimo dashboard:**
1. Cabeçalho do sonho-raiz ativo (status, vetor IKIGAi, próximo marco).
2. Grid de projetos (1 card por Folha Projeto) com semáforo.
3. Linha do tempo das últimas 5 sessões (links).
4. Custo de inação agregado (R$/ano somado).

---

## 5. Tensões que esta versão NÃO resolveu (mas a v2 resolve)

| Tensão | v1 | v2 |
|---|---|---|
| Folha Projeto vs Cluster PROJ | Conflito (Folha Projeto pesada + PMO já tem épicos/sprints) | Distinção clara: Folha Projeto = foco semanal leve; Cluster PROJ = execução histórica |
| Campos da Folha Projeto | 8 (pesado) | 3 (foco reduzido / recursos / entregáveis) |
| Filtro de atenção | Ausente (qualquer coisa entrava) | **Eixo central da Folha Norte** (filtros do "não") |
| Cadência de revisão | Não declarada | Semestral (Folha Norte) + semanal/mensal (Folha Projeto) |
| Hiperfoco | Não modelado | **Campos "Foco Reduzido" e "Hiperfoco Diário"** explícitos |

---

## 6. Onde esta v1 vive

- Este draft: `vault/drafts/folha-norte-projeto-META-v1-invented.md` (esta nota).
- v2 (método conhecido): `vault/drafts/folha-norte-projeto-META-v2-known-method.md`.
- v3 (interseção com clusters): `vault/drafts/folha-norte-projeto-META-v3-interseccao.md`.

Nenhuma vira template canônico antes de 5+ logs manuais ou aprovação
explícita. **Pivô data-first ativo** (ver `vault/ikigai/meta/AGENTS.md` §3).