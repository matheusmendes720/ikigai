---
tipo: discovery-log-backlog
template_version: 1.0
slug_referencia: calistenia-base
folha_projeto_fk: vault/projetos/2026-S39-calistenia-base.md
perfil_de_uso: fisico
data: 2026-09-21
autor: agente-rascunho               # RASCUNHO — humano revisar antes de commitar
---

# 📋 Discovery Log — backlog — 2026-09-21 — calistenia-base

> **Status:** RASCUNHO — gerado automaticamente a partir da Folha Projeto + contexto. Marcar `[CONFIRMADO]` em cada item após revisar.
>
> **Intenção:** diário de bordo operacional da **primeira sessão do ciclo S39** (semana de setup). Aqui só cabe **o que rolou hoje**.

---

## 1. Sessão (factual)

**Quando:** 2026-09-21 (segunda-feira)
**Onde:** sessão de planejamento (não foi treino físico ainda — foi trabalho de estruturação do projeto)
**Qual tópico da Folha Projeto:** **N/A — sessão de setup, pré-execução.** Esta sessão definiu a Folha Norte + Folha Projeto + os 3 tópicos (A, B, C) que serão executados durante a semana S39.

---

## 2. O que testei / observei

> Fatos do dia — sem opinião.

- **Não houve teste físico ainda** (segunda de setup, sem treino planejado pra hoje).
- **Não houve medição** (max reps, RPE, tempo de hold) — esses serão coletados a partir de quarta (entregável A).
- Foi feita **inspeção de estrutura do repo `workout/`** (em `~/code_space/workout/`) — existem 6 subdiretórios candidatos pra tracking (base, biomechanics-shell, exercises-dataset, openGym, tracker-app, 1 PDF). Nenhum ainda escolhido como host do tracker.
- Foi criada **a Folha Norte** (`vault/00-norte/calistenia-campeao.md`) com 4 objetivos macro + 14 habilidades requeridas + 7 filtros de atenção.
- Foi criada **a Folha Projeto semanal** (`vault/projetos/2026-S39-calistenia-base.md`) com foco em 3 tópicos (avaliação baseline + periodização semanal + mobilidade diária 10min).
- Foram criados **3 templates de Discovery Log** em `notes/_templates/` — backlog (agente), reflexão (humano), README (hub).

---

## 3. Decisões tomadas

> Decisões concretas (não aspirações).

- [ ] **[CONFIRMADO]** **Onde vai morar o tracker calistenia:** ainda não decidido. Candidatos: `~/code_space/workout/tracker-app/` (existente, mais óbvio) ou criar do zero como projeto novo. **Pendência: usuário decide.**
- [ ] **[CONFIRMADO]** **Priorizar saúde articular sobre ganho rápido:** filtro de atenção §3 da Folha Norte veta treinamento alta intensidade > 4x/semana. Decisão alinhada com vetor IKIGAi `paixao` mas regulada por prudência.
- [ ] **[CONFIRMADO]** **Sem Pomodoro neste Folha Projeto:** §9 da Folha Projeto ajustada pra bloco contínuo 60-90min (calistenia ≠ cognição). Customização que vai ser aplicada como `perfil_de_uso: fisico` no frontmatter da v3.
- [ ] **[CONFIRMADO]** **3 tópicos focados (não 4):** Folha Norte autoriza 2-4. Optei por 3 pra começar com menos superfície — adicionar tópico D só se sobrar fôlego na sexta.
- [ ] **[CONFIRMADO]** **Mapeamento explícito com Clusters:** Folha Norte §4 registra que treino ocupa `bloco_manha` (CLUSTER_PLAN), **não** usa SoftwareProject/Epic/Sprint (CLUSTER_PROJ), e tem skill gap em biomecânica básica (CLUSTER_STUDY → `vault/study/biomec/`).

---

## 4. Ajustes / Programação que ficou

| Item | Estado final |
|---|---|
| Estrutura do ciclo | S39 = "base/foundation week" (semana de setup, sem PRs) |
| Recursos selecionados | 3 fontes (limite era ≤5): Overcoming Gravity caps 1-3, 1 artigo S&C 2023, Tom Merrick Flexibility playlist 1-5 |
| Notas de estudo a criar | 3: `vault/study/biomec/avaliacao-baseline.md`, `periodizacao-semanal.md`, `mobilidade-diaria.md` (NÃO criadas ainda) |
| Templates de log | 3 templates em `notes/_templates/` prontos |
| Calendário | qua = baseline, qui = periodização tabela, sáb = mobilidade gravada |

---

## 5. Próxima sessão (continuidade)

- **Amanhã (ter, 2026-09-22):** revisar este rascunho de backlog, marcar itens como `[CONFIRMADO]` ou ajustar.
- **Quarta (qua, 2026-09-23):** **avaliação baseline** — medir max reps em push-up, pull-up, dip, squat, hinge. Escrever planilha resultante + `vault/study/biomec/avaliacao-baseline.md`.
- **BLOQUEADOR PENDENTE:** decidir onde vai morar o tracker (recurso físico/digital pro registro de tonelagem). Sem essa decisão, o entregável A vira planilha avulsa em `~/Downloads/` e quebra o ciclo de log.

---

## Notes para o agente futuro

> Se você (agente) está lendo este log:

- Este é o **primeiro backlog de uma Folha Projeto real**, gerado em rascunho pela sessão de brainstorm META-NP. Está marcado `autor: agente-rascunho` — o humano **precisa revisar e marcar `[CONFIRMADO]`** antes de commit.
- O log §3 tem uma decisão explicitamente pendente (`tracker-host decision`) marcada com "**Pendência: usuário decide.**". Se você for um agente futuro, **não** tome essa decisão sozinho; pergunte.
- O log §5 lista BLOQUEADOR PENDENTE em maiúsculas — preserve.

---

## Cross-references

- Folha Projeto: `vault/projetos/2026-S39-calistenia-base.md`
- Folha Norte: `vault/00-norte/calistenia-campeao.md`
- Templates sibling: `notes/_templates/README.md`, `reflexao.md.template`