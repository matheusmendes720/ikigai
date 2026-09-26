# Folha Norte & Folha Projeto — Draft META v2 (método conhecido)

> **Status:** Working draft (v2 — método "Folha Norte + Folha Projeto" apresentado pelo Matheus).
> **Data:** 2026-09-21.
> **Source:** brainstorm session 2026-09-21, message 2 (input do Matheus descrevendo a metodologia).
> **Audiência:** Matheus + future IKIGAi agents revisando pivô data-first.
> **Convenção:** drafts em `vault/drafts/` são working drafts; só viram fonte de verdade depois de 5+ logs manuais ou aprovação explícita.

---

## 0. Contexto

Na segunda mensagem da sessão de 2026-09-21, o Matheus trouxe a **definição
canônica** do método Folha Norte + Folha Projeto — uma metodologia conhecida
de **gestão do conhecimento e combate ao excesso de informações** (combate à
"ilusão dos estudos").

Esta v2 adere à metodologia tal qual foi descrita, sem inventar campos. A v3
(adicionar interseção com clusters do repo) virá depois.

> Comparação: `folha-norte-projeto-META-v1-invented.md` é a versão que
> Hermes inventou na mensagem 1 (não recomendada). Esta v2 é a versão
> correta do método.

---

## 1. Conceito central (do Matheus)

> "Os conceitos de Folha Norte e Folha Projeto fazem parte de uma metodologia
> de gestão do conhecimento e combate ao excesso de informações. Eles servem
> para alinhar seus objetivos macro de vida e carreira com o que você estuda
> semanalmente, evitando a chamada 'ilusão dos estudos'."

**Camadas do método:**

| Camada | Nome do Arquivo / Pasta | Função Prática no Sistema |
|---|---|---|
| Estratégia | 🧭 Folha Norte.md | Nota central fixada no topo. Contém links para as grandes áreas de conhecimento que você quer dominar. |
| Tática | 📅 Folha Projeto - [Semana X].md | Nota temporária/semanal. Lista as 2 a 4 notas de estudo ativas daquela semana. |
| Execução | MOCs / Notas Atômicas | Onde os resumos reais e conceitos aprendidos são escritos e interligados de forma definitiva. |

---

## 2. Folha Norte (a bússola — visão macro)

> "A Folha Norte atua como a sua bússola. É um documento estático (ou revisado
> raramente, como a cada 6 meses) onde você mapeia a sua estratégia de
> aprendizado de longo prazo. O objetivo principal é definir quais informações
> merecem sua atenção para evitar o consumo passivo e inútil."

**O que contém:**

- **Objetivos Principais:** Onde você quer chegar (ex: passar em um concurso x, virar desenvolvedor sênior, dominar um novo idioma).
- **Habilidades Requeridas:** O que você precisa aprender obrigatoriamente para atingir esses objetivos.
- **Filtros de Atenção:** Critérios claros para dizer "não" a conteúdos que não te alinham ao seu Norte, limitando o desperdício de energia.

**Cadência de revisão:** semestral (6 meses).

### Template

