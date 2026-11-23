---
title: Fecho do Q3-2026 — Teste de Fogo e Correção do Trajeto
date: 2026-11-08
status: DECIDIDO
decision_owner: owner
tags: [q3-2026, fecho-de-trimestre, teste-de-fogo, correcao-do-trajeto, cadencia]
related:
  - vault/ikigai/closing-2026/01-q3-2026/01-plano-trimestral/q3-2026-plano-retro.md
  - vault/ikigai/closing-2026/01-q3-2026/03-revisões-semanais/revisao-q3-2026-consolidada.md
  - vault/run-continuation/2026-09-21-master-review-revisited.json
  - strategics/Planejamento (Estratégico e Tático).md
---

# Fecho do Q3-2026 — Teste de Fogo e Correção do Trajeto

> **Decisão.** O Q3-2026 fecha com veredito **PASS aritmético · UNPROVEN
> estratégico**, e abre uma Correção do Trajeto de três itens antes do plano do
> Q4. Não é um veredito de conforto: o número que o método calcula é verde por
> construção, e este documento explica porque é que isso não fecha o trimestre.

---

## 1. O que o método pede

`strategics/Planejamento (Estratégico e Tático).md` §3.1 define o Teste de Fogo
em cinco perguntas, e §3.2 define a Correção do Trajeto:

```
Discrepância = (Metas Concluídas / Metas Planejadas) × 100
Banda aceitável: 70–130 %
< 20 %  → ajuste tático
20–40 % → revisão de metas intermédias
> 40 %  → reavaliação estratégica
```

O mesmo documento datava o Teste de Fogo a **180 dias úteis** (semestre), não a um
trimestre. O fecho do Q3 é, portanto, uma **aplicação parcial** do teste — e isso
fica dito, para o veredito não ser lido como mais do que é.

---

## 2. As cinco perguntas

### P1 — Quantas metas estratégicas permaneceram relevantes após o ciclo?

**Resposta: 1 sobreviveu, e absorveu as outras.**

Antes do pivô de 2026-11-01 o roadmap tinha três frentes: operar TUIs (Fase A),
o harness langgraph (Fase B) e a camada de dados. O pivô
(`2026-11-01-pivot-serverless-canonical-scope.md`) colocou a camada de dados em
primeiro na ordem e mandou as duas outras para standby. Nenhuma meta morreu: a
ordem é que passou a ser única.

Evidência: ADR-037 §D1 (ordem de trabalho) · `tasks.md` §CURRENT FOCUS no commit
`0b0906a1^`.

### P2 — Que percentagem de tarefas diárias contribuiu directamente para o sonho?

**Resposta: `UNKNOWN`.**

Não há sonho escrito para o Q3 (o id `sonho-q3-2026-launch-v1` é citado por três
logs diários; o conteúdo nunca existiu) e não há ledger de tarefas diárias.
Sem denominador declarado, esta percentagem não pode ser calculada — e uma
percentagem inventada seria pior do que a ausência.

### P3 — Que sistemas de apoio falharam mais frequentemente?

**Resposta: a cadência, e só ela.**

| Sistema de apoio | Medida | Falha |
|---|---|---|
| Cadência semanal | 0 revisões em 12 semanas | **100 %** |
| Cadência diária | 3 relatórios em ~60 dias úteis | **95 %** |
| Planos de onda | 0 de 3 escritos | **100 %** |
| Loop de orquestração | 10/10 daemons RUNNING em M80 | 0 % |
| Suíte de drift | 77 → 78 testes durante o trimestre | 0 % |
| CI | verde na janela medida | 0 % |

O padrão é nítido: **a maquinaria que foi construída não falhou; o registo humano
é que nunca existiu.** A auto-maquinaria tem daemons; a cadência não tinha um.

### P4 — Qual a relação custo-benefício média das actividades?

**Resposta: parcial.**

704 commits em 12 semanas, concentrados em 5. O custo em tempo é `UNKNOWN` (não há
horas registadas). O custo em dinheiro está registado de forma incompleta:
`progress.md` fechava 8 ticks com **USD 1,80** acumulados a 2026-09-07 — um valor
que cobre o loop, não o trabalho de sessão.

Uma leitura possível, e é a que interessa: **704 commits por 1,80 USD de
automação é barato; 704 commits sem uma única revisão é caro** — porque ninguém
sabe quais dos 704 pagaram o trimestre.

### P5 — Quantas correcções significativas foram necessárias, e que lições?

**Resposta: 2, e ambas foram de âmbito, não de execução.**

