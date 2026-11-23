---
type: plano
quarter: 2026-Q3
date: 2026-11-08
status: reconstruido
proveniencia: evidencia-do-repositorio
companion: placeholder.md
---

# Q3-2026 — Plano trimestral, reconstruído a partir de evidência

> **Porque este ficheiro existe.** O Q3-2026 correu de 2026-07-06 a 2026-09-27
> **sem plano trimestral escrito**. Este documento não é o plano que o trimestre
> teve — é o **registo do plano que estava em vigor**, levantado a 2026-11-08 a
> partir de evidência datada, e não de memória. Onde a evidência não chega, o
> campo diz `UNKNOWN`; não é preenchido por inferência.
>
> É um ficheiro novo. O `placeholder.md` irmão fica como está (append-only).

---

## 1. Qual era o plano, e onde estava

O plano do trimestre nunca esteve no vault. Esteve em `.claude/loop/roadmap.md`,
apagado em `0b0906a1` (2026-11-05) e recuperável em:

```
git show 0b0906a1^:.claude/loop/roadmap.md
git show 0b0906a1^:.claude/loop/tasks.md
```

É a única fonte com denominador. Tudo o que este documento afirma sobre metas
sai dela.

| Atributo (em 2026-09-27) | Valor |
|---|---:|
| Metas no registo | **110** |
| `STATUS: DONE` | **98** |
| Sem estado declarado | 11 |
| `PUBLISHED` | 1 |
| Taxa registada | **98 / 110 = 89,1 %** |

O roadmap auto-promovia metas (`Auto-promoted by: human authorization`). Isso
importa para o §6.

---

## 2. A janela, e a atividade que a preencheu

O `README.md` do trimestre declara 13 semanas (W28–W40, 2026-07-06 → 2026-09-27).
Medido: W28 começa em 2026-07-06 e W39 termina em 2026-09-27 — são **12 semanas
ISO**, não 13. A décima terceira (W40) já é 2026-09-28 → 2026-10-04, dentro do Q4.

| Semana ISO | Datas | Commits | Leitura |
|---|---|---:|---|
| W28 | 07-06 → 07-12 | 0 | — |
| W29 | 07-13 → 07-19 | 0 | — |
| W30 | 07-20 → 07-26 | 0 | — |
| W31 | 07-27 → 08-02 | 0 | — |
| W32 | 08-03 → 08-09 | 0 | — |
| W33 | 08-10 → 08-16 | 0 | — |
| W34 | 08-17 → 08-23 | 0 | — |
| **W35** | 08-24 → 08-30 | **224** | o merge de sessão (`gateway + B1–B8 + Q1–Q4 + Fases A/E/H/I`, 2026-08-27) |
| **W36** | 08-31 → 09-06 | **119** | loop-engineering a arrancar |
| **W37** | 09-07 → 09-13 | **104** | milestones M4–M80 |
| **W38** | 09-14 → 09-20 | **174** | pico |
| **W39** | 09-21 → 09-27 | **83** | fecho: M148 (`26e208da`, 2026-09-27) |
| **Total Q3** | | **704** | |

**O facto que organiza o trimestre: as primeiras 7 semanas tiveram zero commits, e
as 704 entregas estão todas em 5 semanas.** O trimestre não foi executado em
cadência; foi executado em rajada, um mês depois de começar.

Distribuição temática dos 704 commits: `loop` 186 · sem escopo 89 · `adr` 29 ·
`backtest` 26 · `mesh` 23 · `ikigai` 23 · `cli` 20 · `contracts` 13.

---

## 3. O que o trimestre entregou

Agrupado por linha, com a evidência que o prova:

| Linha | Entrega | Evidência |
|---|---|---|
| Loop de orquestração | M0–M80: daemon, cost dashboard, notificação multi-canal, hill-climb v2, cron de cadências | `feat(loop): M4…M80` |
| Ponte taskdog ↔ IKIGAI | M142–M148: 6 tools de leitura, tools de escrita, spans OTel, binding de produção | `feat(loop): M142…M148` |
| Gateway + mesh | B1–B8, Q1–Q4, Fases A/E/H/I num único merge de sessão | `2026-08-27 full session merge` |
| Governança | 7 → 21 ADRs no trimestre | master review 2026-09-21 |
| Specs | série `docs/superpowers/specs/` | commits `docs(specs)` |

---

## 4. O que o trimestre não entregou

Não por falha de execução — por ausência de plano do lado humano:

| Previsto pelo scaffold | Estado em 2026-09-27 |
|---|---|
| `00-sonho/` com o sonho do trimestre | `placeholder.md` — **nunca escrito** |
| `01-plano-trimestral/` | este ficheiro, escrito a 2026-11-08 |
| `02-onda-1..3/` | três `placeholder.md` |
| `03-revisões-semanais/` — 12 a 13 revisões | **0 de 12** |
| `04-relatórios-diários/` — ~60 relatórios | 3 (`2026-09-05/06/07`), de um gate «1/5 · 2/5» que nunca chegou a 5 |

A cadência do lado humano não falhou parcialmente: **nunca arrancou.**

---

## 5. UNKNOWN — o que só o dono sabe

Estes campos não têm evidência no repositório e ficam abertos até o dono os
escrever. Não foram inferidos de propósito.

| Campo | Estado |
|---|---|
| A intenção declarada do trimestre, nas palavras do dono | `UNKNOWN` |
| O sonho a que o Q3 servia (`sonho-q3-2026-launch-v1`, citado nos 3 logs diários) | `UNKNOWN` — o id existe, o conteúdo não |
| Metas pessoais fora de código (corpo, estudo, trabalho) | `UNKNOWN` |
| Horas investidas no trimestre | `UNKNOWN` |
| Custo acumulado | parcial — `progress.md` registava USD 1,80 em 8 ticks a 2026-09-07 |

---

## 6. Nota de método — porque é que os 89,1 % não provam nada

O Teste de Fogo do método calcula `(metas concluídas / metas planejadas) × 100`
e aceita a banda 70–130 %. O Q3 mede **89,1 %**, ou seja, dentro da banda.

O número é verdadeiro e não significa o que parece:

1. **O denominador cresceu com o trabalho.** As metas eram auto-promovidas
   enquanto se executava. Uma meta que nasce do trabalho que já se ia fazer não
   pode falhar. O rácio mede auto-consistência, não execução estratégica.
2. **O plano só existe em 5 das 12 semanas.** As 7 semanas a zero não têm meta
   nenhuma a falhar, porque não havia plano onde falhar.
3. **O trimestre seguinte herdou 33 metas novas** (110 → 143 em 2026-11-05) e
   fechou 17 delas — o rácio fica perto de 80 % para sempre, por construção.

Conclusão que este documento fixa: **o Q3 fechou em execução e falhou em
cadência.** O que não existiu não foi produção — foi o sistema que a transforma
em decisão.

O veredito e a Correção do Trajeto estão em
`vault/ikigai/decisions/2026-11-08-fecho-q3-teste-de-fogo.md`.

---

*Ficheiro novo, 2026-11-08 — reconstrução por evidência autorizada pelo dono na
mesma data. Não substitui o `placeholder.md` nem o edita.*