```markdown
---
tipo: folha-norte
norte_id: NK-<YYYYMMDD>-<slug>
criado: YYYY-MM-DD
ultima_revisao: YYYY-MM-DD
proxima_revisao: YYYY-MM-DD        # +6 meses
status: [ativa | pausada | concluida]
---

# 🧭 Folha Norte — <título do objetivo macro>

> **Declaração de Norte (1 frase, presente do indicativo):**
> _"Eu quero <resultado observável concreto>, até <data/idade/marco>."_

## 1. Objetivos Principais
Liste **3-5 objetivos macro** (não recursos — resultados finais).

1. <Objetivo 1>
2. <Objetivo 2>
3. <Objetivo 3>

## 2. Habilidades Requeridas (por objetivo)
Para cada objetivo, quais **habilidades** precisam ser aprendidas.

### Objetivo 1: <título>
- Habilidade A
- Habilidade B
- Habilidade C

### Objetivo 2: <título>
- Habilidade A
- Habilidade B

## 3. Filtros de Atenção (o "não" sistemático — combate à ilusão dos estudos)
**Critérios claros que descartam 95% do que aparece.** Sem esses filtros, qualquer conteúdo "interessante" vaza pra Folha Projeto.

- ❌ Não consumo conteúdo que **não está numa habilidade declarada acima**.
- ❌ Não abro > 3 fontes simultâneas sobre o mesmo tema (anti-overload).
- ❌ Não assisto/leo sem entregar algo (Feynman, código, questão resolvida) em ≤7 dias.
- ✅ Só entra na Folha Projeto o que **avança pelo menos 1 Habilidade Requerida**.
- ✅ Se conteúdo não avança objetivo macro, anoto em `vault/inbox/` e reviso mensalmente.

## 4. Folha(s) Projeto Ativas
_(wiki-links pra notas semanais/mensais em execução)_

- [[Folha Projeto — 2026-S39 — <foco>]]
- [[Folha Projeto — 2026-S40 — <foco>]]

## 5. Revisão Semestral (próxima em YYYY-MM-DD)
Perguntas a responder:
- Algum objetivo macro mudou? (realocação, adição, remoção)
- Alguma habilidade virou irrelevante?
- Algum filtro de atenção não está sendo respeitado?
```

---

## 3. Folha Projeto (a execução micro — semanal ou mensal)

> "A Folha Projeto é o seu plano de ação semanal ou mensal. Ela traduz as
> diretrizes da Folha Norte em blocos práticos de estudo focado. Em vez de
> tentar estudar tudo ao mesmo tempo, você escolhe deliberadamente poucos
> tópicos por ciclo para aplicar o hiperfoco."

**O que contém:**

- **Foco Reduzido:** Seleção estrita de apenas 2 a 4 tópicos ou disciplinas para a semana.
- **Recursos Selecionados:** Livros, aulas ou links específicos que serão esgotados (evitando abrir dezenas de abas no navegador).
- **Entregáveis Práticos:** O que você vai produzir para provar o aprendizado (ex: resolver 50 questões, escrever um resumo usando a Técnica de Feynman, codificar um mini projeto).

**Cadência:** semanal (recomendado) ou mensal.

### Template

```markdown
---
tipo: folha-projeto
projeto_id: PK-<YYYY>-S<WW>-<slug>     # ou YYYY-MM se mensal
periodo: [2026-S39 | 2026-10]
folha_norte_fk: <NK-do-sonho>            # wiki-link [[🧭 Folha Norte — ...]]
criado: YYYY-MM-DD
status: [verde | amarelo | vermelho]
entregaveis_concluidos: [0-de-N]
---

# 📅 Folha Projeto — <período> — <foco do ciclo>

> **Origem:** puxada da [[🧭 Folha Norte — <título>]], habilidades X, Y, Z.

## 1. Foco Reduzido (2-4 tópicos, deliberadamente)
**Máximo 4 tópicos** nesta semana/mês. Tudo que não está aqui fica em `vault/inbox/`.

1. **Tópico A** — vinculado à habilidade X da Folha Norte
2. **Tópico B** — vinculado à habilidade Y
3. **Tópico C** — vinculado à habilidade Z
4. *(opcional)* Tópico D

## 2. Recursos Selecionados (livros, aulas, links — exaurir antes de abrir outros)
Anti-tabs-abertas: liste **≤5 fontes totais** que serão esgotadas neste ciclo.

- 📘 Livro/Curso: <título> — capítulos X-Y
- 🎥 Aula: <URL> — aulas 1-7
- 📄 Artigo: <URL>
- 🛠️ Doc oficial: <URL>

## 3. Entregáveis Práticos (o que prova que aprendeu)
**Cada tópico gera 1 entregável concreto** — sem entrega, o tópico cai do próximo ciclo.

| Tópico | Entregável | Deadline | Status |
|---|---|---|---|
| A | Resumo Feynman (1 página) | sex | ⬜ |
| B | 50 questões resolvidas | qua | ⬜ |
| C | Mini-projeto commit em `code_space/X` | sáb | ⬜ |
| D | Mapa mental + 5 cards Obsidian | dom | ⬜ |

## 4. Hiperfoco Diário (micro-rotina)
Como vou **defender** este foco dos outros 95% de inputs?
- [ ] Bloquear X hora(s) por dia só pra este projeto
- [ ] Desligar notificações de <fontes-ruído>
- [ ] Não abrir `vault/inbox/` durante este ciclo
- [ ] Regra: 1 sessão = 1 tópico, sem paralelo

## 5. Revisão de Fim de Ciclo
_(preencher no domingo/último dia)_

- Entregáveis concluídos: X / N
- O que ficou travado e por quê?
- Algum tópico entra no próximo ciclo? Algum sai?
- O que **NÃO** entrou (mas apareceu como tentação) e por quê foi descartado?
```