| # | Data | Correção | Evidência |
|---|---|---|---|
| 1 | 2026-09-03 | *algorithm gate dropped* — a camada algorítmica sai da frente, data-first passa à frente | `[[algorithm-gate-dropped-2026-09-03]]` |
| 2 | 2026-11-01 | pivô para escopo canónico serverless: TUI, MCP stdio e o harness langgraph saem do remoto | `2026-11-01-pivot-serverless-canonical-scope.md` |

Lição que as duas partilham: **o trabalho estava a ser feito na direcção certa e na
ordem errada.** Nenhuma das correcções mudou o que se queria; mudaram o que se
fazia primeiro.

---

## 3. O cálculo, e porque não fecha

| | |
|---|---:|
| Metas planejadas (roadmap em 2026-09-27, `26e208da`) | **110** |
| Metas concluídas (`STATUS: DONE`) | **98** |
| Discrepância | **98 / 110 = 89,1 %** |
| Banda do método | 70–130 % |
| Leitura aritmética | dentro da banda ⇒ sem problema sistémico |

O número está certo e **não pode ser usado como veredito**, por três razões
medidas:

1. **As metas eram auto-promovidas durante o trimestre.** O roadmap escreve
   `Auto-promoted by: human authorization`. Uma meta que nasce do trabalho que já
   se ia fazer tem taxa de sucesso perto de 100 % por desenho.
2. **Sete das doze semanas não tinham plano em vigor.** Não há meta a falhar onde
   não há plano.
3. **O rácio é estável por construção.** Em 2026-11-05 o roadmap tinha 143 metas e
   115 concluídas = 80,4 %. Acrescentar metas e fechá-las mantém o indicador em
   ~80 % para sempre, independentemente do que o trimestre serviu.

**Veredito: `PASS` aritmético, `UNPROVEN` estratégico.** O Q3 entrega execução
provada (704 commits, 21 ADRs, 78 testes de drift) e cadência não-provada
(0 revisões). O que falhou não é o que se fez — é o que se decidiu sobre o que se
fez.

---

## 4. Correção do Trajeto (antes do plano do Q4)

O método manda corrigir antes de abrir o trimestre seguinte. Três correções, cada
uma com um PASS falsificável.

### C1 — A unidade de registo passa a ser a rajada

**Porquê:** a produção real tem semanas a zero e semanas a 224 commits. Uma rotina
diária contra esse formato produz 7 notas vazias ou nenhuma nota.

**O que muda:** o registo mínimo é **um por rajada** (semana com commits > 0), e a
revisão semanal só é exigida em semanas com atividade. Semanas a zero registam-se
com uma linha, não com uma nota.

**PASS:** ao fim de 4 semanas, existe uma revisão por cada semana com commits > 0,
e zero revisões em semanas a zero. Falsifica-se contando os ficheiros em
`02-q4-2026/03-revisões-semanais/`.

### C2 — O plano do trimestre tem denominador fixo

**Porquê:** 89,1 % mede auto-consistência porque o denominador cresceu com o
trabalho. Sem denominador fixo, o Teste de Fogo seguinte dará o mesmo verde.

**O que muda:** as metas do trimestre são escritas **no início** e o plano só
cresce por adição explícita e datada, com o motivo. Uma meta acrescentada a meio
entra no numerador mas **não** no denominador do trimestre em curso.

**PASS:** o plano Q4 v2 declara N metas na data de abertura; qualquer adição
posterior tem data e motivo; o fecho calcula o rácio contra N.

### C3 — O sonho do trimestre existe como artefacto, ou o trimestre não abre

**Porquê:** o Q3 serviu a `sonho-q3-2026-launch-v1`, um id sem conteúdo. Sem ele,
a P2 do Teste de Fogo é permanentemente `UNKNOWN`.

**O que muda:** nenhum trimestre abre sem um `00-sonho/<slug>.md` com uma frase no
presente do indicativo e uma data-limite.

**PASS:** `02-q4-2026/00-sonho/` contém um ficheiro com `norte_id` ou declaração
equivalente, e o plano Q4 v2 cita-o.

---

## 5. O que isto desbloqueia

| Antes | Depois desta decisão |
|---|---|
| Q3 sem fecho | fecho registado, com evidência e com os `UNKNOWN` nomeados |
| Q4 a correr sem base | plano Q4 v2 com denominador fixo e cadência de rajada |
| Teste de Fogo não reprodutível | três PASS falsificáveis para o fecho do Q4 |
| 0 revisões em 5 meses | primeira revisão escrita no mesmo dia (W45) |

---

*Registo append-only — 2026-11-08. Não substitui nem edita o plano de 2026-08-28
em `02-q4-2026/01-plano-trimestral/deep-agent-build-q4-2026.md`, que fica como
estava.*