---

## 4. Workflow semanal (prescrito pelo método)

1. No início da semana, **abrir a Folha Projeto**.
2. **Olhar para a Folha Norte** pra lembrar quais habilidades são prioridade absoluta.
3. **Puxar 2 ou 3 tópicos** da Folha Norte e jogar como foco da semana na Folha Projeto.
4. Ao estudar, **criar links e anotações apenas para esses temas selecionados**, ignorando distrações de outros assuntos.

---

## 5. Como este método combate a "ilusão dos estudos"

| Mecanismo | Como aparece no template |
|---|---|
| **Filtros de atenção explícitos** | Folha Norte §3 — "dizer não" sistemático |
| **Foco reduzido forçado** | Folha Projeto §1 — "máximo 4 tópicos" |
| **Recursos finitos** | Folha Projeto §2 — "≤5 fontes, exaurir antes de abrir outros" |
| **Entregáveis obrigatórios** | Folha Projeto §3 — "sem entrega, o tópico cai do próximo ciclo" |
| **Anti-tabs-abertas** | Folha Projeto §4 — "1 sessão = 1 tópico" |
| **Revisão periódica** | Folha Norte semestral + Folha Projeto fim-de-ciclo |

---

## 6. Tensões conhecidas (não resolvidas por esta v2)

| Tensão | Onde aparece | Sugestão (não decidido) |
|---|---|---|
| Conflito com `CLUSTER_PROJ.md` (PMO) | Folha Projeto é leve vs SoftwareProject/Epic/Sprint/Task são pesados | Distinção: Folha Projeto = **foco semanal** (O QUE entra na semana); Cluster PROJ = **execução histórica** (O QUE já foi entregue, velocity/burndown). Folha Projeto **linka** 0..N SoftwareProjects. |
| Dashboard de visão de cima | Método não prescreve | Ver `folha-norte-projeto-META-v3-interseccao.md` (v3) |
| Onde mora `vault/inbox/` | Método pressupõe | Criar `vault/inbox/` no Obsidian como parking lot de tentação |
| Como atualizar `vault/00-norte/` no repo | Drafts vs fonte de verdade | Decidir entre v3 (interseção clusters) e mover pra `vault/00-norte/` |

---

## 7. Onde esta v2 vive

- v1 (inventada, não recomendada): `vault/drafts/folha-norte-projeto-META-v1-invented.md`.
- **v2 (esta, método conhecido):** `vault/drafts/folha-norte-projeto-META-v2-known-method.md`.
- v3 (interseção com clusters): `vault/drafts/folha-norte-projeto-META-v3-interseccao.md`.

Nenhuma vira template canônico antes de 5+ logs manuais ou aprovação
explícita. **Pivô data-first ativo** (ver `vault/ikigai/meta/AGENTS.md` §3).